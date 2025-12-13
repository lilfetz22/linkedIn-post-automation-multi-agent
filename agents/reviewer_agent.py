"""Reviewer Agent (LLM-powered with local grammar checking).

Implements single-pass LLM review for coherence + local grammar checking.
Includes character count validation loop with hashtag removal logic.
"""

from pathlib import Path
from typing import Dict, Any
import re
import time

from core.envelope import ok, err, validate_envelope
from core.errors import ValidationError, ModelError
from core.persistence import write_and_verify_json
from core.logging import log_event
from core.run_context import get_artifact_path
from core.llm_clients import get_text_client

STEP_CODE = "50_review"
MAX_CHAR_COUNT = 3000
MAX_SHORTENING_ATTEMPTS = 3
REVIEW_TEMPERATURE = 0.3  # Lower temperature for precise review work
BLACKLIST_PATTERN = re.compile(
    r"\s*[-—–]?\s*Tech Audience Accelerator\s*", re.IGNORECASE
)


def count_chars(text: str) -> int:
    """Count characters excluding line breaks."""
    return len(text.replace("\n", "").replace("\r", ""))


def _remove_hashtags(text: str) -> str:
    """Remove hashtag lines from end of post.

    Removes lines that start with # after the final content paragraph.
    """
    lines = text.split("\n")

    # Find last non-empty, non-hashtag line
    last_content_idx = -1
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        if line and not line.startswith("#"):
            last_content_idx = i
            break

    # Keep everything up to and including last content line
    if last_content_idx >= 0:
        return "\n".join(lines[: last_content_idx + 1])

    return text


def _scrub_blacklisted_phrases(text: str) -> tuple[str, int]:
    """Remove forbidden phrases (e.g., Tech Audience Accelerator) from text.

    Returns the scrubbed text and the number of substitutions performed.
    """

    scrubbed, replacements = re.subn(BLACKLIST_PATTERN, "", text)
    scrubbed = re.sub(r" {2,}", " ", scrubbed)
    scrubbed = re.sub(r"\n{3,}", "\n\n", scrubbed).strip()
    return scrubbed, replacements


def _apply_grammar_corrections(text: str) -> tuple[str, int]:
    """Apply local grammar and spell checking using language-tool-python.

    Args:
        text: Text to check

    Returns:
        Tuple of (corrected_text, num_corrections)
    """
    try:
        import language_tool_python

        tool = language_tool_python.LanguageTool("en-US")

        # Get matches
        matches = tool.check(text)

        # Apply corrections
        corrected = language_tool_python.utils.correct(text, matches)

        tool.close()

        return corrected, len(matches)

    except Exception:
        # Fallback: return original text if grammar tool fails
        return text, 0


def _llm_coherence_review(
    draft_text: str, shortening_context: str = None, cost_tracker=None
) -> tuple[str, Dict[str, Any]]:
    """Perform LLM-based coherence and consistency review.

    Args:
        draft_text: Original draft to review
        shortening_context: Optional instruction to shorten

    Returns:
        Tuple of (revised_text, token_usage dict)

    Raises:
        ModelError: If LLM call fails
    """
    # Build review prompt
    if shortening_context:
        prompt = f"""Review and revise this LinkedIn post for coherence \
and Witty Expert persona consistency.

**CRITICAL: This post is too long ({count_chars(draft_text)} characters, limit: 3000).**

{shortening_context}

**Original Post:**
---
{draft_text}
---

**Instructions:**
- Maintain the core message, analogy, and metrics
- Shorten by removing unnecessary elaboration and tightening phrasing
- Preserve the hook, problem, solution, impact, and sign-off structure
- Remove any mention of "Tech Audience Accelerator" or similar newsletter names
- Keep Witty Expert persona (intellectual sparkle, fresh analogies, dry wit)
- Do NOT include hashtags at the end
- Character count MUST be under 3000 (excluding line breaks)

Return ONLY the revised post, no explanations."""
    else:
        prompt = f"""Review this LinkedIn post for logical flow, coherence, \
and persona consistency (Witty Expert).

**Post to Review:**
---
{draft_text}
---

**Review Criteria:**
- Logical flow: Hook → Problem → Solution → Impact → Action → Sign-off
- Persona consistency: Intellectual sparkle, fresh analogies, dry wit (not slapstick)
- Coherence: Ideas connect smoothly, no abrupt transitions
- Clarity: Complex ideas made delightful and accessible

**Instructions:**
- Make minor revisions to improve flow and coherence
- Fix any persona inconsistencies (e.g., cliché analogies, academic tone)
- Remove any mention of "Tech Audience Accelerator" or similar newsletter names
- Preserve the core message and structure
- Return ONLY the revised post, no explanations"""

    # Budget check with constructed prompt
    if cost_tracker:
        try:
            cost_tracker.check_budget("gemini-2.5-pro", prompt)
        except Exception:
            raise

    # Call LLM (no search grounding for review work)
    client = get_text_client()
    start_time = time.time()

    try:
        response = client.generate_text(
            prompt=prompt,
            system_instruction=(
                "You are a meticulous editor reviewing LinkedIn posts for "
                "coherence and persona consistency. Make precise improvements "
                "while preserving the author's voice."
            ),
            temperature=REVIEW_TEMPERATURE,
            use_search_grounding=False,
        )
        revised_text = response["text"]

        duration_ms = int((time.time() - start_time) * 1000)
        # Include duration_ms to avoid unused variable warning and support future metrics
        token_usage = {"duration_ms": duration_ms}  # TODO: Extend with real token usage

        return revised_text.strip(), token_usage

    except Exception as e:
        raise ModelError(f"LLM review failed: {str(e)}")


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Review draft with LLM coherence check + local grammar checking + character validation.

    Input contract:
        - draft_text (required): Draft text to review

    Output contract:
        - original: Original draft text
        - llm_revised: LLM-revised version
        - grammar_checked: Grammar-checked version
        - revised: Final revised version (after all processing)
        - changes: Summary of changes made
        - char_count: Final character count
        - iterations: Number of shortening iterations

    Internal logic:
        - LLM coherence review
        - Local grammar checking with language-tool-python
        - Character count validation (<3000 chars)
        - Hashtag removal if needed
        - Shortening loop (max 3 attempts)
    """
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    cost_tracker = context.get("cost_tracker")
    draft_text = input_obj.get("draft_text")

    attempt = 1
    shortening_attempts = 0
    shortening_instruction = None

    try:
        if not draft_text:
            raise ValidationError("Missing 'draft_text' for reviewer")

        original_text = draft_text

        # Shortening loop
        while shortening_attempts <= MAX_SHORTENING_ATTEMPTS:
            # Step 1: LLM Coherence Review (includes internal budget check)
            llm_revised, token_usage = _llm_coherence_review(
                draft_text, shortening_instruction, cost_tracker
            )

            # Record cost
            if cost_tracker:
                # Use new positional calling pattern: (model, prompt_tokens, completion_tokens, agent_name)
                cost_tracker.record_call(
                    "gemini-2.5-pro",
                    token_usage.get("prompt_tokens", 0),
                    token_usage.get("completion_tokens", 0),
                    agent_name="reviewer_agent",
                )

            # Step 2: Local Grammar Checking
            grammar_checked, num_corrections = _apply_grammar_corrections(llm_revised)

            # Step 3: Blacklist scrubbing (hard block for forbidden phrases)
            scrubbed_text, blacklist_hits = _scrub_blacklisted_phrases(grammar_checked)

            # Log iteration
            char_count = count_chars(scrubbed_text)
            log_event(
                run_id,
                "reviewer",
                attempt,
                "ok",
                duration_ms=None,
                model="gemini-2.5-pro",
                token_usage={
                    "char_count": char_count,
                    "grammar_corrections": num_corrections,
                    "blacklist_removed": blacklist_hits,
                    "shortening_attempt": shortening_attempts,
                },
            )

            # Step 4: Character Count Validation
            if char_count < MAX_CHAR_COUNT:
                # Success! Prepare response
                changes = {
                    "llm_changes": (
                        "coherence_review" if llm_revised != draft_text else "none"
                    ),
                    "grammar_corrections": num_corrections,
                    "blacklist_removed": blacklist_hits,
                    "hashtags_removed": False,
                    "shortening_attempts": shortening_attempts,
                }

                data = {
                    "original": original_text,
                    "llm_revised": llm_revised,
                    "grammar_checked": grammar_checked,
                    "revised": scrubbed_text,
                    "changes": changes,
                    "char_count": char_count,
                    "iterations": shortening_attempts + 1,
                }

                # Persist review artifact
                artifact_path = get_artifact_path(run_path, STEP_CODE)
                write_and_verify_json(artifact_path, data)

                response = ok(data)
                validate_envelope(response)
                return response

            # Too long - try hashtag removal first
            if shortening_attempts == 0:
                text_without_hashtags = _remove_hashtags(scrubbed_text)
                char_count_no_hashtags = count_chars(text_without_hashtags)

                if char_count_no_hashtags < MAX_CHAR_COUNT:
                    # Hashtag removal fixed it!
                    changes = {
                        "llm_changes": "coherence_review",
                        "grammar_corrections": num_corrections,
                        "blacklist_removed": blacklist_hits,
                        "hashtags_removed": True,
                        "shortening_attempts": 0,
                    }

                    data = {
                        "original": original_text,
                        "llm_revised": llm_revised,
                        "grammar_checked": grammar_checked,
                        "revised": text_without_hashtags,
                        "changes": changes,
                        "char_count": char_count_no_hashtags,
                        "iterations": 1,
                    }

                    artifact_path = get_artifact_path(run_path, STEP_CODE)
                    write_and_verify_json(artifact_path, data)

                    response = ok(data)
                    validate_envelope(response)
                    return response

                # Hashtag removal wasn't enough, need to shorten
                scrubbed_text = text_without_hashtags

            # Still too long - retry with shortening instruction
            shortening_attempts += 1
            if shortening_attempts > MAX_SHORTENING_ATTEMPTS:
                raise ValidationError(
                    f"Post still {char_count} chars after {MAX_SHORTENING_ATTEMPTS} "
                    f"shortening attempts (limit: {MAX_CHAR_COUNT})"
                )

            # Prepare for next iteration
            draft_text = scrubbed_text
            shortening_instruction = (
                f"Revise to under 3000 characters with minor adjustments. "
                f"Current: {char_count} characters."
            )
            attempt += 1

        # Should never reach here due to loop logic
        raise ValidationError(
            "Internal error: exceeded shortening loop without proper exit"
        )

    except ValidationError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "reviewer", attempt, "error", error_type=type(e).__name__)
        return response
    except ModelError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "reviewer", attempt, "error", error_type=type(e).__name__)
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        validate_envelope(response)
        log_event(run_id, "reviewer", attempt, "error", error_type=type(e).__name__)
        return response
