"""
Dry-run mode context for the multi-agent system.

Provides a thread-safe context for tracking whether the system is running
in dry-run mode, allowing components to skip LLM API calls while still
executing setup, validation, and cost estimation logic.
"""

import threading
from typing import Optional


class DryRunContext:
    """
    Thread-safe singleton context for dry-run mode.

    This class provides a global flag that can be checked throughout the
    pipeline to determine whether LLM calls should be made or mocked.
    """

    _instance: Optional["DryRunContext"] = None
    _lock = threading.Lock()

    def __new__(cls) -> "DryRunContext":
        """Ensure only one instance exists (singleton pattern)."""
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._enabled = False
        return cls._instance

    def __init__(self):
        """Initialize dry-run context (no-op after first initialization)."""
        # Initialization happens in __new__
        pass

    @property
    def enabled(self) -> bool:
        """
        Check if dry-run mode is enabled.

        Returns:
            bool: True if dry-run mode is active, False otherwise
        """
        return self._enabled

    def enable(self) -> None:
        """Enable dry-run mode for the current execution context."""
        with self._lock:
            self._enabled = True

    def disable(self) -> None:
        """Disable dry-run mode (return to normal operation)."""
        with self._lock:
            self._enabled = False

    def reset(self) -> None:
        """Reset dry-run mode to disabled (useful for testing)."""
        self.disable()


# Global singleton instance
_dry_run_context = DryRunContext()


def is_dry_run() -> bool:
    """
    Check if the system is running in dry-run mode.

    This is the primary interface for checking dry-run status throughout
    the codebase. Components should call this function before making LLM
    API calls.

    Returns:
        bool: True if dry-run mode is active, False otherwise

    Example:
        >>> from core.dry_run import is_dry_run
        >>> if is_dry_run():
        ...     return mock_response()
        ... else:
        ...     return actual_llm_call()
    """
    return _dry_run_context.enabled


def enable_dry_run() -> None:
    """
    Enable dry-run mode globally.

    After calling this function, all components that check `is_dry_run()`
    will receive True and should skip actual LLM API calls.

    Example:
        >>> from core.dry_run import enable_dry_run
        >>> enable_dry_run()
        >>> # Now all LLM calls will be mocked
    """
    _dry_run_context.enable()


def disable_dry_run() -> None:
    """
    Disable dry-run mode globally (return to normal operation).

    Example:
        >>> from core.dry_run import disable_dry_run
        >>> disable_dry_run()
        >>> # Now LLM calls will be made normally
    """
    _dry_run_context.disable()


def reset_dry_run() -> None:
    """
    Reset dry-run context to disabled state.

    Primarily used in testing to ensure clean state between tests.

    Example:
        >>> from core.dry_run import reset_dry_run
        >>> reset_dry_run()
    """
    _dry_run_context.reset()
