"""Image Generator Agent (stub).

Creates placeholder PNG file. Future: integrate Gemini image model.
"""

from pathlib import Path
from typing import Dict, Any

from core.envelope import ok, err, validate_envelope
from core.errors import ValidationError, ModelError
from core.logging import log_event
from core.run_context import get_artifact_path

STEP_CODE = "80_image"


def _write_placeholder_png(path: Path) -> None:
    # Minimal valid PNG header bytes
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"  # Signature
        b"\x00\x00\x00\rIHDR"  # IHDR chunk length + type
        b"\x00\x00\x00\x01\x00\x00\x00\x01"  # 1x1 px
        b"\x08\x02\x00\x00\x00"  # bit depth, color type
        b"\x90wS\xde"  # CRC (placeholder)
        b"\x00\x00\x00\x0aIDAT"  # IDAT chunk (length placeholder)
        b"\x08\xd7c``\x00\x00\x00\x05\x00\x01"  # compressed data (tiny)
        b"\x02\x7f\xe5\x92"  # CRC
        b"\x00\x00\x00\x00IEND\xae\x42\x60\x82"  # IEND
    )
    path.write_bytes(png_bytes)


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    image_prompt_path = input_obj.get("image_prompt_path")  # not used yet
    attempt = 1
    try:
        if not image_prompt_path:
            raise ValidationError("Missing 'image_prompt_path' for image generation")
        artifact_path = get_artifact_path(run_path, STEP_CODE, extension="png")
        _write_placeholder_png(artifact_path)
        if artifact_path.stat().st_size == 0:
            raise ModelError("Generated image file is empty")
        response = ok({"image_path": str(artifact_path)})
        validate_envelope(response)
        log_event(run_id, "image_generation", attempt, "ok")
        return response
    except (ValidationError, ModelError) as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(
            run_id, "image_generation", attempt, "error", error_type=type(e).__name__
        )
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        log_event(
            run_id, "image_generation", attempt, "error", error_type=type(e).__name__
        )
        return response
