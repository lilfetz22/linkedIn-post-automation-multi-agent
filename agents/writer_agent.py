"""Writer Agent (The Witty Expert persona - LLM-powered).

Generates a LinkedIn post draft from structured prompt using Gemini LLM.
Implements internal character count validation with shortening retries.
Strategic planning is now handled by the Prompt Generator Agent
(Strategic Content Architect persona).
"""

from pathlib import Path
from typing import Dict, Any
import time

from core.envelope import ok, err, validate_envelope
from core.errors import ValidationError, ModelError
from core.persistence import atomic_write_text
from core.logging import log_event
from core.run_context import get_artifact_path
from core.llm_clients import get_text_client
from core.system_prompts import load_system_prompt
from core.cost_tracking import CostTracker

STEP_CODE = "40_draft"
MAX_CHAR_COUNT = 3000
MAX_SHORTENING_ATTEMPTS = 3
TEMPERATURE = 0.8  # Higher temperature for creative writing


def count_chars(text: str) -> int:
    """Count characters excluding line breaks."""
    return len(text.replace("\n", "").replace("\r", ""))


def _format_structured_prompt_as_user_message(structured: Dict[str, Any]) -> str:
    """Format structured prompt dict into natural language user prompt.

    Args:
        structured: Structured prompt from Prompt Generator Agent

    Returns:
        Formatted user prompt for LLM
    """
    # Extract all fields from structured prompt
    topic = structured.get("topic_title", "Unknown Topic")
    audience = structured.get("target_audience", "technical professionals")
    pain_point = structured.get("pain_point", "")
    key_metrics = structured.get("key_metrics", [])
    analogy = structured.get("analogy", "")
    solution = structured.get("solution_outline", "")
    code_snippet = structured.get("code_snippet", "")

    # Build comprehensive user message
    user_message = f"""Generate a LinkedIn post using the Witty Expert persona.

**Topic:** {topic}

**Target Audience:** {audience}

**Audience's Core Pain Point:** {pain_point}

**Key Metrics/Facts:** {', '.join(key_metrics) if isinstance(key_metrics, list) else key_metrics}

**The Perfect Analogy:** {analogy}

**The Simple Solution/Code Snippet:**
{solution}
{code_snippet if code_snippet else ''}

**Critical Requirements:**
- Follow the LinkedIn Post Structure exactly: Hook → Problem → Solution → Impact → Action → Sign-off
- Use the provided analogy as the central metaphor throughout the post
- Make the post feel delightful and insightful, not dumbed-down
- Use short paragraphs, white space, **bold** for emphasis
- Include quantifiable impact from the key metrics
- Keep character count UNDER 3000 characters (excluding line breaks)
- Sign off with "— Tech Audience Accelerator" at the end

Generate the complete LinkedIn post now."""

    return user_message


def _generate_draft_with_llm(
    structured: Dict[str, Any], shortening_context: str = None, cost_tracker=None
) -> tuple[str, Dict[str, Any]]:
    """Generate LinkedIn post draft using Gemini LLM.

    Args:
        structured: Structured prompt from Prompt Generator Agent
        shortening_context: Optional previous draft that was too long

    Returns:
        Tuple of (draft_text, token_usage dict)

    Raises:
        ModelError: If LLM call fails
    """
    # Load Witty Expert persona from system_prompts.md
    system_prompt = load_system_prompt("The Witty Expert Persona")

    # Format structured prompt as user message
    user_message = _format_structured_prompt_as_user_message(structured)

    # If this is a shortening attempt, add context
    if shortening_context:
        user_message = f"""{user_message}

**IMPORTANT: Character Count Issue**
The previous draft was too long. Here it is:

---
{shortening_context}
---

Please regenerate the post with the SAME core message and structure, but shorten it to under 3000 characters (excluding line breaks). Remove unnecessary elaboration, tighten phrasing, but preserve the hook, analogy, metrics, and sign-off."""

    # Budget check with full prompt prior to LLM call
    if cost_tracker:
        try:
            cost_tracker.check_budget("gemini-2.5-pro", user_message)
        except Exception:
            # Surface upstream; do not proceed with generation if budget exceeded
            raise

    # Call LLM (no search grounding for creative writing)
    client = get_text_client()
    start_time = time.time()

    try:
        draft = client.generate_text(
            prompt=user_message,
            system_instruction=system_prompt,
            temperature=TEMPERATURE,
            use_search_grounding=False,
        )

        duration_ms = int((time.time() - start_time) * 1000)

        # Extract token usage (implementation depends on client interface)
        # For now, return empty dict - will be populated by cost tracker
        token_usage = {}

        return draft.strip(), token_usage

    except Exception as e:
        raise ModelError(f"LLM generation failed: {str(e)}")


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate LinkedIn post draft with internal character count validation loop.

    Input contract:
        - structured_prompt (required): Structured prompt from Prompt Generator Agent
        - shortening_instruction (optional): External shortening request from orchestrator

    Output contract:
        - draft_path: Path to saved draft markdown file

    Internal logic:
        - Generates draft with LLM (Witty Expert persona)
        - Validates character count < 3000 chars
        - If too long, retries up to MAX_SHORTENING_ATTEMPTS (3) times
        - Raises ValidationError if still too long after max attempts
    """
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    cost_tracker = context.get("cost_tracker")  # Optional from orchestrator
    structured = input_obj.get("structured_prompt")
    external_shortening = input_obj.get("shortening_instruction")  # From orchestrator

    attempt = 1
    shortening_attempts = 0
    previous_draft = None

    try:
        if not structured:
            raise ValidationError("Missing 'structured_prompt' input")

        # Internal character count loop
        while shortening_attempts <= MAX_SHORTENING_ATTEMPTS:
            # Generate draft (includes internal budget check)
            draft, token_usage = _generate_draft_with_llm(structured, previous_draft, cost_tracker)

            # Record cost (if cost tracker provided)
            if cost_tracker:
                cost_tracker.record_call(
                    model="gemini-2.5-pro",
                    prompt_tokens=0,  # TODO: Extract from client
                    completion_tokens=0,  # TODO: Extract from client
                )

            # Log generation attempt
            char_count = count_chars(draft)
            log_event(
                run_id,
                "writer",
                attempt,
                "ok",
                duration_ms=None,
                model="gemini-2.5-pro",
                token_usage={
                    "char_count": char_count,
                    "shortening_attempt": shortening_attempts,
                },
            )

            # Validate character count
            if char_count < MAX_CHAR_COUNT:
                # Success! Save and return
                artifact_path = get_artifact_path(run_path, STEP_CODE, extension="md")
                atomic_write_text(artifact_path, draft)

                response = ok({"draft_path": str(artifact_path)})
                validate_envelope(response)
                return response

            # Too long - retry if attempts remain
            shortening_attempts += 1
            if shortening_attempts > MAX_SHORTENING_ATTEMPTS:
                raise ValidationError(
                    f"Draft still {char_count} chars after {MAX_SHORTENING_ATTEMPTS} shortening attempts (limit: {MAX_CHAR_COUNT})"
                )

            # Prepare for next iteration
            previous_draft = draft
            attempt += 1

        # Should never reach here due to loop logic, but defensive
        raise ValidationError(
            f"Internal error: exceeded shortening loop without proper exit"
        )
    except ValidationError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "writer", attempt, "error", error_type=type(e).__name__)
        return response
    except ModelError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "writer", attempt, "error", error_type=type(e).__name__)
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        validate_envelope(response)
        log_event(run_id, "writer", attempt, "error", error_type=type(e).__name__)
        return response
