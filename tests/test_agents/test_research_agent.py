"""Tests for research_agent.py."""

import tempfile
from pathlib import Path
import pytest
import json
from unittest.mock import patch, MagicMock

from agents.research_agent import run
from core.envelope import validate_envelope
from core.errors import ModelError


@pytest.fixture
def temp_run_dir():
    """Create a temporary run directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_path = Path(tmpdir)
        yield run_path


def test_research_agent_success(temp_run_dir):
    """Test successful research execution with mocked LLM."""
    input_obj = {"topic": "Python asyncio optimization"}
    context = {"run_id": "test-run-001", "run_path": temp_run_dir}

    # Mock LLM response
    mock_research = {
        "sources": [
            {"title": "Asyncio Performance Guide", "url": "https://example.com/1", "key_point": "Event loop optimization"},
            {"title": "Python Concurrency Patterns", "url": "https://example.com/2", "key_point": "Task scheduling strategies"}
        ],
        "summary": "Python asyncio optimization focuses on event loop efficiency and task scheduling."
    }
    mock_llm_response = {
        "text": json.dumps(mock_research),
        "token_usage": {"prompt_tokens": 100, "completion_tokens": 200},
        "model": "gemini-2.5-pro"
    }
    
    with patch("agents.research_agent.get_text_client") as mock_client:
        mock_client.return_value.generate_text.return_value = mock_llm_response
        
        response = run(input_obj, context)

        # Validate envelope structure
        validate_envelope(response)
        assert response["status"] == "ok"
        assert "topic" in response["data"]
        assert "sources" in response["data"]
        assert "summary" in response["data"]
        assert len(response["data"]["sources"]) == 2

        # Verify artifact persistence
        artifact_path = temp_run_dir / "20_research.json"
        assert artifact_path.exists()

        with open(artifact_path) as f:
            artifact_data = json.load(f)
        assert artifact_data["topic"] == "Python asyncio optimization"
        assert len(artifact_data["sources"]) == 2


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

    # Mock LLM response
    mock_research = {
        "sources": [
            {"title": "ML Pipeline Best Practices", "url": "https://ml.example.com/1", "key_point": "Automation strategies"}
        ],
        "summary": "Machine learning pipelines require careful orchestration."
    }
    mock_llm_response = {
        "text": json.dumps(mock_research),
        "token_usage": {"prompt_tokens": 100, "completion_tokens": 150},
        "model": "gemini-2.5-pro"
    }
    
    with patch("agents.research_agent.get_text_client") as mock_client:
        mock_client.return_value.generate_text.return_value = mock_llm_response
        
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

    # Mock LLM response
    mock_research = {
        "sources": [
            {"title": "Forecasting Methods", "url": "https://ts.example.com/1", "key_point": "ARIMA vs Prophet"}
        ],
        "summary": f"Research on {topic} shows multiple approaches for prediction accuracy."
    }
    mock_llm_response = {
        "text": json.dumps(mock_research),
        "token_usage": {"prompt_tokens": 100, "completion_tokens": 150},
        "model": "gemini-2.5-pro"
    }
    
    with patch("agents.research_agent.get_text_client") as mock_client:
        mock_client.return_value.generate_text.return_value = mock_llm_response
        
        response = run(input_obj, context)

        assert response["status"] == "ok"
        summary = response["data"]["summary"]
        assert topic in summary


def test_research_agent_llm_failure(temp_run_dir):
    """Test handling of LLM failure."""
    input_obj = {"topic": "Test topic"}
    context = {"run_id": "test-run-005", "run_path": temp_run_dir}

    with patch("agents.research_agent.get_text_client") as mock_client:
        mock_client.return_value.generate_text.side_effect = ModelError("LLM unavailable")
        
        response = run(input_obj, context)

        validate_envelope(response)
        assert response["status"] == "error"
        assert response["error"]["type"] == "ModelError"
        assert response["error"]["retryable"] is True


def test_research_agent_empty_sources(temp_run_dir):
    """Test handling of empty sources from LLM."""
    input_obj = {"topic": "Test topic"}
    context = {"run_id": "test-run-006", "run_path": temp_run_dir}

    # Mock LLM response with empty sources
    mock_research = {
        "sources": [],
        "summary": "No sources available"
    }
    mock_llm_response = {
        "text": json.dumps(mock_research),
        "token_usage": {"prompt_tokens": 100, "completion_tokens": 50},
        "model": "gemini-2.5-pro"
    }
    
    with patch("agents.research_agent.get_text_client") as mock_client:
        mock_client.return_value.generate_text.return_value = mock_llm_response
        
        response = run(input_obj, context)

        validate_envelope(response)
        assert response["status"] == "error"
        assert response["error"]["type"] == "DataNotFoundError"
        assert response["error"]["retryable"] is False
