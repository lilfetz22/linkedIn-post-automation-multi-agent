"""Tests for prompt_generator_agent.py.

Contains long mock response strings for test fixtures.
"""
# flake8: noqa: E501

import tempfile
from pathlib import Path
import pytest
import json
from unittest.mock import patch

from agents.prompt_generator_agent import run, _validate_prompt_structure
from core.envelope import validate_envelope
from core.errors import ValidationError


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
    """Test successful prompt generation with mocked LLM."""
    input_obj = {"topic": "Redis optimization", "research": sample_research}
    context = {"run_id": "test-run-001", "run_path": temp_run_dir}

    # Mock LLM response with valid structured prompt
    mock_prompt = """Generate a LinkedIn post using the Witty Expert persona.

**Topic:** Redis Optimization: The Art of Speed Without Compromise

**Target Audience:** Backend Engineers and Platform Architects managing high-throughput data systems

**Audience's Core Pain Point:** My Redis instance keeps hitting latency spikes during peak traffic, and I'm constantly firefighting performance issues instead of building features. Every optimization feels like a band-aid, not a real solution.

**Key Metrics/Facts:** Redis can handle 100k+ operations per second with sub-millisecond latency.
- Think of an unoptimized Redis setup as a skilled chef working with a cluttered kitchen: they know what to cook, but spend half their time searching for the right pan. Every wasted moment compounds into visible slowdowns.
- An optimized Redis is that same chef in a meticulously organized kitchen: every tool has its place, movements are fluid, and dishes flow from prep to plate without friction.

**The Simple Solution/Code Snippet:** The "Aha!" moment is connection pooling combined with efficient data structures.
```python
# Instead of creating new connections repeatedly
r = redis.Redis(host='localhost', port=6379)

# Use connection pooling for dramatic improvement
pool = redis.ConnectionPool(host='localhost', port=6379, max_connections=50)
r = redis.Redis(connection_pool=pool)
```
"""

    mock_llm_response = {
        "text": mock_prompt,
        "token_usage": {"prompt_tokens": 200, "completion_tokens": 400},
        "model": "gemini-2.5-pro",
    }

    with patch("agents.prompt_generator_agent.get_text_client") as mock_client:
        mock_client.return_value.generate_text.return_value = mock_llm_response

        response = run(input_obj, context)

        # Validate envelope structure
        validate_envelope(response)
        assert response["status"] == "ok"

        # Verify structured prompt is present
        assert "structured_prompt" in response["data"]
        assert "**Topic:**" in response["data"]["structured_prompt"]
        assert "**Target Audience:**" in response["data"]["structured_prompt"]

        # Verify artifact persistence
        artifact_path = temp_run_dir / "25_structured_prompt.json"
        assert artifact_path.exists()

        with open(artifact_path) as f:
            artifact_data = json.load(f)
        assert "structured_prompt" in artifact_data


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


def test_prompt_generator_rejects_cliche_analogies(temp_run_dir, sample_research):
    """Test that validation rejects prompts with clichéd analogies."""
    input_obj = {"topic": "Blockchain consensus", "research": sample_research}
    context = {"run_id": "test-run-004", "run_path": temp_run_dir}

    # Mock LLM response with cliché
    mock_prompt_with_cliche = """Generate a LinkedIn post using the Witty Expert persona.

**Topic:** Blockchain Consensus

**Target Audience:** Distributed Systems Engineers

**Audience's Core Pain Point:** Understanding consensus mechanisms

**Key Metrics/Facts:** Blockchain is like a distributed ledger that everyone can see.

**The Simple Solution/Code Snippet:** Use proof of stake."""

    mock_llm_response = {
        "text": mock_prompt_with_cliche,
        "token_usage": {"prompt_tokens": 100, "completion_tokens": 200},
        "model": "gemini-2.5-pro",
    }

    with patch("agents.prompt_generator_agent.get_text_client") as mock_client:
        mock_client.return_value.generate_text.return_value = mock_llm_response

        response = run(input_obj, context)

        # Should reject due to cliché
        assert response["status"] == "error"
        assert response["error"]["type"] == "ValidationError"
        assert "cliché" in response["error"]["message"].lower()


def test_prompt_generator_validates_required_sections(temp_run_dir, sample_research):
    """Test that validation checks for all required sections."""
    # Test validation function directly
    valid_prompt = """**Topic:** Test
**Target Audience:** Engineers
**Audience's Core Pain Point:** Problems
**Key Metrics/Facts:** Data
**The Simple Solution/Code Snippet:** Code here"""

    # Should not raise
    _validate_prompt_structure(valid_prompt)

    # Missing section should raise
    invalid_prompt = """**Topic:** Test
**Target Audience:** Engineers"""

    with pytest.raises(ValidationError, match="missing required sections"):
        _validate_prompt_structure(invalid_prompt)


def test_prompt_generator_llm_failure(temp_run_dir, sample_research):
    """Test handling of LLM failure."""
    input_obj = {"topic": "Test topic", "research": sample_research}
    context = {"run_id": "test-run-005", "run_path": temp_run_dir}

    from core.errors import ModelError

    with patch("agents.prompt_generator_agent.get_text_client") as mock_client:
        mock_client.return_value.generate_text.side_effect = ModelError(
            "LLM unavailable"
        )

        response = run(input_obj, context)

        validate_envelope(response)
        assert response["status"] == "error"
        assert response["error"]["type"] == "ModelError"
        assert response["error"]["retryable"] is True
