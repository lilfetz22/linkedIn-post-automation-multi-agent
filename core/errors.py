"""
Custom exception classes for the LinkedIn post automation system.

This module defines the error hierarchy used throughout the multi-agent pipeline.
Each error type has specific semantics for retry logic and error handling.
"""


class BaseAgentError(Exception):
    """Base exception class for all agent-related errors."""
    
    def __init__(self, message: str, retryable: bool = False):
        """
        Initialize the base agent error.
        
        Args:
            message: Human-readable error description
            retryable: Whether this error should trigger a retry attempt
        """
        super().__init__(message)
        self.message = message
        self.retryable = retryable


class ValidationError(BaseAgentError):
    """
    Raised when agent output fails validation checks.
    
    Examples:
    - Character count exceeds limit (>=3000 chars)
    - Missing required sections in structured output
    - Invalid JSON schema
    
    This error is NOT retryable as it indicates a logic issue.
    """
    
    def __init__(self, message: str):
        super().__init__(message, retryable=False)


class DataNotFoundError(BaseAgentError):
    """
    Raised when expected data cannot be retrieved.
    
    Examples:
    - Research agent finds no sources for topic
    - Database query returns empty results
    - RAG query yields no relevant documents
    
    This error triggers fallback strategies (e.g., topic pivot).
    """
    
    def __init__(self, message: str):
        super().__init__(message, retryable=False)


class ModelError(BaseAgentError):
    """
    Raised when LLM API calls fail.
    
    Examples:
    - API timeout or connection error
    - Rate limiting (429 response)
    - Model service unavailable (503)
    - Invalid API key
    
    This error IS retryable with exponential backoff.
    """
    
    def __init__(self, message: str):
        super().__init__(message, retryable=True)


class CorruptionError(BaseAgentError):
    """
    Raised when artifact persistence or parsing fails.
    
    Examples:
    - Written JSON file cannot be re-parsed
    - Disk write operation fails mid-stream
    - File system corruption detected
    
    This error is NOT retryable and triggers immediate run abort.
    """
    
    def __init__(self, message: str):
        super().__init__(message, retryable=False)
