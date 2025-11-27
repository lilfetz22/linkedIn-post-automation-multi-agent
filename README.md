# LinkedIn Post Automation Multi-Agent

A robust, automated pipeline that generates high-quality, strategically-sound LinkedIn posts using a multi-agent architecture powered by Google's Gemini AI models. This system handles everything from topic selection and research to content creation, review, and image generation.

## Overview

This application orchestrates a series of specialized AI agents to create engaging LinkedIn content tailored to your field of expertise. Each agent performs a distinct task in a sequential workflow, ensuring consistent quality and strategic alignment while maintaining full auditability through comprehensive logging and artifact persistence.

### Key Features

- 🤖 **Multi-Agent Architecture**: Specialized agents for each stage of content creation
- 📊 **Intelligent Topic Selection**: Automatic topic generation with built-in variety tracking
- 🔍 **Automated Research**: Gathers relevant information and synthesizes findings
- ✍️ **Strategic Content Creation**: Uses "The Witty Expert" persona for engaging, memorable posts
- 🎨 **AI-Generated Images**: Automated image creation using Gemini's image generation capabilities
- 📝 **Quality Assurance**: Two-pass review system with character count validation
- 💾 **Full Auditability**: Every step logged and artifacts saved for debugging and improvement
- 🔄 **Resilient Error Handling**: Automatic retries, fallback strategies, and circuit breakers

## Architecture

### Language Models

- **Core Logic & Text Agents**: `Gemini 2.5 Pro`
- **AI Image Generator**: `gemini-2.5-flash-image-preview`

#### LLM Integration by Agent

Each agent leverages different LLM capabilities depending on its role:

| Agent | Model | Purpose | Temperature | Est. Tokens/Call |
|-------|-------|---------|-------------|------------------|
| **Topic Agent** | Gemini 2.5 Pro | Generate new topics when database exhausted | 0.7 | ~200 input, ~500 output |
| **Research Agent** | Gemini 2.5 Pro | Synthesize web search results into structured research | 0.5 | ~1000 input, ~800 output |
| **Prompt Generator** | Gemini 2.5 Pro | Transform raw topics into Strategic Content Architect prompts | 0.7 | ~800 input, ~600 output |
| **Writer Agent** | Gemini 2.5 Pro | Draft engaging posts using The Witty Expert persona | 0.8 | ~1000 input, ~1500 output |
| **Reviewer Agent** | Gemini 2.5 Pro | Perform contextual review and coherence checking | 0.3 | ~1500 input, ~1500 output |
| **Image Prompt Generator** | Gemini 2.5 Pro | Create descriptive visual prompts from post content | 0.7 | ~1500 input, ~300 output |
| **Image Generator** | Gemini 2.5 Flash Image | Generate AI images from text prompts | N/A | Fixed cost per image |

**Total Estimated Cost per Run**: $0.08 - $0.15 USD (varies by content complexity and iteration count)

**Note**: Strategic Type Agent was deprecated and removed from the pipeline. Writer Agent now receives structured prompts directly.

### Agent System

The application uses nine specialized agents orchestrated in a sequential workflow:

1. **Orchestrator Agent**: Central controller managing the workflow, data flow, and error handling
2. **Topic Agent**: Selects unique topics from the configured field, avoiding recent repeats
3. **Research Agent**: Gathers and synthesizes information on the selected topic
4. **Prompt Generator Agent (Strategic Content Architect)**: Transforms raw technical topics into structured prompts with inferred audience insights and fresh analogies
5. **Strategic Type Agent**: Designs post structure using RAG-enabled memory bank of proven content strategies
6. **Writer Agent (The Witty Expert)**: Drafts engaging posts using a brilliant, witty persona
7. **Reviewer Agent**: Performs contextual sense-checking and grammar/spelling corrections
8. **Image Prompt Generator Agent**: Creates descriptive prompts for image generation
9. **AI Image Generator Agent**: Generates relevant images for the post

### Agent Personas

The system features two specialized personas defined in `system_prompts.md`:

- **The Strategic Content Architect**: A prompt engineer who transforms technical topics into structured, high-quality prompts by inferring audience pain points and creating fresh analogies
- **The Witty Expert**: A brilliant professor with a late-night talk show vibe—deeply knowledgeable but never stuffy, using intellectual sparkle and wit to make complex topics delightful

## Workflow

Each execution follows this sequence:

1. **Initialization**: Creates unique run directory with timestamp
2. **Topic Selection**: Queries database to select/generate a new topic
3. **Research**: Gathers information and synthesizes findings
4. **Prompt Generation**: Transforms topic into structured prompt with audience insights
5. **Strategy**: Designs post structure using proven content strategies
6. **Writing**: Drafts post using The Witty Expert persona
7. **Review**: Two-pass refinement (contextual + grammar)
8. **Character Count Validation**: Ensures post is under 3000 characters (loops back if needed)
9. **Image Prompt Generation**: Creates descriptive prompt for image
10. **Image Generation**: Generates relevant image
11. **Completion**: Marks run as complete

## Project Structure

```
/project-root
├── main.py                  # Main execution script
├── orchestrator.py          # Orchestration logic
├── agents/                  # Agent implementations
│   ├── __init__.py
│   ├── topic_agent.py
│   ├── research_agent.py
│   ├── prompt_generator_agent.py
│   ├── strategic_type_agent.py
│   ├── writer_agent.py
│   ├── reviewer_agent.py
│   ├── image_prompt_agent.py
│   └── image_generator_agent.py
├── core/                    # Core utilities
│   ├── llm_clients.py
│   ├── rag_setup.py
│   └── ...
├── database/                # Data persistence
│   └── topics.db
├── runs/                    # Run artifacts (created at runtime)
│   └── {YYYY-MM-DD}-{runId}/
│       ├── 00_config.json
│       ├── 10_topic.json
│       ├── 20_research.json
│       ├── 25_structured_prompt.json
│       ├── 30_strategy.json
│       ├── 40_draft.md
│       ├── 50_review.json
│       ├── 60_final_post.txt
│       ├── 70_image_prompt.txt
│       ├── 80_image.png
│       ├── prompts/
│       └── completions/
├── memory_bank/             # RAG corpus
│   └── ... (newsletter .txt files)
├── .env                     # API keys (not in repo)
├── .gitignore
├── requirements.txt
├── system_prompts.md        # Agent persona definitions
├── project_spec.md          # Detailed specifications
└── README.md
```

## Installation

### Prerequisites

- Python 3.10 or higher
- Google AI Studio API key ([Get one here](https://makersuite.google.com/app/apikey))

### Setup

1. **Clone the repository**
	```bash
	git clone https://github.com/lilfetz22/linkedIn-post-automation-multi-agent.git
	cd linkedIn-post-automation-multi-agent
	```

2. **Create a virtual environment**
	```bash
	python -m venv venv
   
	# On Windows
	.\venv\Scripts\activate
   
	# On macOS/Linux
	source venv/bin/activate
	```

3. **Install dependencies**
	```bash
	pip install -r requirements.txt
	```

4. **Configure API keys**
   
	Create a `.env` file in the project root:
	```env
	GOOGLE_API_KEY=your_google_ai_studio_api_key_here
	```

5. **First-time setup**
   
	On first run, you'll be prompted to select your field of expertise:
	- Data Science (Optimizations & Time-Series Analysis)
	- Generative AI & AI Agents
   
	Your selection is saved in `config.json`.

## Usage

### Basic Execution

Run the application from the command line:

```bash
python main.py
```

### Output

Each run generates:
- **Text file**: `60_final_post.txt` - The completed LinkedIn post
- **Image file**: `80_image.png` - AI-generated accompanying image
- **Artifacts**: Complete audit trail in the run directory

### Viewing Run Artifacts

Navigate to `runs/{YYYY-MM-DD}-{runId}/` to inspect:
- All intermediate agent outputs (JSON files)
- Draft versions and revisions
- LLM prompts and completions
- Generated images

### Event Logging

All system events are logged to `events.jsonl` at the project root. Each line is a JSON object containing:
- Timestamp
- Run ID
- Step name
- Attempt number
- Status (ok/error)
- Duration
- Token usage

## Data Persistence

### SQLite Database (`topics.db`)

The application maintains two tables:

**`previous_topics`**
- Tracks all topics used in previous posts
- Prevents repetition

**`potential_topics`**
- Stores curated topic ideas by field
- Used by Topic Agent for generation

### Memory Bank (RAG)

The `memory_bank/` directory contains the corpus for the Strategic Type Agent's RAG system:
- Newsletter content files (.txt)
- Proven content strategies
- Structural templates

## Error Handling & Resilience

The system includes robust error handling:

- **Automatic Retries**: Up to 3 attempts with exponential backoff for transient errors
- **Fallback Strategies**: Simplified prompts, alternative approaches when primary methods fail
- **Circuit Breaker**: Aborts run after 3 consecutive LLM failures
- **Artifact Integrity**: Immediate validation of all written files
- **Failure Logging**: Detailed `run_failed.json` created on abortion

All agents return standardized responses:
```json
{
  "status": "ok" | "error",
  "data": { ... },
  "error": {
	 "type": "ErrorType",
	 "message": "...",
	 "retryable": true
  },
  "metrics": { ... }
}
```

## Cost Management & Budget Controls

The system includes comprehensive cost tracking and safety limits to prevent unexpected API expenses.

### Cost Estimation Methodology

**Token Counting**: Before each LLM call, the system counts input tokens using Gemini's native token counter (fallback to heuristic: ~4 chars per token if offline).

**Cost Calculation**:
- **Gemini 2.5 Pro**: $1.25 per 1M input tokens + $10.00 per 1M output tokens
- **Gemini 2.5 Flash Image**: $0.30 per image (estimated)

**Per-Call Tracking**: Each agent call records:
```json
{
  "model": "gemini-2.5-pro",
  "input_tokens": 1234,
  "output_tokens": 567,
  "cost_usd": 0.0072
}
```

**Aggregation**: Orchestrator accumulates costs across all agents and persists breakdown in run metrics.

### Safety Limits & Flags

The system enforces two types of budget limits:

1. **API Call Limit**: Maximum 25 API calls per run (default)
   - Prevents infinite retry loops
   - Configurable via `CostTracker(max_api_calls=N)`

2. **Cost Limit**: Maximum $3.00 USD per run (default)
   - Proactive budget checking before each call
   - Configurable via `CostTracker(max_cost_usd=N)`

**Budget Enforcement**: If a call would exceed limits, raises `ValidationError` and aborts immediately.

**Dry-Run Mode** (Planned):
```bash
python main.py --dry-run
```
This will execute all logic up to the first LLM call, allowing you to:
- Verify configuration
- Test run directory setup
- Estimate costs without spending money

### Monitoring Costs

**Real-time**: Check `events.jsonl` for per-agent token usage:
```json
{"step": "writer", "token_usage": {"input": 1234, "output": 567}, "cost_usd": 0.0072}
```

**Post-run**: Review `runs/{run_id}/metrics.json` for complete breakdown:
```json
{
  "total_cost_usd": 0.12,
  "costs_by_agent": {
    "topic": 0.005,
    "research": 0.015,
    "writer": 0.045,
    "reviewer": 0.035,
    "image": 0.020
  }
}
```

**Cost Alerts**:
- Warning logged if single run exceeds $0.50
- Abort if single run exceeds configured `max_cost_usd`

### Optimizing Costs

**Reduce API Calls**:
- Use database-seeded topics (no LLM call for Topic Agent)
- Minimize character count loop iterations (better Writer prompts)

**Optimize Token Usage**:
- Keep research summaries concise
- Use lower temperatures where appropriate (Reviewer: 0.3)
- Pre-validate inputs to avoid failed calls

## Configuration

### Field Selection

Edit `config.json` to change your field:
```json
{
  "field": "Data Science (Optimizations & Time-Series Analysis)"
}
```

### Character Limits

The system enforces a 3000-character limit for LinkedIn posts. If a post exceeds this, it's automatically sent back to the Writer Agent for shortening.

## Dependencies

Key libraries include:

- `google-generativeai` - Google's Gemini AI models
- `python-dotenv` - Environment variable management
- `sqlite3` - Topic database (built-in)
- RAG/vector embeddings: `langchain`, `llama-index`, or `chromadb`

See `requirements.txt` for complete list.

## Development

### Code Quality and Linting

This project enforces code quality standards using flake8. To maintain code quality:

**Run linting checks:**
```bash
python -m flake8 .
```

**Check for bare except statements specifically:**
```bash
python -m flake8 . --select=E722
```

**Run tests (including linting checks):**
```bash
pytest tests/
```

#### Why No Bare Except Statements?

Bare `except:` statements (without specifying an exception type) are prohibited because they:
- Catch ALL exceptions, including SystemExit and KeyboardInterrupt
- Make debugging extremely difficult by silently swallowing errors
- Can mask serious bugs and make the application fail silently

**Instead of:**
```python
try:
    risky_operation()
except:  # ❌ This will cause linting to fail
    pass
```

**Use specific exceptions:**
```python
try:
    risky_operation()
except ValueError as e:  # ✅ Specific exception
    logger.error(f"Invalid value: {e}")
except Exception as e:  # ✅ Or catch Exception (but not bare)
    logger.error(f"Unexpected error: {e}")
```

The flake8 E722 rule ensures this standard is enforced across the codebase.

## Future Development

Planned enhancements:
- Scheduling capabilities for automatic daily posting
- Integration with LinkedIn API for direct posting
- Analytics dashboard for post performance tracking
- Multi-platform support (Twitter, Medium, etc.)
- Custom persona training and fine-tuning

## System Prompts

Detailed agent personas and behavioral guidelines are maintained in `system_prompts.md`. Consult this file when:
- Understanding agent behavior
- Debugging output quality
- Extending or modifying agents

### Maintaining System Prompts

The system prompts in `system_prompts.md` are the **core intellectual property** of this system. They define agent personas and behavior patterns that directly impact output quality.

#### How to Update Personas

**File Structure**: `system_prompts.md` contains three main sections:
1. **Strategic Content Architect - User Prompt Engineer**: Transforms raw topics into structured prompts
2. **The Witty Expert Persona**: Drafts engaging, memorable LinkedIn posts
3. **Social Media Visual Strategist**: Creates image prompts from post content

**Editing Guidelines**:

1. **Preserve Template Structures**: Each persona includes exact templates (marked with `**Topic:**`, `**Target Audience:**`, etc.). These must remain intact—agents parse these fields programmatically.

2. **Maintain Persona Voice**: When revising instructions:
   - Strategic Content Architect: Focus on *inferring* audience insights, not just summarizing
   - Witty Expert: Balance intellectual depth with conversational accessibility
   - Visual Strategist: Emphasize emotional hooks and zero-text constraints

3. **Update Analogy Guidelines**: The "fresh analogy" requirement is critical. When adding examples:
   - Add new cliché phrases to avoid (e.g., "like a library", "distributed ledger")
   - Provide 2-3 new fresh analogy examples
   - Explain *why* the analogy works (unexpected + accurate)

4. **Atomic Changes**: Update one persona at a time. Test before moving to the next.

**Example Edit** (adding a new cliché to avoid):
```markdown
**Do not use stale or common analogies.**
❌ Avoid: "distributed ledger", "like a library", "like a recipe", "like a Swiss Army knife"
✅ Use: Unexpected, specific comparisons that reveal insight
```

#### How to Test Prompt Changes

**Testing Workflow**:

1. **Before Making Changes**:
   ```bash
   # Run a baseline test to capture current behavior
   python -m scripts.smoke_test --field "Data Science" --max-cost 0.15
   # Save artifacts from runs/{run_id}/ for comparison
   ```

2. **After Making Changes**:
   ```bash
   # Run with same topic to isolate prompt impact
   python -m scripts.smoke_test --field "Data Science" --max-cost 0.15
   ```

3. **Compare Outputs**:
   - **Prompt Generator**: Check `25_structured_prompt.json` for template compliance
   - **Writer**: Review `40_draft.md` for persona fidelity (wit, analogies, structure)
   - **Image Prompt**: Verify `70_image_prompt.txt` specifies no text/words

**Automated Persona Fidelity Tests**:

The test suite includes persona compliance checks in `tests/test_agents/`:

```bash
# Run persona-specific tests
pytest tests/test_agents/test_prompt_generator_agent.py::test_persona_fidelity -v
pytest tests/test_agents/test_writer_agent.py::test_witty_expert_persona -v
```

**What Tests Check**:
- **Template sections present** (Topic, Audience, Pain Point, etc.)
- **Cliché detection** (fails if blacklisted phrases appear)
- **Structure validation** (hook → problem → solution → impact format)
- **Analogy freshness** (heuristic: checks for unexpected word combinations)

**Manual Review Checklist**:
- [ ] Template fields are all present and populated
- [ ] Analogies are fresh (not in cliché blacklist)
- [ ] Tone matches persona (witty but not silly, deep but not stuffy)
- [ ] Post structure follows LinkedIn framework (hook → problem → solution)
- [ ] Character count stays under 3000 (with reasonable iteration count)
- [ ] Image prompt contains visual keywords but no text instructions

**Regression Testing**:
```bash
# Run full integration test with mocked LLMs
pytest tests/test_integration/test_llm_pipeline.py -v

# Verify all agents still produce valid envelopes
pytest tests/test_agents/ -v
```

**Rollback Strategy**: If prompt changes degrade output quality:
1. Use `git log system_prompts.md` to identify recent changes
2. Revert with `git checkout <commit-hash> -- system_prompts.md`
3. Re-run tests to confirm restoration

**Best Practices**:
- Keep a changelog of prompt modifications in git commit messages
- Test with multiple topics to ensure consistency
- Monitor `events.jsonl` for increased retry rates (indicates prompt issues)
- Compare costs before/after (poorly-worded prompts may require more tokens)
- Get human review on drafts before deploying prompt changes to production

## Troubleshooting

### Common Issues

**API Key Errors**
- Verify `.env` file exists and contains valid `GOOGLE_API_KEY`
- Check API key has proper permissions in Google AI Studio

**Database Errors**
- Ensure `database/` directory exists
- Check file permissions for `topics.db`

**Run Failures**
- Check `events.jsonl` for detailed error logs
- Review `run_failed.json` in the failed run directory
- Verify internet connection for API calls

**Character Count Loop**
- If posts consistently exceed 3000 characters, check Writer Agent prompt
- Review `40_draft.md` and `50_review.json` for excessive verbosity

## Contributing

This project is currently in active development. Contributions, issues, and feature requests are welcome!

### Commit Message Convention

This project follows the [Conventional Commits](https://www.conventionalcommits.org/) specification for commit messages. This enables automated changelog generation and semantic versioning.

#### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

#### Types

- **feat**: A new feature
- **fix**: A bug fix
- **docs**: Documentation only changes
- **style**: Changes that don't affect code meaning (formatting, whitespace)
- **refactor**: Code change that neither fixes a bug nor adds a feature
- **perf**: Performance improvement
- **test**: Adding or correcting tests
- **chore**: Changes to build process or auxiliary tools

#### Examples

```
feat(agents): add prompt generator agent with Strategic Content Architect persona

fix(orchestrator): correct character count loop termination condition

docs(readme): add conventional commits documentation

test(agents): add persona fidelity tests for Writer Agent
```

#### Breaking Changes

For breaking changes, add `BREAKING CHANGE:` in the footer:

```
feat(api)!: change agent envelope structure

BREAKING CHANGE: Agent return format now requires 'metrics' field
```

## License

[License information to be added]

## Acknowledgments

- Google's Gemini AI for powering the agent system
- "The Tech Audience Accelerator" newsletter for content strategy insights

## Contact

For questions or support, please open an issue on GitHub.

---

**Note**: This project is designed for local execution and requires an active internet connection for API calls to Google's Gemini services.
