"""
System prompt loader utility.

Loads and parses system prompts from system_prompts.md for use by agents.
Provides structured access to persona definitions for:
- Strategic Content Architect (Prompt Generator)
- The Witty Expert (Writer)
- Social Media Visual Strategist (Image Prompt Generator)
"""

from pathlib import Path
from typing import Dict


# Cache loaded prompts to avoid repeated file I/O
_PROMPT_CACHE: Dict[str, str] = {}


def load_system_prompt(section_name: str) -> str:
    """
    Load a system prompt section from system_prompts.md.

    Args:
        section_name: One of:
            - "strategic_content_architect"
            - "witty_expert"
            - "visual_strategist"

    Returns:
        The full text of the system prompt section

    Raises:
        ValueError: If section_name is not recognized
        FileNotFoundError: If system_prompts.md is not found
    """
    # Check cache first
    if section_name in _PROMPT_CACHE:
        return _PROMPT_CACHE[section_name]

    # Map section names to file markers
    section_markers = {
        "strategic_content_architect": (
            "The Strategic Content Architect- User Prompt Engineer",
            "---\n\n### System Instructions: The \"Witty Expert\" Persona"
        ),
        "witty_expert": (
            "### System Instructions: The \"Witty Expert\" Persona",
            "### System Instructions: Social Media Visual Strategist"
        ),
        "visual_strategist": (
            "### System Instructions: Social Media Visual Strategist",
            "***"
        )
    }

    if section_name not in section_markers:
        raise ValueError(
            f"Unknown section_name: {section_name}. "
            f"Valid options: {list(section_markers.keys())}"
        )

    # Locate system_prompts.md
    system_prompts_path = Path(__file__).parent.parent / "system_prompts.md"

    if not system_prompts_path.exists():
        raise FileNotFoundError(f"system_prompts.md not found at {system_prompts_path}")

    # Read file and extract section
    content = system_prompts_path.read_text(encoding="utf-8")
    start_marker, end_marker = section_markers[section_name]

    # Find section boundaries
    start_idx = content.find(start_marker)
    if start_idx == -1:
        raise ValueError(f"Start marker not found for section: {section_name}")

    end_idx = content.find(end_marker, start_idx)
    if end_idx == -1:
        # If no end marker, take rest of file
        section_text = content[start_idx:]
    else:
        section_text = content[start_idx:end_idx]

    # Clean up and cache
    section_text = section_text.strip()
    _PROMPT_CACHE[section_name] = section_text

    return section_text


def clear_cache():
    """Clear the prompt cache. Useful for testing."""
    _PROMPT_CACHE.clear()
