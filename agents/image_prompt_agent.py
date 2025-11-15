"""Image Prompt Generator Agent (stub)."""

from pathlib import Path
from typing import Dict, Any

from core.envelope import ok, err, validate_envelope
from core.errors import ValidationError
from core.persistence import atomic_write_text
from core.logging import log_event
from core.run_context import get_artifact_path

STEP_CODE = "70_image_prompt"


def _build_image_prompt(final_post: str) -> str:
    # Very naive extraction for now
    first_line = (
        final_post.splitlines()[0] if final_post else "Insightful technical post"
    )
    return (
        f"High-resolution conceptual illustration reflecting: '{first_line}'. "
        "Modern minimal style, subtle gradients, clean typography accent, professional tone."
    )


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    final_post = input_obj.get("final_post")
    attempt = 1
    try:
        if not final_post:
            raise ValidationError(
                "Missing 'final_post' text for image prompt generation"
            )
        prompt = _build_image_prompt(final_post)
        artifact_path = get_artifact_path(run_path, STEP_CODE, extension="txt")
        atomic_write_text(artifact_path, prompt)
        response = ok({"image_prompt_path": str(artifact_path)})
        validate_envelope(response)
        log_event(run_id, "image_prompt", attempt, "ok")
        return response
    except ValidationError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "image_prompt", attempt, "error", error_type=type(e).__name__)
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        log_event(run_id, "image_prompt", attempt, "error", error_type=type(e).__name__)
        return response
