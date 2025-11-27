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
- [x] CLI structure and flags
  - [x] `--init-config`: initialize `config.json` only and exit
  - [x] `--field <value>`: non-interactive field selection for CI/tests
  - [x] `--run`: execute full pipeline (default when no flags)
- [x] First-run onboarding
  - [x] Validate supported fields against enum:
        "Data Science (Optimizations & Time-Series Analysis)" | "Generative AI & AI Agents"
  - [x] If `config.json` missing: prompt user to select field (interactive)
  - [x] Non-interactive path: accept `--field` value and write `config.json`
  - [x] Atomic write via `core.persistence.atomic_write_json`
  - [x] Re-parse to verify integrity via `write_and_verify_json`
- [x] Configuration loading
  - [x] Load `config.json` from project root
  - [x] Validate schema and value; clear error on invalid
- [x] Orchestrator invocation
  - [x] Instantiate `Orchestrator(config)`
  - [x] Run pipeline; capture result dict
  - [x] Exit code: `0` on success, `1` on failure
- [x] Console summary output
  - [x] Print `run_id`, `run_path`, and key artifacts (`60_final_post.txt`, `80_image.png`)
  - [x] Print status if available
- [x] Tests: config creation logic
  - [x] Create when missing with non-interactive field
  - [x] Validate allowed/invalid field handling
  - [x] Load existing config without overwrite
  - [x] Use helpers (no orchestrator execution required)

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

## Phase 7: LLM Integration & Agent Intelligence (CRITICAL)
**Purpose:** Transform stub agents into fully functional LLM-powered agents. This is the core value-add of the system—without this phase, the pipeline only generates mock content.

### 7.0 Prerequisites & Safety Infrastructure
- [x] Load system prompts from `system_prompts.md` into memory
  - [x] Parse "Strategic Content Architect - User Prompt Engineer" section
  - [x] Parse "The Witty Expert Persona" section
  - [x] Parse "Social Media Visual Strategist" section
  - [x] Create utility function `load_system_prompt(section_name)` in `core/`
- [x] Implement cost tracking infrastructure
  - [x] Add `CostTracker` class to `core/` with per-model pricing
    - [x] Gemini 2.5 Pro text pricing (input/output tokens)
    - [x] Gemini 2.5 Flash Image pricing
  - [x] Add `estimate_run_cost()` method to Orchestrator
  - [x] Add API call counter to orchestrator metrics
  - [x] Add per-run cost accumulator (track actual spend)
- [x] Implement safety limits
  - [x] Add `MAX_API_CALLS_PER_RUN = 25` constant to Orchestrator (implemented in CostTracker with default 25)
  - [x] Add `MAX_COST_PER_RUN_USD = 3.00` constant (configurable) (implemented in CostTracker with default 3.00)
  - [x] Raise `ValidationError` if limits exceeded mid-run
  - [ ] Add `--dry-run` flag to `main.py` (stop before first LLM call) (exists in smoke_test.py but not main.py)

### 7.1 Topic Agent Enhancement
- [x] Add LLM fallback for empty topic database
  - [x] Check if `potential_topics` has any unused topics (`used = FALSE`)
  - [x] If yes: use existing database selection logic (no LLM call)
  - [x] If no: call LLM to generate new topics
    - [x] Build prompt: "Generate 10 topic candidates for [field]. Prefer net-new, specific topics (emerging trends, overlooked fundamentals, concrete pain points). You MAY reuse a previously covered macro-topic ONLY if proposing a distinctly new avenue (fresh sub-problem, perspective, data source, or audience pain point). Otherwise produce topics not yet posted." 
    - [x] Parse LLM response into structured list (flag each as `net_new` or `reused_with_new_angle`)
    - [x] Insert topics into `potential_topics` with `used = FALSE` (for reused angles, include distinguishing detail in name or future metadata column)
    - [x] Select first acceptable topic (prioritize `net_new`; allow `reused_with_new_angle` if clearly distinct)
- [x] Update database schema to include `used` column
  - [x] Migration script: `ALTER TABLE potential_topics ADD COLUMN used BOOLEAN DEFAULT FALSE`
  - [x] Update `select_new_topic()` to mark selected topic as `used = TRUE`
- [x] Tests
  - [x] Test database selection path (no LLM call)
  - [x] Test LLM fallback path with empty database (mock LLM)
  - [x] Test topic insertion and `used` flag toggling

### 7.2 Research Agent Enhancement
- [x] Integrate web search capability
  - [x] Utilize Gemini API's built-in "grounding with Google Search" feature
  - [x] Enable search grounding via `use_search_grounding=True` parameter in LLM calls
  - [x] Uses existing `GOOGLE_API_KEY` from `.env` (no additional API keys needed)
- [x] Replace stub logic with LLM-powered research
  - [x] Execute web search for selected topic via Gemini's search grounding feature
  - [x] Extract sources and synthesis from grounded LLM response
  - [x] Build LLM prompt: "Synthesize research for this topic: [topic]. Focus on key metrics, pain points, and recent developments."
  - [x] Call `get_text_client().generate_text()` with `use_search_grounding=True`
  - [x] Parse LLM response into structured research summary (sources + summary)
  - [x] Persist full sources + summary to `20_research.json`
- [x] Fallback handling
  - [x] If search returns 0 results: raise `DataNotFoundError` (triggers topic pivot)
  - [x] If LLM synthesis fails: use fallback error handling
- [x] Tests
  - [x] Test search grounding integration (mock LLM client)
  - [x] Test LLM synthesis with grounded responses
  - [x] Test fallback path for empty search results

### 7.3 Prompt Generator Agent Enhancement
- [x] Load system prompt from `system_prompts.md`
  - [x] Extract "Strategic Content Architect - User Prompt Engineer" section
  - [x] Store as `PROMPT_ARCHITECT_SYSTEM_PROMPT` constant (loaded via load_system_prompt)
- [x] Replace stub logic with LLM call
  - [x] Build user message: topic + research summary
  - [x] Call `get_text_client().generate_text()` with:
    - [x] `system_instruction=PROMPT_ARCHITECT_SYSTEM_PROMPT`
    - [x] `prompt="[topic]\n[research_summary]"`
    - [x] `temperature=0.7`
  - [x] Parse LLM response to extract structured prompt fields
  - [x] Validate required fields present (topic, audience, pain point, etc.)
- [x] Persona fidelity validation
  - [x] Check for template structure presence
  - [x] Detect cliché analogies (maintain blacklist: "distributed ledger", "like a library", etc.)
  - [x] Raise `ValidationError` if clichés detected
- [x] Tests
  - [x] Test LLM call with mock client
  - [x] Test structured output parsing
  - [x] Test cliché detection logic
  - [x] Test persona compliance assertions

### 7.4 Remove Strategic Type Agent from Pipeline
- [x] Update `orchestrator.py`
  - [x] Remove `_execute_strategic_planning()` method call from pipeline
  - [x] Remove import of `strategic_type_agent`
  - [x] Update Writer Agent input to receive only `structured_prompt` (no `strategy`)
  - [x] Update pipeline flow comments to reflect 7-step process (not 8)
- [x] Keep `agents/strategic_type_agent.py` file (do not delete)
  - [x] Add comment at top: "DEPRECATED: Removed from pipeline. May be refactored in future."
- [x] Update tests
  - [x] Remove Strategic Type Agent tests from integration tests
  - [x] Update orchestrator tests to skip strategic planning step
- [x] Update documentation
  - [x] Update ROADMAP agent list
  - [x] Update README pipeline diagram (when created)

### 7.5 Writer Agent Enhancement
- [x] Load system prompt from `system_prompts.md`
  - [x] Extract "The Witty Expert Persona" section
  - [x] Store as `WITTY_EXPERT_SYSTEM_PROMPT` constant (loaded via load_system_prompt)
- [x] Replace stub logic with LLM call
  - [x] Build user message from `structured_prompt` dict
  - [x] Call `get_text_client().generate_text()` with:
    - [x] `system_instruction=WITTY_EXPERT_SYSTEM_PROMPT`
    - [x] `prompt=formatted_structured_prompt`
    - [x] `temperature=0.8` (higher for creative writing)
- [x] Implement character count loop **within Writer Agent**
  - [x] After LLM generates draft, check `count_chars(draft) < 3000`
  - [x] If pass: return draft in envelope
  - [x] If fail: build shortening prompt
    - [x] "This post is {char_count} characters (limit: 3000). Shorten it to under 3000 characters without impacting overall content."
    - [x] Retry LLM call with original system prompt + draft + shortening instruction
    - [x] Max 3 shortening attempts within agent (raise `ValidationError` if exceeded)
- [x] Update input/output contract
  - [x] Remove `strategy` from input
  - [x] Add optional `shortening_instruction` input (for orchestrator-level loop)
  - [x] Ensure draft passes character validation before returning
- [x] Tests
  - [x] Test LLM call with structured prompt
  - [x] Test character count validation pass/fail
  - [x] Test internal shortening retry loop
  - [x] Test max shortening attempts exceeded

### 7.6 Reviewer Agent Enhancement
- [x] Load review guidelines (optional: extract from persona docs)
- [x] Implement single-pass LLM review with local grammar checking
  - [x] **LLM Pass: Contextual & Coherence Review**
    - [x] Build prompt: "Review this LinkedIn post for logical flow, coherence, and persona consistency (Witty Expert). Return the revised version: [draft]"
    - [x] Call `get_text_client().generate_text()` with review prompt
    - [x] Parse LLM response to extract revised post
  - [x] **Local Grammar & Spelling Check**
    - [x] Use `language-tool-python` to check LLM-revised post for grammar/spelling errors
    - [x] Apply corrections automatically
    - [x] Store grammar-checked version
- [x] Character count validation loop
  - [x] Check if grammar-checked post passes `count_chars(post) < 3000`
  - [x] If pass: persist to `50_review.json` and return
  - [x] If fail: execute hashtag removal logic
    - [x] Programmatically remove all hashtags from end of post (lines starting with `#` after final paragraph)
    - [x] Re-check `count_chars(post_without_hashtags) < 3000`
    - [x] If now pass: persist and return
    - [x] If still fail: build shortening instruction
      - [x] "This post is {char_count} characters (limit: 3000). Revise with minor adjustments to shorten it. Do NOT include hashtags at the end."
      - [x] Send back to LLM review with shortening instruction
      - [x] Max 3 shortening attempts (raise `ValidationError` if exceeded)
- [x] Update artifact structure
  - [x] Persist review outputs to `50_review.json` (include: LLM-revised, grammar-checked, final version, char count, iteration count)
  - [x] Include diff summary between original → LLM-revised → grammar-checked → shortened (if applicable)
- [x] Tests
  - [x] Test LLM review pass with mock client
  - [x] Test local grammar tool integration
  - [x] Test character count validation pass/fail
  - [x] Test hashtag removal logic
  - [x] Test shortening iteration loop
  - [x] Test max shortening attempts exceeded

### 7.7 Image Prompt Generator Agent Enhancement
- [x] Load system prompt from `system_prompts.md`
  - [x] Extract "Social Media Visual Strategist" section
  - [x] Store as `VISUAL_STRATEGIST_SYSTEM_PROMPT` constant (loaded via load_visual_strategist_persona helper)
- [x] Replace stub logic with LLM call
  - [x] Build user message: final reviewed post text
  - [x] Call `get_text_client().generate_text()` with:
    - [x] `system_instruction=VISUAL_STRATEGIST_SYSTEM_PROMPT`
    - [x] `prompt=final_post_text`
    - [x] `temperature=0.7`
  - [x] Parse LLM response to extract image prompt
  - [x] Validate prompt contains no text/words/letters instruction
- [x] Tests
  - [x] Test LLM call with final post
  - [x] Test prompt validation (no-text constraint)
  - [x] Test presence of visual keywords (subject, environment, lighting, mood)

### 7.8 Image Generator Agent Enhancement
- [x] Replace stub PNG with real Gemini image generation
  - [x] Read image prompt from `70_image_prompt.txt`
  - [x] Call `get_image_client().generate_image()` with:
    - [x] `prompt=image_prompt_text`
    - [x] `output_path=80_image.png`
    - [x] `aspect_ratio="1:1"` (LinkedIn optimal)
  - [x] Verify generated image file size > 1KB (not empty)
- [x] Fallback handling
  - [x] If image generation fails: create simple gradient placeholder PNG
  - [x] Log warning but don't abort run
- [x] Tests
  - [x] Test real image generation (mock client)
  - [x] Test fallback placeholder generation
  - [x] Test file integrity validation

### 7.9 Cost Tracking & Reporting
- [x] Instrument all LLM calls with cost tracking
  - [x] After each `generate_text()` call: extract token usage
  - [x] Calculate cost: `(prompt_tokens * input_price + completion_tokens * output_price)`
  - [x] Accumulate in orchestrator metrics: `total_cost_usd`
- [x] Add cost reporting to run summary
  - [x] Print estimated cost before run starts
  - [x] Print actual cost in final summary
  - [x] Include cost breakdown by agent in `metrics` dict
- [x] Add cost alerts
  - [x] Warn if single run exceeds $0.50
  - [x] Abort if single run exceeds `MAX_COST_PER_RUN_USD`
- [x] Tests
  - [x] Test cost calculation with known token counts
  - [x] Test cost accumulation across multiple agents
  - [x] Test max cost abort logic

### 7.10 Integration Testing
- [x] Create `tests/test_integration/test_llm_pipeline.py`
  - [x] Test full pipeline with mocked LLM responses
  - [x] Verify all agents make expected LLM calls
  - [x] Verify system prompts loaded correctly
  - [x] Verify cost tracking across full run
- [x] Create manual smoke test script
  - [x] `python -m scripts.smoke_test --field "Data Science" --max-cost 0.10`
  - [x] Run real pipeline with budget cap
  - [x] Verify artifacts created and valid
  - [x] Print cost summary

### 7.11 Documentation
- [x] Update README with LLM integration details
  - [x] Document which agents call which models
  - [x] Document cost estimation methodology
  - [x] Document safety limits and flags
- [x] Document system prompt maintenance
  - [x] How to update personas in `system_prompts.md`
  - [x] How to test prompt changes

## Phase 8: Memory Bank Content
- [x] Add sample newsletter `.txt` files to `memory_bank/`
- [ ] Document ingestion assumptions in README
- [ ] Test RAG retrieval relevance

## Phase 9: Configuration & Environment
- [ ] Implement `.env` loading using `python-dotenv`
- [ ] Validate presence of `GOOGLE_API_KEY`; raise clear error if missing
- [ ] Update README with environment setup steps

## Phase 10: Testing Infrastructure
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

## Phase 11: Dependency Management
- [ ] Populate `requirements.txt` (initial)
  - [ ] `google-generativeai`
  - [ ] `python-dotenv`
  - [ ] `chromadb` (or chosen RAG lib)
  - [ ] `pytest`
  - [ ] `pytest-cov`
  - [ ] `tqdm` (optional for progress)
  - [ ] `pydantic` (optional for envelope validation)
  - [ ] Search API library (Tavily, SerpAPI, or similar)
  - [ ] `language-tool-python` (optional fallback grammar checker)
- [ ] Freeze versions (pin where critical)
- [ ] Test fresh install in clean venv

## Phase 12: Documentation Enhancements
- [ ] Expand `README.md` with sections: Overview, Architecture Diagram (text-based), Setup, Usage, Testing, Error Taxonomy, Personas, Roadmap reference
- [ ] Add `docs/` directory (optional) for deeper explanations
- [ ] Add `ROADMAP.md` (this file) – DONE
- [ ] Provide example run artifact tree in README
- [ ] Document LLM integration and cost management

## Phase 13: Quality & Validation
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
| M2 | 4–6 | All agents + orchestrator functional (stubs) |
| M3 | 7 | **LLM Integration (CRITICAL)** - Real agent intelligence |
| M4 | 8–10 | Memory bank + config + tests with high coverage |
| M5 | 11–13 | Stable release + CI/CD + docs |
| M6 | 14–16 | Resilience edge cases + enhancements |

## Execution Order (Condensed Checklist)
1. Skeleton & infra (Phases 1–2)
2. DB & RAG (Phases 3 & 2.7)
3. Agents (Phase 4) - Stub implementations
4. Orchestrator + main (Phases 5–6) - Stub pipeline functional
5. **LLM Integration (Phase 7)** - 🚨 CRITICAL: Transform stubs into real agents
6. Memory bank content (Phase 8)
7. Env & config (Phase 9)
8. Tests & coverage (Phase 10)
9. Dependencies (Phase 11)
10. Docs & CI (Phases 12–13)
11. Fallback tests (Phase 14)
12. Optional perf & backlog (15–16)

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
