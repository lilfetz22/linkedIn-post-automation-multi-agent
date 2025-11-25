"""Research agent.

Conducts research on a given topic using LLM-powered synthesis.
Generates sources and summary for the selected topic.
TODO: Integrate external web search API (Tavily, SerpAPI, or Google Custom Search).
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

STEP_CODE = "20_research"


def _conduct_llm_research(topic: str, cost_tracker=None) -> Dict[str, Any]:
    """
    Use LLM to generate research synthesis for a topic.

    TODO: Replace with actual web search API integration (Tavily, SerpAPI, etc.)
    For now, leverages LLM's knowledge to synthesize key points.

    Args:
        topic: The topic to research
        cost_tracker: Optional cost tracker for budget management

    Returns:
        Dict with "sources" (list) and "summary" (str)

    Raises:
        ModelError: If LLM call fails
        DataNotFoundError: If LLM returns no useful information
    """
    prompt = f"""You are a research analyst. Provide a comprehensive research summary for the following topic:

Topic: {topic}

Your response must be valid JSON with this exact structure:
{{
    "sources": [
        {{"title": "Source Title 1", "url": "https://example.com/1", "key_point": "Main insight from this source"}},
        {{"title": "Source Title 2", "url": "https://example.com/2", "key_point": "Main insight from this source"}}
    ],
    "summary": "A comprehensive 2-3 paragraph summary covering: key metrics, pain points, recent developments, and practical considerations. Focus on actionable insights and surprising findings."
}}

Requirements:
- Include 5-7 diverse sources
- URLs should be realistic (can be placeholder domains but follow URL format)
- Summary should be substantive (150-250 words)
- Focus on data, metrics, and concrete examples
- Highlight audience pain points and practical implications

Return ONLY the JSON, no additional text."""

    # Check budget before API call
    if cost_tracker:
        cost_tracker.check_budget("gemini-2.5-pro", prompt)

    client = get_text_client()
    result = client.generate_text(
        prompt=prompt, 
        temperature=0.7, 
        max_output_tokens=2000,
        use_search_grounding=True  # Enable Google Search for current research
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

    try:
        research_data = json.loads(text)
    except json.JSONDecodeError as e:
        raise ModelError(f"Failed to parse LLM research response as JSON: {str(e)}")

    # Validate structure
    if "sources" not in research_data or "summary" not in research_data:
        raise ModelError("LLM research response missing required fields")

    if not research_data["sources"]:
        raise DataNotFoundError(f"No sources found for topic '{topic}'")

    return {
        "sources": research_data["sources"],
        "summary": research_data["summary"],
        "token_usage": result.get("token_usage", {}),
    }


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """
    Execute research for a topic.

    input_obj expects: {"topic": str}
    context expects: {"run_id": str, "run_path": Path, "cost_tracker": optional CostTracker}
    """
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    topic = input_obj.get("topic")
    cost_tracker = context.get("cost_tracker")

    attempt = 1
    metrics_dict = {}

    try:
        if not topic:
            raise ValidationError("Missing 'topic' in research agent input")

        # Conduct LLM-powered research
        research_result = _conduct_llm_research(topic, cost_tracker)

        # Track cost if tracker provided
        if cost_tracker and "token_usage" in research_result:
            token_usage = research_result["token_usage"]
            cost_metrics = CostMetrics(
                model="gemini-2.5-pro",
                input_tokens=token_usage.get("prompt_tokens", 0),
                output_tokens=token_usage.get("completion_tokens", 0),
            )
            cost_tracker.record_call("research_agent", cost_metrics)
            metrics_dict["cost_usd"] = cost_metrics.cost_usd
            metrics_dict["token_usage"] = token_usage

        # Build response data
        data = {
            "topic": topic,
            "sources": research_result["sources"],
            "summary": research_result["summary"],
        }

        # Persist artifact
        artifact_path = get_artifact_path(run_path, STEP_CODE)
        write_and_verify_json(artifact_path, data)

        response = ok(data, metrics=metrics_dict if metrics_dict else None)
        validate_envelope(response)
        log_event(
            run_id,
            "research",
            attempt,
            "ok",
            token_usage=metrics_dict.get("token_usage"),
        )
        return response

    except (ValidationError, DataNotFoundError) as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "research", attempt, "error", error_type=type(e).__name__)
        return response
    except ModelError as e:
        # Model errors are retryable
        response = err(type(e).__name__, str(e), retryable=True)
        validate_envelope(response)
        log_event(run_id, "research", attempt, "error", error_type=type(e).__name__)
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        validate_envelope(response)
        log_event(run_id, "research", attempt, "error", error_type=type(e).__name__)
        return response
