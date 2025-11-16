import json
from pathlib import Path
import builtins
import types

import pytest

from main import ensure_config, load_config, ALLOWED_FIELDS, validate_field
from core.errors import ValidationError

def test_validate_field_accepts_allowed():
    for f in ALLOWED_FIELDS:
        assert validate_field(f) == f


def test_validate_field_rejects_invalid():
    with pytest.raises(ValidationError):
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
