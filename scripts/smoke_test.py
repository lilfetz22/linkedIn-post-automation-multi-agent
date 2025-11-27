"""
Smoke test script for manual pipeline validation.

Usage:
    python -m scripts.smoke_test --field "Data Science" --max-cost 0.10

This script runs the full pipeline with a budget cap to verify:
- All agents execute successfully
- Artifacts are created and valid
- Cost tracking is accurate
- No unexpected errors occur
"""

import argparse
import sys
import json
from pathlib import Path
from datetime import datetime

from orchestrator import Orchestrator
from core.errors import ValidationError


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Run smoke test of LinkedIn post automation pipeline"
    )
    parser.add_argument(
        "--field",
        required=True,
        choices=[
            "Data Science (Optimizations & Time-Series Analysis)",
            "Generative AI & AI Agents",
        ],
        help="Field for topic selection",
    )
    parser.add_argument(
        "--max-cost",
        type=float,
        default=0.10,
        help="Maximum cost in USD for this test run (default: 0.10)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Initialize but don't make any LLM calls",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print detailed progress information",
    )

    return parser.parse_args()


def verify_artifacts(run_path: Path, verbose: bool = False) -> dict:
    """
    Verify all expected artifacts exist and are valid.

    Args:
        run_path: Path to run directory
        verbose: Whether to print detailed verification info

    Returns:
        Dictionary with verification results
    """
    expected_artifacts = [
        ("00_config.json", "json"),
        ("10_topic.json", "json"),
        ("20_research.json", "json"),
        ("25_structured_prompt.json", "json"),
        ("40_draft.md", "text"),
        ("50_review.json", "json"),
        ("60_final_post.txt", "text"),
        ("70_image_prompt.txt", "text"),
        ("80_image.png", "binary"),
    ]

    results = {"total": len(expected_artifacts), "passed": 0, "failed": 0, "errors": []}

    for artifact_name, artifact_type in expected_artifacts:
        artifact_path = run_path / artifact_name

        if verbose:
            print(f"  Checking {artifact_name}...", end=" ")

        if not artifact_path.exists():
            results["failed"] += 1
            results["errors"].append(f"{artifact_name}: File not found")
            if verbose:
                print("❌ NOT FOUND")
            continue

        # Check file is not empty
        if artifact_path.stat().st_size == 0:
            results["failed"] += 1
            results["errors"].append(f"{artifact_name}: File is empty")
            if verbose:
                print("❌ EMPTY")
            continue

        # Validate JSON files can be parsed
        if artifact_type == "json":
            try:
                json.loads(artifact_path.read_text())
            except json.JSONDecodeError as e:
                results["failed"] += 1
                results["errors"].append(f"{artifact_name}: Invalid JSON - {e}")
                if verbose:
                    print(f"❌ INVALID JSON: {e}")
                continue

        # Validate image files have reasonable size
        if artifact_type == "binary" and artifact_name.endswith(".png"):
            if artifact_path.stat().st_size < 1000:  # Less than 1KB is suspicious
                results["failed"] += 1
                results["errors"].append(
                    f"{artifact_name}: File too small ({artifact_path.stat().st_size} bytes)"
                )
                if verbose:
                    print(f"❌ TOO SMALL ({artifact_path.stat().st_size} bytes)")
                continue

        results["passed"] += 1
        if verbose:
            print("✅ OK")

    return results


def print_cost_summary(result: dict, verbose: bool = False):
    """
    Print cost summary from pipeline result.

    Args:
        result: Orchestrator result dictionary
        verbose: Whether to print detailed breakdown
    """
    if "metrics" not in result:
        print("\n⚠️  No cost metrics available")
        return

    metrics = result["metrics"]

    print("\n" + "=" * 60)
    print("COST SUMMARY")
    print("=" * 60)

    if "total_cost_usd" in metrics:
        print(f"Total Cost: ${metrics['total_cost_usd']:.4f} USD")
    else:
        print("Total Cost: Not available")

    if "api_call_count" in metrics:
        print(f"API Calls: {metrics['api_call_count']}")

    if verbose and "costs_by_agent" in metrics:
        print("\nCost Breakdown by Agent:")
        for agent, cost in metrics["costs_by_agent"].items():
            print(f"  {agent}: ${cost:.4f}")

    if verbose and "calls_by_agent" in metrics:
        print("\nAPI Calls by Agent:")
        for agent, calls in metrics["calls_by_agent"].items():
            print(f"  {agent}: {calls} calls")

    print("=" * 60)


def main():
    """Run smoke test."""
    args = parse_args()

    print("=" * 60)
    print("LinkedIn Post Automation - Smoke Test")
    print("=" * 60)
    print(f"Field: {args.field}")
    print(f"Max Cost: ${args.max_cost:.2f}")
    print(f"Dry Run: {args.dry_run}")
    print(f"Timestamp: {datetime.now().isoformat()}")
    print("=" * 60)

    # Create config
    config = {"field": args.field, "max_cost_usd": args.max_cost}

    if args.verbose:
        print("\n📋 Configuration:")
        print(json.dumps(config, indent=2))

    # Initialize orchestrator
    print("\n🚀 Initializing orchestrator...")
    try:
        orchestrator = Orchestrator(config)
    except ValidationError as e:
        print(f"\n❌ Configuration error: {e}")
        return 1

    if args.dry_run:
        print("\n✅ Dry run complete - configuration valid")
        print("   (No LLM calls made)")
        return 0

    # Run pipeline
    print("\n⚙️  Running pipeline...")
    if args.verbose:
        print("   (This may take several minutes)")

    try:
        result = orchestrator.run()
    except Exception as e:
        print(f"\n❌ Pipeline failed with error: {e}")
        if args.verbose:
            import traceback

            print("\nStack trace:")
            traceback.print_exc()
        return 1

    # Check result status
    if result["status"] != "ok":
        print(
            f"\n❌ Pipeline failed: {result.get('error', {}).get('message', 'Unknown error')}"
        )
        if args.verbose and "error" in result:
            print("\nError details:")
            print(json.dumps(result["error"], indent=2))
        return 1

    print("\n✅ Pipeline completed successfully!")

    # Print run information
    data = result.get("data", {})
    run_id = data.get("run_id", "unknown")
    run_path = Path(data.get("run_path", "unknown"))

    print(f"\nRun ID: {run_id}")
    print(f"Run Path: {run_path}")

    # Verify artifacts
    print("\n📦 Verifying artifacts...")
    verification = verify_artifacts(run_path, verbose=args.verbose)

    print(
        f"\nArtifact Verification: {verification['passed']}/{verification['total']} passed"
    )

    if verification["failed"] > 0:
        print(f"❌ {verification['failed']} artifacts failed verification:")
        for error in verification["errors"]:
            print(f"   - {error}")
        return 1

    # Print cost summary
    print_cost_summary(result, verbose=args.verbose)

    # Check if cost exceeded budget
    metrics = result.get("metrics", {})
    total_cost = metrics.get("total_cost_usd", 0)
    if total_cost > args.max_cost:
        print(
            f"\n⚠️  WARNING: Cost ${total_cost:.4f} exceeded budget ${args.max_cost:.2f}"
        )
        return 1

    # Print final post preview
    final_post_path = run_path / "60_final_post.txt"
    if final_post_path.exists():
        print("\n" + "=" * 60)
        print("FINAL POST PREVIEW")
        print("=" * 60)
        final_post = final_post_path.read_text()
        # Print first 500 chars
        preview = final_post[:500]
        if len(final_post) > 500:
            preview += "..."
        print(preview)
        print(f"\nFull post: {final_post_path}")
        print(f"Character count: {len(final_post)}")
        print("=" * 60)

    print("\n✅ All checks passed!")
    print(f"\n📁 View full results at: {run_path}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
