"""
Event logging system for pipeline execution tracking.

All agent invocations, retries, and errors are logged to events.jsonl
in append-only fashion for complete auditability.
"""

import json
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

# Thread lock for safe concurrent writes
_log_lock = threading.Lock()

# Default log file path (relative to project root)
EVENTS_LOG_PATH = Path("events.jsonl")


def log_event(
    run_id: str,
    step: str,
    attempt: int,
    status: str,
    error_type: Optional[str] = None,
    duration_ms: Optional[int] = None,
    model: Optional[str] = None,
    token_usage: Optional[Dict[str, int]] = None,
) -> None:
    """
    Append a structured event to events.jsonl with thread safety.

    Args:
        run_id: Unique run identifier (e.g., "2025-11-09-a3f9d2")
        step: Agent/stage name (e.g., "topic_selection", "writer", "review")
        attempt: Attempt number for this step (1-indexed)
        status: "ok" or "error"
        error_type: Exception class name if status="error" (optional)
        duration_ms: Execution time in milliseconds (optional)
        model: LLM model name if applicable (e.g., "gemini-2.5-pro")
        token_usage: Dict with "prompt" and "completion" token counts (optional)

    Example:
        >>> log_event(
        ...     run_id="2025-11-09-a3f9d2",
        ...     step="writer",
        ...     attempt=1,
        ...     status="ok",
        ...     duration_ms=1234,
        ...     model="gemini-2.5-pro",
        ...     token_usage={"prompt": 450, "completion": 820}
        ... )
    """
    event = {
        "timestamp": datetime.now(timezone.utc).isoformat() + "Z",
        "run_id": run_id,
        "step": step,
        "attempt": attempt,
        "status": status,
    }

    # Add optional fields only if provided
    if error_type is not None:
        event["error_type"] = error_type

    if duration_ms is not None:
        event["duration_ms"] = duration_ms

    if model is not None:
        event["model"] = model

    if token_usage is not None:
        event["token_usage"] = token_usage

    # Thread-safe append to JSONL file
    with _log_lock:
        with open(EVENTS_LOG_PATH, "a", encoding="utf-8") as f:
            json.dump(event, f, ensure_ascii=False)
            f.write("\n")
            f.flush()


def init_events_log() -> None:
    """
    Create events.jsonl file if it doesn't exist.

    This is called once at application startup to ensure the log file exists.
    If the file already exists, this is a no-op.
    """
    if not EVENTS_LOG_PATH.exists():
        EVENTS_LOG_PATH.touch()


def read_events(run_id: Optional[str] = None) -> list[Dict[str, Any]]:
    """
    Read and parse all events from events.jsonl.

    Args:
        run_id: Optional run_id to filter events (returns all if None)

    Returns:
        List of event dictionaries in chronological order

    Example:
        >>> events = read_events(run_id="2025-11-09-a3f9d2")
        >>> print(f"Total events: {len(events)}")
    """
    if not EVENTS_LOG_PATH.exists():
        return []

    events = []
    with open(EVENTS_LOG_PATH, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                event = json.loads(line)
                if run_id is None or event.get("run_id") == run_id:
                    events.append(event)

    return events


def get_run_summary(run_id: str) -> Dict[str, Any]:
    """
    Generate summary statistics for a specific run.

    Args:
        run_id: Run identifier to summarize

    Returns:
        Dictionary with summary metrics:
        - total_steps: Number of agent invocations
        - total_attempts: Total retry attempts across all steps
        - errors: Count of failed steps
        - total_duration_ms: Sum of all step durations
        - total_tokens: Combined prompt + completion tokens

    Example:
        >>> summary = get_run_summary("2025-11-09-a3f9d2")
        >>> print(f"Run took {summary['total_duration_ms']}ms")
    """
    events = read_events(run_id=run_id)

    summary = {
        "run_id": run_id,
        "total_steps": len(set(e["step"] for e in events)),
        "total_attempts": len(events),
        "errors": sum(1 for e in events if e["status"] == "error"),
        "total_duration_ms": sum(e.get("duration_ms", 0) for e in events),
        "total_tokens": {
            "prompt": sum(e.get("token_usage", {}).get("prompt", 0) for e in events),
            "completion": sum(
                e.get("token_usage", {}).get("completion", 0) for e in events
            ),
        },
    }

    return summary
