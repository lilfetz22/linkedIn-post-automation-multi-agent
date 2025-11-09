"""
Atomic file persistence utilities for artifact integrity.

All disk writes use the temp-file-then-rename pattern to prevent partial writes.
JSON artifacts are immediately verified after writing to catch corruption early.
"""
import json
import os
import tempfile
from pathlib import Path
from typing import Any

from core.errors import CorruptionError


def atomic_write_json(path: str | Path, obj: Any) -> None:
    """
    Write JSON to file atomically using temp file + rename pattern.
    
    This prevents partial writes if the process crashes mid-operation.
    
    Args:
        path: Target file path (absolute or relative)
        obj: Python object to serialize (must be JSON-serializable)
        
    Raises:
        OSError: If file operations fail
        TypeError: If obj is not JSON-serializable
        
    Example:
        >>> atomic_write_json("10_topic.json", {"topic": "Python asyncio"})
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    # Write to temporary file in same directory (ensures same filesystem)
    fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            json.dump(obj, f, indent=2, ensure_ascii=False)
            f.flush()
            os.fsync(f.fileno())  # Force write to disk
        
        # Atomic rename (overwrites destination on Windows/Unix)
        os.replace(temp_path, path)
    except Exception:
        # Clean up temp file on error
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def atomic_write_text(path: str | Path, text: str) -> None:
    """
    Write text to file atomically using temp file + rename pattern.
    
    Args:
        path: Target file path (absolute or relative)
        text: String content to write
        
    Raises:
        OSError: If file operations fail
        
    Example:
        >>> atomic_write_text("60_final_post.txt", "My LinkedIn post content...")
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    
    fd, temp_path = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp"
    )
    
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
            f.flush()
            os.fsync(f.fileno())
        
        os.replace(temp_path, path)
    except Exception:
        try:
            os.unlink(temp_path)
        except OSError:
            pass
        raise


def verify_json(path: str | Path) -> dict:
    """
    Re-open and parse JSON file to verify integrity.
    
    This must be called immediately after writing to detect corruption.
    
    Args:
        path: Path to JSON file to verify
        
    Returns:
        Parsed JSON object
        
    Raises:
        CorruptionError: If file cannot be read or parsed
        
    Example:
        >>> write_and_verify_json("10_topic.json", {"topic": "Redis"})
        >>> data = verify_json("10_topic.json")  # Redundant but safe
    """
    path = Path(path)
    
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError as e:
        raise CorruptionError(f"JSON file not found after write: {path}") from e
    except json.JSONDecodeError as e:
        raise CorruptionError(f"JSON file corrupted at {path}: {e}") from e
    except OSError as e:
        raise CorruptionError(f"Cannot read JSON file at {path}: {e}") from e


def write_and_verify_json(path: str | Path, obj: Any) -> dict:
    """
    Write JSON file atomically and immediately verify integrity.
    
    This is the recommended method for all agent artifact persistence.
    
    Args:
        path: Target file path
        obj: Python object to serialize
        
    Returns:
        The verified, parsed JSON object
        
    Raises:
        CorruptionError: If verification fails
        OSError: If write fails
        TypeError: If obj is not JSON-serializable
        
    Example:
        >>> result = write_and_verify_json("20_research.json", {"sources": [...]})
    """
    atomic_write_json(path, obj)
    return verify_json(path)


def count_chars(text: str) -> int:
    """
    Count characters in text for LinkedIn post validation.
    
    LinkedIn has a ~3000 character limit for posts.
    
    Args:
        text: Post content to count
        
    Returns:
        Number of characters (including whitespace)
        
    Example:
        >>> count_chars("Hello, world!")
        13
        >>> count_chars("Line 1\\nLine 2")
        13
    """
    return len(text)
