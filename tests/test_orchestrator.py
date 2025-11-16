"""
Tests for the Orchestrator agent.

Covers configuration loading, run directory creation, circuit breaker integration,
character count loop, topic pivot logic, and error handling scenarios.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from orchestrator import Orchestrator
from core.errors import (
    ValidationError,
    DataNotFoundError,
    CorruptionError,
    ModelError,
)
from core.retry import CircuitBreakerTrippedError
from core.envelope import ok, err


# Fixtures


@pytest.fixture
def valid_config():
    """Valid configuration for testing."""
    return {"field": "Data Science (Optimizations & Time-Series Analysis)"}


@pytest.fixture
def mock_run_dir(tmp_path):
    """Mock run directory."""
    run_dir = tmp_path / "2025-11-16-abc123"
    run_dir.mkdir(parents=True, exist_ok=True)
    return run_dir


@pytest.fixture
def orchestrator_with_config(valid_config):
    """Orchestrator instance with valid config."""
    return Orchestrator(valid_config)


# Test Suite: Configuration & Initialization (5.1)


def test_orchestrator_init_with_valid_config(valid_config):
    """Test orchestrator initialization with valid configuration."""
    orch = Orchestrator(valid_config)

    assert orch.config == valid_config
    assert orch.run_id is None
    assert orch.run_path is None
    assert orch.circuit_breaker is not None
    assert orch.metrics is not None


def test_orchestrator_init_with_missing_field():
    """Test orchestrator rejects config without 'field' key."""
    with pytest.raises(ValidationError, match="must include 'field'"):
        Orchestrator({})


def test_orchestrator_init_with_none_config():
    """Test orchestrator rejects None config."""
    with pytest.raises(ValidationError):
        Orchestrator(None)


@patch("orchestrator.create_run_dir")
@patch("orchestrator.write_and_verify_json")
@patch("orchestrator.log_event")
def test_initialize_run_creates_directory(
    mock_log, mock_write, mock_create_dir, valid_config, mock_run_dir
):
    """Test _initialize_run creates run directory and saves config."""
    mock_create_dir.return_value = ("2025-11-16-abc123", mock_run_dir)

    orch = Orchestrator(valid_config)
    orch._initialize_run()

    assert orch.run_id == "2025-11-16-abc123"
    assert orch.run_path == mock_run_dir
    assert orch.context["run_id"] == "2025-11-16-abc123"
    assert orch.context["run_path"] == mock_run_dir

    mock_create_dir.assert_called_once_with()
    mock_write.assert_called_once()
    mock_log.assert_called_once_with("2025-11-16-abc123", "initialization", 1, "ok")


# Test Suite: Agent Execution Infrastructure (5.2)


@patch("orchestrator.execute_with_retries")
def test_execute_agent_with_retry_success(mock_retry, orchestrator_with_config):
    """Test successful agent execution with no retries needed."""
    mock_agent = Mock(return_value=ok({"result": "success"}))
    mock_retry.return_value = ok({"result": "success"})

    orchestrator_with_config.run_id = "test-run"
    orchestrator_with_config.run_path = Path("/tmp/test-run")
    orchestrator_with_config.context = {
        "run_id": "test-run",
        "run_path": Path("/tmp/test-run"),
    }

    response = orchestrator_with_config._execute_agent_with_retry(
        "test_agent", mock_agent, {"input": "data"}
    )

    assert response["status"] == "ok"
    assert "test_agent" in orchestrator_with_config.metrics["agent_metrics"]
    assert (
        orchestrator_with_config.metrics["agent_metrics"]["test_agent"]["status"]
        == "success"
    )


@patch("orchestrator.execute_with_retries")
def test_execute_agent_with_retry_handles_validation_error(
    mock_retry, orchestrator_with_config
):
    """Test agent execution raises ValidationError from response."""
    mock_agent = Mock(
        return_value=err("ValidationError", "Invalid input", retryable=False)
    )

    def raise_validation_error(*args, **kwargs):
        raise ValidationError("Invalid input")

    mock_retry.side_effect = raise_validation_error

    orchestrator_with_config.run_id = "test-run"
    orchestrator_with_config.run_path = Path("/tmp/test-run")
    orchestrator_with_config.context = {
        "run_id": "test-run",
        "run_path": Path("/tmp/test-run"),
    }

    with pytest.raises(ValidationError):
        orchestrator_with_config._execute_agent_with_retry(
            "test_agent", mock_agent, {"input": "data"}
        )

    assert "test_agent" in orchestrator_with_config.metrics["agent_metrics"]
    assert (
        orchestrator_with_config.metrics["agent_metrics"]["test_agent"]["status"]
        == "failed"
    )


# Test Suite: Sequential Agent Pipeline (5.3)


@patch("orchestrator.topic_agent")
def test_execute_topic_selection_success(mock_topic_agent, orchestrator_with_config):
    """Test successful topic selection."""
    mock_topic_agent.run.return_value = ok({"topic": "Python AsyncIO"})

    orchestrator_with_config.run_id = "test-run"
    orchestrator_with_config.run_path = Path("/tmp/test-run")
    orchestrator_with_config.context = {
        "run_id": "test-run",
        "run_path": Path("/tmp/test-run"),
    }

    with patch.object(
        orchestrator_with_config,
        "_execute_agent_with_retry",
        return_value=ok({"topic": "Python AsyncIO"}),
    ):
        topic = orchestrator_with_config._execute_topic_selection()

    assert topic == "Python AsyncIO"


@patch("orchestrator.research_agent")
def test_execute_research_with_pivot_on_data_not_found(
    mock_research_agent, orchestrator_with_config
):
    """Test research falls back to topic pivot on DataNotFoundError."""
    orchestrator_with_config.run_id = "test-run"
    orchestrator_with_config.run_path = Path("/tmp/test-run")
    orchestrator_with_config.context = {
        "run_id": "test-run",
        "run_path": Path("/tmp/test-run"),
    }

    # Mock first research call fails, second succeeds after pivot
    call_count = 0

    def mock_research_call(*args, **kwargs):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise DataNotFoundError("No sources found")
        return ok({"sources": ["source1"], "summary": "summary"})

    with patch.object(
        orchestrator_with_config, "_execute_agent_with_retry", side_effect=mock_research_call
    ), patch.object(
        orchestrator_with_config,
        "_execute_topic_selection",
        return_value="New Topic",
    ):
        result = orchestrator_with_config._execute_research_with_pivot("Old Topic")

    assert result["sources"] == ["source1"]
    assert orchestrator_with_config.metrics["topic_pivots"] == 1


@patch("orchestrator.research_agent")
def test_execute_research_max_pivots_exceeded(
    mock_research_agent, orchestrator_with_config
):
    """Test research aborts after max topic pivots."""
    orchestrator_with_config.run_id = "test-run"
    orchestrator_with_config.run_path = Path("/tmp/test-run")
    orchestrator_with_config.context = {
        "run_id": "test-run",
        "run_path": Path("/tmp/test-run"),
    }

    # Always fail research
    with patch.object(
        orchestrator_with_config,
        "_execute_agent_with_retry",
        side_effect=DataNotFoundError("No sources"),
    ), patch.object(
        orchestrator_with_config, "_execute_topic_selection", return_value="New Topic"
    ), patch("orchestrator.log_event"):
        with pytest.raises(DataNotFoundError, match="after 2 topic pivots"):
            orchestrator_with_config._execute_research_with_pivot("Initial Topic")

    # The loop increments pivot_count to 3, but should fail after 2 pivots
    # So it will try: initial (fail) -> pivot 1 (fail) -> pivot 2 (fail) -> raise error
    assert orchestrator_with_config.metrics["topic_pivots"] == 3


# Test Suite: Character Count Validation Loop (5.4)


def test_character_count_loop_passes_first_iteration(orchestrator_with_config):
    """Test character count loop succeeds on first iteration if < 3000."""
    orchestrator_with_config.run_id = "test-run"
    orchestrator_with_config.run_path = Path("/tmp/test-run")
    orchestrator_with_config.context = {
        "run_id": "test-run",
        "run_path": Path("/tmp/test-run"),
    }

    short_text = "A" * 2000  # Under 3000 chars

    with patch.object(
        orchestrator_with_config,
        "_execute_agent_with_retry",
        return_value=ok({"draft_path": "40_draft.md"}),
    ) as mock_execute, patch(
        "orchestrator.Path.read_text", return_value=short_text
    ), patch(
        "orchestrator.atomic_write_text"
    ) as mock_write, patch(
        "orchestrator.log_event"
    ):
        # Mock reviewer to return short text
        def mock_agent_call(agent_name, *args, **kwargs):
            if agent_name == "writer_agent":
                return ok({"draft_path": "40_draft.md"})
            elif agent_name == "reviewer_agent":
                return ok({"revised": short_text})

        mock_execute.side_effect = mock_agent_call

        result = orchestrator_with_config._execute_writing_and_review_loop(
            {"topic": "test"}, {"strategy": "test"}
        )

    assert result == short_text
    assert orchestrator_with_config.metrics["char_loop_iterations"] == 1
    mock_write.assert_called_once()


def test_character_count_loop_retries_on_long_text(orchestrator_with_config):
    """Test character count loop retries when text is too long."""
    orchestrator_with_config.run_id = "test-run"
    orchestrator_with_config.run_path = Path("/tmp/test-run")
    orchestrator_with_config.context = {
        "run_id": "test-run",
        "run_path": Path("/tmp/test-run"),
    }

    long_text = "A" * 3100  # Over 3000 chars
    short_text = "A" * 2000  # Under 3000 chars

    iteration = 0

    def mock_agent_call(agent_name, *args, **kwargs):
        nonlocal iteration
        if agent_name == "writer_agent":
            return ok({"draft_path": "40_draft.md"})
        elif agent_name == "reviewer_agent":
            iteration += 1
            if iteration == 1:
                return ok({"revised": long_text})  # First attempt too long
            else:
                return ok({"revised": short_text})  # Second attempt OK

    with patch.object(
        orchestrator_with_config, "_execute_agent_with_retry", side_effect=mock_agent_call
    ), patch("orchestrator.Path.read_text", side_effect=[long_text, short_text]), patch(
        "orchestrator.atomic_write_text"
    ) as mock_write, patch(
        "orchestrator.log_event"
    ):
        result = orchestrator_with_config._execute_writing_and_review_loop(
            {"topic": "test"}, {"strategy": "test"}
        )

    assert result == short_text
    assert orchestrator_with_config.metrics["char_loop_iterations"] == 2
    # atomic_write_text is called with (path, text), not keyword args
    assert mock_write.call_count == 1
    assert mock_write.call_args[0][1] == short_text


def test_character_count_loop_max_iterations_exceeded(orchestrator_with_config):
    """Test character count loop aborts after max iterations."""
    orchestrator_with_config.run_id = "test-run"
    orchestrator_with_config.run_path = Path("/tmp/test-run")
    orchestrator_with_config.context = {
        "run_id": "test-run",
        "run_path": Path("/tmp/test-run"),
    }

    long_text = "A" * 3100  # Always too long

    def mock_agent_call(agent_name, *args, **kwargs):
        if agent_name == "writer_agent":
            return ok({"draft_path": "40_draft.md"})
        elif agent_name == "reviewer_agent":
            return ok({"revised": long_text})

    with patch.object(
        orchestrator_with_config, "_execute_agent_with_retry", side_effect=mock_agent_call
    ), patch("orchestrator.Path.read_text", return_value=long_text), patch(
        "orchestrator.log_event"
    ):
        with pytest.raises(ValidationError, match="exceeded 5 iterations"):
            orchestrator_with_config._execute_writing_and_review_loop(
                {"topic": "test"}, {"strategy": "test"}
            )

    assert orchestrator_with_config.metrics["char_loop_iterations"] == 5


# Test Suite: Run Completion & Error Handling (5.6)


@patch("orchestrator.log_event")
def test_complete_run_success(mock_log, orchestrator_with_config, mock_run_dir):
    """Test successful run completion returns correct summary."""
    orchestrator_with_config.run_id = "test-run"
    orchestrator_with_config.run_path = mock_run_dir

    result = orchestrator_with_config._complete_run_success("Final post text")

    assert result["status"] == "success"
    assert result["run_id"] == "test-run"
    assert "60_final_post.txt" in result["artifacts"]["final_post"]
    assert "80_image.png" in result["artifacts"]["image"]
    mock_log.assert_called_once_with("test-run", "run_complete", 1, "ok")


@patch("orchestrator.write_and_verify_json")
@patch("orchestrator.log_event")
def test_handle_run_failure_creates_artifact(
    mock_log, mock_write, orchestrator_with_config, mock_run_dir
):
    """Test run failure creates run_failed.json with error details."""
    orchestrator_with_config.run_id = "test-run"
    orchestrator_with_config.run_path = mock_run_dir
    orchestrator_with_config.metrics["agent_metrics"]["test_agent"] = {
        "status": "failed"
    }

    error = ValidationError("Test error")
    stack = "Stack trace here"

    result = orchestrator_with_config._handle_run_failure(error, stack)

    assert result["status"] == "failed"
    assert result["error"]["type"] == "ValidationError"
    assert result["error"]["message"] == "Test error"
    assert "run_failed.json" in result["failure_artifact"]

    mock_write.assert_called_once()
    failure_data = mock_write.call_args[0][1]
    assert failure_data["error_type"] == "ValidationError"
    assert failure_data["failed_step"] == "test_agent"
    assert failure_data["stack_trace"] == stack


# Test Suite: Circuit Breaker Integration


@patch("orchestrator.execute_with_retries")
def test_circuit_breaker_trips_after_failures(mock_retry, orchestrator_with_config):
    """Test circuit breaker trips after 3 consecutive failures."""
    orchestrator_with_config.run_id = "test-run"
    orchestrator_with_config.run_path = Path("/tmp/test-run")
    orchestrator_with_config.context = {
        "run_id": "test-run",
        "run_path": Path("/tmp/test-run"),
    }

    mock_retry.side_effect = CircuitBreakerTrippedError("Circuit breaker tripped")

    with pytest.raises(CircuitBreakerTrippedError):
        orchestrator_with_config._execute_agent_with_retry(
            "test_agent", Mock(), {"input": "data"}
        )


# Test Suite: Integration Tests


@patch("orchestrator.topic_agent")
@patch("orchestrator.research_agent")
@patch("orchestrator.prompt_generator_agent")
@patch("orchestrator.strategic_type_agent")
@patch("orchestrator.writer_agent")
@patch("orchestrator.reviewer_agent")
@patch("orchestrator.image_prompt_agent")
@patch("orchestrator.image_generator_agent")
@patch("orchestrator.create_run_dir")
@patch("orchestrator.write_and_verify_json")
@patch("orchestrator.atomic_write_text")
@patch("orchestrator.log_event")
def test_full_pipeline_integration(
    mock_log,
    mock_write_text,
    mock_write_json,
    mock_create_dir,
    mock_img_gen,
    mock_img_prompt,
    mock_reviewer,
    mock_writer,
    mock_strategy,
    mock_prompt,
    mock_research,
    mock_topic,
    valid_config,
    tmp_path,
):
    """Test complete pipeline with all agents mocked."""
    # Setup run directory
    run_dir = tmp_path / "test-run"
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "80_image.png").touch()
    (run_dir / "40_draft.md").write_text("Draft content")
    (run_dir / "70_image_prompt.txt").write_text("Image prompt")

    mock_create_dir.return_value = ("test-run", run_dir)

    # Mock agent responses
    mock_topic.run.return_value = ok({"topic": "Python AsyncIO"})
    mock_research.run.return_value = ok(
        {"sources": ["source1"], "summary": "summary"}
    )
    mock_prompt.run.return_value = ok(
        {"topic_title": "AsyncIO", "pain_point": "complexity"}
    )
    mock_strategy.run.return_value = ok({"strategic_angle": "simplify"})
    mock_writer.run.return_value = ok({"draft_path": "40_draft.md"})
    mock_reviewer.run.return_value = ok({"revised": "A" * 2000})  # Under 3000 chars
    mock_img_prompt.run.return_value = ok({"prompt": "Image prompt"})
    mock_img_gen.run.return_value = ok({"image_path": "80_image.png"})

    # Execute orchestrator
    orch = Orchestrator(valid_config)
    result = orch.run()

    # Verify success
    assert result["status"] == "success"
    assert result["run_id"] == "test-run"
    assert "artifacts" in result
    assert orch.metrics["char_loop_iterations"] == 1
    assert orch.metrics["topic_pivots"] == 0


def test_orchestrator_aborts_on_corruption_error(orchestrator_with_config):
    """Test orchestrator aborts immediately on CorruptionError."""
    orchestrator_with_config.run_id = "test-run"
    orchestrator_with_config.run_path = Path("/tmp/test-run")

    with patch.object(
        orchestrator_with_config, "_initialize_run"
    ), patch.object(
        orchestrator_with_config,
        "_execute_topic_selection",
        side_effect=CorruptionError("Artifact corrupted"),
    ), patch.object(
        orchestrator_with_config, "_handle_run_failure", return_value={"status": "failed"}
    ) as mock_handle:
        result = orchestrator_with_config.run()

    assert result["status"] == "failed"
    mock_handle.assert_called_once()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
