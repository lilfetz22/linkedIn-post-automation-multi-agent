"""
Standardized response envelope for all agent outputs.

All agents must return a consistent structure for orchestration and error handling.
"""

from dataclasses import dataclass, field, asdict
from typing import Any, Optional, Dict


@dataclass
class AgentResponse:
    """
    Standardized agent response envelope.

    Attributes:
        status: "ok" for success, "error" for failure
        data: Agent-specific output data (empty dict on error)
        error: Error details (None on success)
        metrics: Performance and usage metrics (optional)
    """

    status: str  # "ok" | "error"
    data: Dict[str, Any] = field(default_factory=dict)
    error: Optional[Dict[str, Any]] = None
    metrics: Optional[Dict[str, Any]] = None

    def to_dict(self) -> dict:
        """Convert response to dictionary, removing None values."""
        result = asdict(self)
        return {k: v for k, v in result.items() if v is not None}


def ok(data: dict, metrics: Optional[dict] = None) -> dict:
    """
    Create a success response envelope.

    Args:
        data: Agent output data (must be JSON-serializable)
        metrics: Optional performance metrics (duration, token usage, etc.)

    Returns:
        Standardized success response dictionary

    Example:
        >>> ok({"topic": "Python asyncio"}, {"duration_ms": 245})
        {"status": "ok", "data": {"topic": "Python asyncio"}, "metrics": {"duration_ms": 245}}
    """
    response = AgentResponse(status="ok", data=data, metrics=metrics)
    return response.to_dict()


def err(
    error_type: str, message: str, retryable: bool, metrics: Optional[dict] = None
) -> dict:
    """
    Create an error response envelope.

    Args:
        error_type: Exception class name (e.g., "ModelError", "ValidationError")
        message: Human-readable error description
        retryable: Whether the orchestrator should retry this operation
        metrics: Optional metrics captured before failure

    Returns:
        Standardized error response dictionary

    Example:
        >>> err("ModelError", "API timeout after 30s", retryable=True, metrics={"attempt": 2})
        {
            "status": "error",
            "data": {},
            "error": {
                "type": "ModelError",
                "message": "API timeout after 30s",
                "retryable": True
            },
            "metrics": {"attempt": 2}
        }
    """
    response = AgentResponse(
        status="error",
        data={},
        error={"type": error_type, "message": message, "retryable": retryable},
        metrics=metrics,
    )
    return response.to_dict()


def validate_envelope(envelope: dict) -> bool:
    """
    Validate that a dictionary conforms to the agent response schema.

    Args:
        envelope: Dictionary to validate

    Returns:
        True if valid, raises ValueError otherwise

    Raises:
        ValueError: If envelope structure is invalid
    """
    if not isinstance(envelope, dict):
        raise ValueError("Envelope must be a dictionary")

    if "status" not in envelope:
        raise ValueError("Envelope missing required 'status' field")

    if envelope["status"] not in ["ok", "error"]:
        raise ValueError(f"Invalid status: {envelope['status']}")

    if "data" not in envelope:
        raise ValueError("Envelope missing required 'data' field")

    if envelope["status"] == "error":
        if "error" not in envelope or envelope["error"] is None:
            raise ValueError("Error envelope must contain 'error' field")

        error = envelope["error"]
        required_error_fields = ["type", "message", "retryable"]
        for field_name in required_error_fields:
            if field_name not in error:
                raise ValueError(f"Error object missing required field: {field_name}")

    return True
