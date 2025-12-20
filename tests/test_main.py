import json
from pathlib import Path

import pytest

from unittest.mock import Mock, patch

from core.errors import ValidationError, CorruptionError
from main import (
    ensure_config,
    EXAMPLE_FIELDS,
    validate_field,
    prompt_select_field,
    load_config,
    parse_args,
    print_summary,
    run_pipeline,
    main,
)


def test_validate_field_accepts_allowed():
    """Test that validate_field accepts example fields."""
    for f in EXAMPLE_FIELDS:
        assert validate_field(f) == f


def test_validate_field_accepts_custom():
    """Test that validate_field accepts any non-empty custom string."""
    custom_fields = [
        "Machine Learning Operations",
        "Cloud Architecture",
        "DevOps & Infrastructure",
        "Custom Field 123",
    ]
    for f in custom_fields:
        assert validate_field(f) == f


def test_validate_field_strips_whitespace():
    """Test that validate_field strips leading/trailing whitespace."""
    assert validate_field("  Data Science  ") == "Data Science"
    assert validate_field("\tDevOps\n") == "DevOps"


def test_validate_field_rejects_empty():
    """Test that validate_field rejects empty strings."""
    with pytest.raises(ValidationError, match="Field cannot be empty"):
        validate_field("")
    with pytest.raises(ValidationError, match="Field cannot be empty"):
        validate_field("   ")


def test_ensure_config_creates_when_missing(tmp_path: Path):
    field = "Data Science (Optimizations & Time-Series Analysis)"
    ensure_config(tmp_path, non_interactive_field=field)
    # File created
    cfg_path = tmp_path / "config.json"
    assert cfg_path.exists()
    # Re-parse content
    data = json.loads(cfg_path.read_text("utf-8"))
    assert data["field"] == field


def test_ensure_config_no_overwrite_if_exists(tmp_path: Path):
    # Pre-write a config
    existing_field = "Generative AI & AI Agents"
    (tmp_path / "config.json").write_text(
        json.dumps({"field": existing_field}), encoding="utf-8"
    )

    cfg = ensure_config(tmp_path)
    assert cfg["field"] == existing_field

    # Ensure file remains unchanged
    data = json.loads((tmp_path / "config.json").read_text("utf-8"))
    assert data["field"] == existing_field


# Tests for parse_args function


def test_parse_args_init_config_flag():
    """Test that --init-config flag is parsed correctly"""
    args = parse_args(["--init-config"])
    assert args.init_config is True
    assert args.field is None
    assert args.run is False


def test_parse_args_field_argument():
    """Test that --field argument is parsed correctly"""
    field_value = "Data Science (Optimizations & Time-Series Analysis)"
    args = parse_args(["--field", field_value])
    assert args.field == field_value
    assert args.init_config is False
    assert args.run is False


def test_parse_args_run_flag():
    """Test that --run flag is parsed correctly"""
    args = parse_args(["--run"])
    assert args.run is True
    assert args.init_config is False
    assert args.field is None


def test_parse_args_no_flags():
    """Test default behavior when no flags are provided"""
    args = parse_args([])
    assert args.init_config is False
    assert args.run is False
    assert args.field is None


def test_parse_args_init_config_with_field():
    """Test --init-config combined with --field"""
    field_value = "Generative AI & AI Agents"
    args = parse_args(["--init-config", "--field", field_value])
    assert args.init_config is True
    assert args.field == field_value
    assert args.run is False


def test_parse_args_run_with_field():
    """Test --run combined with --field"""
    field_value = "Data Science (Optimizations & Time-Series Analysis)"
    args = parse_args(["--run", "--field", field_value])
    assert args.run is True
    assert args.field == field_value
    assert args.init_config is False


def test_parse_args_all_flags():
    """Test all flags provided together"""
    field_value = "Generative AI & AI Agents"
    args = parse_args(["--init-config", "--run", "--field", field_value])
    assert args.init_config is True
    assert args.run is True
    assert args.field == field_value


def test_parse_args_invalid_flag():
    """Test that invalid flags raise SystemExit"""
    with pytest.raises(SystemExit):
        parse_args(["--invalid-flag"])


# Tests for prompt_select_field()


def test_prompt_select_field_valid_input(monkeypatch, capsys):
    """Test that valid text input returns the field."""
    monkeypatch.setattr("builtins.input", lambda _: "Data Science")
    result = prompt_select_field()
    assert result == "Data Science"
    captured = capsys.readouterr()
    assert "Enter your field of expertise" in captured.out
    assert "Examples:" in captured.out


def test_prompt_select_field_custom_field(monkeypatch, capsys):
    """Test that custom field input is accepted."""
    monkeypatch.setattr("builtins.input", lambda _: "Machine Learning Operations")
    result = prompt_select_field()
    assert result == "Machine Learning Operations"
    captured = capsys.readouterr()
    assert "Enter your field of expertise" in captured.out


def test_prompt_select_field_strips_whitespace(monkeypatch, capsys):
    """Test that whitespace is stripped from input."""
    monkeypatch.setattr("builtins.input", lambda _: "  Cloud Architecture  ")
    result = prompt_select_field()
    assert result == "Cloud Architecture"


def test_prompt_select_field_empty_input_then_valid(monkeypatch, capsys):
    """Test that empty input triggers retry loop, then accepts valid input."""
    inputs = iter(["", "  ", "DevOps"])

    def mock_input(prompt):
        return next(inputs)

    monkeypatch.setattr("builtins.input", mock_input)
    result = prompt_select_field()
    assert result == "DevOps"

    captured = capsys.readouterr()
    # Should show error message twice for empty attempts
    assert captured.out.count("Field cannot be empty") == 2


def test_prompt_select_field_displays_examples(monkeypatch, capsys):
    """Test that example fields are displayed to the user."""
    monkeypatch.setattr("builtins.input", lambda _: "Data Science")
    prompt_select_field()

    captured = capsys.readouterr()
    # Check header message
    assert "Enter your field of expertise" in captured.out
    # Check that examples section exists
    assert "Examples:" in captured.out


# Tests for load_config()


def test_load_config_returns_none_when_missing(tmp_path: Path):
    """Test that load_config returns None when config.json doesn't exist."""
    result = load_config(tmp_path)
    assert result is None


def test_load_config_returns_valid_config(tmp_path: Path):
    """Test that load_config returns valid config when file exists."""
    field = "Data Science (Optimizations & Time-Series Analysis)"
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"field": field}), encoding="utf-8")

    result = load_config(tmp_path)
    assert result is not None
    assert result["field"] == field


def test_load_config_raises_validation_error_missing_field(tmp_path: Path):
    """Test that load_config raises ValidationError when 'field' key is missing."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"other_key": "value"}), encoding="utf-8")

    with pytest.raises(ValidationError, match="missing required 'field'"):
        load_config(tmp_path)


def test_load_config_raises_validation_error_empty_field(tmp_path: Path):
    """Test that load_config raises ValidationError when field value is empty."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"field": ""}), encoding="utf-8")

    with pytest.raises(ValidationError, match="Field cannot be empty"):
        load_config(tmp_path)


def test_load_config_raises_corruption_error_invalid_json(tmp_path: Path):
    """Test that load_config raises CorruptionError when JSON is malformed."""
    config_file = tmp_path / "config.json"
    config_file.write_text("{ invalid json }", encoding="utf-8")

    with pytest.raises(CorruptionError, match="invalid JSON"):
        load_config(tmp_path)


def test_load_config_raises_validation_error_not_dict(tmp_path: Path):
    """Test that load_config raises ValidationError when JSON is not a dictionary."""
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps(["not", "a", "dict"]), encoding="utf-8")

    with pytest.raises(ValidationError, match="missing required 'field'"):
        load_config(tmp_path)


# Tests for print_summary()


def test_print_summary_displays_status_and_basic_info(capsys):
    """Test that print_summary displays status, run_id, and run_path."""
    result = {
        "status": "success",
        "run_id": "20250122-abc123",
        "run_path": "runs/20250122-abc123/",
    }

    print_summary(result)
    captured = capsys.readouterr()

    assert "RUN SUMMARY" in captured.out
    assert "Status     : success" in captured.out
    assert "Run ID     : 20250122-abc123" in captured.out
    assert "Run Path   : runs/20250122-abc123/" in captured.out


def test_print_summary_displays_artifacts_when_present(capsys):
    """Test that print_summary displays artifacts when they exist."""
    result = {
        "status": "success",
        "run_id": "20250122-abc123",
        "run_path": "runs/20250122-abc123/",
        "artifacts": {
            "final_post": "runs/20250122-abc123/60_final_post.txt",
            "image": "runs/20250122-abc123/80_image.png",
        },
    }

    print_summary(result)
    captured = capsys.readouterr()

    assert "Artifacts  :" in captured.out
    assert "runs/20250122-abc123/60_final_post.txt" in captured.out
    assert "runs/20250122-abc123/80_image.png" in captured.out


def test_print_summary_handles_missing_artifacts_gracefully(capsys):
    """Test that print_summary doesn't show Artifacts section when none exist."""
    result = {
        "status": "error",
        "run_id": "20250122-xyz789",
        "run_path": "runs/20250122-xyz789/",
    }

    print_summary(result)
    captured = capsys.readouterr()

    assert "RUN SUMMARY" in captured.out
    assert "Status     : error" in captured.out
    assert "Artifacts  :" not in captured.out


def test_print_summary_handles_empty_artifacts_dict(capsys):
    """Test that print_summary handles empty artifacts dictionary."""
    result = {
        "status": "success",
        "run_id": "20250122-xyz789",
        "run_path": "runs/20250122-xyz789/",
        "artifacts": {},
    }

    print_summary(result)
    captured = capsys.readouterr()

    assert "RUN SUMMARY" in captured.out
    assert "Artifacts  :" not in captured.out


def test_print_summary_handles_partial_artifacts(capsys):
    """Test that print_summary displays only the artifacts that exist."""
    result = {
        "status": "success",
        "run_id": "20250122-abc123",
        "run_path": "runs/20250122-abc123/",
        "artifacts": {
            "final_post": "runs/20250122-abc123/60_final_post.txt"
            # No image artifact
        },
    }

    print_summary(result)
    captured = capsys.readouterr()

    assert "Artifacts  :" in captured.out
    assert "runs/20250122-abc123/60_final_post.txt" in captured.out
    assert "80_image.png" not in captured.out


def test_print_summary_handles_none_artifacts(capsys):
    """Test that print_summary handles None artifacts value."""
    result = {
        "status": "success",
        "run_id": "20250122-xyz789",
        "run_path": "runs/20250122-xyz789/",
        "artifacts": None,
    }

    print_summary(result)
    captured = capsys.readouterr()

    assert "RUN SUMMARY" in captured.out
    assert "Artifacts  :" not in captured.out


# Tests for run_pipeline()


@patch("main.Orchestrator")
def test_run_pipeline_returns_exit_code_0_on_success(
    mock_orchestrator_class, tmp_path: Path, capsys
):
    """Test that run_pipeline returns exit code 0 when pipeline succeeds."""
    field = "Data Science (Optimizations & Time-Series Analysis)"
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"field": field}), encoding="utf-8")

    # Mock orchestrator instance and its run method
    mock_orchestrator = Mock()
    mock_orchestrator.run.return_value = {
        "status": "success",
        "run_id": "20250122-abc123",
        "run_path": "runs/20250122-abc123/",
        "artifacts": {"final_post": "60_final_post.txt"},
    }
    mock_orchestrator_class.return_value = mock_orchestrator

    exit_code, result = run_pipeline(tmp_path, field)

    assert exit_code == 0
    assert result["status"] == "success"
    mock_orchestrator_class.assert_called_once_with(
        {"field": field}, dry_run=False, no_image=False
    )
    mock_orchestrator.run.assert_called_once()


@patch("main.Orchestrator")
def test_run_pipeline_returns_exit_code_1_on_failure(
    mock_orchestrator_class, tmp_path: Path, capsys
):
    """Test that run_pipeline returns exit code 1 when pipeline fails."""
    field = "Data Science (Optimizations & Time-Series Analysis)"
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"field": field}), encoding="utf-8")

    # Mock orchestrator instance and its run method
    mock_orchestrator = Mock()
    mock_orchestrator.run.return_value = {
        "status": "error",
        "run_id": "20250122-xyz789",
        "run_path": "runs/20250122-xyz789/",
        "error": "Something went wrong",
    }
    mock_orchestrator_class.return_value = mock_orchestrator

    exit_code, result = run_pipeline(tmp_path, field)

    assert exit_code == 1
    assert result["status"] == "error"


@patch("main.Orchestrator")
def test_run_pipeline_initializes_config_before_orchestrator(
    mock_orchestrator_class, tmp_path: Path
):
    """Test that run_pipeline properly initializes config before calling orchestrator."""
    field = "Generative AI & AI Agents"

    # Mock orchestrator
    mock_orchestrator = Mock()
    mock_orchestrator.run.return_value = {
        "status": "success",
        "run_id": "20250122-test",
        "run_path": "runs/20250122-test/",
    }
    mock_orchestrator_class.return_value = mock_orchestrator

    exit_code, result = run_pipeline(tmp_path, field)

    # Verify config was created
    config_file = tmp_path / "config.json"
    assert config_file.exists()
    config_data = json.loads(config_file.read_text("utf-8"))
    assert config_data["field"] == field

    # Verify Orchestrator was called with correct config
    mock_orchestrator_class.assert_called_once_with(
        {"field": field}, dry_run=False, no_image=False
    )


@patch("main.Orchestrator")
def test_run_pipeline_calls_orchestrator_with_correct_config(
    mock_orchestrator_class, tmp_path: Path
):
    """Test that run_pipeline passes correct config to Orchestrator."""
    field = "Data Science (Optimizations & Time-Series Analysis)"
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"field": field}), encoding="utf-8")

    mock_orchestrator = Mock()
    mock_orchestrator.run.return_value = {
        "status": "success",
        "run_id": "test",
        "run_path": "runs/test/",
    }
    mock_orchestrator_class.return_value = mock_orchestrator

    run_pipeline(tmp_path, None)

    # Verify orchestrator was instantiated with correct config
    call_args = mock_orchestrator_class.call_args[0][0]
    assert call_args["field"] == field


@patch("main.Orchestrator")
def test_run_pipeline_prints_summary_after_completion(
    mock_orchestrator_class, tmp_path: Path, capsys
):
    """Test that run_pipeline prints summary after orchestrator completes."""
    field = "Data Science (Optimizations & Time-Series Analysis)"
    config_file = tmp_path / "config.json"
    config_file.write_text(json.dumps({"field": field}), encoding="utf-8")

    mock_orchestrator = Mock()
    mock_orchestrator.run.return_value = {
        "status": "success",
        "run_id": "20250122-summary",
        "run_path": "runs/20250122-summary/",
    }
    mock_orchestrator_class.return_value = mock_orchestrator

    run_pipeline(tmp_path, None)

    captured = capsys.readouterr()
    assert "RUN SUMMARY" in captured.out
    assert "20250122-summary" in captured.out


# Tests for main()


@patch("main.run_pipeline")
def test_main_init_config_without_run_exits_with_0(
    mock_run_pipeline, tmp_path: Path, capsys, monkeypatch
):
    """Test that --init-config without --run initializes config and exits with code 0."""
    monkeypatch.chdir(tmp_path)
    field = "Data Science (Optimizations & Time-Series Analysis)"

    exit_code = main(["--init-config", "--field", field])

    assert exit_code == 0
    captured = capsys.readouterr()
    assert "config.json initialized:" in captured.out
    assert field in captured.out

    # Verify config file was created
    config_file = tmp_path / "config.json"
    assert config_file.exists()

    # run_pipeline should NOT be called
    mock_run_pipeline.assert_not_called()


@patch("main.run_pipeline")
def test_main_default_behavior_runs_pipeline(
    mock_run_pipeline, tmp_path: Path, monkeypatch
):
    """Test that default behavior (no flags) runs the pipeline."""
    monkeypatch.chdir(tmp_path)
    mock_run_pipeline.return_value = (0, {"status": "success"})

    exit_code = main([])

    assert exit_code == 0
    mock_run_pipeline.assert_called_once()


@patch("main.run_pipeline")
def test_main_returns_exit_code_from_pipeline(
    mock_run_pipeline, tmp_path: Path, monkeypatch
):
    """Test that main returns the exit code from run_pipeline."""
    monkeypatch.chdir(tmp_path)
    mock_run_pipeline.return_value = (1, {"status": "error"})

    exit_code = main([])

    assert exit_code == 1


def test_main_validation_error_returns_1(tmp_path: Path, monkeypatch, capsys):
    """Test that ValidationError exceptions are caught and return exit code 1."""
    monkeypatch.chdir(tmp_path)

    # Use empty field to trigger ValidationError
    exit_code = main(["--init-config", "--field", ""])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.out
    assert "Field cannot be empty" in captured.out


def test_main_corruption_error_returns_1(tmp_path: Path, monkeypatch, capsys):
    """Test that CorruptionError exceptions are caught and return exit code 1."""
    monkeypatch.chdir(tmp_path)

    # Create corrupted config.json
    config_file = tmp_path / "config.json"
    config_file.write_text("{ invalid json }", encoding="utf-8")

    exit_code = main([])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.out


def test_main_prints_error_message_on_validation_error(
    tmp_path: Path, monkeypatch, capsys
):
    """Test that error messages are printed when ValidationError occurs."""
    monkeypatch.chdir(tmp_path)

    # Use empty field to trigger ValidationError
    exit_code = main(["--init-config", "--field", ""])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.out
    assert "Field cannot be empty" in captured.out


def test_main_prints_error_message_on_corruption_error(
    tmp_path: Path, monkeypatch, capsys
):
    """Test that error messages are printed when CorruptionError occurs."""
    monkeypatch.chdir(tmp_path)

    # Create corrupted config
    config_file = tmp_path / "config.json"
    config_file.write_text("not json at all", encoding="utf-8")

    exit_code = main([])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Error:" in captured.out


@patch("main.run_pipeline")
def test_main_with_run_flag_executes_pipeline(
    mock_run_pipeline, tmp_path: Path, monkeypatch
):
    """Test that --run flag explicitly executes the pipeline."""
    monkeypatch.chdir(tmp_path)
    mock_run_pipeline.return_value = (0, {"status": "success"})
    field = "Data Science (Optimizations & Time-Series Analysis)"

    exit_code = main(["--run", "--field", field])

    assert exit_code == 0
    mock_run_pipeline.assert_called_once()


@patch("main.run_pipeline")
def test_main_init_config_with_run_executes_pipeline(
    mock_run_pipeline, tmp_path: Path, monkeypatch
):
    """Test that --init-config WITH --run executes the pipeline (--run takes precedence)."""
    monkeypatch.chdir(tmp_path)
    mock_run_pipeline.return_value = (0, {"status": "success"})
    field = "Data Science (Optimizations & Time-Series Analysis)"

    exit_code = main(["--init-config", "--run", "--field", field])

    assert exit_code == 0
    mock_run_pipeline.assert_called_once()


def test_main_io_error_returns_1(tmp_path: Path, monkeypatch, capsys):
    """Test that OSError/IOError exceptions are caught and return exit code 1."""
    monkeypatch.chdir(tmp_path)

    # Mock ensure_config to raise OSError during config initialization
    with patch("main.ensure_config", side_effect=OSError("Permission denied")):
        exit_code = main(
            [
                "--init-config",
                "--field",
                "Data Science (Optimizations & Time-Series Analysis)",
            ]
        )

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "File I/O error:" in captured.out


def test_main_keyboard_interrupt_returns_1(tmp_path: Path, monkeypatch, capsys):
    """Test that KeyboardInterrupt is caught and returns exit code 1."""
    monkeypatch.chdir(tmp_path)

    # Mock ensure_config to raise KeyboardInterrupt
    with patch("main.ensure_config", side_effect=KeyboardInterrupt()):
        exit_code = main([])

    assert exit_code == 1
    captured = capsys.readouterr()
    assert "Operation cancelled by user." in captured.out
