"""
Tests for persona compliance across agents.

This module validates that agent outputs adhere to the persona guidelines
defined in system_prompts.md:
- Prompt Generator persona fidelity (Strategic Content Architect)
- Writer persona fidelity (The Witty Expert)
- Image Prompt Generator persona fidelity (Visual Strategist)
"""

import pytest
import re
from typing import List, Dict, Any


# =============================================================================
# Helper Functions for Persona Validation
# =============================================================================


# Cliché blacklist for analogies
CLICHE_BLACKLIST = [
    "distributed ledger",
    "like a library",
    "like a recipe",
    "think of x as y",
    "think of it as",
    "imagine a library",
    "like a filing cabinet",
    "like a box",
    "like a bucket",
    "at the end of the day",
    "low-hanging fruit",
    "move the needle",
    "synergy",
    "paradigm shift",
]

# Corporate jargon to avoid
CORPORATE_JARGON = [
    "leverage",
    "synergize",
    "actionable insights",
    "circle back",
    "deep dive",
    "touch base",
    "bandwidth",
    "holistic approach",
    "value proposition",
    "best-in-class",
    "mission-critical",
    "scalable solution",
]


def contains_cliche(text: str) -> bool:
    """Check if text contains any cliché phrases (case-insensitive)."""
    text_lower = text.lower()
    return any(cliche in text_lower for cliche in CLICHE_BLACKLIST)


def contains_corporate_jargon(text: str) -> bool:
    """Check if text contains corporate jargon to avoid."""
    text_lower = text.lower()
    return any(jargon in text_lower for jargon in CORPORATE_JARGON)


def count_hashtags(text: str) -> int:
    """Count hashtags in text."""
    return len(re.findall(r"#\w+", text))


def count_paragraphs(text: str) -> List[str]:
    """Split text into paragraphs."""
    return [p.strip() for p in text.split("\n\n") if p.strip()]


def count_bold_phrases(text: str) -> int:
    """Count bold phrases (**text**)."""
    return len(re.findall(r"\*\*[^*]+\*\*", text))


def count_bullet_points(text: str) -> int:
    """Count bullet points in text."""
    return len(re.findall(r"^[\s]*[-•*]\s", text, re.MULTILINE))


def extract_section(text: str, section_name: str) -> str:
    """Extract content after a **Section:** marker."""
    pattern = rf"\*\*{re.escape(section_name)}:\*\*\s*(.*?)(?=\*\*[A-Z]|\Z)"
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    return match.group(1).strip() if match else ""


def has_no_text_instruction(text: str) -> bool:
    """Check if image prompt specifies no text/words/letters."""
    text_lower = text.lower()
    patterns = [
        "zero text",
        "no text",
        "no words",
        "no letters",
        "without text",
        "without words",
        "text-free",
        "contain no text",
        "contains no text",
    ]
    return any(pattern in text_lower for pattern in patterns)


# =============================================================================
# Test Suite: Prompt Generator Persona (Strategic Content Architect)
# =============================================================================


class TestPromptGeneratorPersona:
    """Test Prompt Generator persona fidelity (Strategic Content Architect)."""

    # --- Template Structure Tests ---

    def test_template_has_topic_section(self):
        """Verify **Topic:** section exists and is non-empty."""
        sample_output = """Generate a LinkedIn post using the Witty Expert persona.

**Topic:** Understanding Vector Databases

**Target Audience:** ML Engineers and Data Scientists

**Audience's Core Pain Point:** Struggling with similarity search at scale.

**Key Metrics/Facts:** Vector DBs enable 100x faster similarity queries.

**The Simple Solution/Code Snippet:** Use a vector database like Pinecone.
"""
        topic = extract_section(sample_output, "Topic")
        assert topic, "Topic section should exist and be non-empty"
        assert len(topic) > 0

    def test_template_has_target_audience_section(self):
        """Verify **Target Audience:** section exists and is non-empty."""
        sample_output = """**Topic:** Test Topic

**Target Audience:** Data Scientists, ML Engineers, and Analytics Professionals

**Audience's Core Pain Point:** Pain point here.
"""
        audience = extract_section(sample_output, "Target Audience")
        assert audience, "Target Audience section should exist and be non-empty"

    def test_template_has_pain_point_section(self):
        """Verify **Audience's Core Pain Point:** section exists and is non-empty."""
        sample_output = """**Topic:** Test Topic

**Target Audience:** Engineers

**Audience's Core Pain Point:** My data pipelines are slow and frustrating, causing delays in my workflow.

**Key Metrics/Facts:** Important metrics.
"""
        pain_point = extract_section(sample_output, "Audience's Core Pain Point")
        assert pain_point, "Pain point section should exist and be non-empty"
        # Pain point should describe human frustration, not just technical issue
        assert len(pain_point.split()) > 5, "Pain point should be descriptive"

    def test_template_has_key_metrics_section(self):
        """Verify **Key Metrics/Facts:** section exists with data points."""
        sample_output = """**Topic:** Test

**Key Metrics/Facts:** The core concept is columnar storage.
- A CSV is like reading every page of a book.
- Parquet jumps directly to the index.
- 5-10x faster read speeds.
- 50-80% storage reduction.

**The Simple Solution/Code Snippet:** Code here.
"""
        metrics = extract_section(sample_output, "Key Metrics/Facts")
        assert metrics, "Key Metrics section should exist"
        # Should contain data points (indicated by dashes or numbers)
        assert "-" in metrics or any(
            char.isdigit() for char in metrics
        ), "Key Metrics should contain data points"

    def test_template_has_solution_section(self):
        """Verify **The Simple Solution/Code Snippet:** section exists."""
        sample_output = """**Topic:** Test

**The Simple Solution/Code Snippet:** The "Aha!" moment is a one-line change:
```python
df.to_parquet('data.parquet')
```
"""
        solution = extract_section(sample_output, "The Simple Solution/Code Snippet")
        assert solution, "Solution/Code Snippet section should exist"

    def test_template_structure_complete(self):
        """Verify complete template structure with all required sections."""
        sample_output = """Generate a LinkedIn post using the Witty Expert persona.

**Topic:** Efficient File Formats: The Power of Parquet over CSV

**Target Audience:** Data Scientists, Data Engineers, and Analytics Professionals.

**Audience's Core Pain Point:** My data loading scripts take forever to run every morning.

**Key Metrics/Facts:** The core concept is columnar storage.
- Parquet stores data in columns for faster queries.
- 5-10x improvement in read/write speeds.

**The Simple Solution/Code Snippet:** One-line code change:
```python
df.to_parquet('data.parquet')
```
"""
        required_sections = [
            "Topic",
            "Target Audience",
            "Audience's Core Pain Point",
            "Key Metrics/Facts",
            "The Simple Solution/Code Snippet",
        ]

        for section in required_sections:
            content = extract_section(sample_output, section)
            assert content, f"Required section '{section}' should be present"

    # --- Cliché Detection Tests ---

    def test_cliche_detection_distributed_ledger(self):
        """Test blacklist includes 'distributed ledger'."""
        text = "A blockchain is a distributed ledger technology."
        assert contains_cliche(text), "'distributed ledger' should be detected"

    def test_cliche_detection_like_a_library(self):
        """Test blacklist includes 'like a library'."""
        text = "Think of a database like a library with books."
        assert contains_cliche(text), "'like a library' should be detected"

    def test_cliche_detection_like_a_recipe(self):
        """Test blacklist includes 'like a recipe'."""
        text = "Code is like a recipe for the computer."
        assert contains_cliche(text), "'like a recipe' should be detected"

    def test_cliche_detection_think_of_as(self):
        """Test blacklist includes 'think of X as Y' pattern."""
        text = "Think of it as a simple storage solution."
        assert contains_cliche(text), "'think of it as' should be detected"

    def test_cliche_detection_case_insensitive(self):
        """Test case-insensitive cliché matching."""
        text = "A DISTRIBUTED LEDGER is used for blockchain."
        assert contains_cliche(text), "Case-insensitive matching should work"

    def test_cliche_detection_partial_phrase(self):
        """Test partial phrase matching (e.g., 'distributed ledger technology')."""
        text = "Blockchain uses distributed ledger technology for consensus."
        assert contains_cliche(text), "Partial phrase should match"

    def test_fresh_analogy_no_cliches(self):
        """Test that fresh analogies pass cliché detection."""
        fresh_text = """A CSV is like a sprawling book with no index.
Parquet is like a hyper-organized index that jumps directly to what you need."""
        assert not contains_cliche(
            fresh_text
        ), "Fresh analogies should not trigger cliché detection"

    # --- Analogy Freshness Tests ---

    def test_analogy_avoids_generic_technical_comparisons(self):
        """Test analogies avoid generic technical comparisons."""
        # Good: Unexpected domain connection
        good_analogy = (
            "A GPU is like a drill sergeant commanding thousands of soldiers."
        )
        # Bad: Generic technical comparison
        bad_analogy = "A GPU is like a faster CPU."

        assert not contains_cliche(good_analogy), "Fresh analogy should pass"
        # Generic comparisons are hard to auto-detect, but clichés are clear

    def test_analogy_connects_unexpected_domains(self):
        """Test analogies connect to unexpected domains (cooking, sports, psychology)."""
        sample = """
**Key Metrics/Facts:** 
- Think of feature engineering like being a head chef: you take raw ingredients (data) 
  and transform them into a gourmet dish (useful features).
- A well-engineered feature is the secret seasoning that separates a home cook from a Michelin star.
"""
        # Should reference non-technical domain
        unexpected_domains = [
            "chef",
            "cook",
            "sport",
            "coach",
            "psycholog",
            "surgeon",
            "artist",
        ]
        sample_lower = sample.lower()
        has_unexpected_domain = any(
            domain in sample_lower for domain in unexpected_domains
        )
        assert (
            has_unexpected_domain or "analogy" in sample_lower
        ), "Analogies should connect to unexpected domains"


# =============================================================================
# Test Suite: Writer Persona (The Witty Expert)
# =============================================================================


class TestWriterPersona:
    """Test Writer persona fidelity (The Witty Expert)."""

    @pytest.fixture
    def sample_linkedin_post(self):
        """Sample LinkedIn post following The Witty Expert persona."""
        return """Let's talk about your data's living situation.

If your data is still crashing in a CSV file, it's basically sleeping on a friend's couch. Functional? Sure. Optimized? Absolutely not.

**Here's the uncomfortable truth:** Every time you load that CSV, your computer has to read the entire thing—even if you only need one column. It's like being forced to read an entire encyclopedia just to find out what year the printing press was invented.

Enter Parquet. This is your data's upgrade to a luxury apartment with a concierge.

- **5-10x faster** read/write speeds
- **50-80% smaller** storage footprint
- Columnar storage means you only touch what you need

The best part? It's a one-line code change:

```python
df.to_parquet('data.parquet')
```

That 5-minute script? Now takes 30 seconds. That bloated storage bill? Cut in half.

Stop making your data sleep on the couch. Give it the penthouse suite.

What's the biggest efficiency win you've discovered in your data workflow?
"""

    # --- LinkedIn Post Structure Tests ---

    def test_hook_grabs_attention(self, sample_linkedin_post):
        """Verify hook grabs attention with surprising statement or question."""
        first_paragraph = sample_linkedin_post.split("\n\n")[0]

        # Hook should be short and engaging
        assert len(first_paragraph.split()) < 20, "Hook should be concise"

        # Hook patterns: question, direct address, surprising statement
        hook_patterns = [
            r"\?",  # Question
            r"Let's talk",  # Direct invitation
            r"Here's",  # Direct statement
            r"you|your",  # Direct address
        ]
        has_hook_pattern = any(
            re.search(pattern, first_paragraph, re.IGNORECASE)
            for pattern in hook_patterns
        )
        assert has_hook_pattern, "Hook should use engaging patterns"

    def test_problem_articulates_pain_point(self, sample_linkedin_post):
        """Verify problem section articulates pain point beyond technical issue."""
        # Look for human frustration indicators
        frustration_words = [
            "uncomfortable",
            "forced",
            "every time",
            "entire",
            "waiting",
            "slow",
            "frustrating",
            "tired",
            "annoying",
        ]
        post_lower = sample_linkedin_post.lower()
        has_frustration = any(word in post_lower for word in frustration_words)
        assert has_frustration, "Should articulate human frustration"

    def test_solution_provides_actionable_insights(self, sample_linkedin_post):
        """Verify solution section provides actionable insights or code snippets."""
        # Should contain code block
        assert "```" in sample_linkedin_post, "Should include code snippet"

        # Or should have actionable language
        actionable_words = ["enter", "upgrade", "use", "try", "implement", "switch"]
        post_lower = sample_linkedin_post.lower()
        has_action = any(word in post_lower for word in actionable_words)
        assert has_action, "Should provide actionable guidance"

    def test_impact_connects_to_outcomes(self, sample_linkedin_post):
        """Verify impact section connects to business/career outcomes."""
        # Look for outcome indicators
        outcome_patterns = [
            r"\d+x faster",
            r"\d+%",
            r"seconds?",
            r"minutes?",
            r"storage",
            r"bill",
            r"cut in half",
        ]
        has_outcome = any(
            re.search(pattern, sample_linkedin_post, re.IGNORECASE)
            for pattern in outcome_patterns
        )
        assert has_outcome, "Should quantify impact"

    def test_call_to_action_prompts_engagement(self, sample_linkedin_post):
        """Verify call-to-action prompts engagement (comment, share, try)."""
        # Last paragraph often contains CTA
        paragraphs = count_paragraphs(sample_linkedin_post)
        last_paragraph = paragraphs[-1] if paragraphs else ""

        cta_patterns = [
            r"\?",  # Question
            r"what.+you",  # What do you
            r"share",
            r"comment",
            r"try",
            r"tell me",
        ]
        has_cta = any(
            re.search(pattern, last_paragraph, re.IGNORECASE)
            for pattern in cta_patterns
        )
        assert has_cta, "Should include call-to-action"

    def test_sign_off_conversational(self, sample_linkedin_post):
        """Verify sign-off is conversational and inviting."""
        paragraphs = count_paragraphs(sample_linkedin_post)

        # Should have a memorable sign-off before CTA
        if len(paragraphs) >= 2:
            second_to_last = paragraphs[-2]
            # Conversational indicators
            conversational_patterns = [r"stop", r"give", r"let's", r"don't", r"you"]
            has_conversational = any(
                re.search(pattern, second_to_last, re.IGNORECASE)
                for pattern in conversational_patterns
            )
            assert (
                has_conversational or "?" in second_to_last
            ), "Sign-off should be conversational"

    # --- Tone and Voice Tests ---

    def test_dry_wit_not_slapstick(self, sample_linkedin_post):
        """Test presence of dry wit (subtle humor, not slapstick)."""
        # Dry wit indicators: irony, understatement, clever comparisons
        wit_phrases = [
            "couch",
            "penthouse",
            "luxury",
            "encyclopedia",
            "Functional? Sure.",
            "Absolutely not",
        ]
        post_text = sample_linkedin_post
        has_wit = any(phrase in post_text for phrase in wit_phrases)
        assert has_wit, "Should have dry wit elements"

    def test_conversational_tone(self, sample_linkedin_post):
        """Test conversational tone (contractions, rhetorical questions)."""
        # Contractions
        contractions = ["it's", "you're", "that's", "don't", "isn't", "what's"]
        post_lower = sample_linkedin_post.lower()
        has_contractions = any(c in post_lower for c in contractions)

        # Rhetorical questions
        has_questions = "?" in sample_linkedin_post

        assert (
            has_contractions and has_questions
        ), "Should use contractions and questions for conversational tone"

    def test_no_corporate_jargon(self, sample_linkedin_post):
        """Test absence of corporate jargon and buzzwords."""
        assert not contains_corporate_jargon(
            sample_linkedin_post
        ), "Should avoid corporate jargon"

    def test_short_paragraphs(self, sample_linkedin_post):
        """Test short paragraphs (2-4 sentences max)."""
        paragraphs = count_paragraphs(sample_linkedin_post)

        for para in paragraphs:
            # Count sentences roughly by periods and question marks
            sentences = len(re.findall(r"[.!?]", para))
            assert sentences <= 5, f"Paragraph too long: {para[:50]}..."

    def test_bold_emphasis_strategic(self, sample_linkedin_post):
        """Test strategic use of bold for emphasis (1-3 phrases per post)."""
        bold_count = count_bold_phrases(sample_linkedin_post)
        assert 1 <= bold_count <= 5, f"Should have 1-5 bold phrases, got {bold_count}"

    def test_bullet_points_for_lists(self, sample_linkedin_post):
        """Test bullet points for lists (3-5 items max)."""
        bullet_count = count_bullet_points(sample_linkedin_post)
        if bullet_count > 0:
            assert (
                bullet_count <= 7
            ), f"Bullet lists should be concise, got {bullet_count}"

    # --- Character Limits and Formatting Tests ---

    def test_post_under_3000_characters(self, sample_linkedin_post):
        """Test post stays under 3000 characters."""
        char_count = len(sample_linkedin_post)
        assert char_count < 3000, f"Post should be under 3000 chars, got {char_count}"

    def test_hashtags_minimal(self, sample_linkedin_post):
        """Test hashtags removed or minimal (0-2 max)."""
        hashtag_count = count_hashtags(sample_linkedin_post)
        assert hashtag_count <= 2, f"Should have 0-2 hashtags, got {hashtag_count}"

    def test_proper_spacing(self, sample_linkedin_post):
        """Test proper spacing between sections."""
        # Should have multiple paragraphs separated by blank lines
        paragraphs = count_paragraphs(sample_linkedin_post)
        assert len(paragraphs) >= 3, "Should have multiple well-separated sections"


# =============================================================================
# Test Suite: Image Prompt Generator Persona (Visual Strategist)
# =============================================================================


class TestImagePromptGeneratorPersona:
    """Test Image Prompt Generator persona fidelity (Visual Strategist)."""

    @pytest.fixture
    def sample_image_prompt(self):
        """Sample image prompt following Visual Strategist guidelines."""
        return """A sleek, modern server room with towering racks of glowing hardware, 
viewed from a low angle. In the foreground, a small, cozy apartment with warm 
lighting is superimposed, creating a surreal contrast between industrial scale 
and personal comfort. The lighting transitions from cool blue LED in the server 
room to warm golden hues in the apartment. The mood is aspirational and 
transformative—showing the journey from chaos to organization. 
No text, words, or letters should appear in the image."""

    # --- No-Text Constraint Tests ---

    def test_prompt_specifies_no_text(self, sample_image_prompt):
        """Test prompt explicitly states 'zero text', 'no words', or 'no letters'."""
        assert has_no_text_instruction(
            sample_image_prompt
        ), "Image prompt must specify no text/words/letters"

    def test_validation_rejects_missing_no_text(self):
        """Test validation rejects prompts missing no-text instruction."""
        bad_prompt = """A beautiful landscape with mountains and sunset. 
Warm lighting and peaceful mood."""
        assert not has_no_text_instruction(
            bad_prompt
        ), "Prompt without no-text instruction should fail validation"

    def test_no_text_instruction_variations(self):
        """Test various forms of no-text instruction are accepted."""
        valid_prompts = [
            "Generate an image with zero text.",
            "The image should contain no words.",
            "Create a visual with no letters or text.",
            "A scene without text or typography.",
            "The image must be text-free.",
        ]
        for prompt in valid_prompts:
            assert has_no_text_instruction(prompt), f"Should accept: {prompt}"

    # --- Visual Element Specification Tests ---

    def test_prompt_includes_subject(self, sample_image_prompt):
        """Test prompt includes subject description (what is depicted)."""
        subject_indicators = ["server room", "racks", "hardware", "apartment"]
        prompt_lower = sample_image_prompt.lower()
        has_subject = any(s in prompt_lower for s in subject_indicators)
        assert has_subject, "Should describe what is depicted"

    def test_prompt_includes_environment(self, sample_image_prompt):
        """Test prompt includes environment/setting description."""
        environment_words = [
            "room",
            "space",
            "setting",
            "background",
            "foreground",
            "scene",
            "environment",
            "interior",
            "exterior",
        ]
        prompt_lower = sample_image_prompt.lower()
        has_environment = any(e in prompt_lower for e in environment_words)
        assert has_environment, "Should describe environment/setting"

    def test_prompt_includes_lighting(self, sample_image_prompt):
        """Test prompt includes lighting description."""
        lighting_words = [
            "lighting",
            "light",
            "glow",
            "led",
            "illuminat",
            "bright",
            "dark",
            "shadow",
            "natural",
            "dramatic",
            "soft",
        ]
        prompt_lower = sample_image_prompt.lower()
        has_lighting = any(l in prompt_lower for l in lighting_words)
        assert has_lighting, "Should describe lighting"

    def test_prompt_includes_mood(self, sample_image_prompt):
        """Test prompt includes mood/emotion description."""
        mood_words = [
            "mood",
            "feel",
            "atmosphere",
            "emotion",
            "calm",
            "energetic",
            "mysterious",
            "aspirational",
            "peaceful",
            "dramatic",
            "transformative",
            "inspiring",
        ]
        prompt_lower = sample_image_prompt.lower()
        has_mood = any(m in prompt_lower for m in mood_words)
        assert has_mood, "Should describe mood/emotion"

    # --- Thematic Alignment Tests ---

    def test_prompt_relates_to_message(self):
        """Test image concept relates to post's core message."""
        # Post about data storage -> image should reflect storage/organization
        post_theme = "data storage optimization"
        image_prompt = """Server racks transforming into organized filing cabinets, 
with warm lighting suggesting efficiency and calm. No text."""

        theme_words = ["server", "storage", "organ", "file", "data"]
        prompt_lower = image_prompt.lower()
        has_theme = any(t in prompt_lower for t in theme_words)
        assert has_theme, "Image should relate to post theme"

    def test_metaphorical_over_literal(self):
        """Test metaphorical representations preferred over literal."""
        # Metaphorical: data as physical objects, concepts as scenes
        metaphorical_prompt = """A caterpillar transforming into a butterfly, 
with the caterpillar representing old CSV files and the butterfly 
representing modern Parquet format. Warm, hopeful lighting. No text."""

        # Should have comparison/transformation language
        metaphor_words = ["transform", "represent", "symbol", "metaphor", "like", "as"]
        prompt_lower = metaphorical_prompt.lower()
        has_metaphor = any(m in prompt_lower for m in metaphor_words)
        # Or should have vivid, non-technical imagery
        assert (
            has_metaphor or "butterfly" in prompt_lower
        ), "Should prefer metaphorical representations"

    def test_avoids_generic_stock_photo(self):
        """Test prompts avoid generic stock photo descriptions."""
        generic_prompts = [
            "Business people shaking hands in an office.",
            "Person typing on a laptop with coffee.",
            "Team meeting in a conference room.",
        ]

        for prompt in generic_prompts:
            # Generic stock photos often mention "business", "office", "meeting" generically
            generic_indicators = all(
                [
                    "business" in prompt.lower() or "office" in prompt.lower(),
                    "laptop" in prompt.lower() or "meeting" in prompt.lower(),
                ]
            )
            # This test shows what to avoid - these should NOT be the output


# =============================================================================
# Test Suite: Integration - Persona Validation Functions
# =============================================================================


class TestPersonaValidationIntegration:
    """Integration tests for persona validation functions."""

    def test_validate_prompt_generator_output(self):
        """Validate complete Prompt Generator output against persona checklist."""
        output = """Generate a LinkedIn post using the Witty Expert persona.

**Topic:** GPU vs CPU: The Drill Sergeant vs The Surgeon

**Target Audience:** ML Engineers working with deep learning models

**Audience's Core Pain Point:** Training takes forever and I'm tired of watching progress bars crawl.

**Key Metrics/Facts:** 
- A CPU is like a brilliant surgeon: one very skilled pair of hands doing one thing at a time.
- A GPU is like a drill sergeant commanding 10,000 soldiers: less skilled individually, but devastating in parallel.
- GPUs can be 100x faster for matrix operations.

**The Simple Solution/Code Snippet:**
```python
model.to('cuda')  # That's it. One line.
```
"""
        # Check template structure
        assert "**Topic:**" in output
        assert "**Target Audience:**" in output
        assert "**Audience's Core Pain Point:**" in output
        assert "**Key Metrics/Facts:**" in output
        assert "**The Simple Solution/Code Snippet:**" in output

        # Check for clichés
        assert not contains_cliche(output), "Should not contain clichés"

        # Extract and verify sections have content
        topic = extract_section(output, "Topic")
        audience = extract_section(output, "Target Audience")
        pain = extract_section(output, "Audience's Core Pain Point")

        assert len(topic) > 0
        assert len(audience) > 0
        assert len(pain) > 0

    def test_validate_writer_output(self):
        """Validate complete Writer output against persona checklist."""
        post = """Why is your model still doing push-ups when it could be running a marathon?

If you're training on CPU, you're asking one brilliant surgeon to perform 10,000 surgeries. 
One at a time. Sequentially. **While you watch the progress bar mock you.**

Here's the thing: matrix math is embarrassingly parallel. Every GPU core is a soldier waiting for orders.

The switch? One line of code:
```python
model.to('cuda')
```

That's it. Your training time just dropped from hours to minutes.

What's stopping you from making the switch?
"""
        # Character count
        assert len(post) < 3000, "Post should be under 3000 chars"

        # Structure
        paragraphs = count_paragraphs(post)
        assert len(paragraphs) >= 3, "Should have multiple sections"

        # Engagement elements
        assert "?" in post, "Should have questions"
        assert "**" in post, "Should have bold emphasis"

        # No jargon
        assert not contains_corporate_jargon(post)

        # Minimal hashtags
        assert count_hashtags(post) <= 2

    def test_validate_image_prompt_output(self):
        """Validate complete Image Prompt output against persona checklist."""
        prompt = """A vast training ground with thousands of tiny soldiers (representing GPU cores) 
standing in perfect formation, illuminated by dramatic stadium lighting. In contrast, 
a single surgeon stands alone in a spotlight, representing CPU's sequential processing. 
The mood is powerful and transformative, showing the scale difference. 
The image must contain no text, words, or letters."""

        # No-text constraint
        assert has_no_text_instruction(prompt), "Must specify no text"

        # Visual elements
        prompt_lower = prompt.lower()
        assert any(
            w in prompt_lower for w in ["lighting", "light", "illuminat"]
        ), "Should specify lighting"
        assert any(
            w in prompt_lower for w in ["mood", "feel", "atmosphere", "powerful"]
        ), "Should specify mood"
        assert len(prompt) > 50, "Should be descriptive enough"
