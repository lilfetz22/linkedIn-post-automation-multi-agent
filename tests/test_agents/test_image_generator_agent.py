"""Tests for image_generator_agent.py."""

import tempfile
from pathlib import Path
import pytest

from agents.image_generator_agent import run
from core.envelope import validate_envelope


@pytest.fixture
def temp_run_dir():
    """Create a temporary run directory."""
    with tempfile.TemporaryDirectory() as tmpdir:
        run_path = Path(tmpdir)
        
        # Create a placeholder image prompt file
        prompt_path = Path(tmpdir) / "70_image_prompt.txt"
        prompt_path.write_text("Test image prompt")
        
        yield run_path


def test_image_generator_agent_success(temp_run_dir):
    """Test successful image generation."""
    prompt_path = temp_run_dir / "70_image_prompt.txt"
    input_obj = {"image_prompt_path": str(prompt_path)}
    context = {"run_id": "test-run-001", "run_path": temp_run_dir}
    
    response = run(input_obj, context)
    
    # Validate envelope structure
    validate_envelope(response)
    assert response["status"] == "ok"
    assert "image_path" in response["data"]
    
    # Verify artifact persistence
    artifact_path = temp_run_dir / "80_image.png"
    assert artifact_path.exists()
    
    # Verify file is not empty
    assert artifact_path.stat().st_size > 0


def test_image_generator_agent_missing_prompt_path(temp_run_dir):
    """Test error handling when image_prompt_path is missing."""
    input_obj = {}
    context = {"run_id": "test-run-002", "run_path": temp_run_dir}
    
    response = run(input_obj, context)
    
    validate_envelope(response)
    assert response["status"] == "error"
    assert response["error"]["type"] == "ValidationError"
    assert response["error"]["retryable"] is False


def test_image_generator_agent_creates_png(temp_run_dir):
    """Test that generated file is a PNG."""
    prompt_path = temp_run_dir / "70_image_prompt.txt"
    input_obj = {"image_prompt_path": str(prompt_path)}
    context = {"run_id": "test-run-003", "run_path": temp_run_dir}
    
    response = run(input_obj, context)
    
    assert response["status"] == "ok"
    
    artifact_path = temp_run_dir / "80_image.png"
    
    # Check PNG signature bytes
    with open(artifact_path, "rb") as f:
        signature = f.read(8)
    
    # PNG signature: \x89PNG\r\n\x1a\n
    assert signature[:4] == b"\x89PNG"


def test_image_generator_agent_validates_file_size(temp_run_dir):
    """Test that agent validates generated file is non-empty."""
    prompt_path = temp_run_dir / "70_image_prompt.txt"
    input_obj = {"image_prompt_path": str(prompt_path)}
    context = {"run_id": "test-run-004", "run_path": temp_run_dir}
    
    response = run(input_obj, context)
    
    assert response["status"] == "ok"
    
    artifact_path = temp_run_dir / "80_image.png"
    size = artifact_path.stat().st_size
    
    # Should be larger than just the header
    assert size > 50  # Placeholder PNG is small but > 50 bytes


def test_image_generator_agent_returns_correct_path(temp_run_dir):
    """Test that response includes correct image path."""
    prompt_path = temp_run_dir / "70_image_prompt.txt"
    input_obj = {"image_prompt_path": str(prompt_path)}
    context = {"run_id": "test-run-005", "run_path": temp_run_dir}
    
    response = run(input_obj, context)
    
    assert response["status"] == "ok"
    
    returned_path = Path(response["data"]["image_path"])
    expected_path = temp_run_dir / "80_image.png"
    
    # Should match expected path
    assert returned_path == expected_path
