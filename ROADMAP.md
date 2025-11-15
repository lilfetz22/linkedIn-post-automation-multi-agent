# Project Roadmap: LinkedIn Post Multi-Agent Automation

> Purpose: A granular, executable checklist for an AI coding agent to implement everything defined in `project_spec.md` and `system_prompts.md`. Follow phases in order. Each task uses GitHub-style checkboxes. Nested tasks must be completed before their parent can be checked.

## Phase 0: Repository & Planning
- [x] Confirm Python version >= 3.10
- [x] Create initial virtual environment
- [x] Add `.gitignore` (include: `runs/`, `__pycache__/`, `.env`, coverage reports)
- [x] Ensure `README.md` exists with high-level summary (expand later)
- [x] Add placeholder `requirements.txt`
- [x] Initialize Conventional Commit discipline (document in README)

## Phase 1: Core Project Skeleton
- [x] Create directory `agents/` with `__init__.py`
- [x] Create directory `core/`
- [x] Create directory `database/`
- [x] Create directory `memory_bank/` (seed later)
- [x] Create directory `runs/` (ensure gitignored)
- [x] Create directory `tests/` with subfolders per spec
- [x] Add root files: `main.py`, `orchestrator.py`
- [x] Add `.env` (placeholder for `GOOGLE_API_KEY`) - prompt user to fill in API key
- [x] Add `events.jsonl` (empty file or create lazily on first log)

## Phase 2: Shared Infrastructure Code
### 2.1 Standard Return Envelope & Errors
- [x] Define `core/errors.py`
  - [x] `BaseAgentError(Exception)`
  - [x] `ValidationError`
  - [x] `DataNotFoundError`
  - [x] `ModelError`
  - [x] `CorruptionError`
- [x] Define `core/envelope.py`
  - [x] Function `ok(data: dict, metrics: dict|None)`
  - [x] Function `err(error_type: str, message: str, retryable: bool, metrics: dict|None)`
  - [x] Dataclass or schema validator for envelope
### 2.2 Atomic File Persistence Utilities
- [x] Create `core/persistence.py`
  - [x] `atomic_write_json(path, obj)` (write temp + rename)
  - [x] `atomic_write_text(path, text)`
  - [x] `verify_json(path)` (re-open & parse; raise `CorruptionError` if failure)
  - [x] `write_and_verify_json(path, obj)` wrapper
- [x] Implement character counting utility (`count_chars(text: str)`)
### 2.3 Event Logging
- [x] Create `core/logging.py`
  - [x] `log_event(run_id, step, attempt, status, error_type=None, duration_ms=None, model=None, token_usage=None)` appends JSON line
  - [x] Ensure thread-safety (simple file append lock)
### 2.4 Run Directory Management
- [x] Create `core/run_context.py`
  - [x] `create_run_dir(base='runs/')` returns run_id & path
  - [x] Utility to build artifact path by step code (`00_config.json`, etc.)
### 2.5 Circuit Breaker & Retry Logic
- [x] Create `core/retry.py`
  - [x] Exponential backoff function (`sleep_seconds = base * 2**(attempt-1)`)
  - [x] `execute_with_retries(func, max_attempts=3)` handles retryable errors
  - [x] Circuit breaker state (consecutive LLM failures counter)
  - [x] Reset logic after success
### 2.6 LLM Client Abstraction
- [x] Create `core/llm_clients.py`
  - [x] Load API key from `.env`
  - [x] Wrapper for Gemini text model (`gemini-2.5-pro`): `generate_text(prompt, temperature, ...)`
  - [x] Wrapper for Gemini image model (`gemini-2.5-flash-image-preview`): `generate_image(prompt)`
  - [x] Capture token usage (if available) into metrics
### 2.7 RAG Layer
- [x] Decide RAG library (`chromadb` recommended for simplicity)
- [x] Add to `requirements.txt`
- [x] Create `core/rag_setup.py`
  - [x] `init_vector_store(memory_bank_path)` ingest `.txt` files
  - [x] `query_memory_bank(query, k=5)` returns list of docs
  - [x] Unit test with dummy memory docs

## Phase 3: Database Setup
- [ ] Add `database/init_db.py`
  - [ ] Define constant `DEFAULT_DB_PATH = "database/topics.db"`
  - [ ] Function `ensure_db_dir(db_path=DEFAULT_DB_PATH)` creates parent dir if missing
  - [ ] Function `init_db(db_path=DEFAULT_DB_PATH)` (idempotent):
    - [ ] Create tables if not exist:
      - [ ] `previous_topics (id INTEGER PRIMARY KEY, topic_name TEXT NOT NULL, date_posted TEXT NOT NULL)`
      - [ ] `potential_topics (id INTEGER PRIMARY KEY, topic_name TEXT NOT NULL UNIQUE, field TEXT NOT NULL)`
    - [ ] Create indices if not exist:
      - [ ] `idx_previous_topics_date_posted` on `previous_topics(date_posted DESC)`
      - [ ] `idx_potential_topics_field` on `potential_topics(field, topic_name)`
  - [ ] Function `seed_potential_topics(rows, db_path=DEFAULT_DB_PATH)` inserts rows with `INSERT OR IGNORE`
  - [ ] CLI entrypoint (optional): `python -m database.init_db --seed` to init and seed
- [ ] Seed `potential_topics` with sample rows for both fields
  - [ ] At least 8 topics per field
  - [ ] Fields:
    - [ ] "Data Science (Optimizations & Time-Series Analysis)"
    - [ ] "Generative AI & AI Agents"
- [ ] Add helper `database/operations.py`
  - [ ] `get_connection(db_path=DEFAULT_DB_PATH)` context manager returning sqlite3 connection
  - [ ] `get_recent_topics(limit=10, db_path=DEFAULT_DB_PATH)` returns list of topic names ordered by `date_posted` DESC
  - [ ] `record_posted_topic(topic_name, date_posted=None, db_path=DEFAULT_DB_PATH)` inserts with ISO8601 date (UTC) if none provided
  - [ ] `select_new_topic(field, recent_limit=10, db_path=DEFAULT_DB_PATH)`:
    - [ ] Exclude topics in last `recent_limit` of `previous_topics`
    - [ ] Filter by `field`
    - [ ] Deterministic selection: smallest `id` among remaining (avoid randomness for testability)
    - [ ] Return `{"topic": str}` or `None` if none available
- [ ] Tests for DB
  - [ ] Schema existence (both tables, required columns)
  - [ ] Uniqueness constraint on `potential_topics.topic_name`
  - [ ] `record_posted_topic` writes retrievable row with ISO date
  - [ ] `get_recent_topics` ordering is correct (most recent first)
  - [ ] `select_new_topic` excludes recent topics and respects `field`
  - [ ] All functions accept `db_path` override for test isolation

## Phase 4: Agent Implementations
### Design Pattern
- [ ] Each agent file defines `run(input_obj, context)` returning envelope
- [ ] Each agent persists input/output artifacts
- [ ] Each agent logs events with attempt info

### 4.1 Topic Agent (`agents/topic_agent.py`)
- [ ] Input: `field` from config
- [ ] Output: `{"topic": str}` persisted to `10_topic.json`
- [ ] Avoid recent topics (DB query)
- [ ] Tests: selection uniqueness, correct envelope

### 4.2 Research Agent (`agents/research_agent.py`)
- [ ] Input: `topic`
- [ ] Simulated research (stub external calls for now)
- [ ] Output JSON: `{"topic": ..., "sources": [...], "summary": str}` → `20_research.json`
- [ ] Handle empty sources → raise `DataNotFoundError`
- [ ] Tests for fallback pivot logic (simulate two pivots max)

### 4.3 Prompt Generator Agent (`agents/prompt_generator_agent.py`)
- [ ] Load persona template from `system_prompts.md`
- [ ] Construct prompt and call LLM
- [ ] Output structured fields per spec → `25_structured_prompt.json`
- [ ] Validate required keys present (else `ValidationError`)
- [ ] Persona fidelity tests (no clichés, template sections present)

### 4.4 Strategic Type Agent (`agents/strategic_type_agent.py`)
- [ ] Use RAG query (structured_prompt + research summary as query)
- [ ] Output: `{"structure": ..., "strategic_angle": ...}` → `30_strategy.json`
- [ ] Tests: ensures RAG docs influence output (mock vector store)

### 4.5 Writer Agent (`agents/writer_agent.py`)
- [ ] Input: structured prompt + strategy
- [ ] Persona: Witty Expert (verify formatting rules)
- [ ] Output draft markdown → `40_draft.md`
- [ ] Tests: structure sections present, tone heuristics

### 4.6 Reviewer Agent (`agents/reviewer_agent.py`)
- [ ] Two passes: contextual coherence then grammar/spelling
- [ ] Output JSON diff structure: `{"original": ..., "revised": ..., "changes": [...]}` → `50_review.json`
- [ ] Local grammar fallback (simple heuristic) if LLM fails
- [ ] Tests for pass separation

### 4.7 Character Count Loop (Orchestrator Responsibility)
- [ ] Implement loop after review
- [ ] If >=3000 chars: send shortening instruction to Writer Agent (include target length)
- [ ] Persist each iteration's draft & review (version suffix or overwrite?) → Decide: overwrite artifacts for simplicity; log iteration count in events
- [ ] Tests: simulate >3000 then <3000 convergence

### 4.8 Final Post Assembly
- [ ] Save approved post to `60_final_post.txt`

### 4.9 Image Prompt Generator Agent (`agents/image_prompt_agent.py`)
- [ ] Input: final post text
- [ ] Output prompt text → `70_image_prompt.txt`
- [ ] Fallback minimal prompt if error
- [ ] Tests: presence of thematic keywords

### 4.10 Image Generator Agent (`agents/image_generator_agent.py`)
- [ ] Input: prompt text
- [ ] Output PNG → `80_image.png`
- [ ] Validate file saved & non-empty size
- [ ] Tests: stub image generation if offline

## Phase 5: Orchestrator Implementation (`orchestrator.py`)
- [ ] Load config & field
- [ ] Initialize run directory
- [ ] Execute agents in sequence with retries
- [ ] Maintain circuit breaker state
- [ ] Implement character count loop
- [ ] On abort: create `run_failed.json`
- [ ] Metrics aggregation summary (optional)
- [ ] Tests: full mocked pipeline, circuit breaker scenario, corruption abort

## Phase 6: Main Entry Point (`main.py`)
- [ ] First-run onboarding (prompt user for field selection if config missing)
- [ ] Save `00_config.json` to run directory
- [ ] Call orchestrator
- [ ] Print concise status summary to console
- [ ] Tests: config creation logic

## Phase 7: Memory Bank Content
- [ ] Add sample newsletter `.txt` files to `memory_bank/`
- [ ] Document ingestion assumptions in README
- [ ] Test RAG retrieval relevance

## Phase 8: Configuration & Environment
- [ ] Implement `.env` loading using `python-dotenv`
- [ ] Validate presence of `GOOGLE_API_KEY`; raise clear error if missing
- [ ] Update README with environment setup steps

## Phase 9: Testing Infrastructure
### 9.1 Test Utilities
- [ ] Create `tests/conftest.py` (fixtures: temp run dir, mock LLM client, mock RAG store)
- [ ] Fixture for deterministic token usage metrics
### 9.2 Agent Tests (Per Spec)
- [ ] `tests/test_agents/test_topic_agent.py`
- [ ] `tests/test_agents/test_research_agent.py`
- [ ] `tests/test_agents/test_prompt_generator_agent.py`
- [ ] `tests/test_agents/test_strategic_type_agent.py`
- [ ] `tests/test_agents/test_writer_agent.py`
- [ ] `tests/test_agents/test_reviewer_agent.py`
- [ ] `tests/test_agents/test_image_prompt_agent.py`
- [ ] `tests/test_agents/test_image_generator_agent.py`
### 9.3 System-Level Tests
- [ ] `tests/test_orchestrator.py`
- [ ] `tests/test_error_handling.py` (retry vs non-retryable)
- [ ] `tests/test_artifact_persistence.py`
- [ ] `tests/test_integration/test_full_pipeline.py`
### 9.4 Persona Compliance Tests
- [ ] Implement analogy freshness check
- [ ] Implement template section presence assertions
### 9.5 Circuit Breaker Tests
- [ ] Simulate 3 consecutive LLM failures triggers abort
### 9.6 Coverage
- [ ] Add pytest coverage configuration
- [ ] Require >85% coverage (adjust threshold once stable)

## Phase 10: Dependency Management
- [ ] Populate `requirements.txt` (initial)
  - [ ] `google-generativeai`
  - [ ] `python-dotenv`
  - [ ] `chromadb` (or chosen RAG lib)
  - [ ] `pytest`
  - [ ] `pytest-cov`
  - [ ] `tqdm` (optional for progress)
  - [ ] `pydantic` (optional for envelope validation)
- [ ] Freeze versions (pin where critical)
- [ ] Test fresh install in clean venv

## Phase 11: Documentation Enhancements
- [ ] Expand `README.md` with sections: Overview, Architecture Diagram (text-based), Setup, Usage, Testing, Error Taxonomy, Personas, Roadmap reference
- [ ] Add `docs/` directory (optional) for deeper explanations
- [ ] Add `ROADMAP.md` (this file) – DONE
- [ ] Provide example run artifact tree in README

## Phase 12: Quality & Validation
- [ ] Run linting (consider adding `ruff` or `flake8`)
- [ ] Add CI workflow (GitHub Actions) for tests + coverage
- [ ] Add semantic-release workflow (Python flavor or conventional-changelog approach)
- [ ] Verify Conventional Commits enforcement (optional hook)

## Phase 13: Fallback & Resilience Edge Cases
- [ ] Research Agent pivot logic (no sources scenario)
- [ ] Writer simplified prompt fallback
- [ ] Reviewer grammar local pass
- [ ] Image prompt minimal fallback
- [ ] Demonstrate each in tests with forced failure injection

## Phase 14: Performance & Scalability (Optional Future)
- [ ] Batch memory bank ingestion if large corpus
- [ ] Add caching layer for repeated RAG queries
- [ ] Parallelize non-dependent steps (future optimization)

## Phase 15: Future Enhancements (Backlog)
- [ ] Scheduling (cron or Windows Task Scheduler integration)
- [ ] Web UI dashboard for runs & artifacts
- [ ] Post publishing automation to LinkedIn API (requires compliance checks)
- [ ] Advanced analytics on engagement (placeholder)

## Milestone Tracking Summary
| Milestone | Phases Included | Completion Target |
|-----------|-----------------|-------------------|
| M1 | 0–3 | Core skeleton + DB ready |
| M2 | 4–6 | All agents + orchestrator functional |
| M3 | 7–9 | RAG + tests with high coverage |
| M4 | 10–12 | Stable release + CI/CD + docs |
| M5 | 13–15 | Resilience edge cases + enhancements |

## Execution Order (Condensed Checklist)
1. Skeleton & infra (Phases 1–2)
2. DB & RAG (Phases 3 & 2.7)
3. Agents (Phase 4)
4. Orchestrator + main (Phases 5–6)
5. Memory bank content (Phase 7)
6. Env & config (Phase 8)
7. Tests & coverage (Phase 9)
8. Dependencies (Phase 10)
9. Docs & CI (Phases 11–12)
10. Fallback tests (Phase 13)
11. Optional perf & backlog (14–15)

## Agent Contract (Reference)
Each agent must:
- [ ] Accept structured Python input (dict)
- [ ] Produce standardized envelope
- [ ] Persist output artifact immediately (atomic write)
- [ ] Re-parse JSON artifacts to confirm integrity
- [ ] Log event entry per attempt
- [ ] Surface retryable vs non-retryable errors correctly

## Done Definition (Per Feature)
A feature is "Done" when:
- [ ] Code implemented
- [ ] Unit & integration tests passing
- [ ] Coverage threshold met
- [ ] Docs updated (README or docstring)
- [ ] No lint errors
- [ ] Artifacts created & verified (if applicable)

---
**Next Action for AI Agent:** Begin at Phase 1 tasks top-down ensuring atomic commits per logical unit using Conventional Commit messages.
