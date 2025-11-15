"""Research agent (stub).

Generates placeholder sources and summary for the selected topic.
Will later integrate external search / enrichment. Empty sources raise DataNotFoundError.
"""

from pathlib import Path
from typing import Dict, Any, List

from core.envelope import ok, err, validate_envelope
from core.errors import DataNotFoundError, ValidationError
from core.persistence import write_and_verify_json
from core.logging import log_event
from core.run_context import get_artifact_path

STEP_CODE = "20_research"


def _simulate_research(topic: str) -> List[Dict[str, str]]:
    # Simple heuristic stub; later replaced with real research.
    return [
        {"title": f"Deep dive into {topic}", "url": "https://example.com/article1"},
        {
            "title": f"Practical considerations for {topic}",
            "url": "https://example.com/article2",
        },
    ]


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    topic = input_obj.get("topic")
    attempt = 1
    try:
        if not topic:
            raise ValidationError("Missing 'topic' in research agent input")
        sources = _simulate_research(topic)
        if not sources:
            raise DataNotFoundError(f"No sources found for topic '{topic}'")
        summary = f"Summary for {topic}: key themes extracted from {len(sources)} sources (stub)."
        data = {"topic": topic, "sources": sources, "summary": summary}
        artifact_path = get_artifact_path(run_path, STEP_CODE)
        write_and_verify_json(artifact_path, data)
        response = ok(data)
        validate_envelope(response)
        log_event(run_id, "research", attempt, "ok")
        return response
    except (ValidationError, DataNotFoundError) as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "research", attempt, "error", error_type=type(e).__name__)
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        log_event(run_id, "research", attempt, "error", error_type=type(e).__name__)
        return response
