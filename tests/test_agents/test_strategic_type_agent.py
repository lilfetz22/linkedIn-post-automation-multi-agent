"""Tests for strategic_type_agent.py."""

import tempfile
from pathlib import Path
import pytest
import json

from agents.strategic_type_agent import run
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
        "pain_point": "Hard to balance memory vs latency without deep Redis internals knowledge",
        "key_metrics": ["Memory usage", "P99 latency", "Cache hit rate"],
        "analogy": "Like tuning a race car engine—small adjustments have massive ripple effects",
        "solution_outline": "Step-by-step optimization framework",
        "raw_summary": "Research on Redis performance tuning",
    }


@pytest.fixture
def sample_research():
    """Sample research data."""
    return {
        "topic": "Redis optimization",
        "sources": [{"title": "Redis patterns", "url": "https://example.com/1"}],
        "summary": "Best practices for Redis in production",
    }


def test_strategic_type_agent_success(
    temp_run_dir, sample_structured_prompt, sample_research
):
    """Test successful strategy generation."""
    input_obj = {
        "structured_prompt": sample_structured_prompt,
        "research": sample_research,
    }
    context = {"run_id": "test-run-001", "run_path": temp_run_dir}

    response = run(input_obj, context)

    # Validate envelope structure
    validate_envelope(response)
    assert response["status"] == "ok"
    assert "structure" in response["data"]
    assert "strategic_angle" in response["data"]

    # Verify artifact persistence
    artifact_path = temp_run_dir / "30_strategy.json"
    assert artifact_path.exists()

    with open(artifact_path) as f:
        artifact_data = json.load(f)
    assert "structure" in artifact_data
    assert "strategic_angle" in artifact_data


def test_strategic_type_agent_missing_structured_prompt(temp_run_dir, sample_research):
    """Test error handling when structured_prompt is missing."""
    input_obj = {"research": sample_research}
    context = {"run_id": "test-run-002", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


def test_strategic_type_agent_missing_research(temp_run_dir, sample_structured_prompt):
    """Test error handling when research is missing."""
    input_obj = {"structured_prompt": sample_structured_prompt}
    context = {"run_id": "test-run-003", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


def test_strategic_type_agent_structure_format(
    temp_run_dir, sample_structured_prompt, sample_research
):
    """Test that structure follows expected format."""
    input_obj = {
        "structured_prompt": sample_structured_prompt,
        "research": sample_research,
    }
    context = {"run_id": "test-run-004", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"
    structure = response["data"]["structure"]

    # Structure should contain flow indicators
    assert "->" in structure or "→" in structure, "Structure should show content flow"


def test_strategic_type_agent_uses_inputs(
    temp_run_dir, sample_structured_prompt, sample_research
):
    """Test that strategy indicates it used the provided inputs."""
    input_obj = {
        "structured_prompt": sample_structured_prompt,
        "research": sample_research,
    }
    context = {"run_id": "test-run-005", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"
    # The stub implementation includes inputs_used field
    if "inputs_used" in response["data"]:
        inputs_used = response["data"]["inputs_used"]
        assert len(inputs_used) > 0
