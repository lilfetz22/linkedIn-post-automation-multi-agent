"""
Run directory management for artifact organization.

Each execution creates a unique timestamped directory under runs/
to store all inputs, outputs, and intermediate artifacts.
"""
import uuid
from datetime import datetime
from pathlib import Path
from typing import Tuple


def create_run_dir(base: str = "runs") -> Tuple[str, Path]:
    """
    Create a unique run directory with timestamp and random ID.
    
    Directory format: {YYYY-MM-DD}-{shortId}/
    Example: 2025-11-09-a3f9d2/
    
    Args:
        base: Base directory for all runs (default: "runs")
        
    Returns:
        Tuple of (run_id, run_path)
        - run_id: Unique identifier like "2025-11-09-a3f9d2"
        - run_path: Absolute Path object to the created directory
        
    Example:
        >>> run_id, run_path = create_run_dir()
        >>> print(run_id)
        "2025-11-09-a3f9d2"
        >>> print(run_path)
        Path("C:/Users/.../runs/2025-11-09-a3f9d2")
    """
    # Generate unique run ID
    date_prefix = datetime.now().strftime("%Y-%m-%d")
    short_id = str(uuid.uuid4())[:6]
    run_id = f"{date_prefix}-{short_id}"
    
    # Create directory
    base_path = Path(base)
    run_path = base_path / run_id
    run_path.mkdir(parents=True, exist_ok=True)
    
    return run_id, run_path.resolve()


def get_artifact_path(run_path: Path, step_code: str, extension: str = "json") -> Path:
    """
    Build standardized artifact path within a run directory.
    
    Artifact naming convention:
    - 00_config.json
    - 10_topic.json
    - 20_research.json
    - 25_structured_prompt.json
    - 30_strategy.json
    - 40_draft.md
    - 50_review.json
    - 60_final_post.txt
    - 70_image_prompt.txt
    - 80_image.png
    
    Args:
        run_path: Path to run directory
        step_code: Two-digit step code + name (e.g., "10_topic", "40_draft")
        extension: File extension without dot (default: "json")
        
    Returns:
        Full path to artifact file
        
    Example:
        >>> run_path = Path("runs/2025-11-09-a3f9d2")
        >>> path = get_artifact_path(run_path, "10_topic")
        >>> print(path)
        Path("runs/2025-11-09-a3f9d2/10_topic.json")
    """
    return run_path / f"{step_code}.{extension}"


def get_subdirectory(run_path: Path, subdir: str) -> Path:
    """
    Get path to subdirectory within run (e.g., prompts/, completions/).
    
    Creates the subdirectory if it doesn't exist.
    
    Args:
        run_path: Path to run directory
        subdir: Subdirectory name (e.g., "prompts", "completions")
        
    Returns:
        Path to subdirectory
        
    Example:
        >>> run_path = Path("runs/2025-11-09-a3f9d2")
        >>> prompts_dir = get_subdirectory(run_path, "prompts")
        >>> print(prompts_dir)
        Path("runs/2025-11-09-a3f9d2/prompts")
    """
    subdir_path = run_path / subdir
    subdir_path.mkdir(parents=True, exist_ok=True)
    return subdir_path


def list_runs(base: str = "runs") -> list[str]:
    """
    List all run IDs in chronological order (newest first).
    
    Args:
        base: Base directory containing runs (default: "runs")
        
    Returns:
        List of run IDs sorted by timestamp (descending)
        
    Example:
        >>> runs = list_runs()
        >>> print(runs[:3])
        ["2025-11-09-a3f9d2", "2025-11-08-b4e1f3", "2025-11-07-c5d2a1"]
    """
    base_path = Path(base)
    if not base_path.exists():
        return []
    
    # Get all subdirectories that match the run ID pattern
    runs = []
    for item in base_path.iterdir():
        if item.is_dir() and "-" in item.name:
            runs.append(item.name)
    
    # Sort by name (which is timestamp-prefixed) in reverse order
    runs.sort(reverse=True)
    return runs


def get_run_path(run_id: str, base: str = "runs") -> Path:
    """
    Get the path to a specific run directory.
    
    Args:
        run_id: Run identifier (e.g., "2025-11-09-a3f9d2")
        base: Base directory containing runs (default: "runs")
        
    Returns:
        Path to run directory
        
    Example:
        >>> path = get_run_path("2025-11-09-a3f9d2")
        >>> print(path)
        Path("runs/2025-11-09-a3f9d2")
    """
    return Path(base) / run_id
