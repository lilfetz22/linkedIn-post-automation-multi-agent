import json
from pathlib import Path

import pytest

from core.errors import ValidationError
from main import ensure_config, ALLOWED_FIELDS, validate_field, prompt_select_field, load_config

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
