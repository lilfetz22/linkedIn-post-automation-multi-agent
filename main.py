"""
Main entry point for LinkedIn Post Automation Multi-Agent System.

This script handles first-run onboarding, configuration management,
and orchestration of the multi-agent pipeline.

Usage (PowerShell):
    Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
    python main.py [--init-config] [--field "<field>"] [--run] [--dry-run]

Examples:
    # Run full pipeline
    python main.py

    # Test setup without API calls
    python main.py --dry-run

    # Run without image generation (lower cost)
    python main.py --no-image

    # Initialize config only
    python main.py --init-config --field "Data Science (Optimizations & Time-Series Analysis)"
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


# Example fields (users can enter any field they wish)
EXAMPLE_FIELDS = [
    "Data Science (Optimizations & Time-Series Analysis)",
    "Generative AI & AI Agents",
    "Software Engineering (Cloud Architecture)",
    "DevOps & Infrastructure",
]


def validate_field(value: str) -> str:
    """
    Validate that the provided field value is a non-empty string.

    Args:
        value: Field string to validate (any non-empty string is accepted)

    Returns:
        The validated field string (same as input if valid)

    Raises:
        ValidationError: If value is empty or only whitespace

    Example:
        >>> validate_field("Data Science (Optimizations & Time-Series Analysis)")
        "Data Science (Optimizations & Time-Series Analysis)"
        >>> validate_field("Custom Machine Learning Field")
        "Custom Machine Learning Field"
        >>> validate_field("")
        ValidationError: Field cannot be empty
    """
    if not value or not value.strip():
        raise ValidationError("Field cannot be empty")
    return value.strip()


def prompt_select_field() -> str:
    """
    Interactively prompt user to enter their field of expertise.

    Displays example fields and accepts any non-empty string as input.
    Continues prompting until valid input is provided.

    Returns:
        User-entered field string (non-empty)

    Notes:
        This function implements an infinite retry loop, prompting
        repeatedly until user provides non-empty input. Users can
        enter any custom field they wish.

    Example:
        >>> field = prompt_select_field()
        Enter your field of expertise.
        Examples:
          - Data Science (Optimizations & Time-Series Analysis)
          - Generative AI & AI Agents
          - Software Engineering (Cloud Architecture)
          - DevOps & Infrastructure

        Your field: Machine Learning Operations
        >>> print(field)
        "Machine Learning Operations"
    """
    print("\nEnter your field of expertise.")
    print("Examples:")
    for example in EXAMPLE_FIELDS:
        print(f"  - {example}")
    print()

    while True:
        raw = input("Your field: ").strip()
        if raw:
            try:
                return validate_field(raw)
            except ValidationError as e:
                print(f"Error: {e}. Please try again.")
        else:
            print("Field cannot be empty. Please try again.")


def config_path(root: Path) -> Path:
    """
    Returns the path to the configuration file (`config.json`) located at the given project root.

    Args:
        root (Path): The root directory of the project.

    Returns:
        Path: The full path to the `config.json` file within the specified root directory.

    Example:
        >>> from pathlib import Path
        >>> config_path(Path("/my/project"))
        PosixPath('/my/project/config.json')
    """
    return root / "config.json"


def load_config(root: Path) -> Optional[dict]:
    """
    Load and validate configuration from config.json.

    Reads config.json from the project root, validates its structure,
    and ensures the 'field' value is a non-empty string.

    Args:
        root: Project root directory path

    Returns:
        Dictionary with 'field' key if config exists and is valid,
        None if config.json does not exist

    Raises:
        ValidationError: If config.json exists but is missing 'field' key
                        or field value is empty
        CorruptionError: If config.json contains invalid JSON that cannot be parsed

    Example:
        >>> config = load_config(Path.cwd())
        >>> config
        {"field": "Data Science (Optimizations & Time-Series Analysis)"}
    """
    path = config_path(root)
    if not path.exists():
        return None

    try:
        with path.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        raise CorruptionError(f"config.json contains invalid JSON: {e}") from e

    if not isinstance(data, dict) or "field" not in data:
        raise ValidationError("config.json missing required 'field'.")
    validate_field(data["field"])
    return data


def ensure_config(root: Path, non_interactive_field: Optional[str] = None) -> dict:
    """
    Ensure config.json exists and is valid, creating it if necessary.

    If config.json already exists and is valid, returns its contents.
    Otherwise, prompts user interactively or uses non_interactive_field
    to create a new configuration file using atomic write pattern.

    Args:
        root: Project root directory path
        non_interactive_field: Optional field value to use without prompting.
                              If None, user will be prompted interactively.

    Returns:
        Dictionary containing validated configuration with 'field' key

    Raises:
        ValidationError: If non_interactive_field is provided but invalid,
                        or if existing config is malformed
        CorruptionError: If config.json exists but contains invalid JSON,
                        or if write verification fails

    Example:
        >>> config = ensure_config(
        ...     Path.cwd(),
        ...     "Data Science (Optimizations & Time-Series Analysis)"
        ... )
        >>> config
        {"field": "Data Science (Optimizations & Time-Series Analysis)"}
    """
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
    """
    Parse command-line arguments for the multi-agent system.

    Supports six optional flags:
    - --init-config: Initialize config.json without running pipeline
    - --field: Specify field value non-interactively
    - --run: Explicitly execute the pipeline
    - --dry-run: Execute setup and estimate costs without making LLM calls
    - --no-image: Skip image generation to reduce costs
    - --runs: Number of sequential runs to execute (default: 1, min: 1, max: 100)

    Args:
        argv: List of command-line argument strings (typically sys.argv[1:])

    Returns:
        argparse.Namespace object with parsed arguments:
        - init_config (bool): True if --init-config flag provided
        - field (Optional[str]): Field value if --field provided
        - run (bool): True if --run flag provided
        - dry_run (bool): True if --dry-run flag provided
        - no_image (bool): True if --no-image flag provided
        - runs (int): Number of runs to execute (default: 1)

    Example:
        >>> args = parse_args(["--init-config", "--field", "Data Science"])
        >>> args.init_config
        True
        >>> args.field
        "Data Science"
        >>> args = parse_args(["--runs", "3"])
        >>> args.runs
        3
    """
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
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Execute setup and estimate costs without making LLM API calls",
    )
    parser.add_argument(
        "--no-image",
        action="store_true",
        help="Skip image generation (reduces cost to $0.04-$0.10 text-only)",
    )
    parser.add_argument(
        "--runs",
        type=int,
        default=1,
        choices=range(1, 101),
        help="Number of sequential runs to execute (default: 1, max: 100)",
    )
    return parser.parse_args(argv)


def print_summary(result: dict) -> None:
    """
    Print formatted summary of pipeline execution to console.

    Displays run status, unique run identifier, run directory path,
    and paths to generated artifacts (final post and image) if available.
    Handles missing artifacts gracefully by only displaying what exists.
    Shows cost estimates and next steps for dry-run mode.

    Args:
        result: Dictionary returned by Orchestrator.run() containing:
               - status: "success" or "error"
               - mode: "dry_run" if in dry-run mode (optional)
               - run_id: Unique run identifier string
               - run_path: Path to run directory
               - artifacts: Optional dict with 'final_post' and 'image' keys
               - estimated_cost_usd: Estimated cost for dry-run mode

    Output Format:
        ============================================================
        RUN SUMMARY
        ============================================================
        Status     : success
        Run ID     : 20250122-abc123
        Run Path   : runs/20250122-abc123/
        Artifacts  :
          - runs/20250122-abc123/60_final_post.txt
          - runs/20250122-abc123/80_image.png

    Example:
        >>> result = {"status": "success", "run_id": "20250122-abc123",
        ...           "run_path": "runs/20250122-abc123/",
        ...           "artifacts": {"final_post": "60_final_post.txt"}}
        >>> print_summary(result)
    """
    status = result.get("status")
    mode = result.get("mode")

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
        config = artifacts.get("config")
        dry_run_summary = artifacts.get("dry_run_summary")

        if config:
            print(f"  - {config}")
        if dry_run_summary:
            print(f"  - {dry_run_summary}")
        if final_post:
            print(f"  - {final_post}")
        if image:
            print(f"  - {image}")

    # Show cost estimates for dry-run mode
    if mode == "dry_run":
        print()
        estimated_cost = result.get("estimated_cost_usd", 0)
        print(f"Estimated Cost: ${estimated_cost:.2f} USD")

        dry_run_summary = result.get("dry_run_summary", {})
        cost_range = dry_run_summary.get("cost_range_usd", "0.35 - 0.45")
        print(f"Cost Range: ${cost_range}")

        # Show cost savings tip if available
        cost_savings_tip = dry_run_summary.get("cost_savings_tip")
        if cost_savings_tip:
            print(f"💡 Tip: {cost_savings_tip}")

        next_steps = dry_run_summary.get("next_steps", {})
        if next_steps:
            print()
            print(f"Next LLM Call: {next_steps.get('first_llm_call', 'N/A')}")
            model = next_steps.get("model", "N/A")
            temp = next_steps.get("temperature", "N/A")
            print(f"Model: {model} (temperature: {temp})")

        print()
        print(
            "Note: No API calls were made. Remove --dry-run to execute full pipeline."
        )


def run_pipeline(
    root: Path,
    non_interactive_field: Optional[str],
    dry_run: bool = False,
    no_image: bool = False,
    run_number: Optional[int] = None,
) -> Tuple[int, Optional[dict]]:
    """
    Execute the full multi-agent pipeline with configuration initialization.

    Ensures configuration exists (creating if necessary), instantiates
    the Orchestrator with validated config, runs the complete agent pipeline,
    and prints execution summary.

    Args:
        root: Project root directory path
        non_interactive_field: Optional field value for non-interactive config creation.
                              If None and config doesn't exist, user will be prompted.
        dry_run: If True, execute setup and estimate costs without making LLM calls
        no_image: If True, skip image generation to reduce costs (~$0.30 savings)
        run_number: Optional sequential run number for multi-run execution.
                   Used to distinguish multiple runs on the same day.

    Returns:
        Tuple of (exit_code, result_dict) where:
        - exit_code: 0 for successful execution, 1 for failed execution
        - result_dict: Dictionary from Orchestrator.run() containing status,
                      run_id, run_path, and artifacts

    Raises:
        ValidationError: If field validation fails during config creation
        CorruptionError: If config.json is corrupted or write verification fails

    Example:
        >>> exit_code, result = run_pipeline(
        ...     Path.cwd(),
        ...     "Data Science (Optimizations & Time-Series Analysis)"
        ... )
        >>> exit_code
        0
        >>> result["status"]
        "success"
        >>> # For multi-run execution
        >>> exit_code, result = run_pipeline(
        ...     Path.cwd(),
        ...     "Data Science",
        ...     run_number=2
        ... )
    """
    config = ensure_config(root, non_interactive_field)
    orchestrator = Orchestrator(
        config, dry_run=dry_run, no_image=no_image, run_number=run_number
    )
    result = orchestrator.run()
    print_summary(result)
    exit_code = 0 if result.get("status") == "success" else 1
    return exit_code, result


def main(argv: Optional[list[str]] = None) -> int:
    """
    Main entry point for LinkedIn Post Automation Multi-Agent System.

    Handles CLI workflow with four modes:
    1. Config initialization only (--init-config without --run)
    2. Single pipeline execution (default or with --run flag)
    3. Multi-run execution (--runs > 1)
    4. Interactive or non-interactive configuration setup

    The function ensures configuration exists before pipeline execution,
    handles user interruptions gracefully, supports sequential multi-run
    execution with run numbering, and provides comprehensive error handling
    for validation, corruption, and I/O issues.

    Args:
        argv: Optional list of command-line arguments. If None, uses sys.argv[1:].
             Primarily used for testing to inject custom arguments.

    Returns:
        Exit code integer:
        - 0: Successful execution (config initialized, all runs completed, or pipeline completed)
        - 1: Error occurred (validation failure, corruption, I/O error, user interruption,
              or pipeline failure)

    Raises:
        Does not raise exceptions; all errors are caught and return exit code 1.

    CLI Examples:
        # Initialize config interactively and exit:
        $ python main.py --init-config

        # Initialize config non-interactively:
        $ python main.py --init-config --field "Data Science (Optimizations & Time-Series Analysis)"

        # Run pipeline once (default):
        $ python main.py

        # Run pipeline with non-interactive config creation:
        $ python main.py --field "Generative AI & AI Agents"

        # Run pipeline 3 times sequentially:
        $ python main.py --runs 3

        # Run 5 times with no image generation:
        $ python main.py --runs 5 --no-image
    """
    print("LinkedIn Post Automation Multi-Agent System")
    print("=" * 50)

    args = parse_args(sys.argv[1:] if argv is None else argv)
    root = Path.cwd()

    try:
        if args.init_config and not args.run:
            cfg = ensure_config(root, args.field)
            print("config.json initialized:")
            print(json.dumps(cfg, indent=2))
            return 0

        # Multi-run execution logic
        all_runs_successful = True
        for run_num in range(1, args.runs + 1):
            if args.runs > 1:
                print(f"\n{'=' * 50}")
                print(f"Run {run_num} of {args.runs}")
                print(f"{'=' * 50}")

            code, result = run_pipeline(
                root,
                args.field,
                dry_run=args.dry_run,
                no_image=args.no_image,
                run_number=run_num if args.runs > 1 else None,
            )

            if code != 0:
                all_runs_successful = False
                # Stop on first failure
                if args.runs > 1:
                    print(f"\nRun {run_num} failed. Stopping multi-run execution.")
                return code

        return 0 if all_runs_successful else 1

    except (ValidationError, CorruptionError) as e:
        print(f"Error: {e}")
        return 1
    except OSError as e:
        print(f"File I/O error: {e}")
        return 1
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        return 1


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
