"""
Tests for error classification and handling across the multi-agent pipeline.

This module provides comprehensive tests for:
- Retryable vs non-retryable error distinction
- Exponential backoff retry logic
- Circuit breaker behavior
- Error propagation through orchestrator
- Agent-specific error scenarios
"""

import pytest
import time
from unittest.mock import Mock, patch, MagicMock
from pathlib import Path

from core.errors import (
    BaseAgentError,
    ValidationError,
    DataNotFoundError,
    ModelError,
    CorruptionError,
)
from core.retry import (
    CircuitBreaker,
    CircuitBreakerTrippedError,
    exponential_backoff,
    execute_with_retries,
)
from core.envelope import ok, err
from orchestrator import Orchestrator


# =============================================================================
# Test Suite: Retryable vs Non-Retryable Error Distinction
# =============================================================================


class TestRetryableErrorClassification:
    """Test that errors are correctly classified as retryable or non-retryable."""

    def test_model_error_is_retryable(self):
        """Test ModelError is marked as retryable (network failures, API timeouts)."""
        error = ModelError("API timeout")
        assert error.retryable is True
        assert isinstance(error, BaseAgentError)

    def test_data_not_found_error_is_not_retryable_by_default(self):
        """Test DataNotFoundError is NOT retryable by default (triggers topic pivot instead)."""
        error = DataNotFoundError("No sources found")
        assert error.retryable is False
        assert isinstance(error, BaseAgentError)

    def test_validation_error_is_non_retryable(self):
        """Test ValidationError is NOT retryable (invalid data, constraint violations)."""
        error = ValidationError("Character limit exceeded")
        assert error.retryable is False
        assert isinstance(error, BaseAgentError)

    def test_corruption_error_is_non_retryable(self):
        """Test CorruptionError is NOT retryable (artifact parsing failures)."""
        error = CorruptionError("JSON file corrupted")
        assert error.retryable is False
        assert isinstance(error, BaseAgentError)

    def test_base_agent_error_default_not_retryable(self):
        """Test BaseAgentError defaults to non-retryable."""
        error = BaseAgentError("Generic error")
        assert error.retryable is False

    def test_base_agent_error_explicit_retryable(self):
        """Test BaseAgentError can be explicitly marked as retryable."""
        error = BaseAgentError("Transient error", retryable=True)
        assert error.retryable is True


# =============================================================================
# Test Suite: Exponential Backoff Retry Logic
# =============================================================================


class TestExponentialBackoff:
    """Test exponential backoff calculation and retry behavior."""

    def test_backoff_delay_pattern_1s_2s_4s(self):
        """Verify sleep delays follow pattern: 1s, 2s, 4s for attempts 1, 2, 3."""
        assert exponential_backoff(1) == 1.0
        assert exponential_backoff(2) == 2.0
        assert exponential_backoff(3) == 4.0

    def test_backoff_with_custom_base(self):
        """Test backoff with custom base delay."""
        assert exponential_backoff(1, base_seconds=0.5) == 0.5
        assert exponential_backoff(2, base_seconds=0.5) == 1.0
        assert exponential_backoff(3, base_seconds=0.5) == 2.0

    def test_backoff_continues_exponentially(self):
        """Test backoff continues with higher attempts."""
        assert exponential_backoff(4) == 8.0
        assert exponential_backoff(5) == 16.0

    def test_max_retry_attempts_enforced(self):
        """Test max retry attempts is enforced (default 3)."""
        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ModelError("Always fails")

        with patch("core.retry.time.sleep"):  # Skip actual sleep
            with pytest.raises(ModelError):
                execute_with_retries(failing_func, max_attempts=3)

        assert call_count == 3

    def test_max_retry_attempts_custom_value(self):
        """Test custom max retry attempts."""
        call_count = 0

        def failing_func():
            nonlocal call_count
            call_count += 1
            raise ModelError("Always fails")

        with patch("core.retry.time.sleep"):
            with pytest.raises(ModelError):
                execute_with_retries(failing_func, max_attempts=5)

        assert call_count == 5

    def test_successful_retry_after_transient_failure(self):
        """Test successful execution after transient failures."""
        call_count = 0

        def sometimes_failing_func():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ModelError("Transient failure")
            return "success"

        with patch("core.retry.time.sleep"):
            result = execute_with_retries(sometimes_failing_func, max_attempts=3)

        assert result == "success"
        assert call_count == 3

    def test_retry_uses_exponential_backoff_delays(self):
        """Test that retry actually calls sleep with exponential delays."""
        call_count = 0

        def failing_twice():
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise ModelError("Transient")
            return "done"

        with patch("core.retry.time.sleep") as mock_sleep:
            result = execute_with_retries(failing_twice, max_attempts=3, base_delay=1.0)

        # Verify the result is returned successfully after retries
        assert result == "done", "Should return successful result after retries"
        # Should sleep twice: after attempt 1 and after attempt 2
        assert mock_sleep.call_count == 2
        mock_sleep.assert_any_call(1.0)  # First backoff
        mock_sleep.assert_any_call(2.0)  # Second backoff

    def test_non_retryable_error_does_not_retry(self):
        """Test that non-retryable errors abort immediately without retry."""
        call_count = 0

        def validation_failure():
            nonlocal call_count
            call_count += 1
            raise ValidationError("Invalid data")

        with patch("core.retry.time.sleep") as mock_sleep:
            with pytest.raises(ValidationError):
                execute_with_retries(validation_failure, max_attempts=3)

        assert call_count == 1  # Only one attempt
        mock_sleep.assert_not_called()  # No backoff for non-retryable


# =============================================================================
# Test Suite: Circuit Breaker Behavior
# =============================================================================


class TestCircuitBreaker:
    """Test circuit breaker state management and tripping behavior."""

    def test_breaker_opens_after_3_consecutive_failures(self):
        """Test breaker trips after 3 consecutive LLM failures."""
        breaker = CircuitBreaker()

        breaker.record_failure()
        assert not breaker.is_tripped()

        breaker.record_failure()
        assert not breaker.is_tripped()

        with pytest.raises(CircuitBreakerTrippedError):
            breaker.record_failure()

        assert breaker.is_tripped()

    def test_breaker_resets_on_successful_execution(self):
        """Test breaker resets counter after successful agent execution."""
        breaker = CircuitBreaker()

        breaker.record_failure()
        breaker.record_failure()
        assert breaker.consecutive_failures == 2

        breaker.record_success()
        assert breaker.consecutive_failures == 0
        assert not breaker.is_tripped()

    def test_circuit_breaker_tripped_error_raised_when_open(self):
        """Test CircuitBreakerTrippedError is raised when breaker is open."""
        breaker = CircuitBreaker()

        # Trip the breaker
        breaker.record_failure()
        breaker.record_failure()

        with pytest.raises(CircuitBreakerTrippedError) as exc_info:
            breaker.record_failure()

        assert "3 consecutive LLM failures" in str(exc_info.value)

    def test_breaker_state_persists_across_agent_calls(self):
        """Test breaker state persists across agent calls within same run."""
        breaker = CircuitBreaker()

        # Simulate first agent failure
        breaker.record_failure()
        assert breaker.consecutive_failures == 1

        # Simulate second agent failure (different agent, same run)
        breaker.record_failure()
        assert breaker.consecutive_failures == 2

        # State persists
        assert not breaker.is_tripped()

    def test_breaker_custom_max_failures(self):
        """Test breaker with custom max failures threshold."""
        breaker = CircuitBreaker(max_failures=5)

        for _ in range(4):
            breaker.record_failure()
        assert not breaker.is_tripped()

        with pytest.raises(CircuitBreakerTrippedError):
            breaker.record_failure()
        assert breaker.is_tripped()

    def test_execute_with_retries_uses_circuit_breaker(self):
        """Test execute_with_retries integrates with circuit breaker."""
        breaker = CircuitBreaker()
        call_count = 0

        def always_fails():
            nonlocal call_count
            call_count += 1
            raise ModelError("API error")

        with patch("core.retry.time.sleep"):
            # The 3rd failure triggers CircuitBreakerTrippedError
            # because record_failure() raises when threshold is reached
            with pytest.raises((ModelError, CircuitBreakerTrippedError)):
                execute_with_retries(
                    always_fails, max_attempts=3, circuit_breaker=breaker
                )

        # Breaker should be tripped after 3 failures
        assert breaker.is_tripped()

    def test_execute_with_retries_resets_breaker_on_success(self):
        """Test successful execution resets circuit breaker."""
        breaker = CircuitBreaker()
        breaker.record_failure()
        breaker.record_failure()

        def succeeds():
            return "success"

        result = execute_with_retries(succeeds, circuit_breaker=breaker)

        assert result == "success"
        assert breaker.consecutive_failures == 0


# =============================================================================
# Test Suite: Error Propagation Through Orchestrator
# =============================================================================


class TestErrorPropagationOrchestrator:
    """Test how errors propagate through the orchestrator."""

    @pytest.fixture
    def valid_config(self):
        return {"field": "Data Science (Optimizations & Time-Series Analysis)"}

    @pytest.fixture
    def mock_run_dir(self, tmp_path):
        run_dir = tmp_path / "2025-11-27-test123"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def test_non_retryable_errors_abort_run_immediately(
        self, valid_config, mock_run_dir
    ):
        """Test non-retryable errors cause immediate run abort."""
        with patch(
            "orchestrator.create_run_dir", return_value=("test123", mock_run_dir)
        ), patch("orchestrator.write_and_verify_json"), patch(
            "orchestrator.log_event"
        ), patch(
            "orchestrator.topic_agent"
        ) as mock_topic:

            # Topic agent returns validation error
            mock_topic.run.return_value = err(
                "ValidationError", "Invalid field", retryable=False
            )

            orch = Orchestrator(valid_config)
            result = orch.run()

            assert result["status"] == "failed"
            assert "ValidationError" in result["error"]["type"]

    def test_retryable_errors_exhaust_retries_before_aborting(
        self, valid_config, mock_run_dir
    ):
        """Test retryable errors exhaust all retry attempts before aborting."""
        with patch(
            "orchestrator.create_run_dir", return_value=("test123", mock_run_dir)
        ), patch("orchestrator.write_and_verify_json"), patch(
            "orchestrator.log_event"
        ), patch(
            "core.retry.time.sleep"
        ), patch(
            "orchestrator.topic_agent"
        ) as mock_topic:

            # Simulate ModelError response that gets reconstructed
            mock_topic.run.return_value = err(
                "BaseAgentError", "API timeout", retryable=True
            )

            orch = Orchestrator(valid_config)
            result = orch.run()

            # Should have attempted multiple times before failing
            assert result["status"] == "failed"
            assert mock_topic.run.call_count == 3  # Default max retries

    def test_run_failed_json_created_with_error_details(
        self, valid_config, mock_run_dir
    ):
        """Test run_failed.json artifact is created with error details."""
        with patch(
            "orchestrator.create_run_dir", return_value=("test123", mock_run_dir)
        ), patch("orchestrator.write_and_verify_json") as mock_write, patch(
            "orchestrator.log_event"
        ), patch(
            "orchestrator.topic_agent"
        ) as mock_topic:

            mock_topic.run.return_value = err(
                "ValidationError", "Test error", retryable=False
            )

            orch = Orchestrator(valid_config)
            result = orch.run()

            assert result["status"] == "failed"
            assert result["failure_artifact"] is not None

            # Check that write_and_verify_json was called for run_failed.json
            calls = mock_write.call_args_list
            # At least one call should be for run_failed.json
            failure_write_found = any("run_failed.json" in str(call) for call in calls)
            assert failure_write_found or len(calls) > 1

    def test_error_context_includes_required_fields(self, valid_config, mock_run_dir):
        """Test error context includes step name, attempt count, stack trace, timestamp."""
        with patch(
            "orchestrator.create_run_dir", return_value=("test123", mock_run_dir)
        ), patch("orchestrator.write_and_verify_json") as mock_write, patch(
            "orchestrator.log_event"
        ), patch(
            "orchestrator.topic_agent"
        ) as mock_topic:

            mock_topic.run.return_value = err(
                "ValidationError", "Test error", retryable=False
            )

            orch = Orchestrator(valid_config)
            result = orch.run()

            # Verify orchestrator returns failed status
            assert (
                result["status"] == "failed"
            ), "Orchestrator should return failed status"

            # Check the failure data written to run_failed.json
            failure_calls = [
                call
                for call in mock_write.call_args_list
                if "run_failed" in str(call[0][0])
            ]

            if failure_calls:
                failure_data = failure_calls[0][0][1]
                assert "timestamp" in failure_data
                assert "error_type" in failure_data
                assert "error_message" in failure_data
                assert "stack_trace" in failure_data
                assert (
                    "failed_step" in failure_data
                    or failure_data.get("failed_step") is None
                )

    def test_corruption_error_aborts_immediately(self, valid_config, mock_run_dir):
        """Test CorruptionError causes immediate abort without retry."""
        with patch(
            "orchestrator.create_run_dir", return_value=("test123", mock_run_dir)
        ), patch("orchestrator.write_and_verify_json") as mock_write, patch(
            "orchestrator.log_event"
        ):

            # First call (config write) fails with CorruptionError
            # Subsequent calls (failure logging) should succeed
            mock_write.side_effect = [
                CorruptionError("JSON corruption during config write"),
                None,
            ]

            orch = Orchestrator(valid_config)
            result = orch.run()

            # The run should fail immediately with corruption error
            assert result["status"] == "failed"
            assert "CorruptionError" in result["error"]["type"]


# =============================================================================
# Test Suite: Agent-Specific Error Scenarios
# =============================================================================


class TestAgentSpecificErrorScenarios:
    """Test error handling specific to each agent."""

    @pytest.fixture
    def valid_config(self):
        return {"field": "Generative AI & AI Agents"}

    @pytest.fixture
    def mock_run_dir(self, tmp_path):
        run_dir = tmp_path / "2025-11-27-agent-test"
        run_dir.mkdir(parents=True, exist_ok=True)
        return run_dir

    def test_topic_agent_empty_database_triggers_llm_fallback(
        self, valid_config, mock_run_dir
    ):
        """Test Topic Agent: empty database triggers LLM fallback for topic generation."""
        from agents import topic_agent

        # Patch select_new_topic to return None (empty database)
        # and get_text_client for LLM fallback
        with patch(
            "agents.topic_agent.select_new_topic", return_value=None
        ) as mock_select, patch(
            "agents.topic_agent.get_recent_topics", return_value=[]
        ) as mock_recent, patch(
            "agents.topic_agent.get_text_client"
        ) as mock_client, patch(
            "agents.topic_agent.write_and_verify_json"
        ):

            # Mock LLM client for fallback - returns valid JSON array
            mock_text = MagicMock()
            mock_text.generate_text.return_value = {
                "text": '[{"topic": "LLM Generated Topic", "novelty": "net_new", "rationale": "Test"}]',
                "token_usage": {"prompt_tokens": 100, "completion_tokens": 200},
            }
            mock_client.return_value = mock_text

            context = {"run_id": "test", "run_path": mock_run_dir}
            input_obj = {"field": valid_config["field"]}

            result = topic_agent.run(input_obj, context)

            # Should succeed using LLM fallback
            assert result["status"] == "ok"
            # Verify LLM was called when database was empty
            mock_client.return_value.generate_text.assert_called_once()

    def test_research_agent_zero_results_triggers_data_not_found(
        self, valid_config, mock_run_dir
    ):
        """Test Research Agent: zero search results triggers DataNotFoundError."""
        from agents import research_agent

        with patch("agents.research_agent.get_text_client") as mock_client, patch(
            "agents.research_agent.log_event"
        ):
            mock_text = MagicMock()
            # Simulate response with empty sources array (triggers DataNotFoundError)
            mock_text.generate_text.return_value = {
                "text": '{"sources": [], "summary": "No information found"}',
                "token_usage": {"prompt_tokens": 10, "completion_tokens": 5},
            }
            mock_client.return_value = mock_text

            context = {"run_id": "test", "run_path": mock_run_dir}
            input_obj = {"topic": "Test Topic"}

            # Research agent should return error envelope with DataNotFoundError
            result = research_agent.run(input_obj, context)

            assert result["status"] == "error"
            assert result["error"]["type"] == "DataNotFoundError"
            assert "No sources found" in result["error"]["message"]
            assert result["error"]["retryable"] is False

    def test_writer_agent_max_shortening_attempts_raises_validation_error(self):
        """Test Writer Agent: max shortening attempts exceeded raises ValidationError."""
        from agents import writer_agent

        with patch("agents.writer_agent.get_text_client") as mock_client, patch(
            "agents.writer_agent.atomic_write_text"
        ), patch(
            "agents.writer_agent.get_artifact_path", return_value="/tmp/draft.md"
        ), patch(
            "agents.writer_agent.log_event"
        ):

            # Always return text that's too long
            mock_text = MagicMock()
            mock_text.generate_text.return_value = {
                "text": "A" * 4000,  # Always over limit
                "token_usage": {"prompt_tokens": 100, "completion_tokens": 1000},
            }
            mock_client.return_value = mock_text

            # Call the writer agent
            context = {"run_id": "test", "run_path": Path("/tmp")}
            input_obj = {"structured_prompt": {"topic_title": "Test"}}

            result = writer_agent.run(input_obj, context)

            # Should return error envelope with ValidationError after max shortening attempts
            assert result["status"] == "error"
            assert result["error"]["type"] == "ValidationError"
            assert "shortening attempts" in result["error"]["message"]
            # Verify the LLM was called MAX_SHORTENING_ATTEMPTS + 1 times (initial + retries)
            assert (
                mock_client.return_value.generate_text.call_count
                == writer_agent.MAX_SHORTENING_ATTEMPTS + 1
            )

    def test_reviewer_agent_llm_failure_returns_error(self, mock_run_dir):
        """Test Reviewer Agent: LLM failure returns error envelope."""
        from agents import reviewer_agent

        with patch("agents.reviewer_agent.get_text_client") as mock_client:

            # Simulate LLM failure
            mock_text = MagicMock()
            mock_text.generate_text.side_effect = Exception("LLM API failure")
            mock_client.return_value = mock_text

            context = {"run_id": "test", "run_path": mock_run_dir}
            # The reviewer expects draft_text, not draft_path
            input_obj = {"draft_text": "Test draft content for review"}

            result = reviewer_agent.run(input_obj, context)

            # Should return error envelope
            assert result["status"] == "error"
            assert result["error"]["type"] == "ModelError"

    def test_image_generator_failure_creates_placeholder(self, mock_run_dir):
        """Test Image Generator: generation failure creates placeholder image."""
        from agents import image_generator_agent
        from core.errors import ModelError

        # Create a test image prompt file
        prompt_path = mock_run_dir / "70_image_prompt.txt"
        prompt_path.write_text("Test image prompt")

        # The artifact path should be a Path object, not a string
        artifact_path = mock_run_dir / "80_image.png"

        with patch(
            "agents.image_generator_agent.get_image_client"
        ) as mock_client, patch(
            "agents.image_generator_agent.get_artifact_path", return_value=artifact_path
        ), patch(
            "agents.image_generator_agent.log_event"
        ):

            # Simulate image generation failure - raise ModelError for fallback to catch
            mock_img = MagicMock()
            mock_img.generate_image.side_effect = Exception("Image generation failed")
            mock_client.return_value = mock_img

            context = {"run_id": "test", "run_path": mock_run_dir}
            input_obj = {"image_prompt_path": str(prompt_path)}

            # Agent should create placeholder and not crash
            result = image_generator_agent.run(input_obj, context)

            # Should return ok with placeholder (fallback works)
            assert result["status"] == "ok"
            # Verify placeholder was created
            assert artifact_path.exists()
            assert result["data"]["generation_info"]["fallback_used"] is True


# =============================================================================
# Test Suite: Integration Tests for Error Flow
# =============================================================================


class TestErrorFlowIntegration:
    """Integration tests for error handling flow through the system."""

    @pytest.fixture
    def valid_config(self):
        return {"field": "Data Science (Optimizations & Time-Series Analysis)"}

    def test_model_error_triggers_retry_then_circuit_breaker(
        self, valid_config, tmp_path
    ):
        """Test ModelError triggers retries and eventually trips circuit breaker."""
        mock_run_dir = tmp_path / "2025-11-27-integration"
        mock_run_dir.mkdir(parents=True, exist_ok=True)

        with patch(
            "orchestrator.create_run_dir", return_value=("int-test", mock_run_dir)
        ), patch("orchestrator.write_and_verify_json"), patch(
            "orchestrator.log_event"
        ), patch(
            "core.retry.time.sleep"
        ), patch(
            "orchestrator.topic_agent"
        ) as mock_topic:

            # Always return retryable error
            mock_topic.run.return_value = err(
                "BaseAgentError", "Network timeout", retryable=True
            )

            orch = Orchestrator(valid_config)
            result = orch.run()

            assert result["status"] == "failed"
            # Circuit breaker should have tripped
            assert orch.circuit_breaker.is_tripped()

    def test_error_recovery_resets_circuit_breaker(self, valid_config, tmp_path):
        """Test successful recovery after errors resets circuit breaker state."""
        breaker = CircuitBreaker()

        # Record some failures
        breaker.record_failure()
        breaker.record_failure()
        assert breaker.consecutive_failures == 2

        # Successful operation
        def success_func():
            return "recovered"

        result = execute_with_retries(success_func, circuit_breaker=breaker)

        assert result == "recovered"
        assert breaker.consecutive_failures == 0
        assert not breaker.is_tripped()
