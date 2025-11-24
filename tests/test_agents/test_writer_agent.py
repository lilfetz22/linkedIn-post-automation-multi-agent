"""Tests for writer_agent.py (Phase 7.5 - LLM-powered)."""

import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from agents.writer_agent import run, count_chars
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
        "code_snippet": "redis.config('maxmemory-policy', 'allkeys-lru')",
    }


@pytest.fixture
def mock_short_draft():
    """Sample short draft (under 3000 chars)."""
    return """**Redis Optimization: The Race Car Tuning Analogy**

Ever feel like Redis is a race car engine that's either overheating or underperforming?

**The Problem:** Balancing memory vs latency is like tuning a race car—push too hard on speed, and you'll blow the engine. Play it too safe, and you'll never win.

**The Solution:** Use a step-by-step framework. Start with `maxmemory-policy` set to `allkeys-lru`. Monitor memory usage and P99 latency.

**The Impact:** You'll see 40% reduction in memory footprint with no latency increase.

**The Action:** Try this one-line config change today.

— Tech Audience Accelerator"""


@pytest.fixture
def mock_long_draft():
    """Sample long draft (over 3000 chars)."""
    return "A" * 3100  # Exceeds MAX_CHAR_COUNT


@pytest.fixture
def mock_cost_tracker():
    """Mock cost tracker."""
    mock_tracker = MagicMock()
    mock_tracker.check_budget = MagicMock()
    mock_tracker.record_call = MagicMock()
    return mock_tracker


@patch("agents.writer_agent.load_system_prompt")
@patch("agents.writer_agent.get_text_client")
def test_writer_agent_success(
    mock_get_client, mock_load_prompt,
    temp_run_dir, sample_structured_prompt, mock_short_draft, mock_cost_tracker
):
    """Test successful draft writing with LLM."""
    # Mock system prompt loader
    mock_load_prompt.return_value = "You are the Witty Expert persona."
    
    # Mock LLM client
    mock_client = MagicMock()
    mock_client.generate_text.return_value = mock_short_draft
    mock_get_client.return_value = mock_client
    
    input_obj = {
        "structured_prompt": sample_structured_prompt,
    }
    context = {
        "run_id": "test-run-001",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

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
    # Check content is present (ignore encoding issues with em dashes)
    assert "Redis Optimization" in draft_text
    assert "race car" in draft_text
    
    # Verify LLM was called
    mock_client.generate_text.assert_called_once()
    call_kwargs = mock_client.generate_text.call_args.kwargs
    assert call_kwargs["temperature"] == 0.8
    assert call_kwargs["use_search_grounding"] is False


def test_writer_agent_missing_structured_prompt(temp_run_dir):
    """Test error handling when structured_prompt is missing."""
    input_obj = {}
    context = {"run_id": "test-run-002", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


@patch("agents.writer_agent.load_system_prompt")
@patch("agents.writer_agent.get_text_client")
def test_writer_agent_character_count_loop(
    mock_get_client, mock_load_prompt,
    temp_run_dir, sample_structured_prompt, mock_long_draft, mock_short_draft, mock_cost_tracker
):
    """Test internal character count shortening loop."""
    # Mock system prompt loader
    mock_load_prompt.return_value = "You are the Witty Expert persona."
    
    # Mock LLM client to return long draft first, then short draft
    mock_client = MagicMock()
    mock_client.generate_text.side_effect = [mock_long_draft, mock_short_draft]
    mock_get_client.return_value = mock_client
    
    input_obj = {
        "structured_prompt": sample_structured_prompt,
    }
    context = {
        "run_id": "test-run-003",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    # Should succeed after shortening
    assert response["status"] == "ok"
    
    # Verify LLM was called twice (once for initial, once for shortening)
    assert mock_client.generate_text.call_count == 2
    
    # Verify second call included shortening context
    second_call_prompt = mock_client.generate_text.call_args_list[1].kwargs["prompt"]
    assert "IMPORTANT: Character Count Issue" in second_call_prompt
    assert mock_long_draft in second_call_prompt


@patch("agents.writer_agent.load_system_prompt")
@patch("agents.writer_agent.get_text_client")
def test_writer_agent_max_shortening_attempts_exceeded(
    mock_get_client, mock_load_prompt,
    temp_run_dir, sample_structured_prompt, mock_long_draft, mock_cost_tracker
):
    """Test failure after max shortening attempts."""
    # Mock system prompt loader
    mock_load_prompt.return_value = "You are the Witty Expert persona."
    
    # Mock LLM client to always return long draft
    mock_client = MagicMock()
    mock_client.generate_text.return_value = mock_long_draft
    mock_get_client.return_value = mock_client
    
    input_obj = {
        "structured_prompt": sample_structured_prompt,
    }
    context = {
        "run_id": "test-run-004",
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


@patch("agents.writer_agent.load_system_prompt")
@patch("agents.writer_agent.get_text_client")
def test_writer_agent_llm_failure(
    mock_get_client, mock_load_prompt,
    temp_run_dir, sample_structured_prompt, mock_cost_tracker
):
    """Test error handling when LLM call fails."""
    # Mock system prompt loader
    mock_load_prompt.return_value = "You are the Witty Expert persona."
    
    # Mock LLM client to raise exception
    mock_client = MagicMock()
    mock_client.generate_text.side_effect = Exception("API timeout")
    mock_get_client.return_value = mock_client
    
    input_obj = {
        "structured_prompt": sample_structured_prompt,
    }
    context = {
        "run_id": "test-run-005",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    # Should fail with ModelError
    assert response["status"] == "error"
    assert response["error"]["type"] == "ModelError"
    assert "LLM generation failed" in response["error"]["message"]


def test_count_chars_excludes_newlines():
    """Test that count_chars excludes line breaks."""
    text_with_newlines = "Hello\nWorld\r\nTest"
    assert count_chars(text_with_newlines) == len("HelloWorldTest")


@patch("agents.writer_agent.load_system_prompt")
@patch("agents.writer_agent.get_text_client")
def test_writer_agent_formats_prompt_correctly(
    mock_get_client, mock_load_prompt,
    temp_run_dir, sample_structured_prompt, mock_short_draft, mock_cost_tracker
):
    """Test that structured prompt is formatted correctly for LLM."""
    # Mock system prompt loader
    mock_load_prompt.return_value = "You are the Witty Expert persona."
    
    # Mock LLM client
    mock_client = MagicMock()
    mock_client.generate_text.return_value = mock_short_draft
    mock_get_client.return_value = mock_client
    
    input_obj = {
        "structured_prompt": sample_structured_prompt,
    }
    context = {
        "run_id": "test-run-007",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    assert response["status"] == "ok"
    
    # Verify prompt contains key elements
    call_prompt = mock_client.generate_text.call_args.kwargs["prompt"]
    assert "Redis Optimization Strategies" in call_prompt
    assert "Hard to balance memory vs latency" in call_prompt
    assert "Like tuning a race car engine" in call_prompt
    assert "Tech Audience Accelerator" in call_prompt
