"""
Tests for system prompt loader utility.
"""

import pytest
from core.system_prompts import load_system_prompt, clear_cache


class TestSystemPromptLoader:
    """Test system prompt loading from system_prompts.md."""

    def setup_method(self):
        """Clear cache before each test."""
        clear_cache()

    def test_load_strategic_content_architect(self):
        """Test loading Strategic Content Architect prompt."""
        prompt = load_system_prompt("strategic_content_architect")

        # Verify key content is present
        assert "Strategic Content Architect" in prompt
        assert "User Prompt Engineer" in prompt
        assert "**Topic:**" in prompt
        assert "**Target Audience:**" in prompt
        assert "**Audience's Core Pain Point:**" in prompt
        assert "**Key Metrics/Facts:**" in prompt
        assert "fresh, clever, and powerful analogy" in prompt

    def test_load_witty_expert(self):
        """Test loading Witty Expert prompt."""
        prompt = load_system_prompt("witty_expert")

        # Verify key content is present
        assert "Witty Expert" in prompt
        assert "brilliant professor who hosts a late-night talk show" in prompt
        assert "Analogies are Your Superpower" in prompt
        assert "LinkedIn Post Structure" in prompt
        assert "Scroll-Stopping Hook" in prompt

    def test_load_visual_strategist(self):
        """Test loading Visual Strategist prompt."""
        prompt = load_system_prompt("visual_strategist")

        # Verify key content is present
        assert "Social Media Visual Strategist" in prompt
        assert "zero text, words, or letters" in prompt
        assert "subject, the environment, the lighting, and the mood" in prompt

    def test_invalid_section_name(self):
        """Test that invalid section name raises ValueError."""
        with pytest.raises(ValueError, match="Unknown section_name"):
            load_system_prompt("invalid_section")

    def test_caching(self):
        """Test that prompts are cached after first load."""
        # Load once
        prompt1 = load_system_prompt("witty_expert")

        # Load again (should use cache)
        prompt2 = load_system_prompt("witty_expert")

        # Should be identical
        assert prompt1 == prompt2
        assert prompt1 is prompt2  # Same object reference (cached)

    def test_clear_cache(self):
        """Test cache clearing."""
        # Load and cache
        load_system_prompt("witty_expert")

        # Clear cache
        clear_cache()

        # Load again (should re-read from file)
        prompt = load_system_prompt("witty_expert")
        assert "Witty Expert" in prompt
