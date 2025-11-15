"""Tests for prompt_generator_agent.py."""

import tempfile
from pathlib import Path
import pytest
import json

from agents.prompt_generator_agent import run, REQUIRED_FIELDS
from core.envelope import validate_envelope


@pytest.fixture
def temp_run_dir():
    """Create a temporary run directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_path = Path(tmpdir)
        yield run_path


@pytest.fixture
def sample_research():
    """Sample research data for testing."""
    return {
        "topic": "Redis optimization",
        "sources": [{"title": "Redis best practices", "url": "https://example.com/1"}],
        "summary": "Key strategies for optimizing Redis performance including connection pooling and data structure selection.",
    }


def test_prompt_generator_success(temp_run_dir, sample_research):
    """Test successful prompt generation."""
    input_obj = {"topic": "Redis optimization", "research": sample_research}
    context = {"run_id": "test-run-001", "run_path": temp_run_dir}

    response = run(input_obj, context)

    # Validate envelope structure
    validate_envelope(response)
    assert response["status"] == "ok"

    # Verify all required fields are present
    for field in REQUIRED_FIELDS:
        assert field in response["data"], f"Missing required field: {field}"

    # Verify artifact persistence
    artifact_path = temp_run_dir / "25_structured_prompt.json"
    assert artifact_path.exists()

    with open(artifact_path) as f:
        artifact_data = json.load(f)
    for field in REQUIRED_FIELDS:
        assert field in artifact_data


def test_prompt_generator_missing_topic(temp_run_dir, sample_research):
    """Test error handling when topic is missing."""
    input_obj = {"research": sample_research}
    context = {"run_id": "test-run-002", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


def test_prompt_generator_missing_research(temp_run_dir):
    """Test error handling when research is missing."""
    input_obj = {"topic": "Redis optimization"}
    context = {"run_id": "test-run-003", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


def test_prompt_generator_no_cliche_analogies(temp_run_dir, sample_research):
    """Test that generated analogies avoid common clichés (basic check)."""
    input_obj = {"topic": "Blockchain consensus", "research": sample_research}
    context = {"run_id": "test-run-004", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"
    analogy = response["data"]["analogy"].lower()

    # Check that common clichés are avoided
    cliche_phrases = ["distributed ledger", "like a library", "like a recipe"]
    for cliche in cliche_phrases:
        assert cliche not in analogy, f"Found cliché phrase: {cliche}"


def test_prompt_generator_target_audience_specificity(temp_run_dir, sample_research):
    """Test that target audience is specific, not generic."""
    input_obj = {"topic": "Neural network pruning", "research": sample_research}
    context = {"run_id": "test-run-005", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"
    audience = response["data"]["target_audience"]

    # Should be more specific than just "engineers" or "developers"
    assert len(audience) > 20, "Target audience description should be specific"


def test_prompt_generator_pain_point_depth(temp_run_dir, sample_research):
    """Test that pain points go beyond surface-level technical issues."""
    input_obj = {"topic": "Kubernetes scaling", "research": sample_research}
    context = {"run_id": "test-run-006", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"
    pain_point = response["data"]["pain_point"]

    # Pain point should be substantive
    assert len(pain_point) > 30, "Pain point should be detailed"
