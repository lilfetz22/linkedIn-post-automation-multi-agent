"""Image Generator Agent - Real Gemini image generation with fallback placeholder.

Uses gemini-2.5-flash-image to generate images from prompts.
Falls back to placeholder PNG if generation fails.
"""

import time
from pathlib import Path
from typing import Dict, Any

from core.envelope import ok, err, validate_envelope
from core.errors import ValidationError, ModelError
from core.logging import log_event
from core.run_context import get_artifact_path
from core.llm_clients import get_image_client

STEP_CODE = "80_image"


def _write_placeholder_png(path: Path) -> None:
    """Write a minimal valid 1x1 PNG as fallback.
    
    Args:
        path: Path where to write the placeholder PNG
    """
    # Minimal valid PNG header bytes (1x1 pixel)
    png_bytes = (
        b"\x89PNG\r\n\x1a\n"  # PNG signature
        b"\x00\x00\x00\rIHDR"  # IHDR chunk length + type
        b"\x00\x00\x00\x01\x00\x00\x00\x01"  # 1x1 px dimensions
        b"\x08\x02\x00\x00\x00"  # bit depth, color type
        b"\x90wS\xde"  # CRC
        b"\x00\x00\x00\x0aIDAT"  # IDAT chunk
        b"\x08\xd7c``\x00\x00\x00\x05\x00\x01"  # compressed data
        b"\x02\x7f\xe5\x92"  # CRC
        b"\x00\x00\x00\x00IEND\xae\x42\x60\x82"  # IEND chunk
    )
    path.write_bytes(png_bytes)


def _generate_image_with_gemini(
    prompt: str, output_path: Path, cost_tracker=None
) -> tuple[str, dict]:
    """Generate image using Gemini image model.
    
    Args:
        prompt: Image generation prompt
        output_path: Where to save the generated PNG
        cost_tracker: Optional cost tracker for budget management
        
    Returns:
        Tuple of (image_path, generation_info)
        
    Raises:
        ModelError: If image generation fails
    """
    # Check budget before API call (if tracker provided)
    if cost_tracker:
        cost_tracker.check_budget("gemini-2.5-flash-image")
    
    # Get image client
    client = get_image_client()
    start_time = time.time()
    
    try:
        # Generate image
        result = client.generate_image(
            prompt=prompt,
            output_path=output_path,
            aspect_ratio="1:1",  # Square images for LinkedIn
        )
        
        duration_ms = int((time.time() - start_time) * 1000)
        
        # Record cost (if tracker provided)
        if cost_tracker:
            cost_tracker.record_call(
                model="gemini-2.5-flash-image",
                prompt_tokens=0,  # Image models don't expose token counts
                completion_tokens=0,
            )
        
        generation_info = {
            "model": result["model"],
            "duration_ms": duration_ms,
            "fallback_used": False,
        }
        
        return result["image_path"], generation_info
        
    except Exception as e:
        raise ModelError(f"Gemini image generation failed: {str(e)}") from e


def run(input_obj: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
    """Generate image from prompt using Gemini with fallback to placeholder.
    
    Input contract:
        - image_prompt_path (required): Path to text file containing image prompt
    
    Output contract:
        - image_path: Path to generated PNG file
        - generation_info: Dict with model, duration, fallback status
    
    Internal logic:
        - Read prompt from image_prompt_path
        - Attempt Gemini image generation (gemini-2.5-flash-image)
        - If generation fails, write placeholder PNG as fallback
        - Validate file exists and is non-empty
        - Persist image artifact
    """
    run_id = context["run_id"]
    run_path: Path = context["run_path"]
    cost_tracker = context.get("cost_tracker")
    image_prompt_path = input_obj.get("image_prompt_path")
    attempt = 1
    
    try:
        # Validate input
        if not image_prompt_path:
            raise ValidationError("Missing 'image_prompt_path' for image generation")
        
        prompt_path = Path(image_prompt_path)
        if not prompt_path.exists():
            raise ValidationError(
                f"Image prompt file not found: {image_prompt_path}"
            )
        
        # Read prompt from file
        prompt_text = prompt_path.read_text(encoding="utf-8").strip()
        if not prompt_text:
            raise ValidationError("Image prompt file is empty")
        
        # Determine output path
        artifact_path = get_artifact_path(run_path, STEP_CODE, extension="png")
        
        # Attempt real image generation with Gemini
        generation_info = None
        try:
            image_path, generation_info = _generate_image_with_gemini(
                prompt_text, artifact_path, cost_tracker
            )
            
            log_event(
                run_id,
                "image_generation",
                attempt,
                "ok",
                duration_ms=generation_info.get("duration_ms"),
                model=generation_info.get("model"),
                token_usage={"fallback": False},
            )
            
        except ModelError as e:
            # Fallback to placeholder PNG
            _write_placeholder_png(artifact_path)
            image_path = str(artifact_path)
            generation_info = {
                "model": "placeholder",
                "fallback_used": True,
                "fallback_reason": str(e),
            }
            
            log_event(
                run_id,
                "image_generation",
                attempt,
                "ok",
                model="placeholder",
                token_usage={
                    "fallback": True,
                    "reason": "gemini_generation_failed",
                },
            )
        
        # Validate generated file
        if not artifact_path.exists():
            raise ModelError("Image file was not created")
        
        if artifact_path.stat().st_size == 0:
            raise ModelError("Generated image file is empty")
        
        # Success response
        response = ok({
            "image_path": image_path,
            "generation_info": generation_info,
        })
        validate_envelope(response)
        return response
        
    except ValidationError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(
            run_id, "image_generation", attempt, "error", error_type=type(e).__name__
        )
        return response
    except ModelError as e:
        response = err(type(e).__name__, str(e), retryable=e.retryable)
        validate_envelope(response)
        log_event(
            run_id, "image_generation", attempt, "error", error_type=type(e).__name__
        )
        return response
    except Exception as e:
        response = err(type(e).__name__, str(e), retryable=True)
        validate_envelope(response)
        log_event(
            run_id, "image_generation", attempt, "error", error_type=type(e).__name__
        )
        return response
