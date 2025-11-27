"""
Tests for cost tracking infrastructure.
"""

import pytest

from core.cost_tracking import (
    CostMetrics,
    CostTracker,
    GEMINI_PRO_INPUT_PRICE,
    GEMINI_PRO_OUTPUT_PRICE,
    GEMINI_FLASH_IMAGE_PRICE,
)
from core.errors import ValidationError


class TestCostMetrics:
    """Test cost calculation for individual LLM calls."""

    def test_text_generation_cost(self):
        """Test cost calculation for text generation."""
        metrics = CostMetrics(
            model="gemini-2.5-pro", input_tokens=1000, output_tokens=500
        )

        expected_input = (1000 / 1_000_000) * GEMINI_PRO_INPUT_PRICE
        expected_output = (500 / 1_000_000) * GEMINI_PRO_OUTPUT_PRICE
        expected_total = expected_input + expected_output

        assert metrics.cost_usd == pytest.approx(expected_total)

    def test_image_generation_cost(self):
        """Test cost calculation for image generation."""
        metrics = CostMetrics(
            model="gemini-2.5-flash-image", input_tokens=0, output_tokens=0
        )

        assert metrics.cost_usd == GEMINI_FLASH_IMAGE_PRICE

    def test_zero_tokens(self):
        """Test cost with zero tokens."""
        metrics = CostMetrics(model="gemini-2.5-pro", input_tokens=0, output_tokens=0)

        assert metrics.cost_usd == 0.0


class TestCostTracker:
    """Test cost tracking across a run."""

    def test_record_single_call(self):
        """Test recording a single API call."""
        tracker = CostTracker(max_cost_usd=1.0, max_api_calls=10)

        metrics = CostMetrics(
            model="gemini-2.5-pro", input_tokens=1000, output_tokens=500
        )

        tracker.record_call("test_agent", metrics)

        assert tracker.api_call_count == 1
        assert tracker.total_cost_usd > 0
        assert "test_agent" in tracker.costs_by_agent
        assert tracker.calls_by_agent["test_agent"] == 1

    def test_record_multiple_calls(self):
        """Test recording multiple API calls."""
        tracker = CostTracker(max_cost_usd=1.0, max_api_calls=10)

        # Record 3 calls
        for i in range(3):
            metrics = CostMetrics(
                model="gemini-2.5-pro", input_tokens=1000, output_tokens=500
            )
            tracker.record_call(f"agent_{i}", metrics)

        assert tracker.api_call_count == 3
        assert len(tracker.costs_by_agent) == 3

    def test_max_api_calls_exceeded(self):
        """Test that exceeding max API calls raises error."""
        tracker = CostTracker(max_cost_usd=10.0, max_api_calls=2)

        # Record 2 calls (should succeed)
        for i in range(2):
            metrics = CostMetrics(
                model="gemini-2.5-pro", input_tokens=100, output_tokens=50
            )
            tracker.record_call(f"agent_{i}", metrics)

        # 3rd call should fail
        with pytest.raises(ValidationError, match="Maximum API calls"):
            metrics = CostMetrics(
                model="gemini-2.5-pro", input_tokens=100, output_tokens=50
            )
            tracker.record_call("agent_3", metrics)

    def test_max_cost_exceeded(self):
        """Test that exceeding max cost raises error."""
        tracker = CostTracker(max_cost_usd=0.0001, max_api_calls=10)

        # Try to record expensive call that exceeds budget
        with pytest.raises(ValidationError, match="Maximum cost.*would be exceeded"):
            metrics = CostMetrics(
                model="gemini-2.5-pro",
                input_tokens=1_000_000,  # 1M tokens = significant cost
                output_tokens=500_000,
            )
            tracker.record_call("expensive_agent", metrics)

    def test_get_summary(self):
        """Test cost summary generation."""
        tracker = CostTracker(max_cost_usd=1.0, max_api_calls=10)

        # Record some calls
        metrics1 = CostMetrics(
            model="gemini-2.5-pro", input_tokens=1000, output_tokens=500
        )
        tracker.record_call("agent_1", metrics1)

        metrics2 = CostMetrics(model="gemini-2.5-flash-image")
        tracker.record_call("agent_2", metrics2)

        summary = tracker.get_summary()

        assert "total_cost_usd" in summary
        assert "total_api_calls" in summary
        assert summary["total_api_calls"] == 2
        assert "costs_by_agent" in summary
        assert "agent_1" in summary["costs_by_agent"]
        assert "agent_2" in summary["costs_by_agent"]
        assert "budget_remaining_usd" in summary
        assert "calls_remaining" in summary

    def test_estimate_run_cost(self):
        """Test run cost estimation."""
        tracker = CostTracker()

        estimated_cost = tracker.estimate_run_cost(
            avg_input_tokens=1000,
            avg_output_tokens=500,
            num_text_agents=5,
            num_image_agents=1,
        )

        # Should be positive
        assert estimated_cost > 0

        # Should include text and image costs
        assert estimated_cost > GEMINI_FLASH_IMAGE_PRICE

    def test_warn_if_high_cost(self, capsys):
        """Test high cost warning."""
        tracker = CostTracker(max_cost_usd=10.0, max_api_calls=100)

        # Record expensive call
        metrics = CostMetrics(
            model="gemini-2.5-pro", input_tokens=500_000, output_tokens=250_000
        )
        tracker.record_call("expensive_agent", metrics)

        # Trigger warning with low threshold
        tracker.warn_if_high_cost(threshold=0.001)

        captured = capsys.readouterr()
        assert "Warning" in captured.out or "⚠️" in captured.out
        assert "exceeds" in captured.out
