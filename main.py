"""
Main entry point for LinkedIn Post Automation Multi-Agent System.

This script handles first-run onboarding, configuration management,
and orchestration of the multi-agent pipeline.

Usage (PowerShell):
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    python main.py [--init-config] [--field "<field>"] [--run]
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional, Tuple

from core.persistence import write_and_verify_json
from core.errors import ValidationError, CorruptionError
from orchestrator import Orchestrator


ALLOWED_FIELDS = [
    "Data Science (Optimizations & Time-Series Analysis)",
    "Generative AI & AI Agents",
]


def validate_field(value: str) -> str:
    if value not in ALLOWED_FIELDS:
        raise ValidationError(
            "Invalid field. Choose one of: " + ", ".join(ALLOWED_FIELDS)
        )
    return value


def prompt_select_field() -> str:
    print("Select your field of expertise:")
    for idx, val in enumerate(ALLOWED_FIELDS, start=1):
        print(f"  {idx}. {val}")
    while True:
        raw = input("Enter number (1-{}): ".format(len(ALLOWED_FIELDS))).strip()
        if raw.isdigit():
            i = int(raw)
            if 1 <= i <= len(ALLOWED_FIELDS):
                return ALLOWED_FIELDS[i - 1]
        print("Invalid selection. Please try again.")


def config_path(root: Path) -> Path:
    return root / "config.json"


def load_config(root: Path) -> Optional[dict]:
    path = config_path(root)
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict) or "field" not in data:
        raise ValidationError("config.json missing required 'field'.")
    validate_field(data["field"])
    return data


def ensure_config(root: Path, non_interactive_field: Optional[str] = None) -> dict:
    existing = load_config(root)
    if existing is not None:
        return existing

    if non_interactive_field is None:
        field_value = prompt_select_field()
    else:
        field_value = validate_field(non_interactive_field)

    cfg = {"field": field_value}
    # Atomic write and verify integrity
    verified = write_and_verify_json(config_path(root), cfg)
    return verified


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="LinkedIn Post Automation Multi-Agent System"
    )
    parser.add_argument(
        "--init-config",
        action="store_true",
        help="Initialize config.json and exit",
    )
    parser.add_argument(
        "--field",
        type=str,
        help="Field value to set non-interactively (used with --init-config or default run)",
    )
    parser.add_argument(
        "--run",
        action="store_true",
        help="Execute the full pipeline (default behavior if no flags provided)",
    )
    return parser.parse_args(argv)


def print_summary(result: dict) -> None:
    status = result.get("status")
    print("\n" + "=" * 60)
    print("RUN SUMMARY")
    print("=" * 60)
    print(f"Status     : {status}")
    print(f"Run ID     : {result.get('run_id')}")
    print(f"Run Path   : {result.get('run_path')}")

    artifacts = result.get("artifacts") or {}
    if artifacts:
        print("Artifacts  :")
        final_post = artifacts.get("final_post")
        image = artifacts.get("image")
        if final_post:
            print(f"  - {final_post}")
        if image:
            print(f"  - {image}")


def run_pipeline(root: Path, non_interactive_field: Optional[str]) -> Tuple[int, Optional[dict]]:
    config = ensure_config(root, non_interactive_field)
    orchestrator = Orchestrator(config)
    result = orchestrator.run()
    print_summary(result)
    exit_code = 0 if result.get("status") == "success" else 1
    return exit_code, result


def main(argv: Optional[list[str]] = None) -> int:
    print("LinkedIn Post Automation Multi-Agent System")
    print("=" * 50)

    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path.cwd()

    try:
        if args.init_config and not args.run:
            ensure_config(root, args.field)
            cfg = load_config(root)
            print("config.json initialized:")
            print(json.dumps(cfg, indent=2))
            return 0

        # Default behavior: run pipeline (with config onboarding)
        code, _ = run_pipeline(root, args.field)
        return code

    except (ValidationError, CorruptionError) as e:
        print(f"Error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
