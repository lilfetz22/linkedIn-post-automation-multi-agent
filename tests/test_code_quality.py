"""
Test suite for code quality standards.

This module tests that code quality standards are enforced,
particularly preventing bare except statements that could
cause silent failures.
"""

import subprocess
import sys
from pathlib import Path


def test_no_bare_except_statements():
    """
    Test that the codebase doesn't contain bare except statements.

    Bare except statements (except:) catch all exceptions including
    SystemExit and KeyboardInterrupt, which can mask bugs and make
    debugging extremely difficult. This test ensures E722 violations
    are caught.
    """
    # Get project root
    project_root = Path(__file__).parent.parent

    # Run flake8 on the main source directories
    result = subprocess.run(
        [sys.executable, "-m", "flake8", ".", "--select=E722"],
        cwd=project_root,
        capture_output=True,
        text=True,
        timeout=60
    )

    # If flake8 found violations, the test should fail
    assert result.returncode == 0, (
        f"Found bare except statements (E722 violations):\n{result.stdout}\n"
        f"Bare except statements should be replaced with specific exception types.\n"
        f"Example: Change 'except:' to 'except Exception:' or more specific exceptions."
    )


def test_flake8_installed():
    """
    Verify that flake8 is installed and available.
    """
    result = subprocess.run(
        [sys.executable, "-m", "flake8", "--version"],
        capture_output=True,
        text=True,
        timeout=10
    )

    assert result.returncode == 0, "flake8 is not installed or not available"
    # Check for version pattern (e.g., "7.3.0") instead of "flake8" string
    assert any(char.isdigit() for char in result.stdout), "flake8 version check failed"
    assert "mccabe" in result.stdout.lower() or "pycodestyle" in result.stdout.lower(), "flake8 version output unexpected"


def test_flake8_config_exists():
    """
    Verify that .flake8 configuration file exists.
    """
    project_root = Path(__file__).parent.parent
    config_file = project_root / ".flake8"

    assert config_file.exists(), ".flake8 configuration file not found"

    # Verify E722 is mentioned in the config
    content = config_file.read_text()
    assert "E722" in content, "E722 (bare except) check not enabled in .flake8"
