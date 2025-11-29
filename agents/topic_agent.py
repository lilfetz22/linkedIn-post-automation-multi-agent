"""Topic selection agent.

Selects a new topic for the configured field avoiding recently posted topics.
If database is empty, falls back to LLM-generated topics.
Persists artifact to 10_topic.json and returns standardized envelope.
"""

from pathlib import Path
from typing import Dict, Any, List
import json

from core.envelope import ok, err, validate_envelope
from core.errors import DataNotFoundError, ValidationError, ModelError
from core.persistence import write_and_verify_json
from core.logging import log_event
from core.run_context import get_artifact_path
from core.llm_clients import get_text_client
from core.cost_tracking import CostMetrics
from database.operations import select_new_topic, get_recent_topics


STEP_CODE = "10_topic"


def _generate_topics_with_llm(field: str, recent_topics: List[str], cost_tracker=None) -> str:
    """
    Use LLM to generate a new topic when database is empty.

    Args:
        field: The field to generate topics for
        recent_topics: List of recently posted topics to avoid
        cost_tracker: Optional cost tracker for budget management

    Returns:
        A new topic string

    Raises:
        ModelError: If LLM call fails
    """
    recent_text = (
        "\n".join(f"- {topic}" for topic in recent_topics) if recent_topics else "None"
    )

    prompt = f"""Generate 10 topic candidates for {field}. 

Prefer net-new, specific topics (emerging trends, overlooked fundamentals, concrete pain points).

You MAY reuse a previously covered macro-topic ONLY if proposing a distinctly new avenue 
(fresh sub-problem, perspective, data source, or audience pain point). Otherwise produce 
topics not yet posted.

Recently posted topics to avoid or reimagine:
{recent_text}

Return ONLY a JSON array of topic objects, each with:
- "topic": the topic title (string)
- "novelty": either "net_new" or "reused_with_new_angle" (string)
- "rationale": brief explanation of why this is valuable (string)

Example format:
[
    {{"topic": "Topic 1", "novelty": "net_new", "rationale": "..."}},
    {{"topic": "Topic 2", "novelty": "reused_with_new_angle", "rationale": "..."}}
]"""

    # Check budget before API call
    if cost_tracker:
        cost_tracker.check_budget("gemini-2.5-pro", prompt)

    client = get_text_client()
    result = client.generate_text(
        prompt=prompt,
        temperature=0.8,  # Higher temperature for creative topic generation
        max_output_tokens=2000,
        use_search_grounding=True  # Enable Google Search for current trends
    )

    # Parse JSON response
    text = result["text"].strip()
    # Remove markdown code blocks if present
    if text.startswith("```json"):
        text = text[7:]
    if text.startswith("```"):
        text = text[3:]
    if text.endswith("```"):
        text = text[:-3]
    text = text.strip()

    topics = json.loads(text)

    # Prioritize net_new topics, fall back to reused_with_new_angle
    for topic_obj in topics:
        if topic_obj.get("novelty") == "net_new":
            return topic_obj["topic"]

    # If no net_new, accept first reused_with_new_angle
    for topic_obj in topics:
        if topic_obj.get("novelty") == "reused_with_new_angle":
            return topic_obj["topic"]

    # Fallback: return first topic regardless
    if topics:
        return topics[0]["topic"]

    raise ModelError("LLM failed to generate any valid topics")


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Execute topic selection.

    input_obj expects: {"field": str, "db_path": optional str}
    context expects: {"run_id": str, "run_path": Path, "cost_tracker": optional CostTracker}
    """
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    field = input_obj.get("field")
    db_path = input_obj.get("db_path")
    cost_tracker = context.get("cost_tracker")

    attempt = 1
    metrics_dict = {}

    try:
        if not field:
            raise ValidationError("Missing 'field' in topic agent input")

        # Try database first
        topic_data = (
            select_new_topic(field=field, db_path=db_path)
            if db_path
            else select_new_topic(field=field)
        )

        # If database is empty, use LLM fallback
        if not topic_data:
            recent = get_recent_topics(limit=10, db_path=db_path) if db_path else []

            try:
                topic = _generate_topics_with_llm(field, recent, cost_tracker)
                topic_data = {"topic": topic}

                # Track cost if tracker provided
                if cost_tracker:
                    # Estimate cost (this is a fallback, actual usage tracked in client)
                    cost_metrics = CostMetrics(
                        model="gemini-2.5-pro",
                        input_tokens=500,  # Estimate
                        output_tokens=1000,  # Estimate
                    )
                    cost_tracker.record_call("topic_agent_llm_fallback", cost_metrics)
                    metrics_dict["cost_usd"] = cost_metrics.cost_usd

            except (ModelError, json.JSONDecodeError) as llm_err:
                # LLM fallback failed
                raise DataNotFoundError(
                    f"No topics in database and LLM fallback failed: {str(llm_err)}"
                )

        artifact_path = get_artifact_path(run_path, STEP_CODE)
        write_and_verify_json(artifact_path, topic_data)

        response = ok(topic_data, metrics=metrics_dict if metrics_dict else None)
        validate_envelope(response)
        log_event(run_id, "topic_selection", attempt, "ok")
        return response

    except (ValidationError, DataNotFoundError) as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(
            run_id, "topic_selection", attempt, "error", error_type=type(e).__name__
        )
        return response
    except Exception as e:  # Unexpected; treat as retryable generic error
        response = err(type(e).__name__, str(e), retryable=True)
        validate_envelope(response)
        log_event(
            run_id, "topic_selection", attempt, "error", error_type=type(e).__name__
        )
        return response
