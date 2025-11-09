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
