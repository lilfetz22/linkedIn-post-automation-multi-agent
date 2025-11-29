"""Tests for topic_agent.py."""

import tempfile
from pathlib import Path
import pytest
import json
from unittest.mock import patch

from agents.topic_agent import run
from core.envelope import validate_envelope
from core.errors import ModelError
from database.init_db import (
    init_db,
    seed_potential_topics,
    DEFAULT_FIELD_DS,
    DEFAULT_FIELD_GAI,
)


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary database for testing."""
    db_path = str(tmp_path / "test_topics.db")
    init_db(db_path)
    # Seed with test topics
    seed_potential_topics(
        [
            ("Test topic 1", DEFAULT_FIELD_DS),
            ("Test topic 2", DEFAULT_FIELD_DS),
            ("Test topic 3", DEFAULT_FIELD_GAI),
        ],
        db_path,
    )

    yield db_path

    # Cleanup: Force garbage collection to release file handles
    import gc

    gc.collect()


@pytest.fixture
def temp_run_dir():
    """Create a temporary run directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_path = Path(tmpdir)
        yield run_path


def test_topic_agent_success(temp_db, temp_run_dir):
    """Test successful topic selection."""
    input_obj = {"field": DEFAULT_FIELD_DS, "db_path": temp_db}
    context = {"run_id": "test-run-001", "run_path": temp_run_dir}

    response = run(input_obj, context)

    # Validate envelope structure
    validate_envelope(response)
    assert response["status"] == "ok"
    assert "topic" in response["data"]
    assert response["data"]["topic"] in ["Test topic 1", "Test topic 2"]

    # Verify artifact persistence
    artifact_path = temp_run_dir / "10_topic.json"
    assert artifact_path.exists()

    with open(artifact_path) as f:
        artifact_data = json.load(f)
    assert artifact_data["topic"] == response["data"]["topic"]


def test_topic_agent_field_filtering(temp_db, temp_run_dir):
    """Test that topics are filtered by field."""
    input_obj = {"field": DEFAULT_FIELD_GAI, "db_path": temp_db}
    context = {"run_id": "test-run-002", "run_path": temp_run_dir}

    response = run(input_obj, context)

    assert response["status"] == "ok"
    assert response["data"]["topic"] == "Test topic 3"


def test_topic_agent_missing_field(temp_run_dir):
    """Test error handling when field is missing."""
    input_obj = {}
    context = {"run_id": "test-run-003", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert "field" in response["error"]["message"].lower()
    assert response["error"]["retryable"] is False


def test_topic_agent_no_available_topics(temp_run_dir, tmp_path):
    """Test error when no topics are available and LLM fallback also fails."""
    db_path = str(tmp_path / "empty_db.db")
    init_db(db_path)
    # Don't seed any topics

    input_obj = {"field": DEFAULT_FIELD_DS, "db_path": db_path}
    context = {"run_id": "test-run-004", "run_path": temp_run_dir}

    # Mock LLM to fail as well
    with patch("agents.topic_agent.get_text_client") as mock_client:
        mock_client.return_value.generate_text.side_effect = ModelError(
            "LLM unavailable"
        )

        response = run(input_obj, context)

        validate_envelope(response)
        assert response["status"] == "error"
        assert response["error"]["type"] == "DataNotFoundError"
        assert "llm fallback failed" in response["error"]["message"].lower()
        assert response["error"]["retryable"] is False

    # Force garbage collection to release handles
    import gc

    gc.collect()


def test_topic_agent_deterministic_selection(temp_db, temp_run_dir):
    """Test that topic selection is deterministic (smallest id)."""
    input_obj = {"field": DEFAULT_FIELD_DS, "db_path": temp_db}
    context = {"run_id": "test-run-005", "run_path": temp_run_dir}

    response1 = run(input_obj, context)

    # Should always select the first topic for the field
    assert response1["data"]["topic"] == "Test topic 1"


def test_topic_agent_llm_fallback_success(temp_run_dir, tmp_path):
    """Test successful LLM fallback when database is empty."""
    db_path = str(tmp_path / "empty_db.db")
    init_db(db_path)
    # Don't seed any topics

    input_obj = {"field": DEFAULT_FIELD_DS, "db_path": db_path}
    context = {"run_id": "test-run-006", "run_path": temp_run_dir}

    # Mock LLM to return valid topics
    mock_llm_response = {
        "text": json.dumps(
            [
                {
                    "topic": "LLM-generated topic about data optimization",
                    "novelty": "net_new",
                    "rationale": "Addresses emerging need for faster pipelines",
                }
            ]
        ),
        "token_usage": {"prompt_tokens": 100, "completion_tokens": 200},
        "model": "gemini-2.5-pro",
    }

    with patch("agents.topic_agent.get_text_client") as mock_client:
        mock_client.return_value.generate_text.return_value = mock_llm_response

        response = run(input_obj, context)

        validate_envelope(response)
        assert response["status"] == "ok"
        assert "topic" in response["data"]
        assert "LLM-generated" in response["data"]["topic"]

        # Verify artifact was created
        artifact_path = temp_run_dir / "10_topic.json"
        assert artifact_path.exists()

    # Force garbage collection
    import gc

    gc.collect()
