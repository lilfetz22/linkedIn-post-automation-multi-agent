# LinkedIn Post Automation Multi-Agent System

## Project Architecture

This is a **multi-agent orchestration system** that generates LinkedIn posts through a sequential 11-step pipeline. Each agent is isolated with standardized input/output contracts, not a monolithic application.

### Core Design Principles

1. **Hybrid Communication**: Agents pass Python objects in-memory for speed, but MUST persist every I/O to disk (`runs/{YYYY-MM-DD}-{runId}/`) for auditability
2. **Standardized Agent Envelope**: All agents return `{"status": "ok"|"error", "data": {...}, "error": {...}, "metrics": {...}}`
3. **Fail-Fast with Retries**: Max 3 attempts with exponential backoff for retryable errors; immediate abort on corruption/validation failures
4. **Circuit Breaker**: Abort run after 3 consecutive LLM failures across any agents

## Agent Workflow & Artifacts

**Sequential Pipeline** (orchestrated by `orchestrator.py`):
1. Topic Selection → `10_topic.json`
2. Research → `20_research.json`
3. Prompt Generation (Strategic Content Architect) → `25_structured_prompt.json`
4. Strategy (RAG-enabled) → `30_strategy.json`
5. Writing (The Witty Expert persona) → `40_draft.md`
6. Two-Pass Review (contextual + grammar) → `50_review.json`
7. Character Count Loop (retry if ≥3000 chars)
8. Image Prompt → `70_image_prompt.txt`
9. Image Generation → `80_image.png`
10. Final Output → `60_final_post.txt`

**Artifact Integrity**: Immediately re-parse any JSON written to disk. If parse fails, raise `CorruptionError` and abort.

## Key Implementation Patterns

### Agent System Prompts
**Critical**: Consult `system_prompts.md` for exact persona definitions:
- **Strategic Content Architect** (Prompt Generator): Transforms technical topics into structured prompts with fresh analogies—NOT a content writer
- **The Witty Expert** (Writer): "Brilliant professor hosting late-night talk show" persona—intellectual sparkle with dry wit

When implementing these agents, preserve the exact template structures and behavioral guidelines from `system_prompts.md`.

### RAG Memory Bank
The Strategic Type Agent queries `memory_bank/` (Tech Audience Accelerator newsletter corpus) using vector embeddings. Use ChromaDB/LangChain/LlamaIndex for RAG layer.

### Error Handling Taxonomy
- **ValidationError**: Character limit exceeded, missing required sections
- **DataNotFoundError**: Research found no sources (fallback: request new topic, max 2 pivots)
- **ModelError**: LLM API failure (retryable with exponential backoff)
- **CorruptionError**: Artifact parsing failed (non-retryable, abort immediately)

Fallback strategies: Simplified prompts for Writer, local grammar check for Reviewer, minimal image prompt from post summary.

### Database Schema (`database/topics.db`)
```sql
previous_topics: id, topic_name, date_posted
potential_topics: id, topic_name, field  -- field: "Data Science..." or "Generative AI..."
```

### Event Logging
Append-only `events.jsonl` at project root:
```json
{"timestamp": "...", "run_id": "...", "step": "topic_selection", "attempt": 1, "status": "ok", "duration_ms": 234, "model": "gemini-2.5-pro", "token_usage": {"prompt": 45, "completion": 120}}
```

## LLM Configuration

- **All Text Agents**: `google-generativeai` with `gemini-2.5-pro`
- **Image Generation**: `gemini-2.5-flash-image-preview`
- **API Key**: Load from `.env` file (`GOOGLE_API_KEY`), never hardcode

## Common Pitfalls

1. **Don't bypass disk persistence**: Even though agents pass objects in-memory, ALWAYS write artifacts for auditability
2. **Character count enforcement**: The Writer→Reviewer→Orchestrator loop must continue until post <3000 chars
3. **Atomic writes**: Use temp file + rename pattern to prevent partial writes
4. **Retry only retryable errors**: ValidationError and CorruptionError should never auto-retry
5. **RAG context**: Strategic Type Agent must query memory bank, not generate strategies from scratch

## Project Structure Reference

```
agents/           # Each agent in separate file (topic_agent.py, writer_agent.py, etc.)
core/             # llm_clients.py, rag_setup.py
database/         # topics.db SQLite database
runs/             # Runtime artifacts (gitignored)
memory_bank/      # Newsletter .txt files for RAG
system_prompts.md # AUTHORITATIVE source for agent personas
project_spec.md   # Complete technical specification
```

## Development Workflow

### PowerShell Execution Policy (CRITICAL)
**MUST run before any terminal commands on Windows:**
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
```
This is required for venv activation and Python script execution.

### Standard Workflow
1. **First-time setup**: Prompt user to enter their field of expertise (accepts any custom field), save to `config.json`
2. **Execution**: `python main.py` triggers orchestrator, creates unique run directory
3. **Debugging**: Check `events.jsonl` and per-run `run_failed.json` for failures
4. **Testing**: Validate retry logic, artifact integrity, character limit loop, fallback activation

### Test Driven Development (TDD)
**ALWAYS write tests before implementation**. This project requires extremely high test coverage.

**TDD Cycle**:
1. Write failing test for new feature/agent
2. Implement minimal code to pass test
3. Refactor while keeping tests green
4. Repeat

**Critical Test Areas**:
- **Agent I/O Contracts**: Test standardized return envelope for every agent
- **Retry Logic**: Verify exponential backoff, max attempts, retryable vs non-retryable errors
- **Artifact Persistence**: Test atomic writes, corruption detection, immediate re-parsing
- **Character Count Loop**: Test Writer→Reviewer→Orchestrator iteration until <3000 chars
- **Fallback Strategies**: Test simplified prompts, topic pivots, local grammar checks
- **Circuit Breaker**: Test abort after 3 consecutive LLM failures
- **Persona Compliance**: Test that agents follow `system_prompts.md` guidelines
- **RAG Integration**: Test memory bank queries return relevant context
- **Database Operations**: Test topic selection, uniqueness, field filtering
- **Event Logging**: Test JSONL format, required fields, append-only behavior

**Test Structure**:
```
tests/
├── test_agents/
│   ├── test_topic_agent.py
│   ├── test_research_agent.py
│   ├── test_prompt_generator_agent.py
│   ├── test_strategic_type_agent.py
│   ├── test_writer_agent.py
│   ├── test_reviewer_agent.py
│   ├── test_image_prompt_agent.py
│   └── test_image_generator_agent.py
├── test_orchestrator.py
├── test_error_handling.py
├── test_artifact_persistence.py
└── test_integration/
    └── test_full_pipeline.py
```

**Running Tests**:
```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
pytest tests/ --cov=. --cov-report=html
```

### Semantic Release Process
This project uses semantic versioning with automated releases:
- **Commit Convention**: Follow Conventional Commits (e.g., `feat:`, `fix:`, `docs:`, `refactor:`)
- **Version Bumping**: Automatic based on commit messages (major.minor.patch)
- **Release Triggers**: Commits to `master` branch trigger semantic-release workflow
- **Changelog**: Auto-generated from commit history
- **Tags**: Git tags created automatically on release

## When Modifying Agents

- Preserve standardized return envelope
- Update `events.jsonl` logging for new steps
- Follow persona guidelines in `system_prompts.md` exactly
- Test error paths (retryable vs non-retryable)
- Validate artifact persistence after changes

### Testing Persona Fidelity

**Strategic Content Architect (Prompt Generator)**:
- Verify output follows exact template structure from `system_prompts.md`
- Ensure analogies are fresh and unexpected (not clichés)
- Confirm it's creating prompts, NOT writing content
- Check that audience pain points go beyond technical to human frustration

**The Witty Expert (Writer)**:
- Validate LinkedIn post structure: hook → problem → solution → impact → action → sign-off
- Ensure tone is conversational with dry wit (not slapstick)
- Check for fresh analogies throughout (no generic comparisons)
- Verify formatting: short paragraphs, bold emphasis, bullet points
- Test that complex topics feel delightful, not dumbed-down

**Persona Testing Pattern**:
```python
# After agent execution, validate against persona checklist
def validate_prompt_generator(output):
    assert "**Topic:**" in output
    assert "**Target Audience:**" in output
    assert "**Audience's Core Pain Point:**" in output
    assert "**Key Metrics/Facts:**" in output
    assert "**The Simple Solution/Code Snippet:**" in output
    # Check for cliché analogies (fail if found)
    cliche_phrases = ["distributed ledger", "like a library", "like a recipe"]
    assert not any(phrase in output.lower() for phrase in cliche_phrases)
```
