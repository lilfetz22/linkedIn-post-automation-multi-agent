"""Tests for research_agent.py."""

import tempfile
from pathlib import Path
import pytest
import json

from agents.research_agent import run
from core.envelope import validate_envelope


@pytest.fixture
def temp_run_dir():
    """Create a temporary run directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_path = Path(tmpdir)
        yield run_path


def test_research_agent_success(temp_run_dir):
    """Test successful research execution."""
    input_obj = {"topic": "Python asyncio optimization"}
    context = {"run_id": "test-run-001", "run_path": temp_run_dir}

    response = run(input_obj, context)

    # Validate envelope structure
    validate_envelope(response)
    assert response["status"] == "ok"
    assert "topic" in response["data"]
    assert "sources" in response["data"]
    assert "summary" in response["data"]
    assert len(response["data"]["sources"]) > 0

    # Verify artifact persistence
    artifact_path = temp_run_dir / "20_research.json"
    assert artifact_path.exists()

    with open(artifact_path) as f:
        artifact_data = json.load(f)
    assert artifact_data["topic"] == "Python asyncio optimization"
    assert len(artifact_data["sources"]) > 0


def test_research_agent_missing_topic(temp_run_dir):
    """Test error handling when topic is missing."""
    input_obj = {}
    context = {"run_id": "test-run-002", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert "topic" in response["error"]["message"].lower()
    assert response["error"]["retryable"] is False


def test_research_agent_sources_structure(temp_run_dir):
    """Test that sources have expected structure."""
    input_obj = {"topic": "Machine learning pipelines"}
    context = {"run_id": "test-run-003", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"
    sources = response["data"]["sources"]

    # Each source should have title and url
    for source in sources:
        assert "title" in source
        assert "url" in source
        assert isinstance(source["title"], str)
        assert isinstance(source["url"], str)


def test_research_agent_summary_contains_topic(temp_run_dir):
    """Test that summary references the topic."""
    topic = "Time-series forecasting"
    input_obj = {"topic": topic}
    context = {"run_id": "test-run-004", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"
    summary = response["data"]["summary"]
    assert topic in summary
