"""
Fallback Tracking & User Approval System

Manages fallback warnings, user notifications, and approvals for pipeline resilience.
Persists warnings to run directory for auditability and final reporting.
"""

from pathlib import Path
from datetime import datetime
import json


class FallbackWarning:
    """Represents a single fallback event with timestamp and metadata."""

    def __init__(
        self,
        agent_name: str,
        reason: str,
        error_message: str,
        step_number: int,
        original_objective: str,
    ):
        """
        Args:
            agent_name: Name of agent that triggered fallback
            reason: Fallback reason (e.g., 'no_sources', 'model_error', 'character_limit')
            error_message: Original error or issue description
            step_number: Pipeline step number
            original_objective: What the agent was trying to accomplish
        """
        self.agent_name = agent_name
        self.reason = reason
        self.error_message = error_message
        self.step_number = step_number
        self.original_objective = original_objective
        self.timestamp = datetime.now().isoformat()
        self.user_approved = False

    def to_dict(self) -> dict:
        """Convert warning to dictionary for persistence."""
        return {
            "timestamp": self.timestamp,
            "agent": self.agent_name,
            "step": self.step_number,
            "reason": self.reason,
            "error_message": self.error_message,
            "original_objective": self.original_objective,
            "user_approved": self.user_approved,
        }


class FallbackTracker:
    """Centralized tracking of fallback events during a run."""

    def __init__(self, run_path: Path):
        """
        Initialize tracker for a run.

        Args:
            run_path: Path to run directory where warnings will be persisted
        """
        self.run_path = Path(run_path)
        self.warnings: list[FallbackWarning] = []
        self.warnings_file = self.run_path / "fallback_warnings.jsonl"

    def record_warning(
        self,
        agent_name: str,
        reason: str,
        error_message: str,
        step_number: int,
        original_objective: str,
    ) -> FallbackWarning:
        """
        Record a fallback warning with automatic persistence.

        Args:
            agent_name: Name of agent
            reason: Reason for fallback
            error_message: Error details
            step_number: Pipeline step
            original_objective: What was being attempted

        Returns:
            FallbackWarning object
        """
        warning = FallbackWarning(
            agent_name=agent_name,
            reason=reason,
            error_message=error_message,
            step_number=step_number,
            original_objective=original_objective,
        )

        self.warnings.append(warning)
        self._persist_warning(warning)

        return warning

    def request_user_approval(self, warning: FallbackWarning) -> bool:
        """
        Prompt user for approval to proceed with fallback.

        Args:
            warning: FallbackWarning to request approval for

        Returns:
            True if user approves, False if user declines

        Raises:
            KeyboardInterrupt if user cancels (Ctrl+C)
        """
        print("\n" + "=" * 70)
        print("⚠️  FALLBACK REQUIRED - USER APPROVAL NEEDED")
        print("=" * 70)
        print(f"\nAgent: {warning.agent_name}")
        print(f"Step {warning.step_number}: {warning.original_objective}")
        print(f"Reason: {warning.reason}")
        print(f"\nError Details:")
        print(f"  {warning.error_message}")
        print("\n" + "-" * 70)
        print("FALLBACK PLAN:")
        print("-" * 70)

        if warning.reason == "no_sources":
            print("  • Switching to offline memory bank for research summary")
            print("  • Using existing local content instead of web search")
        elif warning.reason == "model_error":
            print("  • Using deterministic template (not LLM-generated)")
            print(
                "  • Content will follow persona guidelines but without LLM creativity"
            )
        elif warning.reason == "character_limit":
            print("  • Content shortened to meet 3000 character limit")
            print("  • Core message preserved; elaboration trimmed")
        elif warning.reason == "validation_error":
            print("  • Using minimal safe alternative")
            print("  • Pipeline will continue with reduced quality")

        print("\n" + "-" * 70)
        print("CONSEQUENCES:")
        print("-" * 70)
        print(
            "  • If you approve: Pipeline proceeds with fallback (no additional LLM cost)"
        )
        print("  • If you decline: Run aborts; no further LLM calls will be made")
        print("\n")

        while True:
            try:
                response = (
                    input("Continue with fallback? (yes/no/show_error): ")
                    .strip()
                    .lower()
                )

                if response in ["yes", "y"]:
                    warning.user_approved = True
                    self._persist_warning(warning)
                    print("✓ Continuing with fallback...\n")
                    return True

                elif response in ["no", "n"]:
                    print("✗ Run aborted by user.\n")
                    return False

                elif response in ["show_error", "error", "e"]:
                    print("\nFull Error Message:")
                    print("-" * 70)
                    print(warning.error_message)
                    print("-" * 70 + "\n")

                else:
                    print(
                        "Invalid input. Please answer 'yes', 'no', or 'show_error'.\n"
                    )

            except KeyboardInterrupt:
                print("\n✗ Run cancelled by user (Ctrl+C).\n")
                raise

    def _persist_warning(self, warning: FallbackWarning) -> None:
        """Append warning to persistent JSONL file."""
        self.warnings_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.warnings_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(warning.to_dict()) + "\n")

    def get_summary(self) -> dict:
        """Get summary of all recorded warnings."""
        return {
            "total_warnings": len(self.warnings),
            "approved_warnings": sum(1 for w in self.warnings if w.user_approved),
            "warnings": [w.to_dict() for w in self.warnings],
        }

    def create_fallback_report(self) -> str:
        """
        Generate a human-readable fallback report for final output.

        Returns:
            Formatted report as string
        """
        if not self.warnings:
            return ""

        lines = [
            "\n" + "=" * 70,
            "FALLBACK USAGE REPORT",
            "=" * 70,
            f"\nTotal Fallbacks Used: {len(self.warnings)}",
            f"User Approvals: {sum(1 for w in self.warnings if w.user_approved)}/{len(self.warnings)}",
            "\n" + "-" * 70,
            "Fallback Details:",
            "-" * 70,
        ]

        for i, warning in enumerate(self.warnings, 1):
            lines.extend(
                [
                    f"\n{i}. Step {warning.step_number}: {warning.agent_name}",
                    f"   Reason: {warning.reason}",
                    f"   Objective: {warning.original_objective}",
                    f"   Error: {warning.error_message[:100]}...",
                    f"   User Approved: {'Yes ✓' if warning.user_approved else 'No ✗'}",
                ]
            )

        lines.extend(
            [
                "\n" + "=" * 70,
                "IMPORTANT: Review fallback usage above.",
                "Quality may have been reduced due to errors.",
                "=" * 70 + "\n",
            ]
        )

        return "\n".join(lines)
