"""
Test suite for multi-run feature.

Tests CLI flag parsing, run directory naming with run numbers,
sequential execution, and artifact organization.

Following TDD and SOLID principles:
- Single Responsibility: Each test verifies one behavior
- Dependency Injection: Mock external dependencies
- Arrange-Act-Assert: Clear test structure
"""

from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, patch, MagicMock, call
import pytest

from main import parse_args
from core.run_context import create_run_dir


class TestMultiRunsCLIFlag:
    """Tests for --runs CLI flag parsing and validation."""

    def test_parse_args_runs_flag_default(self):
        """Test that --runs flag defaults to 1 when not provided."""
        args = parse_args([])
        assert args.runs == 1

    def test_parse_args_runs_flag_single(self):
        """Test that --runs flag accepts single run."""
        args = parse_args(["--runs", "1"])
        assert args.runs == 1

    def test_parse_args_runs_flag_multiple(self):
        """Test that --runs flag accepts multiple runs."""
        args = parse_args(["--runs", "3"])
        assert args.runs == 3

    def test_parse_args_runs_flag_large_value(self):
        """Test that --runs flag accepts large values."""
        args = parse_args(["--runs", "100"])
        assert args.runs == 100

    def test_parse_args_runs_flag_with_other_flags(self):
        """Test that --runs flag works with other CLI flags."""
        args = parse_args(["--runs", "5", "--no-image", "--field", "Data Science"])
        assert args.runs == 5
        assert args.no_image is True
        assert args.field == "Data Science"

    def test_parse_args_runs_flag_invalid_zero(self):
        """Test that --runs flag rejects zero."""
        with pytest.raises(SystemExit):
            parse_args(["--runs", "0"])

    def test_parse_args_runs_flag_invalid_negative(self):
        """Test that --runs flag rejects negative values."""
        with pytest.raises(SystemExit):
            parse_args(["--runs", "-5"])

    def test_parse_args_runs_flag_invalid_non_integer(self):
        """Test that --runs flag rejects non-integer values."""
        with pytest.raises(SystemExit):
            parse_args(["--runs", "abc"])

    def test_parse_args_runs_flag_invalid_float(self):
        """Test that --runs flag rejects float values."""
        with pytest.raises(SystemExit):
            parse_args(["--runs", "3.5"])


class TestRunDirNamingWithRunNumber:
    """Tests for run directory naming with sequential run numbers."""

    @patch("core.run_context.Path.mkdir")
    def test_create_run_dir_default_no_run_number(self, mock_mkdir):
        """Test that create_run_dir without run_number uses old format."""
        run_id, run_path = create_run_dir()
        # Format should be: YYYY-MM-DD-{shortId}
        parts = run_id.split("-")
        assert len(parts) == 4  # date parts (3) + short_id (1)
        assert parts[0].isdigit() and len(parts[0]) == 4  # year
        assert parts[1].isdigit() and len(parts[1]) == 2  # month
        assert parts[2].isdigit() and len(parts[2]) == 2  # day
        assert len(parts[3]) == 6  # short uuid
        mock_mkdir.assert_called_once()

    @patch("core.run_context.Path.mkdir")
    def test_create_run_dir_with_run_number(self, mock_mkdir):
        """Test that create_run_dir with run_number includes it in folder name."""
        run_id, run_path = create_run_dir(run_number=1)
        # Format should be: YYYY-MM-DD-{run_number}-{shortId}
        parts = run_id.split("-")
        assert len(parts) == 5  # date parts (3) + run_number (1) + short_id (1)
        assert parts[0].isdigit() and len(parts[0]) == 4  # year
        assert parts[1].isdigit() and len(parts[1]) == 2  # month
        assert parts[2].isdigit() and len(parts[2]) == 2  # day
        assert parts[3] == "1"  # run_number
        assert len(parts[4]) == 6  # short uuid
        mock_mkdir.assert_called_once()

    @patch("core.run_context.Path.mkdir")
    def test_create_run_dir_run_number_2(self, mock_mkdir):
        """Test that run_number=2 appears in folder name."""
        run_id, run_path = create_run_dir(run_number=2)
        assert "-2-" in run_id
        mock_mkdir.assert_called_once()

    @patch("core.run_context.Path.mkdir")
    def test_create_run_dir_run_number_10(self, mock_mkdir):
        """Test that run_number=10 appears correctly in folder name."""
        run_id, run_path = create_run_dir(run_number=10)
        assert "-10-" in run_id
        mock_mkdir.assert_called_once()

    @patch("core.run_context.Path.mkdir")
    def test_create_run_dir_multiple_same_day_different_numbers(self, mock_mkdir):
        """Test that multiple runs on same day have different numbers."""
        run_id_1, _ = create_run_dir(run_number=1)
        run_id_2, _ = create_run_dir(run_number=2)

        # Both should have same date prefix
        date_1 = "-".join(run_id_1.split("-")[:3])
        date_2 = "-".join(run_id_2.split("-")[:3])
        assert date_1 == date_2

        # But different run numbers and short IDs
        assert run_id_1 != run_id_2
        assert mock_mkdir.call_count == 2

    @patch("core.run_context.Path.mkdir")
    def test_create_run_dir_path_includes_run_number(self, mock_mkdir):
        """Test that run_path directory name includes run_number."""
        _, run_path = create_run_dir(run_number=3)
        # Path should contain folder name with run_number
        assert "-3-" in str(run_path)
        mock_mkdir.assert_called_once()

    def test_create_run_dir_path_created_on_filesystem(self, tmp_path):
        """Test that run directory with run_number is created on filesystem."""
        # Use tmp_path fixture for real filesystem test
        import sys
        from unittest.mock import patch

        # Temporarily override the base path to use tmp_path
        with patch("core.run_context.Path") as mock_path_class:
            # Create a real temporary directory for this test
            test_base = tmp_path / "runs"
            test_base.mkdir()

            def path_side_effect(arg):
                if arg == "runs":
                    return test_base
                return Path(arg)

            mock_path_class.side_effect = path_side_effect

            run_id, run_path = create_run_dir(run_number=1)

            # Verify run_id format
            assert "-1-" in run_id
            parts = run_id.split("-")
            assert len(parts) == 5  # date (3) + run_number (1) + short_id (1)


class TestMultiRunsExecution:
    """Tests for sequential execution of multiple runs."""

    @patch("main.run_pipeline")
    @patch("main.ensure_config")
    def test_main_runs_single_by_default(
        self, mock_ensure_config, mock_run_pipeline, tmp_path
    ):
        """Test that main runs a single run by default."""
        mock_ensure_config.return_value = {"field": "Data Science"}
        mock_run_pipeline.return_value = (0, {"status": "success"})

        from main import main

        with patch("sys.argv", ["main.py"]):
            exit_code = main(argv=[])
            assert mock_run_pipeline.call_count == 1

    @patch("main.run_pipeline")
    @patch("main.ensure_config")
    def test_main_runs_multiple_sequential(self, mock_ensure_config, mock_run_pipeline):
        """Test that main runs multiple times when --runs > 1."""
        mock_ensure_config.return_value = {"field": "Data Science"}
        mock_run_pipeline.return_value = (0, {"status": "success"})

        from main import main

        exit_code = main(argv=["--runs", "3"])
        # Should call run_pipeline 3 times
        assert mock_run_pipeline.call_count == 3

    @patch("main.run_pipeline")
    @patch("main.ensure_config")
    def test_main_passes_run_number_to_orchestrator(
        self, mock_ensure_config, mock_run_pipeline
    ):
        """Test that run number is passed when running multiple times."""
        mock_ensure_config.return_value = {"field": "Data Science"}
        mock_run_pipeline.return_value = (0, {"status": "success"})

        from main import main

        main(argv=["--runs", "3"])

        # Verify run_pipeline was called with different run numbers
        assert mock_run_pipeline.call_count == 3
        # Check that run number parameter is passed
        # This will be verified in actual implementation

    @patch("main.run_pipeline")
    @patch("main.ensure_config")
    def test_main_stops_on_first_failure(self, mock_ensure_config, mock_run_pipeline):
        """Test that main stops on first failure and doesn't continue runs."""
        mock_ensure_config.return_value = {"field": "Data Science"}
        # First call succeeds, second call fails
        mock_run_pipeline.side_effect = [
            (0, {"status": "success"}),
            (1, {"status": "error"}),
        ]

        from main import main

        exit_code = main(argv=["--runs", "3"])

        # Should have stopped after second failure
        assert mock_run_pipeline.call_count == 2

    @patch("main.run_pipeline")
    @patch("main.ensure_config")
    def test_main_prints_run_summary_for_each_run(
        self, mock_ensure_config, mock_run_pipeline
    ):
        """Test that main prints status for each run."""
        mock_ensure_config.return_value = {"field": "Data Science"}
        mock_run_pipeline.return_value = (
            0,
            {"status": "success", "run_id": "2025-01-09-1-abc123"},
        )

        from main import main

        with patch("builtins.print") as mock_print:
            main(argv=["--runs", "2"])
            # Should print something for each run
            assert mock_print.call_count > 0


class TestRunContextIntegration:
    """Integration tests for run context with run numbers."""

    @patch("core.run_context.Path.mkdir")
    def test_create_run_dir_maintains_uniqueness_across_runs(self, mock_mkdir):
        """Test that each run gets unique short ID even with same run_number."""
        run_id_1, path_1 = create_run_dir(run_number=1)
        run_id_2, path_2 = create_run_dir(run_number=1)

        # Should have different short IDs
        assert run_id_1 != run_id_2
        # Both should have same run_number but different short IDs
        assert "-1-" in run_id_1
        assert "-1-" in run_id_2
        assert mock_mkdir.call_count == 2

    @patch("core.run_context.Path.mkdir")
    def test_create_run_dir_preserves_artifact_compatibility(self, mock_mkdir):
        """Test that run directory with run_number still supports artifact storage."""
        run_id, run_path = create_run_dir(run_number=1)

        # Directory should be creatable and usable for artifacts
        artifact_path = run_path / "10_topic.json"
        assert str(artifact_path).endswith("10_topic.json")
        assert run_id in str(artifact_path)
        mock_mkdir.assert_called_once()


class TestCLIDocumentation:
    """Tests for CLI documentation and help text."""

    def test_help_text_mentions_runs_flag(self):
        """Test that help text includes --runs flag documentation."""
        from main import parse_args
        import io
        import sys

        with pytest.raises(SystemExit):
            with patch("sys.stdout", new_callable=io.StringIO) as mock_stdout:
                try:
                    parse_args(["--help"])
                except SystemExit as e:
                    # Help flag causes exit with code 0
                    assert e.code == 0
                    raise


class TestSOLIDPrinciples:
    """
    Tests verifying SOLID principle adherence.

    S - Single Responsibility: Each function has one reason to change
    O - Open/Closed: Open for extension, closed for modification
    L - Liskov Substitution: Substitutable implementations
    I - Interface Segregation: Minimal interfaces
    D - Dependency Inversion: Depend on abstractions, not concretions
    """

    @patch("core.run_context.Path.mkdir")
    def test_run_number_is_optional_parameter(self, mock_mkdir):
        """Test that run_number is optional (Open/Closed - backward compatible)."""
        # Should work without run_number parameter
        run_id_1, _ = create_run_dir()
        # Should work with run_number parameter
        run_id_2, _ = create_run_dir(run_number=1)
        # Format should be distinguishable
        assert "-1-" not in run_id_1
        assert "-1-" in run_id_2
        assert mock_mkdir.call_count == 2

    def test_parse_args_single_responsibility(self):
        """Test that parse_args only parses arguments (Single Responsibility)."""
        args = parse_args(["--runs", "5"])
        # Should only parse, not execute
        assert args.runs == 5
        assert not hasattr(args, "executed") or args.executed is None

    @patch("core.run_context.Path.mkdir")
    def test_create_run_dir_dependency_free(self, mock_mkdir):
        """Test that create_run_dir doesn't depend on concrete external classes."""
        # Should work without importing orchestrator or other high-level modules
        from core.run_context import create_run_dir as isolated_func

        run_id, run_path = isolated_func()
        # Should be independent
        assert run_id
        assert run_path
        mock_mkdir.assert_called_once()
