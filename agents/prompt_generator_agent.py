"""Prompt Generator Agent (Strategic Content Architect).

Transforms topic + research into structured prompt components using
the Strategic Content Architect persona from system_prompts.md.
"""

from pathlib import Path
from typing import Dict, Any

from core.envelope import ok, err, validate_envelope
from core.errors import ValidationError, ModelError
from core.persistence import write_and_verify_json, atomic_write_text
from core.logging import log_event
from core.run_context import get_artifact_path
from core.llm_clients import get_text_client
from core.system_prompts import load_system_prompt
from core.cost_tracking import CostMetrics

STEP_CODE = "25_structured_prompt"


def _validate_prompt_structure(prompt_text: str) -> None:
    """
    Validate that the prompt follows the required template structure.

    Raises ValidationError if required sections are missing or clichés detected.
    """
    required_sections = [
        "**Topic:**",
        "**Target Audience:**",
        "**Audience's Core Pain Point:**",
        "**Key Metrics/Facts:**",
        "**The Simple Solution/Code Snippet:**",
    ]

    missing = [section for section in required_sections if section not in prompt_text]
    if missing:
        raise ValidationError(f"Prompt missing required sections: {missing}")

    # Check for clichéd analogies (per persona guidelines)
    cliche_phrases = [
        "distributed ledger",
        "like a library",
        "like a recipe",
        "like building a house",
        "tip of the iceberg",
    ]

    prompt_lower = prompt_text.lower()
    found_cliches = [phrase for phrase in cliche_phrases if phrase in prompt_lower]
    if found_cliches:
        raise ValidationError(
            f"Prompt contains clichéd analogies: {found_cliches}. "
            "Strategic Content Architect must use fresh, unexpected analogies."
        )


def _generate_structured_prompt(topic: str, research: Dict[str, Any], cost_tracker=None) -> Dict[str, Any]:
    """
    Use LLM with Strategic Content Architect persona to generate structured prompt.

    Args:
        topic: The topic to generate a prompt for
        research: Research data with 'sources' and 'summary'
        cost_tracker: Optional cost tracker for budget management

    Returns:
        Dict with:
            - structured_prompt_text: The full generated prompt
            - token_usage: Token usage metrics

    Raises:
        ModelError: If LLM call fails
        ValidationError: If prompt doesn't follow template
    """
    # Load Strategic Content Architect system prompt
    system_prompt = load_system_prompt("strategic_content_architect")

    # Build user message with topic and research context
    sources_text = "\n".join(
        [
            f"- {src.get('title', 'Unknown')}: {src.get('key_point', 'N/A')}"
            for src in research.get("sources", [])
        ]
    )

    user_message = f"""Raw topic and research to transform into a structured prompt:

**Topic:** {topic}

**Research Summary:**
{research.get('summary', 'No summary available')}

**Key Sources:**
{sources_text}

Please transform this into the structured prompt format as defined in your instructions."""

    # Check budget before API call
    if cost_tracker:
        cost_tracker.check_budget("gemini-2.5-pro", user_message)

    # Call LLM
    client = get_text_client()
    result = client.generate_text(
        prompt=user_message,
        system_instruction=system_prompt,
        temperature=0.7,  # Some creativity for fresh analogies
        max_output_tokens=2000,
    )

    prompt_text = result["text"].strip()

    # Validate structure
    _validate_prompt_structure(prompt_text)

    return {
        "structured_prompt_text": prompt_text,
        "token_usage": result.get("token_usage", {}),
    }


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute prompt generation using Strategic Content Architect persona.

    input_obj expects: {"topic": str, "research": dict}
    context expects: {"run_id": str, "run_path": Path, "cost_tracker": optional CostTracker}
    """
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    topic = input_obj.get("topic")
    research = input_obj.get("research")
    cost_tracker = context.get("cost_tracker")

    attempt = 1
    metrics_dict = {}

    try:
        if not topic or not research:
            raise ValidationError("Missing 'topic' or 'research' input")

        # Generate structured prompt with LLM
        result = _generate_structured_prompt(topic, research, cost_tracker)

        # Track cost if tracker provided
        if cost_tracker and "token_usage" in result:
            token_usage = result["token_usage"]
            cost_metrics = CostMetrics(
                model="gemini-2.5-pro",
                input_tokens=token_usage.get("prompt_tokens", 0),
                output_tokens=token_usage.get("completion_tokens", 0),
            )
            cost_tracker.record_call("prompt_generator_agent", cost_metrics)
            metrics_dict["cost_usd"] = cost_metrics.cost_usd
            metrics_dict["token_usage"] = token_usage

        # Build data for artifact
        data = {"topic": topic, "structured_prompt": result["structured_prompt_text"]}

        # Persist artifact
        artifact_path = get_artifact_path(run_path, STEP_CODE)
        write_and_verify_json(artifact_path, data)

        response = ok(data, metrics=metrics_dict if metrics_dict else None)
        validate_envelope(response)
        log_event(
            run_id,
            "prompt_generator",
            attempt,
            "ok",
            token_usage=metrics_dict.get("token_usage"),
        )
        return response

    except ValidationError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(
            run_id, "prompt_generator", attempt, "error", error_type=type(e).__name__
        )
        return response
    except ModelError as e:
        response = err(type(e).__name__, str(e), retryable=True)
        validate_envelope(response)
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
