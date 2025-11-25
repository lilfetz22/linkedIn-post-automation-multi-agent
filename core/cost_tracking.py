"""
Cost tracking and budget management for LLM API calls.

Tracks token usage and costs across all agents during a run.
Enforces per-run budget limits to prevent unexpected expenses.
"""

from dataclasses import dataclass, field
from typing import Dict, Optional
import os

try:
    # Lazy import so unit tests can run without network; will fail gracefully
    from google import genai as genai_new  # type: ignore

    _COST_CLIENT = (
        genai_new.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        if os.getenv("GOOGLE_API_KEY")
        else None
    )
except Exception:  # pragma: no cover - defensive fallback
    _COST_CLIENT = None
from core.errors import ValidationError


# Gemini pricing (as of 11/25/2025, verify at https://ai.google.dev/pricing)
# Prices are per 1M tokens
GEMINI_PRO_INPUT_PRICE = 0.00125  # $1.25 per 1M input tokens
GEMINI_PRO_OUTPUT_PRICE = 0.01000  # $10.00 per 1M output tokens
GEMINI_FLASH_IMAGE_PRICE = 0.000300  # $0.30 per image (estimate)


@dataclass
class CostMetrics:
    """Token usage and cost metrics for a single LLM call."""

    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0

    def __post_init__(self):
        """Calculate cost based on token usage and model."""
        if "image" in self.model.lower():
            # Image generation has fixed cost per image
            self.cost_usd = GEMINI_FLASH_IMAGE_PRICE
        elif "gemini" in self.model.lower() and "pro" in self.model.lower():
            # Text generation cost based on tokens
            input_cost = (self.input_tokens / 1_000_000) * GEMINI_PRO_INPUT_PRICE
            output_cost = (self.output_tokens / 1_000_000) * GEMINI_PRO_OUTPUT_PRICE
            self.cost_usd = input_cost + output_cost
        else:
            # Unknown model, use default Pro pricing
            input_cost = (self.input_tokens / 1_000_000) * GEMINI_PRO_INPUT_PRICE
            output_cost = (self.output_tokens / 1_000_000) * GEMINI_PRO_OUTPUT_PRICE
            self.cost_usd = input_cost + output_cost


@dataclass
class CostTracker:
    """
    Tracks cumulative costs across a pipeline run.

    Enforces budget limits and provides cost reporting.
    """

    max_cost_usd: float = 3.00
    max_api_calls: int = 25

    # Internal state
    total_cost_usd: float = 0.0
    api_call_count: int = 0
    costs_by_agent: Dict[str, float] = field(default_factory=dict)
    calls_by_agent: Dict[str, int] = field(default_factory=dict)

    def check_budget(
        self, model: str, prompt: str, estimated_output_tokens: int = 1000
    ):
        """Proactively validate budget before an API call using real token counts.

        Args:
            model: Model name for the upcoming call
            prompt: Prompt text whose tokens will be counted
            estimated_output_tokens: Conservative estimate of completion tokens (default 1000)

        Raises:
            ValidationError: If API call or cost budget would be exceeded
        """
        # API call count enforcement
        if self.api_call_count >= self.max_api_calls:
            raise ValidationError(
                f"Maximum API calls ({self.max_api_calls}) exceeded. Current count: {self.api_call_count}"
            )

        # Count input tokens using Gemini if available; fallback to heuristic
        input_tokens = 0
        if _COST_CLIENT is not None:
            try:  # pragma: no branch
                token_info = _COST_CLIENT.models.count_tokens(
                    model=model, contents=prompt
                )
                # Some client versions return dict-like, others object with total_tokens
                input_tokens = getattr(token_info, "total_tokens", None) or token_info.get("total_tokens", 0)  # type: ignore
            except Exception:
                # Fallback heuristic: rough average 4 chars per token
                input_tokens = max(1, len(prompt) // 4)
        else:
            input_tokens = max(1, len(prompt) // 4)

        # Compute projected cost
        projected_cost_metrics = CostMetrics(
            model=model,
            input_tokens=input_tokens,
            output_tokens=estimated_output_tokens,
        )
        projected_total = self.total_cost_usd + projected_cost_metrics.cost_usd
        if projected_total > self.max_cost_usd:
            raise ValidationError(
                f"Maximum cost (${self.max_cost_usd:.2f}) would be exceeded. Current: ${self.total_cost_usd:.4f}, "
                f"Projected new total: ${projected_total:.4f} (input_tokens={input_tokens}, output_tokens={estimated_output_tokens})"
            )

        # Store a lightweight preview (not recorded yet) for possible future use
        self._last_budget_preview = {
            "model": model,
            "input_tokens": input_tokens,
            "estimated_output_tokens": estimated_output_tokens,
            "projected_cost_usd": projected_cost_metrics.cost_usd,
        }

    def record_call(
        self,
        agent_name_or_model: str,
        metrics_or_prompt_tokens: "CostMetrics | int" = 0,
        completion_tokens: Optional[int] = None,
        agent_name: Optional[str] = None,
    ):
        """
        Record an API call and update cost tracking.

        Supports two calling patterns:
        1. Old pattern: record_call(agent_name: str, metrics: CostMetrics)
        2. New pattern: record_call(model: str, prompt_tokens: int, completion_tokens: int, agent_name: str)

        Args:
            agent_name_or_model: Agent name (old) or model name (new)
            metrics_or_prompt_tokens: CostMetrics object (old) or prompt tokens count (new)
            completion_tokens: Number of output tokens (new pattern only)
            agent_name: Agent name (new pattern only)

        Raises:
            ValidationError: If budget limits would be exceeded
        """
        # Determine which calling pattern is being used
        if isinstance(metrics_or_prompt_tokens, CostMetrics):
            # Old pattern: record_call(agent_name, metrics)
            agent = agent_name_or_model
            metrics = metrics_or_prompt_tokens
        else:
            # New pattern: record_call(model, prompt_tokens, completion_tokens, agent_name)
            model = agent_name_or_model
            prompt_tokens = metrics_or_prompt_tokens if metrics_or_prompt_tokens else 0
            completion_tokens = completion_tokens if completion_tokens else 0
            agent = agent_name

            # Create cost metrics
            metrics = CostMetrics(
                model=model,
                input_tokens=prompt_tokens,
                output_tokens=completion_tokens,
            )

        # Check limits BEFORE recording
        if self.api_call_count >= self.max_api_calls:
            raise ValidationError(
                f"Maximum API calls ({self.max_api_calls}) exceeded. "
                f"Current count: {self.api_call_count}"
            )

        new_total_cost = self.total_cost_usd + metrics.cost_usd
        if new_total_cost > self.max_cost_usd:
            raise ValidationError(
                f"Maximum cost (${self.max_cost_usd:.2f}) would be exceeded. "
                f"Current: ${self.total_cost_usd:.4f}, "
                f"Requested: ${metrics.cost_usd:.4f}, "
                f"New total: ${new_total_cost:.4f}"
            )

        # Update tracking
        self.total_cost_usd = new_total_cost
        self.api_call_count += 1

        # Update per-agent tracking (if agent name provided)
        if agent:
            self.costs_by_agent[agent] = (
                self.costs_by_agent.get(agent, 0.0) + metrics.cost_usd
            )
            self.calls_by_agent[agent] = self.calls_by_agent.get(agent, 0) + 1

    def get_summary(self) -> Dict[str, any]:
        """
        Get cost summary for reporting.

        Returns:
            Dictionary with cost breakdown by agent and totals
        """
        return {
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_api_calls": self.api_call_count,
            "costs_by_agent": {
                agent: round(cost, 4) for agent, cost in self.costs_by_agent.items()
            },
            "calls_by_agent": self.calls_by_agent.copy(),
            "budget_remaining_usd": round(self.max_cost_usd - self.total_cost_usd, 4),
            "calls_remaining": self.max_api_calls - self.api_call_count,
        }

    def estimate_run_cost(
        self,
        avg_input_tokens: int = 1000,
        avg_output_tokens: int = 500,
        num_text_agents: int = 6,
        num_image_agents: int = 1,
    ) -> float:
        """
        Estimate total cost for a typical run.

        Args:
            avg_input_tokens: Average input tokens per text agent
            avg_output_tokens: Average output tokens per text agent
            num_text_agents: Number of text generation agents
            num_image_agents: Number of image generation agents

        Returns:
            Estimated cost in USD
        """
        # Text generation cost
        text_cost_per_call = (avg_input_tokens / 1_000_000) * GEMINI_PRO_INPUT_PRICE + (
            avg_output_tokens / 1_000_000
        ) * GEMINI_PRO_OUTPUT_PRICE
        total_text_cost = text_cost_per_call * num_text_agents

        # Image generation cost
        total_image_cost = GEMINI_FLASH_IMAGE_PRICE * num_image_agents

        return total_text_cost + total_image_cost

    def warn_if_high_cost(self, threshold: float = 0.50):
        """
        Log warning if cost exceeds threshold.

        Args:
            threshold: Warning threshold in USD
        """
        if self.total_cost_usd >= threshold:
            print(
                f"⚠️  Warning: Run cost ${self.total_cost_usd:.4f} "
                f"exceeds ${threshold:.2f} threshold"
            )
