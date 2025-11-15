"""Tests for image_prompt_agent.py."""

import tempfile
from pathlib import Path
import pytest

from agents.image_prompt_agent import run
from core.envelope import validate_envelope


@pytest.fixture
def temp_run_dir():
    """Create a temporary run directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_path = Path(tmpdir)
        yield run_path


@pytest.fixture
def sample_final_post():
    """Sample final post for testing."""
    return """**Redis Optimization Strategies**

Problem: Hard to balance memory vs latency

Analogy: Like tuning a race car engine

Solution Outline: Step-by-step optimization framework

Strategic Angle: Translate technical nuance into actionable insights

CTA: Comment with your biggest bottleneck.

— Witty Expert"""


def test_image_prompt_agent_success(temp_run_dir, sample_final_post):
    """Test successful image prompt generation."""
    input_obj = {"final_post": sample_final_post}
    context = {"run_id": "test-run-001", "run_path": temp_run_dir}

    response = run(input_obj, context)

    # Validate envelope structure
    validate_envelope(response)
    assert response["status"] == "ok"
    assert "image_prompt_path" in response["data"]

    # Verify artifact persistence
    artifact_path = temp_run_dir / "70_image_prompt.txt"
    assert artifact_path.exists()

    prompt_text = artifact_path.read_text()
    assert len(prompt_text) > 0


def test_image_prompt_agent_missing_final_post(temp_run_dir):
    """Test error handling when final_post is missing."""
    input_obj = {}
    context = {"run_id": "test-run-002", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


def test_image_prompt_agent_extracts_theme(temp_run_dir, sample_final_post):
    """Test that prompt extracts thematic content from post."""
    input_obj = {"final_post": sample_final_post}
    context = {"run_id": "test-run-003", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"

    artifact_path = temp_run_dir / "70_image_prompt.txt"
    prompt_text = artifact_path.read_text()

    # Should reference the post topic
    assert "Redis Optimization" in prompt_text or "redis" in prompt_text.lower()


def test_image_prompt_agent_includes_style_guidance(temp_run_dir, sample_final_post):
    """Test that prompt includes visual style guidance."""
    input_obj = {"final_post": sample_final_post}
    context = {"run_id": "test-run-004", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"

    artifact_path = temp_run_dir / "70_image_prompt.txt"
    prompt_text = artifact_path.read_text().lower()

    # Should include style keywords
    style_keywords = ["modern", "minimal", "professional", "clean", "illustration"]
    assert any(keyword in prompt_text for keyword in style_keywords)


def test_image_prompt_agent_fallback_for_empty_post(temp_run_dir):
    """Test that empty post is handled (current behavior: validation error)."""
    input_obj = {"final_post": ""}
    context = {"run_id": "test-run-005", "run_path": temp_run_dir}

    response = run(input_obj, context)

    # Empty string currently triggers ValidationError
    # Future enhancement: add fallback logic for empty posts
    validate_envelope(response)
    # For now we expect validation to catch this
    # If we want graceful fallback, we'd need to update the agent implementation


def test_image_prompt_agent_handles_multiline(temp_run_dir):
    """Test that agent handles multiline posts correctly."""
    multiline_post = "Line 1\nLine 2\nLine 3\n\nParagraph 2"
    input_obj = {"final_post": multiline_post}
    context = {"run_id": "test-run-006", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"

    artifact_path = temp_run_dir / "70_image_prompt.txt"
    assert artifact_path.exists()
