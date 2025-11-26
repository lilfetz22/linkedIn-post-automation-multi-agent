# Integration Tests - README

## Overview

This directory contains integration tests for the LinkedIn Post Automation Multi-Agent System's LLM pipeline.

## Test Files

### `test_llm_pipeline.py`

Comprehensive integration tests for the full pipeline with mocked LLM responses. Tests verify:

- **System Prompts**: Correctly loaded from `system_prompts.md`
- **Cost Tracking**: Accumulates costs across all agents
- **Artifact Creation**: All expected artifacts are created and valid
- **Event Logging**: Events are properly logged for each pipeline step
- **Full Pipeline**: Complete end-to-end execution with mocked LLM
- **Agent LLM Calls**: Each agent makes expected LLM calls
- **Data Flow**: Data passes correctly between agents

## Test Status

✅ **Passing Tests** (6/8):
- `test_database_fixture_works` - Verifies database fixture creates valid DB with seed data
- `test_system_prompts_loaded_correctly` - Verifies system prompts are loadable
- `test_cost_tracking_across_full_run` - Validates cost accumulation
- `test_artifacts_created_at_each_step` - Checks artifact persistence
- `test_event_logging_for_all_steps` - Confirms event logging
- `test_all_agents_make_expected_llm_calls` - Verifies LLM client calls

⚠️ **Tests Needing Refinement** (2/8):
- `test_full_pipeline_with_mocked_llm` - Mocking strategy needs adjustment (runs slowly)
- `test_data_flows_correctly_between_agents` - Mocking strategy needs adjustment

**Note**: Database setup issues have been FIXED. All tests now use a proper test database fixture.

## Running Tests

### Run all integration tests:
```powershell
pytest tests/test_integration/ -v
```

### Run specific test:
```powershell
pytest tests/test_integration/test_llm_pipeline.py::TestLLMPipelineIntegration::test_system_prompts_loaded_correctly -v
```

### Run with coverage:
```powershell
pytest tests/test_integration/ --cov=. --cov-report=html
```

## Test Fixtures

### `mock_llm_responses`
Provides realistic mock LLM responses for each agent:
- Research synthesis
- Structured prompt generation  
- Draft post creation
- Reviewed post
- Image prompt

### `mock_config`
Test configuration with field selection:
```python
{"field": "Data Science (Optimizations & Time-Series Analysis)"}
```

### `temp_run_dir`
Temporary directory for run artifacts during testing.

## Mocking Strategy

The tests use comprehensive mocking to avoid:
- Real LLM API calls (expensive)
- Real database operations (requires setup)
- Real image generation (slow)
- Real web searches (network dependency)

### Mocked Components:
- `core.llm_clients.get_text_client()` - Text generation LLM
- `agents.image_generator_agent.get_image_client()` - Image generation
- `agents.reviewer_agent._apply_grammar_corrections()` - Grammar checking
- `agents.topic_agent.select_new_topic()` - Database topic selection

## Known Issues

1. ✅ **Database Setup**: FIXED - Test database fixture now properly initializes temp database with schema and seed data
   - Implemented `test_database` fixture that creates isolated test database for each test
   - Uses `database.init_db` and `seed_potential_topics` for proper setup

2. **LLM Response Format**: Tests assume specific response structure from Gemini API
   - **Note**: Update mock responses if API response format changes

3. **Path Dependencies**: Tests require proper working directory setup
   - **Fix**: Tests use `monkeypatch.chdir(tmp_path)` to isolate environment

## Future Improvements

- [ ] Add fixture for database initialization with test data
- [ ] Add tests for error scenarios (API failures, malformed responses)
- [ ] Add tests for retry logic and circuit breaker
- [ ] Add performance benchmarks for pipeline execution
- [ ] Add tests for character count loop convergence
- [ ] Add integration test with real (sandboxed) LLM calls for smoke testing

## Manual Smoke Testing

For real pipeline validation with budget caps, use the smoke test script:

```powershell
python -m scripts.smoke_test --field "Data Science" --max-cost 0.10
```

This runs the full pipeline with real LLM calls but limits spending to prevent unexpected costs.

## Related Documentation

- `../../ROADMAP.md` - Phase 7.10 Integration Testing
- `../../project_spec.md` - Complete technical specification
- `../../system_prompts.md` - Agent persona definitions
