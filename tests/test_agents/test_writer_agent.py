"""Tests for writer_agent.py."""

import tempfile
from pathlib import Path
import pytest

from agents.writer_agent import run
from core.envelope import validate_envelope


@pytest.fixture
def temp_run_dir():
    """Create a temporary run directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_path = Path(tmpdir)
        yield run_path


@pytest.fixture
def sample_structured_prompt():
    """Sample structured prompt for testing."""
    return {
        "topic_title": "Redis Optimization Strategies",
        "target_audience": "Senior engineers scaling distributed systems",
        "pain_point": "Hard to balance memory vs latency",
        "key_metrics": ["Memory usage", "P99 latency"],
        "analogy": "Like tuning a race car engine",
        "solution_outline": "Step-by-step optimization framework",
    }


@pytest.fixture
def sample_strategy():
    """Sample strategy for testing."""
    return {
        "structure": "Hook -> Pain -> Insight -> Example -> Impact -> CTA",
        "strategic_angle": "Translate technical nuance into actionable insights",
    }


def test_writer_agent_success(temp_run_dir, sample_structured_prompt, sample_strategy):
    """Test successful draft writing."""
    input_obj = {
        "structured_prompt": sample_structured_prompt,
        "strategy": sample_strategy,
    }
    context = {"run_id": "test-run-001", "run_path": temp_run_dir}

    response = run(input_obj, context)

    # Validate envelope structure
    validate_envelope(response)
    assert response["status"] == "ok"
    assert "draft_path" in response["data"]

    # Verify artifact persistence
    artifact_path = temp_run_dir / "40_draft.md"
    assert artifact_path.exists()

    draft_text = artifact_path.read_text()
    assert len(draft_text) > 0


def test_writer_agent_missing_structured_prompt(temp_run_dir, sample_strategy):
    """Test error handling when structured_prompt is missing."""
    input_obj = {"strategy": sample_strategy}
    context = {"run_id": "test-run-002", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


def test_writer_agent_missing_strategy(temp_run_dir, sample_structured_prompt):
    """Test error handling when strategy is missing."""
    input_obj = {"structured_prompt": sample_structured_prompt}
    context = {"run_id": "test-run-003", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


def test_writer_agent_draft_structure(
    temp_run_dir, sample_structured_prompt, sample_strategy
):
    """Test that draft includes expected structural elements."""
    input_obj = {
        "structured_prompt": sample_structured_prompt,
        "strategy": sample_strategy,
    }
    context = {"run_id": "test-run-004", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"

    artifact_path = temp_run_dir / "40_draft.md"
    draft_text = artifact_path.read_text()

    # Check for key structural elements from stub
    assert "Problem:" in draft_text or "problem" in draft_text.lower()
    assert "Analogy:" in draft_text or "analogy" in draft_text.lower()
    assert "Solution" in draft_text or "solution" in draft_text.lower()


def test_writer_agent_includes_cta(
    temp_run_dir, sample_structured_prompt, sample_strategy
):
    """Test that draft includes a call-to-action."""
    input_obj = {
        "structured_prompt": sample_structured_prompt,
        "strategy": sample_strategy,
    }
    context = {"run_id": "test-run-005", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"

    artifact_path = temp_run_dir / "40_draft.md"
    draft_text = artifact_path.read_text()

    # Should include CTA
    assert "CTA:" in draft_text or "comment" in draft_text.lower()


def test_writer_agent_includes_signature(
    temp_run_dir, sample_structured_prompt, sample_strategy
):
    """Test that draft includes The Witty Expert signature."""
    input_obj = {
        "structured_prompt": sample_structured_prompt,
        "strategy": sample_strategy,
    }
    context = {"run_id": "test-run-006", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"

    artifact_path = temp_run_dir / "40_draft.md"
    draft_text = artifact_path.read_text()

    # Should include signature
    assert "Witty Expert" in draft_text
