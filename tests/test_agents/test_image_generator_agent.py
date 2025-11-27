"""Tests for image_generator_agent.py (Phase 7.8 - Real Gemini image generation)."""

import tempfile
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock

from agents.image_generator_agent import run, _write_placeholder_png
from core.envelope import validate_envelope


@pytest.fixture
def temp_run_dir():
    """Create a temporary run directory with image prompt file."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_path = Path(tmpdir)

        # Create a sample image prompt file
        prompt_path = run_path / "70_image_prompt.txt"
        prompt_path.write_text(
            "A futuristic data center with flowing streams of light, "
            "cool blue tones, modern aesthetic. Zero text in image."
        )

        yield run_path


@pytest.fixture
def mock_cost_tracker():
    """Mock cost tracker."""
    mock_tracker = MagicMock()
    mock_tracker.check_budget = MagicMock()
    mock_tracker.record_call = MagicMock()
    return mock_tracker


@pytest.fixture
def sample_png_bytes():
    """Sample valid PNG bytes for mocking."""
    return (
        b"\x89PNG\r\n\x1a\n"
        b"\x00\x00\x00\rIHDR"
        b"\x00\x00\x00\x01\x00\x00\x00\x01"
        b"\x08\x02\x00\x00\x00"
        b"\x90wS\xde"
        b"\x00\x00\x00\x0aIDAT"
        b"\x08\xd7c``\x00\x00\x00\x05\x00\x01"
        b"\x02\x7f\xe5\x92"
        b"\x00\x00\x00\x00IEND\xae\x42\x60\x82"
    )


@patch("agents.image_generator_agent.get_image_client")
def test_image_generator_agent_success_with_gemini(
    mock_get_client, temp_run_dir, mock_cost_tracker
):
    """Test successful image generation with Gemini."""
    # Mock image client
    mock_client = MagicMock()

    # Simulate successful image generation
    def mock_generate_image(prompt, output_path, aspect_ratio):
        # Write a valid PNG file
        _write_placeholder_png(Path(output_path))
        return {
            "image_path": str(output_path),
            "model": "gemini-2.5-flash-image",
        }

    mock_client.generate_image = mock_generate_image
    mock_get_client.return_value = mock_client

    prompt_path = temp_run_dir / "70_image_prompt.txt"
    input_obj = {"image_prompt_path": str(prompt_path)}
    context = {
        "run_id": "test-run-001",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    # Validate envelope structure
    validate_envelope(response)
    assert response["status"] == "ok"
    assert "image_path" in response["data"]
    assert "generation_info" in response["data"]

    # Verify generation info
    gen_info = response["data"]["generation_info"]
    assert gen_info["model"] == "gemini-2.5-flash-image"
    assert gen_info["fallback_used"] is False

    # Verify artifact persistence
    artifact_path = temp_run_dir / "80_image.png"
    assert artifact_path.exists()
    assert artifact_path.stat().st_size > 0

    # Verify PNG signature
    with open(artifact_path, "rb") as f:
        signature = f.read(4)
    assert signature == b"\x89PNG"


@patch("agents.image_generator_agent.get_image_client")
def test_image_generator_agent_fallback_to_placeholder(
    mock_get_client, temp_run_dir, mock_cost_tracker
):
    """Test fallback to placeholder when Gemini fails."""
    # Mock image client to raise exception
    mock_client = MagicMock()
    mock_client.generate_image.side_effect = Exception("API rate limit exceeded")
    mock_get_client.return_value = mock_client

    prompt_path = temp_run_dir / "70_image_prompt.txt"
    input_obj = {"image_prompt_path": str(prompt_path)}
    context = {
        "run_id": "test-run-002",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    # Should succeed with fallback
    validate_envelope(response)
    assert response["status"] == "ok"

    # Verify fallback was used
    gen_info = response["data"]["generation_info"]
    assert gen_info["model"] == "placeholder"
    assert gen_info["fallback_used"] is True
    assert "fallback_reason" in gen_info

    # Verify placeholder PNG was created
    artifact_path = temp_run_dir / "80_image.png"
    assert artifact_path.exists()
    assert artifact_path.stat().st_size > 0


def test_image_generator_agent_missing_prompt_path(temp_run_dir):
    """Test error handling when image_prompt_path is missing."""
    input_obj = {}
    context = {"run_id": "test-run-003", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


def test_image_generator_agent_prompt_file_not_found(temp_run_dir):
    """Test error handling when prompt file doesn't exist."""
    input_obj = {"image_prompt_path": str(temp_run_dir / "nonexistent.txt")}
    context = {"run_id": "test-run-004", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert "not found" in response["error"]["message"].lower()


def test_image_generator_agent_empty_prompt_file(temp_run_dir):
    """Test error handling when prompt file is empty."""
    # Create empty prompt file
    empty_prompt = temp_run_dir / "empty_prompt.txt"
    empty_prompt.write_text("")

    input_obj = {"image_prompt_path": str(empty_prompt)}
    context = {"run_id": "test-run-005", "run_path": temp_run_dir}

    response = run(input_obj, context)

    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert "empty" in response["error"]["message"].lower()


@patch("agents.image_generator_agent.get_image_client")
def test_image_generator_agent_creates_valid_png(
    mock_get_client, temp_run_dir, mock_cost_tracker
):
    """Test that generated file is a valid PNG."""
    # Mock image client
    mock_client = MagicMock()

    def mock_generate_image(prompt, output_path, aspect_ratio):
        _write_placeholder_png(Path(output_path))
        return {
            "image_path": str(output_path),
            "model": "gemini-2.5-flash-image",
        }

    mock_client.generate_image = mock_generate_image
    mock_get_client.return_value = mock_client

    prompt_path = temp_run_dir / "70_image_prompt.txt"
    input_obj = {"image_prompt_path": str(prompt_path)}
    context = {
        "run_id": "test-run-006",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    assert response["status"] == "ok"

    artifact_path = temp_run_dir / "80_image.png"

    # Check PNG signature bytes
    with open(artifact_path, "rb") as f:
        signature = f.read(8)

    # PNG signature: \x89PNG\r\n\x1a\n
    assert signature[:4] == b"\x89PNG"
    assert signature[4:8] == b"\r\n\x1a\n"


@patch("agents.image_generator_agent.get_image_client")
def test_image_generator_agent_cost_tracking_integration(
    mock_get_client, temp_run_dir, mock_cost_tracker
):
    """Test that cost tracking is properly integrated."""
    # Mock image client
    mock_client = MagicMock()

    def mock_generate_image(prompt, output_path, aspect_ratio):
        _write_placeholder_png(Path(output_path))
        return {
            "image_path": str(output_path),
            "model": "gemini-2.5-flash-image",
        }

    mock_client.generate_image = mock_generate_image
    mock_get_client.return_value = mock_client

    prompt_path = temp_run_dir / "70_image_prompt.txt"
    input_obj = {"image_prompt_path": str(prompt_path)}
    context = {
        "run_id": "test-run-007",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    assert response["status"] == "ok"

    # Verify budget check was called (first positional arg is model)
    assert mock_cost_tracker.check_budget.call_count == 1
    gen_args, gen_kwargs = mock_cost_tracker.check_budget.call_args
    assert gen_args[0] == "gemini-2.5-flash-image"

    # Verify cost was recorded
    mock_cost_tracker.record_call.assert_called_once()
    call_kwargs = mock_cost_tracker.record_call.call_args.kwargs
    assert call_kwargs["model"] == "gemini-2.5-flash-image"


def test_write_placeholder_png():
    """Test that placeholder PNG is valid."""
    with tempfile.TemporaryDirectory() as tmpdir:
        png_path = Path(tmpdir) / "placeholder.png"

        _write_placeholder_png(png_path)

        assert png_path.exists()
        assert png_path.stat().st_size > 0

        # Verify PNG signature
        with open(png_path, "rb") as f:
            signature = f.read(4)
        assert signature == b"\x89PNG"


@patch("agents.image_generator_agent.get_image_client")
def test_image_generator_agent_reads_prompt_correctly(
    mock_get_client, temp_run_dir, mock_cost_tracker
):
    """Test that agent correctly reads and uses the prompt."""
    # Mock image client to capture the prompt
    mock_client = MagicMock()
    captured_prompt = None

    def mock_generate_image(prompt, output_path, aspect_ratio):
        nonlocal captured_prompt
        captured_prompt = prompt
        _write_placeholder_png(Path(output_path))
        return {
            "image_path": str(output_path),
            "model": "gemini-2.5-flash-image",
        }

    mock_client.generate_image = mock_generate_image
    mock_get_client.return_value = mock_client

    prompt_path = temp_run_dir / "70_image_prompt.txt"
    expected_prompt = prompt_path.read_text().strip()

    input_obj = {"image_prompt_path": str(prompt_path)}
    context = {
        "run_id": "test-run-008",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    assert response["status"] == "ok"
    assert captured_prompt == expected_prompt


@patch("agents.image_generator_agent.get_image_client")
def test_image_generator_agent_aspect_ratio_setting(
    mock_get_client, temp_run_dir, mock_cost_tracker
):
    """Test that agent uses correct aspect ratio for LinkedIn."""
    # Mock image client to capture aspect ratio
    mock_client = MagicMock()
    captured_aspect_ratio = None

    def mock_generate_image(prompt, output_path, aspect_ratio):
        nonlocal captured_aspect_ratio
        captured_aspect_ratio = aspect_ratio
        _write_placeholder_png(Path(output_path))
        return {
            "image_path": str(output_path),
            "model": "gemini-2.5-flash-image",
        }

    mock_client.generate_image = mock_generate_image
    mock_get_client.return_value = mock_client

    prompt_path = temp_run_dir / "70_image_prompt.txt"
    input_obj = {"image_prompt_path": str(prompt_path)}
    context = {
        "run_id": "test-run-009",
        "run_path": temp_run_dir,
        "cost_tracker": mock_cost_tracker,
    }

    response = run(input_obj, context)

    assert response["status"] == "ok"
    # LinkedIn works well with square images
    assert captured_aspect_ratio == "1:1"
