"""Tests for image_prompt_agent.py (Phase 7.7 - LLM-powered Visual Strategist)."""

import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from agents.image_prompt_agent import run, _validate_no_text_constraint
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
    return """**Redis Optimization: The Race Car Tuning Analogy**

Ever feel like Redis is a race car engine that's either overheating or underperforming?

**The Problem:** Balancing memory vs latency is like tuning a race car.

**The Solution:** Use maxmemory-policy set to allkeys-lru.

**The Impact:** 40% reduction in memory footprint.

— Tech Audience Accelerator"""


@pytest.fixture
def sample_valid_prompt():
    """Sample valid image prompt with no-text constraint."""
    return """A sleek race car engine with glowing red and blue circuits, 
representing the balance between speed and efficiency. The scene is set in a 
modern, minimalist garage with dramatic side lighting creating strong shadows. 
The mood is focused and precise, with cool metallic tones. 
**Critical: The image must contain zero text, words, or letters.**"""


@pytest.fixture
def sample_invalid_prompt():
    """Sample invalid prompt missing no-text constraint."""
    return """A race car engine with circuits, modern garage setting, 
dramatic lighting, cool metallic tones."""


@pytest.fixture
def mock_cost_tracker():
    """Mock cost tracker."""
    mock_tracker = MagicMock()
    mock_tracker.check_budget = MagicMock()
    mock_tracker.record_call = MagicMock()
    return mock_tracker


@patch("agents.image_prompt_agent.get_text_client")
def test_image_prompt_agent_success(
    mock_get_client, temp_run_dir, sample_final_post, 
    sample_valid_prompt, mock_cost_tracker
):
    """Test successful image prompt generation with LLM."""
    # Mock LLM client
    mock_client = MagicMock()
    mock_client.generate_text.return_value = sample_valid_prompt
    mock_get_client.return_value = mock_client
    
    input_obj = {"final_post": sample_final_post}
    context = {
        "run_id": "test-run-001",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    # Validate envelope structure
    validate_envelope(response)
    assert response["status"] == "ok"
    assert "image_prompt_path" in response["data"]
    assert "prompt_preview" in response["data"]
    
    # Verify artifact persistence
    artifact_path = temp_run_dir / "70_image_prompt.txt"
    assert artifact_path.exists()
    
    prompt_text = artifact_path.read_text()
    assert len(prompt_text) > 0
    assert "zero text" in prompt_text.lower() or "no text" in prompt_text.lower()
    
    # Verify LLM was called with correct parameters
    mock_client.generate_text.assert_called_once()
    call_kwargs = mock_client.generate_text.call_args.kwargs
    assert call_kwargs["temperature"] == 0.6
    assert call_kwargs["use_search_grounding"] is False
    assert "Visual Strategist" in call_kwargs["system_instruction"]
    
    # Verify post content was in prompt
    assert sample_final_post in call_kwargs["prompt"]


def test_image_prompt_agent_missing_final_post(temp_run_dir):
    """Test error handling when final_post is missing."""
    input_obj = {}
    context = {"run_id": "test-run-002", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


def test_image_prompt_agent_empty_final_post(temp_run_dir):
    """Test error handling when final_post is empty."""
    input_obj = {"final_post": "   "}
    context = {"run_id": "test-run-003", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert "Empty" in response["error"]["message"]


@patch("agents.image_prompt_agent.get_text_client")
def test_image_prompt_agent_validates_no_text_constraint(
    mock_get_client, temp_run_dir, sample_final_post, 
    sample_invalid_prompt, mock_cost_tracker
):
    """Test that agent validates no-text constraint is present."""
    # Mock LLM to return invalid prompt (missing no-text constraint)
    mock_client = MagicMock()
    mock_client.generate_text.return_value = sample_invalid_prompt
    mock_get_client.return_value = mock_client
    
    input_obj = {"final_post": sample_final_post}
    context = {
        "run_id": "test-run-004",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    # Should fail validation
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert "no text" in response["error"]["message"].lower()


@patch("agents.image_prompt_agent.get_text_client")
def test_image_prompt_agent_llm_failure(
    mock_get_client, temp_run_dir, sample_final_post, mock_cost_tracker
):
    """Test error handling when LLM call fails."""
    # Mock LLM client to raise exception
    mock_client = MagicMock()
    mock_client.generate_text.side_effect = Exception("API timeout")
    mock_get_client.return_value = mock_client
    
    input_obj = {"final_post": sample_final_post}
    context = {
        "run_id": "test-run-005",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    # Should fail with ModelError
    assert response["status"] == "error"
    assert response["error"]["type"] == "ModelError"
    assert "LLM image prompt generation failed" in response["error"]["message"]


def test_validate_no_text_constraint_accepts_valid():
    """Test no-text constraint validation accepts valid prompts."""
    valid_prompts = [
        "A scene with zero text in the image",
        "Visual with no text or words",
        "Image without text, words, or letters",
        "Must contain no words on the visual",
        "The image should be text-free and word-free",
    ]
    
    for prompt in valid_prompts:
        assert _validate_no_text_constraint(prompt) is True


def test_validate_no_text_constraint_rejects_invalid():
    """Test no-text constraint validation rejects invalid prompts."""
    invalid_prompts = [
        "A beautiful scene with dramatic lighting",
        "Modern minimal style with gradients",
        "Professional tone and clean composition",
    ]
    
    for prompt in invalid_prompts:
        assert _validate_no_text_constraint(prompt) is False


@patch("agents.image_prompt_agent.get_text_client")
def test_image_prompt_agent_prompt_preview(
    mock_get_client, temp_run_dir, sample_final_post, 
    sample_valid_prompt, mock_cost_tracker
):
    """Test that prompt_preview is truncated correctly."""
    # Create a long prompt
    long_prompt = sample_valid_prompt + " " + ("A" * 200)
    
    mock_client = MagicMock()
    mock_client.generate_text.return_value = long_prompt
    mock_get_client.return_value = mock_client
    
    input_obj = {"final_post": sample_final_post}
    context = {
        "run_id": "test-run-006",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    assert response["status"] == "ok"
    preview = response["data"]["prompt_preview"]
    
    # Should be truncated to 100 chars + "..."
    assert len(preview) <= 103  # 100 chars + "..."
    if len(long_prompt) > 100:
        assert preview.endswith("...")


@patch("agents.image_prompt_agent.get_text_client")
def test_image_prompt_agent_includes_visual_elements(
    mock_get_client, temp_run_dir, sample_final_post, mock_cost_tracker
):
    """Test that generated prompt includes visual elements."""
    # Mock a realistic prompt
    realistic_prompt = """A high-tech data center with flowing streams of light 
representing data pipelines, set against a dark background with cool blue and 
green accent lighting. The mood is efficient and futuristic, with sharp focus 
on the central data flow. Modern minimal aesthetic with subtle gradients. 
The image must contain zero text, words, or letters."""
    
    mock_client = MagicMock()
    mock_client.generate_text.return_value = realistic_prompt
    mock_get_client.return_value = mock_client
    
    input_obj = {"final_post": sample_final_post}
    context = {
        "run_id": "test-run-007",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    assert response["status"] == "ok"
    
    artifact_path = temp_run_dir / "70_image_prompt.txt"
    prompt_text = artifact_path.read_text().lower()
    
    # Should include visual style elements
    visual_elements = ["lighting", "mood", "setting", "background", "aesthetic", "style"]
    assert any(element in prompt_text for element in visual_elements)


@patch("agents.image_prompt_agent.get_text_client")
def test_image_prompt_agent_cost_tracking_integration(
    mock_get_client, temp_run_dir, sample_final_post, 
    sample_valid_prompt, mock_cost_tracker
):
    """Test that cost tracking is properly integrated."""
    mock_client = MagicMock()
    mock_client.generate_text.return_value = sample_valid_prompt
    mock_get_client.return_value = mock_client
    
    input_obj = {"final_post": sample_final_post}
    context = {
        "run_id": "test-run-008",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    assert response["status"] == "ok"
    
    # Verify budget check was called
    mock_cost_tracker.check_budget.assert_called_once_with("gemini-2.5-pro")
    
    # Verify cost was recorded
    mock_cost_tracker.record_call.assert_called_once()
    call_kwargs = mock_cost_tracker.record_call.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-pro"
