"""Prompt Generator Agent (Strategic Content Architect, stub).

Transforms topic + research into structured prompt components.
In future will call LLM with persona template from system_prompts.md.
"""

from pathlib import Path
from typing import Dict, Any

from core.envelope import ok, err, validate_envelope
from core.errors import ValidationError, ModelError
from core.persistence import write_and_verify_json
from core.logging import log_event
from core.run_context import get_artifact_path

STEP_CODE = "25_structured_prompt"
REQUIRED_FIELDS = [
    "topic_title",
    "target_audience",
    "pain_point",
    "key_metrics",
    "analogy",
    "solution_outline",
]


def _build_structured_prompt(topic: str, research_summary: str) -> Dict[str, Any]:
    # Stub logic – deterministic values for now
    return {
        "topic_title": topic.title(),
        "target_audience": "Senior engineers scaling AI/Data systems",
        "pain_point": "Hard to translate complexity into crisp narrative",
        "key_metrics": ["Latency reduction %", "Throughput", "Retrieval hit-rate"],
        "analogy": "Like tuning an orchestra so each instrument supports the melody without noise.",
        "solution_outline": "Stepwise breakdown + strategic framing + wit hooks",
        "raw_summary": research_summary,
    }


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    topic = input_obj.get("topic")
    research = input_obj.get("research")  # expects dict with "summary"
    attempt = 1
    try:
        if not topic or not research:
            raise ValidationError("Missing 'topic' or 'research' input")
        structured = _build_structured_prompt(topic, research.get("summary", ""))
        missing = [f for f in REQUIRED_FIELDS if f not in structured]
        if missing:
            raise ValidationError(f"Structured prompt missing fields: {missing}")
        artifact_path = get_artifact_path(run_path, STEP_CODE)
        write_and_verify_json(artifact_path, structured)
        response = ok(structured)
        validate_envelope(response)
        log_event(run_id, "prompt_generator", attempt, "ok")
        return response
    except (ValidationError,) as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(
            run_id, "prompt_generator", attempt, "error", error_type=type(e).__name__
        )
        return response
    except ModelError as e:  # Placeholder for future LLM errors
        response = err(type(e).__name__, str(e), retryable=True)
        log_event(
            run_id, "prompt_generator", attempt, "error", error_type=type(e).__name__
        )
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        validate_envelope(response)
        log_event(
            run_id, "prompt_generator", attempt, "error", error_type=type(e).__name__
        )
        return response
