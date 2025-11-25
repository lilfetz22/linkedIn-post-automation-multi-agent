"""Image Prompt Generator Agent - LLM-powered with Visual Strategist persona."""

import time
from pathlib import Path
from typing import Dict, Any

from core.envelope import ok, err, validate_envelope
from core.errors import ValidationError, ModelError
from core.persistence import atomic_write_text
from core.logging import log_event
from core.run_context import get_artifact_path
from core.llm_clients import get_text_client
from core.system_prompts import load_visual_strategist_persona

STEP_CODE = "70_image_prompt"
PROMPT_TEMPERATURE = 0.6  # Moderate creativity for visual descriptions


def _validate_no_text_constraint(prompt: str) -> bool:
    """Validate that the prompt specifies no text in the image.

    Returns:
        True if the constraint is present, False otherwise
    """
    no_text_keywords = [
        "zero text",
        "no text",
        "no words",
        "no letters",
        "without text",
        "without words",
        "text-free",
        "word-free",
    ]
    prompt_lower = prompt.lower()
    return any(keyword in prompt_lower for keyword in no_text_keywords)


def _generate_image_prompt_with_llm(
    final_post: str, cost_tracker=None
) -> tuple[str, dict]:
    """Generate image prompt using LLM with Visual Strategist persona.

    Args:
        final_post: The final LinkedIn post text
        cost_tracker: Optional cost tracker for budget management

    Returns:
        Tuple of (generated_prompt, token_usage)

    Raises:
        ModelError: If LLM call fails
        ValidationError: If no-text constraint is missing
    """
    # Load Visual Strategist system instruction
    system_instruction = load_visual_strategist_persona()

    # Build user prompt
    user_prompt = f"""Here is the LinkedIn post I just created:

---
{final_post}
---

Generate an AI image prompt that perfectly complements this narrative. Remember:
- Analyze the emotional hook and core subject
- Create a prompt with literal or metaphorical visual representation
- **CRITICAL:** Specify that the image must contain **zero text, words, or letters**
- Specify: subject, environment, lighting, and mood

Provide only the image prompt, ready for an AI image generator."""

    # Check budget before API call using full user prompt
    if cost_tracker:
        cost_tracker.check_budget("gemini-2.5-pro", user_prompt)

    # Call LLM (no search grounding for creative visual work)
    client = get_text_client()
    start_time = time.time()

    try:
        prompt = client.generate_text(
            prompt=user_prompt,
            system_instruction=system_instruction,
            temperature=PROMPT_TEMPERATURE,
            use_search_grounding=False,
        )

        duration_ms = int((time.time() - start_time) * 1000)
        token_usage = {"duration_ms": duration_ms}  # TODO: Extract from client

        # Validate no-text constraint
        if not _validate_no_text_constraint(prompt):
            raise ValidationError(
                "Generated image prompt missing 'no text' constraint. "
                "Image must explicitly specify zero text/words/letters."
            )

        return prompt.strip(), token_usage

    except ValidationError:
        raise
    except Exception as e:
        raise ModelError(f"LLM image prompt generation failed: {str(e)}")


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate AI image prompt using LLM with Visual Strategist persona.

    Input contract:
        - final_post (required): The final LinkedIn post text

    Output contract:
        - image_prompt_path: Path to the generated prompt file
        - prompt_preview: First 100 chars of the prompt

    Internal logic:
        - Load Visual Strategist persona from system_prompts.md
        - Call LLM to generate creative image prompt
        - Validate no-text constraint is present
        - Persist prompt as text file
    """
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    cost_tracker = context.get("cost_tracker")
    final_post = input_obj.get("final_post")
    attempt = 1

    try:
        if not final_post:
            raise ValidationError(
                "Missing 'final_post' text for image prompt generation"
            )

        if not final_post.strip():
            raise ValidationError("Empty 'final_post' text for image prompt generation")

        # Generate prompt with LLM
        prompt, token_usage = _generate_image_prompt_with_llm(final_post, cost_tracker)

        # Record cost
        if cost_tracker:
            cost_tracker.record_call(
                model="gemini-2.5-pro",
                prompt_tokens=0,  # TODO: Extract from client
                completion_tokens=0,
            )

        # Persist prompt
        artifact_path = get_artifact_path(run_path, STEP_CODE, extension="txt")
        atomic_write_text(artifact_path, prompt)

        # Log success
        log_event(
            run_id,
            "image_prompt",
            attempt,
            "ok",
            duration_ms=token_usage.get("duration_ms"),
            model="gemini-2.5-pro",
            token_usage=token_usage,
        )

        response = ok(
            {
                "image_prompt_path": str(artifact_path),
                "prompt_preview": prompt[:100] + ("..." if len(prompt) > 100 else ""),
            }
        )
        validate_envelope(response)
        return response

    except ValidationError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "image_prompt", attempt, "error", error_type=type(e).__name__)
        return response
    except ModelError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(run_id, "image_prompt", attempt, "error", error_type=type(e).__name__)
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        validate_envelope(response)
        log_event(run_id, "image_prompt", attempt, "error", error_type=type(e).__name__)
        return response
