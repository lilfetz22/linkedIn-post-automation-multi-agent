"""
LLM client abstraction for Google Gemini models.

Provides unified interface for text generation (gemini-2.5-pro) and
image generation (gemini-2.5-flash-image-preview) with automatic
API key loading, error handling, and token usage tracking.
"""

import os
from typing import Optional, Dict, Any
from pathlib import Path

import google.generativeai as genai
from google import genai as genai_new
from google.genai import types
from dotenv import load_dotenv

from core.errors import ModelError

# Load environment variables from .env
load_dotenv()

# Configure Gemini API
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

if not GOOGLE_API_KEY:  # pragma: no cover
    raise ValueError(
        "GOOGLE_API_KEY not found in environment. " "Please add it to your .env file."
    )

genai.configure(api_key=GOOGLE_API_KEY)

# Initialize new genai client for grounding
_grounding_client = genai_new.Client(api_key=GOOGLE_API_KEY)

# Model names
TEXT_MODEL = "gemini-2.5-pro"
IMAGE_MODEL = "gemini-2.5-flash-image"


class GeminiTextClient:
    """Client for Gemini text generation (gemini-2.5-pro)."""

    def __init__(self, model_name: str = TEXT_MODEL):
        """
        Initialize text generation client.

        Args:
            model_name: Gemini model to use (default: gemini-2.5-pro)
        """
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)

    def generate_text(
        self,
        prompt: str,
        temperature: float = 0.7,
        max_output_tokens: Optional[int] = None,
        system_instruction: Optional[str] = None,
        use_search_grounding: bool = False,
    ) -> Dict[str, Any]:
        """
        Generate text from prompt with token usage tracking.

        Args:
            prompt: User prompt text
            temperature: Sampling temperature (0.0-1.0, default: 0.7)
            max_output_tokens: Maximum tokens to generate (optional)
            system_instruction: System prompt for persona/instructions (optional)
            use_search_grounding: Enable Google Search grounding for current information (default: False)

        Returns:
            Dict with keys:
            - text: Generated text content
            - token_usage: Dict with "prompt_tokens" and "completion_tokens"
            - model: Model name used
            - grounding_metadata: Search grounding info (if enabled)

        Raises:
            ModelError: If API call fails

        Example:
            >>> client = GeminiTextClient()
            >>> result = client.generate_text(
            ...     "Write a LinkedIn post about Python asyncio",
            ...     temperature=0.8
            ... )
            >>> print(result["text"])
            >>> print(f"Tokens: {result['token_usage']}")
        """
        try:
            # Use new client with grounding if requested
            if use_search_grounding:
                # Build grounding tool
                grounding_tool = types.Tool(google_search=types.GoogleSearch())

                # Build config with grounding
                config = types.GenerateContentConfig(
                    temperature=temperature,
                    max_output_tokens=max_output_tokens,
                    tools=[grounding_tool],
                    system_instruction=system_instruction,
                )

                # Generate with grounding
                response = _grounding_client.models.generate_content(
                    model=self.model_name,
                    contents=prompt,
                    config=config,
                )

                # Extract token usage and grounding metadata
                token_usage = {}
                grounding_metadata = {}

                if hasattr(response, "usage_metadata"):
                    usage = response.usage_metadata
                    token_usage = {
                        "prompt_tokens": getattr(usage, "prompt_token_count", 0),
                        "completion_tokens": getattr(
                            usage, "candidates_token_count", 0
                        ),
                    }

                # Extract grounding metadata if available
                if hasattr(response, "candidates") and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, "grounding_metadata"):
                        grounding_metadata["grounded"] = True
                        grounding_metadata["search_queries"] = getattr(
                            candidate.grounding_metadata, "search_entry_point", None
                        )

                return {
                    "text": response.text,
                    "token_usage": token_usage,
                    "model": self.model_name,
                    "grounding_metadata": grounding_metadata,
                }

            else:
                # Use standard generation without grounding
                # Build generation config
                generation_config = {
                    "temperature": temperature,
                }
                if max_output_tokens:
                    generation_config["max_output_tokens"] = max_output_tokens

                # Create model with system instruction if provided
                if system_instruction:
                    model = genai.GenerativeModel(
                        self.model_name, system_instruction=system_instruction
                    )
                else:
                    model = self.model

                # Generate content
                response = model.generate_content(
                    prompt, generation_config=generation_config
                )

                # Extract token usage (if available)
                token_usage = {}
                if hasattr(response, "usage_metadata"):
                    usage = response.usage_metadata
                    token_usage = {
                        "prompt_tokens": getattr(usage, "prompt_token_count", 0),
                        "completion_tokens": getattr(
                            usage, "candidates_token_count", 0
                        ),
                    }

                return {
                    "text": response.text,
                    "token_usage": token_usage,
                    "model": self.model_name,
                }

        except Exception as e:
            raise ModelError(f"Text generation failed: {str(e)}") from e


class GeminiImageClient:
    """Client for Gemini image generation."""

    def __init__(self, model_name: str = IMAGE_MODEL):
        """
        Initialize image generation client.

        Args:
            model_name: Gemini image model to use
        """
        self.model_name = model_name
        self.model = genai.GenerativeModel(model_name)

    def generate_image(
        self, prompt: str, output_path: str | Path, aspect_ratio: str = "1:1"
    ) -> Dict[str, Any]:
        """
        Generate image from text prompt and save to file.

        Args:
            prompt: Image description prompt
            output_path: Path to save generated PNG file
            aspect_ratio: Image aspect ratio (default: "1:1")
                Options: "1:1", "16:9", "9:16", "4:3", "3:4"

        Returns:
            Dict with keys:
            - image_path: Path where image was saved
            - model: Model name used

        Raises:
            ModelError: If image generation or saving fails

        Example:
            >>> client = GeminiImageClient()
            >>> result = client.generate_image(
            ...     "Abstract visualization of Python asyncio event loop",
            ...     output_path="80_image.png"
            ... )
            >>> print(f"Image saved to {result['image_path']}")
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)

            # Generate image
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_modalities": ["Image"],
                },
            )

            # Extract image from response
            if not response.candidates or not response.candidates[0].content.parts:
                raise ModelError("No image generated in response")

            # Save image
            image_data = response.candidates[0].content.parts[0]

            # Write binary image data
            with open(output_path, "wb") as f:
                if hasattr(image_data, "inline_data"):
                    f.write(image_data.inline_data.data)
                else:
                    # Fallback: try to get image from text response
                    raise ModelError("Image data not found in expected format")

            return {"image_path": str(output_path), "model": self.model_name}

        except Exception as e:
            raise ModelError(f"Image generation failed: {str(e)}") from e


# Singleton instances for convenience
_text_client: Optional[GeminiTextClient] = None
_image_client: Optional[GeminiImageClient] = None


def get_text_client() -> GeminiTextClient:
    """
    Get singleton text generation client.

    Returns:
        GeminiTextClient instance

    Example:
        >>> client = get_text_client()
        >>> result = client.generate_text("Write a post about...")
    """
    global _text_client
    if _text_client is None:
        _text_client = GeminiTextClient()
    return _text_client


def get_image_client() -> GeminiImageClient:
    """
    Get singleton image generation client.

    Returns:
        GeminiImageClient instance

    Example:
        >>> client = get_image_client()
        >>> result = client.generate_image("Abstract art...", "output.png")
    """
    global _image_client
    if _image_client is None:
        _image_client = GeminiImageClient()
    return _image_client
