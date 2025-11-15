"""Topic selection agent.

Selects a new topic for the configured field avoiding recently posted topics.
Persists artifact to 10_topic.json and returns standardized envelope.
"""

from pathlib import Path
from typing import Dict, Any

from core.envelope import ok, err, validate_envelope
from core.errors import DataNotFoundError, ValidationError
from core.persistence import write_and_verify_json
from core.logging import log_event
from core.run_context import get_artifact_path
from database.operations import select_new_topic


STEP_CODE = "10_topic"


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute topic selection.

    input_obj expects: {"field": str, "db_path": optional str}
    context expects: {"run_id": str, "run_path": Path}
    """
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    field = input_obj.get("field")
    db_path = input_obj.get("db_path")

    attempt = 1
    try:
        if not field:
            raise ValidationError("Missing 'field' in topic agent input")

        topic_data = select_new_topic(field=field, db_path=db_path) if db_path else select_new_topic(field=field)
        if not topic_data:
            raise DataNotFoundError(f"No selectable topics remain for field '{field}'")

        artifact_path = get_artifact_path(run_path, STEP_CODE)
        write_and_verify_json(artifact_path, topic_data)

        response = ok(topic_data)
        validate_envelope(response)
        log_event(run_id, "topic_selection", attempt, "ok")
        return response
    except (ValidationError, DataNotFoundError) as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "topic_selection", attempt, "error", error_type=type(e).__name__)
        return response
    except Exception as e:  # Unexpected; treat as retryable generic error
        response = err(type(e).__name__, str(e), retryable=True)
        log_event(run_id, "topic_selection", attempt, "error", error_type=type(e).__name__)
        return response
