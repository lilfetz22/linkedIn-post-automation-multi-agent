"""Writer Agent (The Witty Expert persona - LLM-powered).

Generates a LinkedIn post draft from structured prompt using Gemini LLM.
Implements internal character count validation with shortening retries.
Strategic planning is now handled by the Prompt Generator Agent
(Strategic Content Architect persona).
"""

from pathlib import Path
from typing import Dict, Any
import re
import time

from core.envelope import ok, err, validate_envelope
from core.errors import ValidationError, ModelError
from core.persistence import atomic_write_text
from core.logging import log_event
from core.run_context import get_artifact_path
from core.llm_clients import get_text_client
from core.system_prompts import load_system_prompt

STEP_CODE = "40_draft"
MAX_CHAR_COUNT = 3000
MAX_SHORTENING_ATTEMPTS = 3
TEMPERATURE = 0.8  # Higher temperature for creative writing
BLACKLIST_PATTERN = re.compile(r"\s*[-—–]?\s*Tech Audience Accelerator\s*", re.IGNORECASE)


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
- Do NOT mention "Tech Audience Accelerator" (remove it entirely if it ever appears)

Deliver a concise sign-off that fits the persona, but never reference external newsletters.

Generate the complete LinkedIn post now."""

    return user_message


def _scrub_blacklisted_phrases(text: str) -> tuple[str, int]:
    """Remove forbidden phrases (e.g., Tech Audience Accelerator) from text.

    Returns the scrubbed text and the number of substitutions performed.
    """

    scrubbed, replacements = re.subn(BLACKLIST_PATTERN, "", text)
    # Tidy up spacing/newlines that may be left behind by removals
    scrubbed = re.sub(r" {2,}", " ", scrubbed)
    scrubbed = re.sub(r"\n{3,}", "\n\n", scrubbed).strip()
    return scrubbed, replacements


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
    system_prompt = load_system_prompt("witty_expert")

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

Please regenerate the post with the SAME core message and structure, \
but shorten it to under 3000 characters (excluding line breaks). \
Remove unnecessary elaboration, tighten phrasing, but preserve the hook, \
analogy, and metrics."""

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
        response = client.generate_text(
            prompt=user_message,
            system_instruction=system_prompt,
            temperature=TEMPERATURE,
            use_search_grounding=False,
        )
        draft_text = response["text"]

        duration_ms = int((time.time() - start_time) * 1000)

        # Extract token usage (implementation depends on client interface)
        # Include duration_ms to avoid unused variable warning and support future metrics
        token_usage = {"duration_ms": duration_ms}

        return draft_text.strip(), token_usage

    except Exception as e:
        raise ModelError(f"LLM generation failed: {str(e)}")


def _generate_fallback_post(structured: Dict[str, Any]) -> str:
    """Generate a deterministic short post when LLM is unavailable.

    Keeps persona essentials while guaranteeing we stay below the
    character limit to unblock the pipeline.
    """

    topic = structured.get("topic_title", "Practical Engineering Insight")
    pain_point = structured.get(
        "pain_point", "Teams struggle to balance speed, quality, and cost."
    )
    solution = structured.get(
        "solution_outline",
        "Share a three-step approach with a small code/config example.",
    )
    metrics = structured.get("key_metrics", [])
    metrics_str = ", ".join(metrics) if metrics else "measurable gains"

    fallback_post = f"""**{topic}: A fast, clear take**

Hook: A quick gut-check on something we keep over-complicating.

Problem: {pain_point} It slows momentum and frustrates teams.

Solution: {solution}

Impact: Expect {metrics_str} when you implement this calmly and consistently.

Action: Try it today, share what broke, and keep the iteration tight."""

    # Guardrail: ensure we stay under limit even with unexpected long fields
    SAFETY_BUFFER = 50  # Buffer for any minor additions downstream

    if count_chars(fallback_post) >= MAX_CHAR_COUNT - SAFETY_BUFFER:
        trimmed = fallback_post[: MAX_CHAR_COUNT - SAFETY_BUFFER]
        fallback_post = trimmed.strip()

    return fallback_post


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
    # external_shortening retained for future orchestrator-driven shortening; currently unused
    fallback_tracker = context.get("fallback_tracker")

    attempt = 1
    shortening_attempts = 0
    previous_draft = None

    try:
        if not structured:
            raise ValidationError("Missing 'structured_prompt' input")

        # Internal character count loop
        while shortening_attempts <= MAX_SHORTENING_ATTEMPTS:
            # Generate draft (includes internal budget check)
            draft, token_usage = _generate_draft_with_llm(
                structured, previous_draft, cost_tracker
            )

            # Remove any blacklisted phrases before further processing/persistence
            draft, blacklist_hits = _scrub_blacklisted_phrases(draft)

            # Record cost (if cost tracker provided)
            if cost_tracker:
                cost_tracker.record_call(
                    "gemini-2.5-pro",  # model (positional arg)
                    token_usage.get("prompt_tokens", 0),  # prompt_tokens
                    token_usage.get("completion_tokens", 0),  # completion_tokens
                    agent_name="writer_agent",
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
                    "blacklist_removed": blacklist_hits,
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
                    f"Draft still {char_count} chars after {MAX_SHORTENING_ATTEMPTS} "
                    f"shortening attempts (limit: {MAX_CHAR_COUNT})"
                )

            # Prepare for next iteration
            previous_draft = draft
            attempt += 1

        # Should never reach here due to loop logic, but defensive
        raise ValidationError(
            "Max shortening attempts (3) exceeded; post still exceeds 3000 characters",
            error_code="MAX_SHORTENING_EXCEEDED"
        )
    except ValidationError as e:
        # If we exhausted shortening attempts, fall back to deterministic template
        if getattr(e, 'error_code', None) == "MAX_SHORTENING_EXCEEDED":
            # Request user approval before proceeding with fallback
            warning = fallback_tracker.record_warning(
                agent_name="writer_agent",
                reason="character_limit",
                error_message=f"Could not shorten post below 3000 chars after 3 attempts. Last attempt: {str(e)}",
                step_number=5,
                original_objective="Generate LinkedIn post under 3000 characters",
            )

            if not fallback_tracker.request_user_approval(warning):
                response = err(type(e).__name__, str(e), retryable=e.retryable)
                validate_envelope(response)
                log_event(
                    run_id, "writer", attempt, "error", error_type=type(e).__name__
                )
                return response

            fallback_post = _generate_fallback_post(structured)
            artifact_path = get_artifact_path(run_path, STEP_CODE, extension="md")
            atomic_write_text(artifact_path, fallback_post)

            log_event(
                run_id,
                "writer",
                attempt,
                "ok",
                token_usage={
                    "fallback": True,
                    "reason": "character_limit",
                    "user_approved": True,
                },
            )

            response = ok(
                {
                    "draft_path": str(artifact_path),
                    "fallback_used": True,
                    "fallback_reason": "character_limit",
                }
            )
            validate_envelope(response)
            return response

        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "writer", attempt, "error", error_type=type(e).__name__)
        return response
    except ModelError as e:
        # LLM unavailable: generate deterministic fallback draft
        warning = fallback_tracker.record_warning(
            agent_name="writer_agent",
            reason="model_error",
            error_message=f"LLM generation failed: {str(e)}",
            step_number=5,
            original_objective="Generate LinkedIn post using LLM (Witty Expert persona)",
        )

        if not fallback_tracker.request_user_approval(warning):
            response = err(type(e).__name__, str(e), retryable=e.retryable)
            validate_envelope(response)
            log_event(run_id, "writer", attempt, "error", error_type=type(e).__name__)
            return response

        fallback_post = _generate_fallback_post(structured)
        artifact_path = get_artifact_path(run_path, STEP_CODE, extension="md")
        atomic_write_text(artifact_path, fallback_post)

        log_event(
            run_id,
            "writer",
            attempt,
            "ok",
            token_usage={
                "fallback": True,
                "reason": "model_error",
                "user_approved": True,
            },
        )

        response = ok(
            {
                "draft_path": str(artifact_path),
                "fallback_used": True,
                "fallback_reason": "model_error",
            }
        )
        validate_envelope(response)
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        validate_envelope(response)
        log_event(run_id, "writer", attempt, "error", error_type=type(e).__name__)
        return response
