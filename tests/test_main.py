import json
from pathlib import Path
import builtins
import types

import pytest

from main import ensure_config, load_config, ALLOWED_FIELDS, validate_field, parse_args


def test_validate_field_accepts_allowed():
    for f in ALLOWED_FIELDS:
        assert validate_field(f) == f


def test_validate_field_rejects_invalid():
    with pytest.raises(Exception):
        validate_field("Not A Real Field")


def test_ensure_config_creates_when_missing(tmp_path: Path, monkeypatch):
    field = ALLOWED_FIELDS[0]
    cfg = ensure_config(tmp_path, non_interactive_field=field)
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
