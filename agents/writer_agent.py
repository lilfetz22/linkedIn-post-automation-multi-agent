"""Writer Agent (The Witty Expert persona, stub).

Generates a markdown draft from structured prompt + strategy.
"""

from pathlib import Path
from typing import Dict, Any

from core.envelope import ok, err, validate_envelope
from core.errors import ValidationError
from core.persistence import atomic_write_text
from core.logging import log_event
from core.run_context import get_artifact_path

STEP_CODE = "40_draft"


def _compose_markdown(structured: Dict[str, Any], strategy: Dict[str, Any]) -> str:
    title = structured.get("topic_title", "Untitled")
    pain = structured.get("pain_point", "")
    analogy = structured.get("analogy", "")
    solution = structured.get("solution_outline", "")
    strategic_angle = strategy.get("strategic_angle", "")
    return (
        f"**{title}**\n\n"
        f"Problem: {pain}\n\n"
        f"Analogy: {analogy}\n\n"
        f"Solution Outline: {solution}\n\n"
        f"Strategic Angle: {strategic_angle}\n\n"
        "CTA: Comment with your biggest bottleneck.\n\n"
        "— Witty Expert"
    )


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    structured = input_obj.get("structured_prompt")
    strategy = input_obj.get("strategy")
    attempt = 1
    try:
        if not structured or not strategy:
            raise ValidationError("Missing 'structured_prompt' or 'strategy' input")
        draft = _compose_markdown(structured, strategy)
        artifact_path = get_artifact_path(run_path, STEP_CODE, extension="md")
        atomic_write_text(artifact_path, draft)
        response = ok({"draft_path": str(artifact_path)})
        validate_envelope(response)
        log_event(run_id, "writer", attempt, "ok")
        return response
    except ValidationError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "writer", attempt, "error", error_type=type(e).__name__)
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        validate_envelope(response)
        log_event(run_id, "writer", attempt, "error", error_type=type(e).__name__)
        return response
