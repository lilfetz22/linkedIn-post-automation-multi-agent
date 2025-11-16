import json
from pathlib import Path

import pytest

from core.errors import ValidationError
from main import ensure_config, ALLOWED_FIELDS, validate_field, prompt_select_field, load_config, parse_args

def test_validate_field_accepts_allowed():
    for f in ALLOWED_FIELDS:
        assert validate_field(f) == f


def test_validate_field_rejects_invalid():
    with pytest.raises(ValidationError):
        validate_field("Not A Real Field")


def test_ensure_config_creates_when_missing(tmp_path: Path, monkeypatch):
    field = ALLOWED_FIELDS[0]
    ensure_config(tmp_path, non_interactive_field=field)
    # File created
    cfg_path = tmp_path / "config.json"
    assert cfg_path.exists()
    # Re-parse content
    data = json.loads(cfg_path.read_text("utf-8"))
    assert data["field"] == field


def test_ensure_config_no_overwrite_if_exists(tmp_path: Path):
    # Pre-write a config
    existing_field = ALLOWED_FIELDS[1]
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
    field_value = ALLOWED_FIELDS[0]
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
    field_value = ALLOWED_FIELDS[1]
    args = parse_args(["--init-config", "--field", field_value])
    assert args.init_config is True
    assert args.field == field_value
    assert args.run is False


def test_parse_args_run_with_field():
    """Test --run combined with --field"""
    field_value = ALLOWED_FIELDS[0]
    args = parse_args(["--run", "--field", field_value])
    assert args.run is True
    assert args.field == field_value
    assert args.init_config is False


def test_parse_args_all_flags():
    """Test all flags provided together"""
    field_value = ALLOWED_FIELDS[1]
    args = parse_args(["--init-config", "--run", "--field", field_value])
    assert args.init_config is True
    assert args.run is True
    assert args.field == field_value


def test_parse_args_invalid_flag():
    """Test that invalid flags raise SystemExit"""
    with pytest.raises(SystemExit):
        parse_args(["--invalid-flag"])
# Tests for prompt_select_field()


def test_prompt_select_field_valid_input_first_option(monkeypatch, capsys):
    """Test that valid numeric input '1' returns the first field."""
    monkeypatch.setattr("builtins.input", lambda _: "1")
    result = prompt_select_field()
    assert result == ALLOWED_FIELDS[0]
    captured = capsys.readouterr()
    assert "Select your field of expertise:" in captured.out


def test_prompt_select_field_valid_input_second_option(monkeypatch, capsys):
    """Test that valid numeric input '2' returns the second field."""
    monkeypatch.setattr("builtins.input", lambda _: "2")
    result = prompt_select_field()
    assert result == ALLOWED_FIELDS[1]
    captured = capsys.readouterr()
    assert "Select your field of expertise:" in captured.out


def test_prompt_select_field_invalid_then_valid(monkeypatch, capsys):
    """Test that invalid input triggers retry loop, then accepts valid input."""
    inputs = iter(["0", "3"])  # First two invalid, then valid

    def mock_input(prompt):
        try:
            return next(inputs)
        except StopIteration:
            return "1"  # Finally return valid input

    monkeypatch.setattr("builtins.input", mock_input)
    result = prompt_select_field()
    assert result == ALLOWED_FIELDS[0]

    captured = capsys.readouterr()
    # Should show error message twice for invalid attempts
    assert captured.out.count("Invalid selection. Please try again.") == 2


def test_prompt_select_field_non_numeric_input(monkeypatch, capsys):
    """Test that non-numeric input triggers retry loop with error message."""
    inputs = iter(["abc", "xyz"])

    def mock_input(prompt):
        try:
            return next(inputs)
        except StopIteration:
            return "1"  # Finally return valid input

    monkeypatch.setattr("builtins.input", mock_input)
    result = prompt_select_field()
    assert result == ALLOWED_FIELDS[0]

    captured = capsys.readouterr()
    assert captured.out.count("Invalid selection. Please try again.") == 2


def test_prompt_select_field_empty_input(monkeypatch, capsys):
    """Test that empty input triggers retry loop with error message."""
    inputs = iter(["", "  "])  # Empty and whitespace-only

    def mock_input(prompt):
        try:
            return next(inputs)
        except StopIteration:
            return "2"  # Finally return valid input

    monkeypatch.setattr("builtins.input", mock_input)
    result = prompt_select_field()
    assert result == ALLOWED_FIELDS[1]

    captured = capsys.readouterr()
    assert captured.out.count("Invalid selection. Please try again.") == 2


def test_prompt_select_field_out_of_range_negative(monkeypatch, capsys):
    """Test that negative numbers trigger retry loop."""
    inputs = iter(["-1", "-999"])

    def mock_input(prompt):
        try:
            return next(inputs)
        except StopIteration:
            return "1"

    monkeypatch.setattr("builtins.input", mock_input)
    result = prompt_select_field()
    assert result == ALLOWED_FIELDS[0]

    captured = capsys.readouterr()
    assert captured.out.count("Invalid selection. Please try again.") == 2


def test_prompt_select_field_out_of_range_too_high(monkeypatch, capsys):
    """Test that numbers above range trigger retry loop."""
    inputs = iter(["3", "100", "999"])

    def mock_input(prompt):
        try:
            return next(inputs)
        except StopIteration:
            return "2"

    monkeypatch.setattr("builtins.input", mock_input)
    result = prompt_select_field()
    assert result == ALLOWED_FIELDS[1]

    captured = capsys.readouterr()
    assert captured.out.count("Invalid selection. Please try again.") == 3


def test_prompt_select_field_special_characters(monkeypatch, capsys):
    """Test that special characters trigger retry loop."""
    inputs = iter(["!", "@#$", "1.5", "1/2"])

    def mock_input(prompt):
        try:
            return next(inputs)
        except StopIteration:
            return "1"

    monkeypatch.setattr("builtins.input", mock_input)
    result = prompt_select_field()
    assert result == ALLOWED_FIELDS[0]

    captured = capsys.readouterr()
    assert captured.out.count("Invalid selection. Please try again.") == 4


def test_prompt_select_field_displays_all_options(monkeypatch, capsys):
    """Test that all field options are displayed to the user."""
    monkeypatch.setattr("builtins.input", lambda _: "1")
    prompt_select_field()

    captured = capsys.readouterr()
    # Check header message
    assert "Select your field of expertise:" in captured.out
    # Check that each field is displayed with proper numbering
    for idx, field in enumerate(ALLOWED_FIELDS, start=1):
        assert f"{idx}. {field}" in captured.out
