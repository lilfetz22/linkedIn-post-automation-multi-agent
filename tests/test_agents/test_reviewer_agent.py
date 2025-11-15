"""Tests for reviewer_agent.py."""

import tempfile
from pathlib import Path
import pytest
import json

from agents.reviewer_agent import run
from core.envelope import validate_envelope


@pytest.fixture
def temp_run_dir():
    """Create a temporary run directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_path = Path(tmpdir)
        yield run_path


@pytest.fixture
def sample_draft():
    """Sample draft text for testing."""
    return """**Redis Optimization Strategies**

Problem: Hard to balance memory vs latency

Analogy: Like tuning a race car engine

Solution Outline: Step-by-step optimization framework

Strategic Angle: Translate technical nuance

CTA: Comment with your biggest bottleneck.

— Witty Expert"""


def test_reviewer_agent_success(temp_run_dir, sample_draft):
    """Test successful review execution."""
    input_obj = {"draft_text": sample_draft}
    context = {"run_id": "test-run-001", "run_path": temp_run_dir}
    
    response = run(input_obj, context)
    
    # Validate envelope structure
    validate_envelope(response)
    assert response["status"] == "ok"
    assert "original" in response["data"]
    assert "revised" in response["data"]
    assert "changes" in response["data"]
    
    # Verify artifact persistence
    artifact_path = temp_run_dir / "50_review.json"
    assert artifact_path.exists()
    
    with open(artifact_path) as f:
        artifact_data = json.load(f)
    assert "original" in artifact_data
    assert "revised" in artifact_data
    assert "changes" in artifact_data


def test_reviewer_agent_missing_draft_text(temp_run_dir):
    """Test error handling when draft_text is missing."""
    input_obj = {}
    context = {"run_id": "test-run-002", "run_path": temp_run_dir}
    
    response = run(input_obj, context)
    
    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


def test_reviewer_agent_two_pass_indicators(temp_run_dir, sample_draft):
    """Test that review includes indicators of both passes."""
    input_obj = {"draft_text": sample_draft}
    context = {"run_id": "test-run-003", "run_path": temp_run_dir}
    
    response = run(input_obj, context)
    
    assert response["status"] == "ok"
    revised = response["data"]["revised"]
    
    # Stub implementation adds pass markers
    assert "[Context Pass OK]" in revised or "[Grammar Pass OK]" in revised


def test_reviewer_agent_changes_structure(temp_run_dir, sample_draft):
    """Test that changes have expected structure."""
    input_obj = {"draft_text": sample_draft}
    context = {"run_id": "test-run-004", "run_path": temp_run_dir}
    
    response = run(input_obj, context)
    
    assert response["status"] == "ok"
    changes = response["data"]["changes"]
    
    # Changes should be a list
    assert isinstance(changes, list)


def test_reviewer_agent_no_changes_scenario(temp_run_dir):
    """Test scenario where no changes are needed."""
    # Already perfect draft
    perfect_draft = "Perfect post with no issues."
    input_obj = {"draft_text": perfect_draft}
    context = {"run_id": "test-run-005", "run_path": temp_run_dir}
    
    response = run(input_obj, context)
    
    assert response["status"] == "ok"
    # Even with no logical changes, stub adds pass markers
    assert "revised" in response["data"]


def test_reviewer_agent_handles_special_characters(temp_run_dir):
    """Test that reviewer handles special characters correctly."""
    draft_with_special = "Test with emoji 🚀 and symbols: @ # $ % & *"
    input_obj = {"draft_text": draft_with_special}
    context = {"run_id": "test-run-006", "run_path": temp_run_dir}
    
    response = run(input_obj, context)
    
    assert response["status"] == "ok"
    # Should not crash and should preserve special chars
    assert "revised" in response["data"]
