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
**Granular Breakdown (expanded based on Phase 2 patterns & resilience needs)**
- [x] Add `database/init_db.py`
  - [x] Constant `DEFAULT_DB_PATH = "database/topics.db"`
  - [x] `ensure_db_dir(db_path)` creates parent dir if missing
  - [x] `init_db(db_path)` idempotent table + index creation
    - [x] Table: `previous_topics (id INTEGER PRIMARY KEY, topic_name TEXT NOT NULL, date_posted TEXT NOT NULL)`
    - [x] Table: `potential_topics (id INTEGER PRIMARY KEY, topic_name TEXT NOT NULL UNIQUE, field TEXT NOT NULL)`
    - [x] Index: `idx_previous_topics_date_posted` on `previous_topics(date_posted DESC)`
    - [x] Index: `idx_potential_topics_field` on `potential_topics(field, topic_name)`
  - [x] `seed_potential_topics(rows, db_path)` uses `INSERT OR IGNORE`
  - [x] CLI: `python -m database.init_db --seed` prints inserted count
- [x] Seed `potential_topics`
  - [x] ≥8 topics per field
  - [x] Field enum values:
    - [x] "Data Science (Optimizations & Time-Series Analysis)"
    - [x] "Generative AI & AI Agents"
  - [ ] Add guard: validate field value belongs to supported enum before selection (utility function)
- [x] Add helper `database/operations.py`
  - [x] Context-managed `get_connection(db_path)` enabling foreign keys
  - [x] `_iso_now()` returns UTC ISO8601 `YYYY-MM-DDTHH:MM:SSZ`
  - [x] `get_recent_topics(limit, db_path)` newest-first ordering by `date_posted` DESC
  - [x] `record_posted_topic(topic_name, date_posted=None, db_path)` auto-populates ISO timestamp
  - [x] `select_new_topic(field, recent_limit, db_path)` deterministic smallest id excluding recent set
  - [ ] Add `validate_field(field)` raising `ValueError` for unsupported field (used by agents + tests)
  - [ ] Add `list_all_potential(field, db_path)` for future analytics & debug tooling
- [ ] Add DB utilities test coverage enhancements
  - [x] Schema existence (tables + columns)
  - [x] Uniqueness constraint enforcement
  - [x] `record_posted_topic` persists ISO timestamp format
  - [x] Recent ordering correctness
  - [x] Deterministic selection excludes recents & filters by field
  - [ ] Test index presence (`PRAGMA index_list` / `PRAGMA index_info`)
  - [ ] Test seed function rowcount vs duplicates
  - [ ] Test `validate_field` rejects invalid values
  - [ ] Test `_iso_now()` format compliance
  - [ ] Test `list_all_potential` returns sorted deterministic list
- [ ] Add resilience/edge utilities (optional backlog)
  - [ ] Optional `purge_previous(before_days)` archival helper
  - [ ] Optional `export_topics_csv(db_path, dest)` for analytics

Note: Unchecked items added for future granularity; can be scheduled before Phase 5 orchestration for stronger guarantees.

## Phase 4: Agent Implementations
### Design Pattern
- [ ] Each agent file defines `run(input_obj, context)` returning envelope
- [ ] Each agent persists input/output artifacts
- [ ] Each agent logs events with attempt info

### 4.1 Topic Agent (`agents/topic_agent.py`)
- [x] Tests: selection uniqueness, correct envelope

### 4.2 Research Agent (`agents/research_agent.py`)
- [x] Tests for fallback pivot logic (simulate two pivots max)

### 4.3 Prompt Generator Agent (`agents/prompt_generator_agent.py`)
- [x] Persona fidelity tests (no clichés, template sections present)

### 4.4 Strategic Type Agent (`agents/strategic_type_agent.py`)
- [x] Tests: ensures RAG docs influence output (mock vector store)

### 4.5 Writer Agent (`agents/writer_agent.py`)
- [x] Tests: structure sections present, tone heuristics

### 4.6 Reviewer Agent (`agents/reviewer_agent.py`)
- [x] Tests for pass separation

### 4.7 Character Count Loop (Orchestrator Responsibility)
- [ ] Implement loop after review (pending Phase 5)
- [ ] If >=3000 chars: send shortening instruction to Writer Agent (include target length)
- [ ] Persist each iteration's draft & review (overwrite; log iteration count)
- [ ] Tests: simulate >3000 then <3000 convergence

### 4.8 Final Post Assembly
- [ ] Save approved post to `60_final_post.txt` (pending orchestrator)

### 4.9 Image Prompt Generator Agent (`agents/image_prompt_agent.py`)
- [x] Tests: presence of thematic keywords

### 4.10 Image Generator Agent (`agents/image_generator_agent.py`)
- [x] Tests: stub image generation if offline

## Phase 5: Orchestrator Implementation (`orchestrator.py`)
### 5.1 Configuration & Initialization
- [x] Load configuration from `config.json`
  - [x] Validate config structure (field present)
  - [x] Handle missing config file gracefully
- [x] Initialize run directory using `create_run_dir()`
  - [x] Store run_id and run_path in orchestrator state
  - [x] Save `00_config.json` to run directory
- [x] Initialize circuit breaker instance
- [x] Set up context dictionary for agents (`run_id`, `run_path`)

### 5.2 Agent Execution Infrastructure
- [x] Implement `_execute_agent_with_retry()` helper method
  - [x] Accept agent function, input dict, max attempts
  - [x] Use `execute_with_retries()` from `core.retry`
  - [x] Update circuit breaker on success/failure
  - [x] Return agent response envelope
- [x] Implement error classification logic
  - [x] Distinguish retryable vs non-retryable errors
  - [x] Handle `CircuitBreakerTrippedError`
  - [x] Log all attempts to `events.jsonl`

### 5.3 Sequential Agent Pipeline
- [x] Execute Topic Agent (Step 1)
  - [x] Build input: `{"field": config["field"]}`
  - [x] Call with retry wrapper
  - [x] Extract topic from response data
  - [x] Handle `DataNotFoundError` (no topics available)
- [x] Execute Research Agent (Step 2)
  - [x] Build input: `{"topic": topic}`
  - [x] Call with retry wrapper
  - [x] Extract research data from response
  - [x] Handle pivot logic if `DataNotFoundError` (max 2 pivots)
- [x] Execute Prompt Generator Agent (Step 3)
  - [x] Build input: `{"topic": topic, "research": research_data}`
  - [x] Call with retry wrapper
  - [x] Extract structured prompt from response
- [x] Execute Strategic Type Agent (Step 4)
  - [x] Build input: `{"structured_prompt": prompt, "research": research_data}`
  - [x] Call with retry wrapper
  - [x] Extract strategy from response
- [x] Execute Writer Agent (Step 5)
  - [x] Build input: `{"structured_prompt": prompt, "strategy": strategy}`
  - [x] Call with retry wrapper
  - [x] Read draft from artifact path
  - [x] Store draft text for review
- [x] Execute Reviewer Agent (Step 6)
  - [x] Build input: `{"draft_text": draft}`
  - [x] Call with retry wrapper
  - [x] Extract revised text from response

### 5.4 Character Count Validation Loop
- [x] Implement character count validation inline within the writing/review loop
  - [x] Use `count_chars()` from `core.persistence` to check post length
  - [x] Store and log character count result for each iteration
- [x] Implement character count loop after review
  - [x] Check if revised post < 3000 characters
  - [x] If pass: save to `60_final_post.txt` and proceed
  - [x] If fail: build shortening instruction
    - [x] Include current count and target (2950)
    - [x] Send back to Writer Agent with instructions
  - [x] Track loop iteration count (log to events)
  - [x] Implement max iterations safety (e.g., 5 attempts)
  - [x] Update draft artifact on each iteration
  - [x] Update review artifact on each iteration

### 5.5 Image Generation Pipeline
- [x] Execute Image Prompt Generator Agent (Step 8)
  - [x] Build input: `{"final_post": final_post_text}`
  - [x] Call with retry wrapper
  - [x] Extract image prompt from response
- [x] Execute Image Generator Agent (Step 9)
  - [x] Build input: `{"image_prompt_path": image_prompt_path}`
  - [x] Call with retry wrapper
  - [x] Verify image artifact exists at `80_image.png`

### 5.6 Run Completion & Error Handling
- [x] Implement successful completion flow
  - [x] Mark run as complete
  - [x] Return summary with artifact paths
  - [x] Log final metrics (total duration, agent calls, etc.)
- [x] Implement `_create_run_failed_json()` method
  - [x] Accept error details, failed step, circuit breaker state
  - [x] Save to run directory as `run_failed.json`
  - [x] Include: timestamp, error type, message, stack trace, retries attempted
- [x] Handle abort scenarios
  - [x] Circuit breaker tripped
  - [x] Non-retryable error (ValidationError, CorruptionError)
  - [x] Max character count iterations exceeded
  - [x] Topic pivot limit exceeded

### 5.7 Metrics Aggregation (Optional)
- [x] Track per-agent metrics
  - [x] Duration for each agent call
  - [x] Token usage (if available from LLM)
  - [x] Retry counts per agent
- [x] Aggregate run-level metrics
  - [x] Total duration
  - [x] Total tokens used
  - [x] Total retries across all agents
  - [x] Character count loop iterations
- [x] Save metrics summary to run directory

### 5.8 Testing
- [x] Create `tests/test_orchestrator.py`
  - [x] Test configuration loading
  - [x] Test run directory creation
  - [x] Test circuit breaker integration
  - [x] Test character count loop convergence
  - [x] Test character count loop max iterations
  - [x] Test topic pivot logic (max 2 pivots)
  - [x] Test run failure artifact creation
  - [x] Test successful full pipeline (mocked agents)
  - [x] Test abort on non-retryable error
  - [x] Test abort on circuit breaker tripped
  - [x] Test abort on corruption error
  - [x] Test metrics aggregation
- [x] Integration test for full pipeline
  - [x] Mock all agent responses
  - [x] Verify artifact creation at each step
  - [x] Verify proper data flow between agents
  - [x] Verify event logging for all steps

## Phase 6: Main Entry Point (`main.py`)
- [ ] First-run onboarding (prompt user for field selection if config missing)
- [ ] Save `00_config.json` to run directory
- [ ] Call orchestrator
- [ ] Print concise status summary to console
- [ ] Tests: config creation logic

### Phase 5 Verification Notes (Implemented)
- Config handling: Orchestrator validates `config['field']` but does not load `config.json`; loading is deferred to Phase 6 (`main.py`). Orchestrator persists `00_config.json` via `core.run_context.get_artifact_path`.
- Run setup: `create_run_dir()` sets `run_id`/`run_path` and `context` for agents; initialization event is logged.
- Retry + breaker: `_execute_agent_with_retry()` wraps calls with `execute_with_retries()` and records per-agent metrics; breaker trips after 3 consecutive LLM failures.
- Pipeline: Steps 1–6 call agents in order and pass structured IO; topic pivot logic respects max of 2 pivots and logs pivots.
- Character loop: Writer→Reviewer loop enforces `<3000` chars, emits shortening instructions with target `2950`, and caps at 5 iterations.
- Artifact updates: Writer overwrites `40_draft.md`; Reviewer overwrites `50_review.json` each iteration; Orchestrator writes `60_final_post.txt` on success.
- Images: Image prompt path is returned and passed to image generator as `image_prompt_path`; final PNG verified at `80_image.png`.
- Completion/failure: Success returns summary with artifacts and metrics; failures write `run_failed.json` with breaker state and stack trace.
- Tests: `tests/test_orchestrator.py` covers initialization, breaker, char loop, pivots, success/failure flows, and integration with mocked agents.

### Handoff Notes To Phase 6
- Main responsibilities:
  - Load or create `config.json` with `{"field": "Data Science (Optimizations & Time-Series Analysis)"|"Generative AI & AI Agents"}`.
  - Instantiate `Orchestrator(config)` and call `run()`.
  - Print a concise summary: `run_id`, `run_path`, key artifact paths, and status.
- First-run onboarding:
  - If no `config.json`, prompt user to choose a field; write it atomically and validate the value (align with DB supported fields).
  - Optionally call `database.init_db` seeding path on first run (optional convenience).
- Artifacts & persistence:
  - Orchestrator will write `00_config.json` into the run directory automatically; `main.py` just needs to supply a valid in-memory config.
- Windows execution policy (PowerShell): ensure sessions run with `Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass` before invoking scripts.
- Nice-to-have outputs:
  - Print relative paths to: `60_final_post.txt`, `70_image_prompt.txt`, `80_image.png`.
  - Exit with non-zero code if `status == "failed"` to aid CI.

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
