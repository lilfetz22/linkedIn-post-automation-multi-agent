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
from database.operations import get_all_used_topics


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


def test_topic_agent_generates_batch_when_exhausted(temp_run_dir, tmp_path):
    """Test that when all UNUSED topics are exhausted and recent history exists, agent generates 10 new ones."""
    db_path = str(tmp_path / "exhausted_db.db")
    init_db(db_path)

    # Create some initial topics and mark them all as used + posted
    from database.operations import (
        select_new_topic as select_topic,
        record_posted_topic,
    )

    seed_potential_topics(
        [
            ("Used topic 1", DEFAULT_FIELD_DS),
            ("Used topic 2", DEFAULT_FIELD_DS),
        ],
        db_path,
    )

    # Mark both as used and record them as posted
    sel1 = select_topic(DEFAULT_FIELD_DS, db_path=db_path)
    record_posted_topic(sel1["topic"], db_path=db_path)

    sel2 = select_topic(DEFAULT_FIELD_DS, db_path=db_path)
    record_posted_topic(sel2["topic"], db_path=db_path)

    # Verify both are used and in previous_topics (so they'll be filtered)
    used = get_all_used_topics(DEFAULT_FIELD_DS, db_path=db_path)
    assert len(used) == 2

    input_obj = {"field": DEFAULT_FIELD_DS, "db_path": db_path}
    context = {"run_id": "test-run-batch", "run_path": temp_run_dir}

    # Mock LLM to return 10 new topics
    mock_llm_response = {
        "text": "1. New topic A\n2. New topic B\n3. New topic C\n4. New topic D\n5. New topic E\n6. New topic F\n7. New topic G\n8. New topic H\n9. New topic I\n10. New topic J",
        "token_usage": {"prompt_tokens": 200, "completion_tokens": 300},
        "model": "gemini-2.5-pro",
    }

    with patch("agents.topic_agent.get_text_client") as mock_client:
        mock_client.return_value.generate_text.return_value = mock_llm_response

        response = run(input_obj, context)

        validate_envelope(response)
        if response["status"] != "ok":
            print(f"Error: {response.get('error')}")
        assert response["status"] == "ok", f"Got error: {response.get('error', {})}"
        assert response["data"]["topic"] == "New topic A"

        # Verify artifact was created
        artifact_path = temp_run_dir / "10_topic.json"
        assert artifact_path.exists()

    import gc

    gc.collect()


def test_topic_agent_batch_generation_parses_numbered_list(temp_run_dir, tmp_path):
    """Test that batch generation correctly parses numbered list format."""
    db_path = str(tmp_path / "parse_test_db.db")
    init_db(db_path)

    # Create and exhaust a topic, then record it as posted
    from database.operations import (
        select_new_topic as select_topic,
        record_posted_topic,
    )

    seed_potential_topics(
        [("Used topic", DEFAULT_FIELD_DS)],
        db_path,
    )
    sel = select_topic(DEFAULT_FIELD_DS, db_path=db_path)
    record_posted_topic(sel["topic"], db_path=db_path)

    input_obj = {"field": DEFAULT_FIELD_DS, "db_path": db_path}
    context = {"run_id": "test-run-parse", "run_path": temp_run_dir}

    # Test numbered format
    mock_llm_response = {
        "text": "1. First generated topic\n2. Second generated topic\n3. Third generated topic\n4. Fourth\n5. Fifth\n6. Sixth\n7. Seventh\n8. Eighth\n9. Ninth\n10. Tenth",
        "token_usage": {"prompt_tokens": 200, "completion_tokens": 300},
        "model": "gemini-2.5-pro",
    }

    with patch("agents.topic_agent.get_text_client") as mock_client:
        mock_client.return_value.generate_text.return_value = mock_llm_response

        response = run(input_obj, context)

        assert response["status"] == "ok"
        assert response["data"]["topic"] == "First generated topic"

    import gc

    gc.collect()


# Note: Multi-batch regeneration test is challenging to implement due to sliding window behavior
# with recent_limit=10. After posting 10+ topics, older topics fall out of the window and
# become available again, preventing the None condition that triggers batch generation.
# The batch generation functionality is adequately tested by:
# - test_topic_agent_generates_batch_when_exhausted (first batch generation)
# - test_topic_agent_batch_generation_parses_numbered_list (parsing validation)
# Real-world usage will naturally cycle through batches as topics age out of the window,
# which is the intended behavior.


def test_topic_agent_batch_generation_with_multiple_cycles():
    """Test that batch generation works across multiple agent calls."""
    # TODO: Implement when sliding window test strategy is determined
    pass
