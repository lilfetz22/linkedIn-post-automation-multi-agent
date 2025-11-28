"""Tests for reviewer_agent.py (Phase 7.6 - LLM-powered with grammar checking)."""

import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from agents.reviewer_agent import run, count_chars, _remove_hashtags
from core.envelope import validate_envelope


@pytest.fixture
def temp_run_dir():
    """Create a temporary run directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_path = Path(tmpdir)
        yield run_path


@pytest.fixture
def sample_short_draft():
    """Sample short draft (under 3000 chars)."""
    return """**Redis Optimization: The Race Car Tuning Analogy**

Ever feel like Redis is a race car engine that's either overheating or underperforming?

**The Problem:** Balancing memory vs latency is like tuning a race car.

**The Solution:** Use maxmemory-policy set to allkeys-lru.

**The Impact:** 40% reduction in memory footprint.

— Tech Audience Accelerator"""


@pytest.fixture
def sample_long_draft():
    """Sample long draft (over 3000 chars)."""
    return "A" * 3100


@pytest.fixture
def sample_draft_with_hashtags():
    """Sample draft with hashtags at the end."""
    return """**Redis Optimization**

Great content here.

— Tech Audience Accelerator

#redis #optimization #performance #tech"""


@pytest.fixture
def mock_cost_tracker():
    """Mock cost tracker."""
    mock_tracker = MagicMock()
    mock_tracker.check_budget = MagicMock()
    mock_tracker.record_call = MagicMock()
    return mock_tracker


@patch("agents.reviewer_agent.get_text_client")
@patch("agents.reviewer_agent._apply_grammar_corrections")
def test_reviewer_agent_success(
    mock_grammar, mock_get_client, temp_run_dir, sample_short_draft, mock_cost_tracker
):
    """Test successful review with LLM and grammar checking."""
    # Mock LLM client - must return dict with 'text' key
    mock_client = MagicMock()
    mock_client.generate_text.return_value = {
        "text": sample_short_draft,
        "token_usage": {"prompt_tokens": 200, "completion_tokens": 150},
        "model": "gemini-2.5-pro",
    }
    mock_get_client.return_value = mock_client

    # Mock grammar checking (no changes)
    mock_grammar.return_value = (sample_short_draft, 0)

    input_obj = {"draft_text": sample_short_draft}
    context = {
        "run_id": "test-run-001",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    # Validate envelope structure
    validate_envelope(response)
    assert response["status"] == "ok"
    assert "revised" in response["data"]
    assert "changes" in response["data"]
    assert response["data"]["char_count"] < 3000

    # Verify artifact persistence
    artifact_path = temp_run_dir / "50_review.json"
    assert artifact_path.exists()

    # Verify LLM was called
    mock_client.generate_text.assert_called_once()
    call_kwargs = mock_client.generate_text.call_args.kwargs
    assert call_kwargs["temperature"] == 0.3
    assert call_kwargs["use_search_grounding"] is False


def test_reviewer_agent_missing_draft_text(temp_run_dir):
    """Test error handling when draft_text is missing."""
    input_obj = {}
    context = {"run_id": "test-run-002", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


@patch("agents.reviewer_agent.get_text_client")
@patch("agents.reviewer_agent._apply_grammar_corrections")
def test_reviewer_agent_hashtag_removal(
    mock_grammar,
    mock_get_client,
    temp_run_dir,
    sample_draft_with_hashtags,
    mock_cost_tracker,
):
    """Test automatic hashtag removal when post is too long."""
    # Create a version that's ~2990 chars + hashtags (total ~3020)
    # After hashtag removal, should be under 3000
    base_text = "A" * 2990
    long_with_hashtags = base_text + "\n\n#redis #optimization"
    text_without_hashtags = base_text

    # Mock LLM to return the long draft - must return dict with 'text' key
    mock_client = MagicMock()
    mock_client.generate_text.return_value = {
        "text": long_with_hashtags,
        "token_usage": {"prompt_tokens": 200, "completion_tokens": 150},
        "model": "gemini-2.5-pro",
    }
    mock_get_client.return_value = mock_client

    # Mock grammar checking (no changes)
    mock_grammar.return_value = (long_with_hashtags, 0)

    input_obj = {"draft_text": long_with_hashtags}
    context = {
        "run_id": "test-run-003",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    # Should succeed after hashtag removal
    assert response["status"] == "ok"
    assert response["data"]["changes"]["hashtags_removed"] is True
    assert "#redis" not in response["data"]["revised"]
    assert response["data"]["char_count"] < 3000


@patch("agents.reviewer_agent.get_text_client")
@patch("agents.reviewer_agent._apply_grammar_corrections")
def test_reviewer_agent_shortening_loop(
    mock_grammar,
    mock_get_client,
    temp_run_dir,
    sample_long_draft,
    sample_short_draft,
    mock_cost_tracker,
):
    """Test shortening loop when post is too long."""
    # Mock LLM to return long draft first, then short draft - must return dict with 'text' key
    mock_client = MagicMock()
    mock_client.generate_text.side_effect = [
        {
            "text": sample_long_draft,
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 1000},
            "model": "gemini-2.5-pro",
        },
        {
            "text": sample_short_draft,
            "token_usage": {"prompt_tokens": 100, "completion_tokens": 100},
            "model": "gemini-2.5-pro",
        },
    ]
    mock_get_client.return_value = mock_client

    # Mock grammar checking (no changes)
    mock_grammar.side_effect = [
        (sample_long_draft, 0),
        (sample_short_draft, 0),
    ]

    input_obj = {"draft_text": sample_long_draft}
    context = {
        "run_id": "test-run-004",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    # Should succeed after shortening
    assert response["status"] == "ok"
    assert response["data"]["iterations"] >= 2
    assert mock_client.generate_text.call_count >= 2

    # Verify second call included shortening context
    second_call_prompt = mock_client.generate_text.call_args_list[1].kwargs["prompt"]
    assert "too long" in second_call_prompt.lower()
    assert "3000" in second_call_prompt


@patch("agents.reviewer_agent.get_text_client")
@patch("agents.reviewer_agent._apply_grammar_corrections")
def test_reviewer_agent_max_shortening_attempts_exceeded(
    mock_grammar, mock_get_client, temp_run_dir, sample_long_draft, mock_cost_tracker
):
    """Test failure after max shortening attempts."""
    # Mock LLM to always return long draft - must return dict with 'text' key
    mock_client = MagicMock()
    mock_client.generate_text.return_value = {
        "text": sample_long_draft,
        "token_usage": {"prompt_tokens": 100, "completion_tokens": 1000},
        "model": "gemini-2.5-pro",
    }
    mock_get_client.return_value = mock_client

    # Mock grammar checking (no changes)
    mock_grammar.return_value = (sample_long_draft, 0)

    input_obj = {"draft_text": sample_long_draft}
    context = {
        "run_id": "test-run-005",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    # Should fail with ValidationError
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert "shortening attempts" in response["error"]["message"].lower()
    assert response["error"]["retryable"] is False

    # Verify LLM was called 4 times (1 initial + 3 shortening)
    assert mock_client.generate_text.call_count == 4


@patch("agents.reviewer_agent.get_text_client")
@patch("agents.reviewer_agent._apply_grammar_corrections")
def test_reviewer_agent_llm_failure(
    mock_grammar, mock_get_client, temp_run_dir, sample_short_draft, mock_cost_tracker
):
    """Test error handling when LLM call fails."""
    # Mock LLM client to raise exception
    mock_client = MagicMock()
    mock_client.generate_text.side_effect = Exception("API timeout")
    mock_get_client.return_value = mock_client

    # Mock grammar checking
    mock_grammar.return_value = (sample_short_draft, 0)

    input_obj = {"draft_text": sample_short_draft}
    context = {
        "run_id": "test-run-006",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    # Should fail with ModelError
    assert response["status"] == "error"
    assert response["error"]["type"] == "ModelError"
    assert "LLM review failed" in response["error"]["message"]


@patch("agents.reviewer_agent._apply_grammar_corrections")
def test_reviewer_agent_grammar_corrections(mock_grammar, temp_run_dir):
    """Test that grammar corrections are applied."""
    original = "This is a tets post with errrors."
    corrected = "This is a test post with errors."

    # Mock grammar tool
    mock_grammar.return_value = (corrected, 2)

    # We still need to mock LLM - must return dict with 'text' key
    with patch("agents.reviewer_agent.get_text_client") as mock_get_client:
        mock_client = MagicMock()
        mock_client.generate_text.return_value = {
            "text": original,
            "token_usage": {"prompt_tokens": 50, "completion_tokens": 50},
            "model": "gemini-2.5-pro",
        }
        mock_get_client.return_value = mock_client

        input_obj = {"draft_text": original}
        context = {"run_id": "test-run-007", "run_path": temp_run_dir}

        response = run(input_obj, context)

        assert response["status"] == "ok"
        assert response["data"]["changes"]["grammar_corrections"] == 2
        assert response["data"]["grammar_checked"] == corrected


def test_count_chars_excludes_newlines():
    """Test that count_chars excludes line breaks."""
    text_with_newlines = "Hello\nWorld\r\nTest"
    assert count_chars(text_with_newlines) == len("HelloWorldTest")


def test_remove_hashtags():
    """Test hashtag removal logic."""
    text_with_hashtags = """Great content here.

— Tech Audience Accelerator

#redis #optimization #performance"""

    result = _remove_hashtags(text_with_hashtags)

    assert "#redis" not in result
    assert "Tech Audience Accelerator" in result
    assert result.strip().endswith("Tech Audience Accelerator")


def test_remove_hashtags_no_hashtags():
    """Test hashtag removal when there are no hashtags."""
    text_no_hashtags = """Great content here.

— Tech Audience Accelerator"""

    result = _remove_hashtags(text_no_hashtags)

    # Should return unchanged
    assert result == text_no_hashtags


@patch("agents.reviewer_agent.get_text_client")
@patch("agents.reviewer_agent._apply_grammar_corrections")
def test_reviewer_agent_output_structure(
    mock_grammar, mock_get_client, temp_run_dir, sample_short_draft, mock_cost_tracker
):
    """Test that output data structure is correct."""
    # Mock LLM and grammar - must return dict with 'text' key
    mock_client = MagicMock()
    mock_client.generate_text.return_value = {
        "text": sample_short_draft,
        "token_usage": {"prompt_tokens": 100, "completion_tokens": 100},
        "model": "gemini-2.5-pro",
    }
    mock_get_client.return_value = mock_client
    mock_grammar.return_value = (sample_short_draft, 0)

    input_obj = {"draft_text": sample_short_draft}
    context = {
        "run_id": "test-run-008",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    assert response["status"] == "ok"
    data = response["data"]

    # Verify required fields
    assert "original" in data
    assert "llm_revised" in data
    assert "grammar_checked" in data
    assert "revised" in data
    assert "changes" in data
    assert "char_count" in data
    assert "iterations" in data

    # Verify changes structure
    changes = data["changes"]
    assert "llm_changes" in changes
    assert "grammar_corrections" in changes
    assert "hashtags_removed" in changes
    assert "shortening_attempts" in changes
