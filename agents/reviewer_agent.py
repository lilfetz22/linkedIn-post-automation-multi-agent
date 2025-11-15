"""Reviewer Agent (stub).

Performs two-pass review on draft markdown: contextual then grammar.
Returns revised text and simple change list.
"""

from pathlib import Path
from typing import Dict, Any, List

from core.envelope import ok, err, validate_envelope
from core.errors import ValidationError
from core.persistence import write_and_verify_json
from core.logging import log_event
from core.run_context import get_artifact_path

STEP_CODE = "50_review"


def _contextual_pass(text: str) -> str:
    # Stub: ensure required sections exist; append a coherence note.
    if "Strategic Angle:" not in text:
        text += "\n\nStrategic Angle: (added stub)"
    return text + "\n\n[Context Pass OK]"


def _grammar_pass(text: str) -> str:
    # Stub: replace double spaces, minor formatting.
    return text.replace("  ", " ") + "\n[Grammar Pass OK]"


def _diff(original: str, revised: str) -> List[Dict[str, str]]:
    if original == revised:
        return []
    return [
        {
            "change": "modified",
            "original_len": str(len(original)),
            "revised_len": str(len(revised)),
        }
    ]


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    draft_text = input_obj.get("draft_text")  # direct text content expected
    attempt = 1
    try:
        if not draft_text:
            raise ValidationError("Missing 'draft_text' for reviewer")
        pass1 = _contextual_pass(draft_text)
        pass2 = _grammar_pass(pass1)
        changes = _diff(draft_text, pass2)
        data = {"original": draft_text, "revised": pass2, "changes": changes}
        artifact_path = get_artifact_path(run_path, STEP_CODE)
        write_and_verify_json(artifact_path, data)
        response = ok(data)
        validate_envelope(response)
        log_event(run_id, "reviewer", attempt, "ok")
        return response
    except ValidationError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "reviewer", attempt, "error", error_type=type(e).__name__)
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        log_event(run_id, "reviewer", attempt, "error", error_type=type(e).__name__)
        return response
