"""
Tests for atomic file persistence and artifact integrity verification.

This module provides comprehensive tests for:
- Atomic JSON write operations (temp file + rename pattern)
- Atomic text write operations
- JSON verification and corruption detection
- Artifact immutability and versioning
- Concurrent write safety
- Disk space and permission error handling
"""

import pytest
import json
import os
import tempfile
import threading
import time
from unittest.mock import patch

from core.persistence import (
    atomic_write_json,
    atomic_write_text,
    verify_json,
    write_and_verify_json,
    count_chars,
)
from core.errors import CorruptionError


# =============================================================================
# Test Suite: Atomic JSON Write Operations
# =============================================================================


class TestAtomicJsonWrite:
    """Test atomic JSON write operations using temp file + rename pattern."""

    def test_atomic_write_json_creates_temp_file(self, tmp_path):
        """Test atomic_write_json() creates a temp file during write."""
        target_path = tmp_path / "test.json"
        test_data = {"key": "value"}

        # Track temp files during write
        temp_files = []
        original_mkstemp = tempfile.mkstemp

        def tracking_mkstemp(*args, **kwargs):
            fd, path = original_mkstemp(*args, **kwargs)
            temp_files.append(path)
            return fd, path

        with patch("core.persistence.tempfile.mkstemp", side_effect=tracking_mkstemp):
            atomic_write_json(target_path, test_data)

        # Temp file should have been created (and cleaned up)
        assert len(temp_files) == 1
        # Temp file should have .tmp suffix
        assert temp_files[0].endswith(".tmp")

    def test_rename_operation_is_atomic(self, tmp_path):
        """Test rename operation is atomic (no partial writes visible)."""
        target_path = tmp_path / "atomic.json"
        test_data = {"large": "data" * 1000}

        atomic_write_json(target_path, test_data)

        # Final file should exist and be valid
        assert target_path.exists()
        with open(target_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        assert result == test_data

    def test_existing_file_not_corrupted_if_write_fails(self, tmp_path):
        """Test existing file is not corrupted if write fails mid-operation."""
        target_path = tmp_path / "existing.json"
        original_data = {"original": "data"}

        # Create original file
        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(original_data, f)

        # Simulate write failure during dump
        with patch("json.dump", side_effect=TypeError("Serialization failed")):
            with pytest.raises(TypeError):
                atomic_write_json(target_path, {"new": "data"})

        # Original file should be intact
        with open(target_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        assert result == original_data

    def test_directory_creation_if_parent_missing(self, tmp_path):
        """Test directory is created if parent path doesn't exist."""
        target_path = tmp_path / "nested" / "deep" / "file.json"
        test_data = {"nested": True}

        assert not target_path.parent.exists()

        atomic_write_json(target_path, test_data)

        assert target_path.exists()
        with open(target_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        assert result == test_data

    def test_json_serialization_preserves_types(self, tmp_path):
        """Test JSON serialization preserves data types correctly."""
        target_path = tmp_path / "types.json"
        test_data = {
            "string": "hello",
            "number": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "array": [1, 2, 3],
            "object": {"nested": "value"},
        }

        atomic_write_json(target_path, test_data)

        with open(target_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        assert result == test_data

    def test_json_unicode_handling(self, tmp_path):
        """Test JSON handles Unicode characters correctly."""
        target_path = tmp_path / "unicode.json"
        test_data = {
            "emoji": "🚀💻🔥",
            "chinese": "你好世界",
            "arabic": "مرحبا بالعالم",
        }

        atomic_write_json(target_path, test_data)

        with open(target_path, "r", encoding="utf-8") as f:
            result = json.load(f)
        assert result == test_data


# =============================================================================
# Test Suite: Atomic Text Write Operations
# =============================================================================


class TestAtomicTextWrite:
    """Test atomic text write operations."""

    def test_atomic_write_text_uses_temp_rename_pattern(self, tmp_path):
        """Test atomic_write_text() uses same temp-then-rename pattern."""
        target_path = tmp_path / "test.txt"
        test_content = "Hello, World!"

        temp_files = []
        original_mkstemp = tempfile.mkstemp

        def tracking_mkstemp(*args, **kwargs):
            fd, path = original_mkstemp(*args, **kwargs)
            temp_files.append(path)
            return fd, path

        with patch("core.persistence.tempfile.mkstemp", side_effect=tracking_mkstemp):
            atomic_write_text(target_path, test_content)

        assert len(temp_files) == 1
        assert temp_files[0].endswith(".tmp")

    def test_utf8_encoding_preserved(self, tmp_path):
        """Test UTF-8 encoding is preserved correctly."""
        target_path = tmp_path / "utf8.txt"
        test_content = "Unicode: 日本語 🎉 émojis"

        atomic_write_text(target_path, test_content)

        with open(target_path, "r", encoding="utf-8") as f:
            result = f.read()
        assert result == test_content

    def test_newline_handling(self, tmp_path):
        """Test newline handling in text files."""
        target_path = tmp_path / "newlines.txt"
        test_content = "Line 1\nLine 2\nLine 3"

        atomic_write_text(target_path, test_content)

        with open(target_path, "r", encoding="utf-8") as f:
            result = f.read()

        # Content should match (Python normalizes newlines on read)
        assert result == test_content or result == test_content.replace(
            "\n", os.linesep
        )

    def test_empty_string_write(self, tmp_path):
        """Test writing empty string creates empty file."""
        target_path = tmp_path / "empty.txt"

        atomic_write_text(target_path, "")

        assert target_path.exists()
        assert target_path.read_text() == ""

    def test_large_text_write(self, tmp_path):
        """Test writing large text content."""
        target_path = tmp_path / "large.txt"
        test_content = "A" * 1_000_000  # 1MB of text

        atomic_write_text(target_path, test_content)

        assert target_path.read_text() == test_content


# =============================================================================
# Test Suite: JSON Verification and Corruption Detection
# =============================================================================


class TestJsonVerification:
    """Test JSON verification and corruption detection."""

    def test_verify_json_parses_valid_json(self, tmp_path):
        """Test verify_json() successfully parses valid JSON artifacts."""
        target_path = tmp_path / "valid.json"
        test_data = {"status": "ok", "data": {"key": "value"}}

        with open(target_path, "w", encoding="utf-8") as f:
            json.dump(test_data, f)

        result = verify_json(target_path)
        assert result == test_data

    def test_verify_json_raises_corruption_for_malformed(self, tmp_path):
        """Test verify_json() raises CorruptionError for malformed JSON."""
        target_path = tmp_path / "malformed.json"

        # Write malformed JSON
        with open(target_path, "w", encoding="utf-8") as f:
            f.write('{"key": "value",}')  # Trailing comma is invalid

        with pytest.raises(CorruptionError) as exc_info:
            verify_json(target_path)

        assert "corrupted" in str(exc_info.value).lower()

    def test_write_and_verify_json_reparses_after_write(self, tmp_path):
        """Test write_and_verify_json() immediately re-parses after write."""
        target_path = tmp_path / "verified.json"
        test_data = {"verified": True}

        result = write_and_verify_json(target_path, test_data)

        assert result == test_data
        assert target_path.exists()

    def test_truncated_json_detected_as_corrupted(self, tmp_path):
        """Test truncated JSON file is detected as corrupted."""
        target_path = tmp_path / "truncated.json"

        # Write truncated JSON
        with open(target_path, "w", encoding="utf-8") as f:
            f.write('{"key": "value", "nested": {"deep":')  # Truncated

        with pytest.raises(CorruptionError):
            verify_json(target_path)

    def test_json_missing_quotes_rejected(self, tmp_path):
        """Test JSON with missing quotes is rejected."""
        target_path = tmp_path / "missing_quotes.json"

        with open(target_path, "w", encoding="utf-8") as f:
            f.write('{key: "value"}')  # Missing quotes around key

        with pytest.raises(CorruptionError):
            verify_json(target_path)

    def test_json_with_trailing_comma_rejected(self, tmp_path):
        """Test JSON with trailing commas is rejected."""
        target_path = tmp_path / "trailing_comma.json"

        with open(target_path, "w", encoding="utf-8") as f:
            f.write('{"key": "value",}')

        with pytest.raises(CorruptionError):
            verify_json(target_path)

    def test_verify_json_file_not_found(self, tmp_path):
        """Test verify_json raises CorruptionError for missing file."""
        target_path = tmp_path / "nonexistent.json"

        with pytest.raises(CorruptionError) as exc_info:
            verify_json(target_path)

        assert "not found" in str(exc_info.value).lower()

    def test_empty_file_detected_as_corrupted(self, tmp_path):
        """Test empty file is detected as corrupted JSON."""
        target_path = tmp_path / "empty.json"
        target_path.touch()

        with pytest.raises(CorruptionError):
            verify_json(target_path)


# =============================================================================
# Test Suite: Artifact Immutability and Versioning
# =============================================================================


class TestArtifactImmutability:
    """Test artifact immutability and versioning behavior."""

    def test_overwriting_artifact_replaces_content(self, tmp_path):
        """Test overwriting artifacts replaces content completely."""
        target_path = tmp_path / "artifact.json"

        # First write
        write_and_verify_json(target_path, {"version": 1})
        assert verify_json(target_path)["version"] == 1

        # Overwrite
        write_and_verify_json(target_path, {"version": 2})
        assert verify_json(target_path)["version"] == 2

    def test_character_count_loop_can_preserve_iterations(self, tmp_path):
        """Test character count loop iterations can be tracked."""
        run_dir = tmp_path / "run-test"
        run_dir.mkdir()

        iterations = []
        for i in range(1, 4):
            draft_path = run_dir / f"40_draft_v{i}.md"
            atomic_write_text(draft_path, f"Draft version {i}")
            iterations.append(draft_path)

        # All iterations preserved
        for i, path in enumerate(iterations, 1):
            assert path.exists()
            assert f"version {i}" in path.read_text()

    def test_run_directory_isolation(self, tmp_path):
        """Test run directory isolation (no cross-run contamination)."""
        run1 = tmp_path / "run-001"
        run2 = tmp_path / "run-002"
        run1.mkdir()
        run2.mkdir()

        # Write to run1
        write_and_verify_json(run1 / "10_topic.json", {"topic": "Run 1 Topic"})

        # Write to run2
        write_and_verify_json(run2 / "10_topic.json", {"topic": "Run 2 Topic"})

        # Verify isolation
        assert verify_json(run1 / "10_topic.json")["topic"] == "Run 1 Topic"
        assert verify_json(run2 / "10_topic.json")["topic"] == "Run 2 Topic"


# =============================================================================
# Test Suite: Concurrent Write Safety
# =============================================================================


class TestConcurrentWriteSafety:
    """Test concurrent write safety."""

    def test_multiple_agents_different_artifacts_simultaneously(self, tmp_path):
        """Test multiple agents writing to different artifacts simultaneously."""
        results = {}
        errors = []

        def write_artifact(name, data):
            try:
                path = tmp_path / f"{name}.json"
                write_and_verify_json(path, data)
                results[name] = verify_json(path)
            except Exception as e:
                errors.append((name, e))

        threads = [
            threading.Thread(target=write_artifact, args=("topic", {"topic": "AI"})),
            threading.Thread(target=write_artifact, args=("research", {"sources": []})),
            threading.Thread(target=write_artifact, args=("draft", {"text": "Hello"})),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0
        assert results["topic"]["topic"] == "AI"
        assert results["research"]["sources"] == []
        assert results["draft"]["text"] == "Hello"

    def test_concurrent_writes_to_same_file(self, tmp_path):
        """Test concurrent writes to the same file (last write wins)."""
        target_path = tmp_path / "shared.json"
        completed = []

        def write_with_delay(value, delay):
            time.sleep(delay)
            write_and_verify_json(target_path, {"value": value})
            completed.append(value)

        threads = [
            threading.Thread(target=write_with_delay, args=(1, 0)),
            threading.Thread(target=write_with_delay, args=(2, 0.01)),
            threading.Thread(target=write_with_delay, args=(3, 0.02)),
        ]

        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # File should contain valid JSON (last write wins)
        result = verify_json(target_path)
        assert "value" in result
        # The final value should be one of the written values
        assert result["value"] in [1, 2, 3]


# =============================================================================
# Test Suite: Disk Space and Permission Error Handling
# =============================================================================


class TestDiskErrorHandling:
    """Test disk space and permission error handling."""

    def test_graceful_failure_on_write_error(self, tmp_path):
        """Test graceful failure if write fails."""
        target_path = tmp_path / "write_fail.json"

        with patch("os.fdopen", side_effect=OSError("Disk full")):
            with pytest.raises(OSError):
                atomic_write_json(target_path, {"data": "test"})

    def test_temp_file_cleanup_after_failed_write(self, tmp_path):
        """Test cleanup of temp files after failed writes."""
        target_path = tmp_path / "cleanup_test.json"

        # Count temp files before
        initial_files = set(tmp_path.iterdir())

        # Simulate failure during json.dump
        with patch("json.dump", side_effect=RuntimeError("Serialization failed")):
            with pytest.raises(RuntimeError):
                atomic_write_json(target_path, {"data": "test"})

        # Temp file should be cleaned up
        final_files = set(tmp_path.iterdir())
        temp_files = [f for f in (final_files - initial_files) if ".tmp" in f.name]
        assert len(temp_files) == 0


# =============================================================================
# Test Suite: Character Counting Utility
# =============================================================================


class TestCharacterCounting:
    """Test character counting utility for LinkedIn post validation."""

    def test_count_chars_basic(self):
        """Test basic character counting."""
        assert count_chars("Hello") == 5
        assert count_chars("Hello, World!") == 13

    def test_count_chars_with_newlines(self):
        """Test character counting includes newlines."""
        text = "Line 1\nLine 2"
        assert count_chars(text) == 13  # 6 + 1 + 6

    def test_count_chars_with_spaces(self):
        """Test character counting includes spaces."""
        assert count_chars("Hello World") == 11
        assert count_chars("   ") == 3

    def test_count_chars_empty_string(self):
        """Test counting empty string returns 0."""
        assert count_chars("") == 0

    def test_count_chars_unicode(self):
        """Test counting Unicode characters."""
        # Each emoji is counted as one character in Python
        text = "🚀💻🔥"
        assert count_chars(text) == 3

    def test_count_chars_linkedin_limit(self):
        """Test character counting for LinkedIn limit validation."""
        under_limit = "A" * 2999
        at_limit = "A" * 3000
        over_limit = "A" * 3001

        assert count_chars(under_limit) < 3000
        assert count_chars(at_limit) == 3000
        assert count_chars(over_limit) > 3000
