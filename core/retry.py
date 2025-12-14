"""
Retry logic with exponential backoff and circuit breaker pattern.

Handles transient failures (e.g., LLM API timeouts) with automatic retries
while preventing cascading failures through circuit breaker protection.
"""

import time
from typing import Callable, TypeVar
from dataclasses import dataclass

from core.errors import BaseAgentError

T = TypeVar("T")


@dataclass
class CircuitBreaker:
    """
    Circuit breaker state to prevent cascading failures.

    Tracks consecutive LLM failures across all agents in a run.
    After 3 consecutive failures, the run is aborted immediately.
    """

    consecutive_failures: int = 0
    max_failures: int = 3

    def record_failure(self) -> None:
        """Increment failure counter. Raises exception if threshold exceeded."""
        self.consecutive_failures += 1
        if self.consecutive_failures >= self.max_failures:
            raise CircuitBreakerTrippedError(
                f"Circuit breaker tripped: {self.consecutive_failures} consecutive LLM failures"
            )

    def record_success(self) -> None:
        """Reset failure counter after successful operation."""
        self.consecutive_failures = 0

    def is_tripped(self) -> bool:
        """Check if circuit breaker has tripped."""
        return self.consecutive_failures >= self.max_failures


class CircuitBreakerTrippedError(Exception):
    """Raised when circuit breaker threshold is exceeded."""

    pass


def _is_quota_or_rate_limit_error(message: str) -> bool:
    """Detect quota or rate limit exhaustion markers in an error message."""

    lowered = message.lower()
    keywords = [
        "resource_exhausted",
        "quota exceeded",
        "exceeded your current quota",
        "rate limit",
    ]

    return any(keyword in lowered for keyword in keywords)


def exponential_backoff(attempt: int, base_seconds: float = 1.0) -> float:
    """
    Calculate exponential backoff delay.

    Formula: base_seconds * 2^(attempt - 1)

    Args:
        attempt: Current attempt number (1-indexed)
        base_seconds: Base delay in seconds (default: 1.0)

    Returns:
        Delay in seconds

    Example:
        >>> exponential_backoff(1)  # First retry
        1.0
        >>> exponential_backoff(2)  # Second retry
        2.0
        >>> exponential_backoff(3)  # Third retry
        4.0
    """
    return base_seconds * (2 ** (attempt - 1))


def execute_with_retries(
    func: Callable[[], T],
    max_attempts: int = 3,
    circuit_breaker: CircuitBreaker | None = None,
    base_delay: float = 1.0,
) -> T:
    """
    Execute function with automatic retries for retryable errors.

    Retries are triggered for exceptions marked as retryable (e.g., ModelError).
    Non-retryable errors (ValidationError, CorruptionError) abort immediately.

    Args:
        func: Function to execute (must take no arguments)
        max_attempts: Maximum number of attempts (default: 3)
        circuit_breaker: Optional circuit breaker instance for failure tracking
        base_delay: Base delay for exponential backoff in seconds (default: 1.0)

    Returns:
        Result of func() if successful

    Raises:
        BaseAgentError: If all retries exhausted or non-retryable error occurs
        CircuitBreakerTrippedError: If circuit breaker trips

    Example:
        >>> def unstable_api_call():
        ...     # May raise ModelError
        ...     return gemini.generate_text("...")
        >>>
        >>> breaker = CircuitBreaker()
        >>> result = execute_with_retries(unstable_api_call, circuit_breaker=breaker)
    """
    last_error: Exception | None = None

    for attempt in range(1, max_attempts + 1):
        try:
            result = func()

            # Success - reset circuit breaker
            if circuit_breaker:
                circuit_breaker.record_success()

            return result

        except BaseAgentError as e:
            last_error = e

            if e.retryable and _is_quota_or_rate_limit_error(str(e)):
                # Quota/rate limit exhaustion is not recoverable within a run
                e.retryable = False
                e.message = (
                    f"{str(e)} | Resolve quota/billing or wait for limits to reset."
                )
                raise

            # Non-retryable errors abort immediately
            if not e.retryable:
                raise

            # Record failure in circuit breaker
            if circuit_breaker:
                circuit_breaker.record_failure()

            # Last attempt - don't sleep
            if attempt == max_attempts:
                break

            # Exponential backoff
            delay = exponential_backoff(attempt, base_delay)
            time.sleep(delay)

        except Exception:
            # Unexpected errors are not retried
            if circuit_breaker:
                circuit_breaker.record_failure()
            raise

    # All retries exhausted
    if last_error:
        raise last_error
    else:
        raise RuntimeError("Retry logic failed without capturing error")


def create_circuit_breaker() -> CircuitBreaker:
    """
    Factory function to create a new circuit breaker instance.

    Returns:
        New CircuitBreaker with default settings (3 failures max)

    Example:
        >>> breaker = create_circuit_breaker()
        >>> # Pass to orchestrator for entire run
    """
    return CircuitBreaker()
