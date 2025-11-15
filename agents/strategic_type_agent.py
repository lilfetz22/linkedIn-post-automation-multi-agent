"""Strategic Type Agent (stub).

Uses structured prompt + research summary + (future) RAG memory bank to propose post structure.
"""

from pathlib import Path
from typing import Dict, Any

from core.envelope import ok, err, validate_envelope
from core.errors import ValidationError
from core.persistence import write_and_verify_json
from core.logging import log_event
from core.run_context import get_artifact_path

STEP_CODE = "30_strategy"


def _derive_strategy(structured: Dict[str, Any], research: Dict[str, Any]) -> Dict[str, Any]:
    # Placeholder strategy derivation
    return {
        "structure": "Hook -> Pain -> Insight -> Example -> Impact -> CTA -> Sign-off",
        "strategic_angle": "Translate technical nuance into executive-ready narrative with wit",
        "inputs_used": ["structured_prompt", "research_summary"],
    }


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    structured = input_obj.get("structured_prompt")
    research = input_obj.get("research")
    attempt = 1
    try:
        if not structured or not research:
            raise ValidationError("Missing 'structured_prompt' or 'research' input")
        data = _derive_strategy(structured, research)
        artifact_path = get_artifact_path(run_path, STEP_CODE)
        write_and_verify_json(artifact_path, data)
        response = ok(data)
        validate_envelope(response)
        log_event(run_id, "strategic_type", attempt, "ok")
        return response
    except ValidationError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "strategic_type", attempt, "error", error_type=type(e).__name__)
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        log_event(run_id, "strategic_type", attempt, "error", error_type=type(e).__name__)
        return response
