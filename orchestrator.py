"""
Orchestrator Agent - Central Controller

This module manages the sequential execution of all sub-agents,
handles data flow, implements the character count validation loop,
and oversees error handling and retry logic.

Key Responsibilities:
- Initialize run directory with unique ID
- Execute agents in correct sequence
- Maintain circuit breaker state
- Implement character count loop (Writer -> Reviewer -> validation)
- Create run_failed.json on abortion
- Aggregate metrics (optional)
"""

import json
import time
import traceback
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Callable

from core.run_context import create_run_dir, get_artifact_path
from core.retry import CircuitBreaker, execute_with_retries, CircuitBreakerTrippedError
from core.persistence import write_and_verify_json, atomic_write_text, count_chars
from core.errors import (
    BaseAgentError,
    ValidationError,
    DataNotFoundError,
    CorruptionError,
)
from core.logging import log_event
from core.cost_tracking import CostTracker

# Import all agents
from agents import (
    topic_agent,
    research_agent,
    prompt_generator_agent,
    writer_agent,
    reviewer_agent,
    image_prompt_agent,
    image_generator_agent,
)


class Orchestrator:
    """
    Central orchestration agent for the LinkedIn post generation pipeline.

    Attributes:
        config (dict): Configuration with field selection
        run_id (str): Unique identifier for this run
        run_path (Path): Path to run directory
        circuit_breaker (CircuitBreaker): Failure tracking across agents
        context (dict): Shared context for all agents
        metrics (dict): Aggregated performance metrics
    """

    MAX_CHAR_COUNT = 3000
    TARGET_CHAR_COUNT = 2950
    MAX_CHAR_LOOP_ITERATIONS = 5
    MAX_TOPIC_PIVOTS = 2

    def __init__(self, config: dict):
        """
        Initialize orchestrator with configuration.

        Args:
            config (dict): Configuration dictionary with field selection

        Raises:
            ValidationError: If config is invalid
        """
        if not config or "field" not in config:
            raise ValidationError("Configuration must include 'field'")

        self.config = config
        self.run_id = None
        self.run_path = None
        self.circuit_breaker = CircuitBreaker()
        self.cost_tracker = CostTracker()  # Initialize cost tracking
        self.context = {}
        self.metrics = {
            "start_time": None,
            "end_time": None,
            "total_duration_ms": 0,
            "agent_metrics": {},
            "char_loop_iterations": 0,
            "topic_pivots": 0,
        }

    def run(self) -> Dict[str, Any]:
        """
        Execute the complete pipeline.

        Returns:
            dict: Final run summary with status and artifact paths

        Raises:
            Various exceptions on failure (captured and logged)
        """
        self.metrics["start_time"] = datetime.now().isoformat()
        start_time = time.time()

        try:
            # Phase 5.1: Configuration & Initialization
            self._initialize_run()

            # Phase 5.3: Sequential Agent Pipeline (7 steps)
            # Step 1: Topic Selection
            topic = self._execute_topic_selection()
            # Step 2: Research with pivot fallback
            research_data = self._execute_research_with_pivot(topic)
            # Step 3: Prompt Generation (Strategic Content Architect)
            structured_prompt = self._execute_prompt_generation(topic, research_data)

            # Phase 5.4: Character Count Validation Loop
            # Step 4-5: Writing and Review with character limit enforcement
            final_post = self._execute_writing_and_review_loop(structured_prompt)

            # Phase 5.5: Image Generation Pipeline
            image_prompt = self._execute_image_prompt_generation(final_post)
            self._execute_image_generation(image_prompt)

            # Phase 5.6: Run Completion
            return self._complete_run_success(final_post)

        except (
            CircuitBreakerTrippedError,
            ValidationError,
            CorruptionError,
            DataNotFoundError,
        ) as e:
            return self._handle_run_failure(e, traceback.format_exc())
        except Exception as e:
            return self._handle_run_failure(e, traceback.format_exc())
        finally:
            end_time = time.time()
            self.metrics["end_time"] = datetime.now().isoformat()
            self.metrics["total_duration_ms"] = int((end_time - start_time) * 1000)

    def _initialize_run(self) -> None:
        """Initialize run directory, context, and save config (Phase 5.1)."""
        # Create unique run directory
        self.run_id, self.run_path = create_run_dir()

        # Set up shared context for all agents
        self.context = {
            "run_id": self.run_id,
            "run_path": self.run_path,
            "cost_tracker": self.cost_tracker,  # Add cost tracker to context
        }

        # Save config to run directory
        config_path = get_artifact_path(self.run_path, "00_config")
        write_and_verify_json(config_path, self.config)

        log_event(self.run_id, "initialization", 1, "ok")

    def _execute_agent_with_retry(
        self,
        agent_name: str,
        agent_func: Callable,
        input_obj: Dict[str, Any],
        max_attempts: int = 3,
    ) -> Dict[str, Any]:
        """
        Execute agent with retry logic and circuit breaker (Phase 5.2).

        Args:
            agent_name: Human-readable agent name for logging
            agent_func: Agent's run() function
            input_obj: Input dictionary for agent
            max_attempts: Maximum retry attempts

        Returns:
            Agent response envelope

        Raises:
            BaseAgentError: On failure after retries
            CircuitBreakerTrippedError: If circuit breaker trips
        """
        agent_start = time.time()

        def _wrapped_call():
            response = agent_func(input_obj, self.context)

            # Check response status
            if response.get("status") == "error":
                error_info = response.get("error", {})
                error_type = error_info.get("type", "UnknownError")
                error_msg = error_info.get("message", "No error message")
                retryable = error_info.get("retryable", False)

                # Reconstruct exception from response
                if error_type == "ValidationError":
                    raise ValidationError(error_msg)
                elif error_type == "DataNotFoundError":
                    raise DataNotFoundError(error_msg)
                elif error_type == "CorruptionError":
                    raise CorruptionError(error_msg)
                else:
                    # Generic retryable error
                    raise BaseAgentError(error_msg, retryable=retryable)

            return response

        try:
            response = execute_with_retries(
                _wrapped_call,
                max_attempts=max_attempts,
                circuit_breaker=self.circuit_breaker,
            )

            # Record metrics
            agent_duration = int((time.time() - agent_start) * 1000)
            self.metrics["agent_metrics"][agent_name] = {
                "duration_ms": agent_duration,
                "status": "success",
            }

            return response

        except BaseAgentError as e:
            agent_duration = int((time.time() - agent_start) * 1000)
            self.metrics["agent_metrics"][agent_name] = {
                "duration_ms": agent_duration,
                "status": "failed",
                "error": str(e),
            }
            raise

    def _execute_topic_selection(self) -> str:
        """Execute Topic Agent (Phase 5.3 - Step 1)."""
        input_obj = {"field": self.config["field"]}

        response = self._execute_agent_with_retry(
            "topic_agent", topic_agent.run, input_obj
        )

        topic = response["data"].get("topic")
        if not topic:
            raise ValidationError("Topic agent returned no topic")

        return topic

    def _execute_research_with_pivot(self, initial_topic: str) -> Dict[str, Any]:
        """
        Execute Research Agent with topic pivot fallback (Phase 5.3 - Step 2).

        If research fails with DataNotFoundError, requests a new topic
        (max 2 pivots).
        """
        topic = initial_topic
        pivot_count = 0

        while pivot_count <= self.MAX_TOPIC_PIVOTS:
            try:
                input_obj = {"topic": topic}
                response = self._execute_agent_with_retry(
                    "research_agent", research_agent.run, input_obj
                )

                return response["data"]

            except DataNotFoundError:
                pivot_count += 1
                self.metrics["topic_pivots"] = pivot_count

                if pivot_count > self.MAX_TOPIC_PIVOTS:
                    raise DataNotFoundError(
                        f"Research failed after {self.MAX_TOPIC_PIVOTS} topic pivots"
                    )

                # Request new topic
                log_event(
                    self.run_id,
                    "research_pivot",
                    pivot_count,
                    "info",
                )
                topic = self._execute_topic_selection()

        raise DataNotFoundError("Topic pivot logic exhausted unexpectedly")

    def _execute_prompt_generation(
        self, topic: str, research_data: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Execute Prompt Generator Agent (Phase 5.3 - Step 3)."""
        input_obj = {"topic": topic, "research": research_data}

        response = self._execute_agent_with_retry(
            "prompt_generator_agent", prompt_generator_agent.run, input_obj
        )

        return response["data"]

    def _execute_writing_and_review_loop(
        self, structured_prompt: Dict[str, Any]
    ) -> str:
        """
        Execute Writer and Reviewer with character count validation loop
        (Phase 5.3 Steps 5-6, Phase 5.4).
        """
        iteration = 0
        shortening_instruction = None

        while iteration < self.MAX_CHAR_LOOP_ITERATIONS:
            iteration += 1
            self.metrics["char_loop_iterations"] = iteration

            # Execute Writer Agent
            writer_input = {
                "structured_prompt": structured_prompt,
            }

            if shortening_instruction:
                writer_input["shortening_instruction"] = shortening_instruction

            writer_response = self._execute_agent_with_retry(
                "writer_agent", writer_agent.run, writer_input
            )

            # Read draft content from returned path (more robust than assuming filename)
            draft_path_str = writer_response["data"].get("draft_path")
            draft_path = Path(draft_path_str)
            if not draft_path.is_absolute():
                draft_path = self.run_path / draft_path
            draft_text = draft_path.read_text(encoding="utf-8")

            # Execute Reviewer Agent
            reviewer_input = {"draft_text": draft_text}

            reviewer_response = self._execute_agent_with_retry(
                "reviewer_agent", reviewer_agent.run, reviewer_input
            )

            revised_text = reviewer_response["data"].get("revised")

            # Validate character count
            char_count = count_chars(revised_text)

            log_event(
                self.run_id,
                "char_count_check",
                iteration,
                "ok",
                duration_ms=None,
                model=None,
                token_usage={"char_count": char_count},
            )

            if char_count < self.MAX_CHAR_COUNT:
                # Save final post
                final_path = get_artifact_path(
                    self.run_path, "60_final_post", extension="txt"
                )
                atomic_write_text(final_path, revised_text)
                return revised_text

            # Character count failed - prepare shortening instruction
            shortening_instruction = {
                "current_count": char_count,
                "target_count": self.TARGET_CHAR_COUNT,
                "message": f"Post is {char_count} characters (limit: {self.MAX_CHAR_COUNT}). "
                f"Please shorten to ~{self.TARGET_CHAR_COUNT} characters while "
                "preserving key insights and the Witty Expert persona.",
            }

        # Max iterations exceeded
        raise ValidationError(
            f"Character count loop exceeded {self.MAX_CHAR_LOOP_ITERATIONS} iterations"
        )

    def _execute_image_prompt_generation(self, final_post: str) -> str:
        """Execute Image Prompt Generator Agent (Phase 5.5 - Step 8)."""
        input_obj = {"final_post": final_post}

        response = self._execute_agent_with_retry(
            "image_prompt_agent", image_prompt_agent.run, input_obj
        )

        # Return the image prompt artifact path for downstream consumption
        prompt_path_str = response["data"].get("image_prompt_path")
        if not prompt_path_str:
            # Fallback to expected filename if agent did not return path (legacy behavior)
            prompt_path = self.run_path / "70_image_prompt.txt"
            return str(prompt_path)
        return prompt_path_str

    def _execute_image_generation(self, image_prompt_path: str) -> None:
        """Execute Image Generator Agent (Phase 5.5 - Step 9)."""
        input_obj = {"image_prompt_path": image_prompt_path}

        response = self._execute_agent_with_retry(
            "image_generator_agent", image_generator_agent.run, input_obj
        )

        # Verify image artifact exists using returned path
        image_path_str = response["data"].get("image_path")
        if not image_path_str:
            # Fallback to expected filename if agent did not return path (legacy behavior)
            image_path = self.run_path / "80_image.png"
        else:
            image_path = Path(image_path_str)
            if not image_path.is_absolute():
                image_path = self.run_path / image_path

        if not image_path.exists():
            raise CorruptionError("Image generation completed but artifact not found")

    def _complete_run_success(self, final_post: str) -> Dict[str, Any]:
        """Mark run as complete and return summary (Phase 5.6)."""
        log_event(self.run_id, "run_complete", 1, "ok")

        # Add cost summary to metrics
        cost_summary = self.cost_tracker.get_summary()

        return {
            "status": "success",
            "run_id": self.run_id,
            "run_path": str(self.run_path),
            "artifacts": {
                "final_post": str(self.run_path / "60_final_post.txt"),
                "image": str(self.run_path / "80_image.png"),
            },
            "metrics": self.metrics,
            "cost": cost_summary,
        }

    def _handle_run_failure(self, error: Exception, stack_trace: str) -> Dict[str, Any]:
        """Create run_failed.json and return error summary (Phase 5.6)."""
        error_type = type(error).__name__
        error_msg = str(error)

        # Determine failed step from metrics
        failed_step = None
        for agent_name, agent_metrics in self.metrics["agent_metrics"].items():
            if agent_metrics["status"] == "failed":
                failed_step = agent_name
                break

        # Create failure artifact
        cost_summary = self.cost_tracker.get_summary()
        
        failure_data = {
            "timestamp": datetime.now().isoformat(),
            "run_id": self.run_id,
            "error_type": error_type,
            "error_message": error_msg,
            "failed_step": failed_step,
            "circuit_breaker_state": {
                "consecutive_failures": self.circuit_breaker.consecutive_failures,
                "is_tripped": self.circuit_breaker.is_tripped(),
            },
            "metrics": self.metrics,
            "cost": cost_summary,
            "stack_trace": stack_trace,
        }

        if self.run_path:
            failure_path = self.run_path / "run_failed.json"
            write_and_verify_json(failure_path, failure_data)

        log_event(self.run_id, "run_failed", 1, "error", error_type=error_type)

        return {
            "status": "failed",
            "run_id": self.run_id,
            "run_path": str(self.run_path) if self.run_path else None,
            "error": {"type": error_type, "message": error_msg},
            "failure_artifact": str(failure_path) if self.run_path else None,
            "cost": cost_summary,
        }


def main():  # pragma: no cover
    """Test harness for orchestrator development."""
    test_config = {"field": "Data Science (Optimizations & Time-Series Analysis)"}

    try:
        orchestrator = Orchestrator(test_config)
        result = orchestrator.run()

        print(f"\n{'='*60}")
        print("ORCHESTRATOR RESULT")
        print(f"{'='*60}")
        print(json.dumps(result, indent=2))
        
        # Display cost summary
        if "cost" in result:
            print(f"\n{'='*60}")
            print("COST SUMMARY")
            print(f"{'='*60}")
            cost = result["cost"]
            print(f"Total Cost: ${cost['total_cost_usd']:.4f}")
            print(f"Total API Calls: {cost['total_api_calls']}")
            print(f"Budget Remaining: ${cost['budget_remaining_usd']:.4f}")
            print(f"\nCosts by Agent:")
            for agent, agent_cost in cost['costs_by_agent'].items():
                calls = cost['calls_by_agent'].get(agent, 0)
                print(f"  {agent}: ${agent_cost:.4f} ({calls} calls)")

    except Exception as e:
        print(f"\nOrchestrator failed: {e}")
        traceback.print_exc()


if __name__ == "__main__":  # pragma: no cover
    main()
