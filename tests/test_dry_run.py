"""
Tests for dry-run mode functionality.

Validates that dry-run mode:
- Parses --dry-run argument correctly
- Creates run directory and config
- Estimates costs without making LLM calls
- Generates comprehensive summary report
- Does not make actual API calls to Gemini
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from main import parse_args, run_pipeline
from orchestrator import Orchestrator
from core.dry_run import enable_dry_run, disable_dry_run, is_dry_run, reset_dry_run
from core.llm_clients import GeminiTextClient, GeminiImageClient


class TestDryRunArgParsing:
    """Test command-line argument parsing for dry-run mode."""

    def test_dry_run_flag_parsed(self):
        """Test that --dry-run flag is parsed correctly."""
        args = parse_args(["--dry-run"])
        assert args.dry_run is True

    def test_dry_run_with_field(self):
        """Test --dry-run combined with --field argument."""
        args = parse_args(
            ["--dry-run", "--field", "Data Science (Optimizations & Time-Series Analysis)"]
        )
        assert args.dry_run is True
        assert args.field == "Data Science (Optimizations & Time-Series Analysis)"

    def test_default_no_dry_run(self):
        """Test that dry_run defaults to False when not specified."""
        args = parse_args([])
        assert args.dry_run is False

    def test_dry_run_with_run_flag(self):
        """Test --dry-run can be combined with --run flag."""
        args = parse_args(["--dry-run", "--run"])
        assert args.dry_run is True
        assert args.run is True


class TestDryRunContext:
    """Test dry-run context management."""

    def setup_method(self):
        """Reset dry-run state before each test."""
        reset_dry_run()

    def teardown_method(self):
        """Reset dry-run state after each test."""
        reset_dry_run()

    def test_enable_dry_run(self):
        """Test enabling dry-run mode."""
        assert is_dry_run() is False
        enable_dry_run()
        assert is_dry_run() is True

    def test_disable_dry_run(self):
        """Test disabling dry-run mode."""
        enable_dry_run()
        assert is_dry_run() is True
        disable_dry_run()
        assert is_dry_run() is False

    def test_reset_dry_run(self):
        """Test resetting dry-run mode."""
        enable_dry_run()
        assert is_dry_run() is True
        reset_dry_run()
        assert is_dry_run() is False


class TestLLMClientDryRun:
    """Test that LLM clients respect dry-run mode."""

    def setup_method(self):
        """Reset dry-run state before each test."""
        reset_dry_run()

    def teardown_method(self):
        """Reset dry-run state after each test."""
        reset_dry_run()

    def test_text_client_dry_run_enabled(self):
        """Test that text generation returns mock response in dry-run mode."""
        enable_dry_run()
        client = GeminiTextClient()

        result = client.generate_text(
            prompt="Test prompt for dry-run",
            temperature=0.7,
        )

        assert result["dry_run"] is True
        assert "[DRY RUN]" in result["text"]
        assert "prompt_tokens" in result["token_usage"]
        assert "completion_tokens" in result["token_usage"]
        assert result["model"] == "gemini-2.5-pro"

    @patch("google.generativeai.GenerativeModel")
    def test_text_client_normal_mode(self, mock_model_class):
        """Test that text generation makes real API call when dry-run is disabled."""
        disable_dry_run()
        
        # Mock the API response
        mock_response = MagicMock()
        mock_response.text = "Real API response"
        mock_response.usage_metadata = MagicMock()
        mock_response.usage_metadata.prompt_token_count = 10
        mock_response.usage_metadata.candidates_token_count = 20
        
        mock_model = MagicMock()
        mock_model.generate_content.return_value = mock_response
        mock_model_class.return_value = mock_model
        
        client = GeminiTextClient()
        result = client.generate_text(prompt="Test prompt")

        # Should not have dry_run flag
        assert "dry_run" not in result or result.get("dry_run") is False

    def test_image_client_dry_run_enabled(self, tmp_path):
        """Test that image generation returns mock response in dry-run mode."""
        enable_dry_run()
        client = GeminiImageClient()

        output_path = tmp_path / "test_image.png"
        result = client.generate_image(
            prompt="Test image prompt",
            output_path=str(output_path),
        )

        assert result["dry_run"] is True
        assert output_path.exists()
        # Check placeholder content
        content = output_path.read_text()
        assert "[DRY RUN]" in content


class TestOrchestratorDryRun:
    """Test orchestrator dry-run mode functionality."""

    def setup_method(self):
        """Reset dry-run state before each test."""
        reset_dry_run()

    def teardown_method(self):
        """Reset dry-run state after each test."""
        reset_dry_run()

    def test_orchestrator_accepts_dry_run_param(self):
        """Test that Orchestrator accepts dry_run parameter."""
        config = {"field": "Data Science (Optimizations & Time-Series Analysis)"}
        orchestrator = Orchestrator(config, dry_run=True)

        assert orchestrator.dry_run is True
        assert orchestrator.metrics["dry_run"] is True

    def test_orchestrator_enables_global_dry_run(self):
        """Test that Orchestrator enables global dry-run context."""
        config = {"field": "Data Science (Optimizations & Time-Series Analysis)"}
        assert is_dry_run() is False
        
        Orchestrator(config, dry_run=True)
        
        assert is_dry_run() is True

    def test_dry_run_creates_run_directory(self, tmp_path, monkeypatch):
        """Test that dry-run mode still creates run directory."""
        monkeypatch.chdir(tmp_path)
        config = {"field": "Data Science (Optimizations & Time-Series Analysis)"}
        orchestrator = Orchestrator(config, dry_run=True)
        
        result = orchestrator.run()

        assert result["status"] == "success"
        assert result["mode"] == "dry_run"
        assert "run_id" in result
        assert "run_path" in result
        
        # Verify run directory exists
        run_path = Path(result["run_path"])
        assert run_path.exists()

    def test_dry_run_creates_config_file(self, tmp_path, monkeypatch):
        """Test that dry-run mode creates config file."""
        monkeypatch.chdir(tmp_path)
        config = {"field": "Data Science (Optimizations & Time-Series Analysis)"}
        orchestrator = Orchestrator(config, dry_run=True)
        
        result = orchestrator.run()

        # Verify config file exists
        run_path = Path(result["run_path"])
        config_file = run_path / "00_config.json"
        assert config_file.exists()
        
        # Verify config content
        saved_config = json.loads(config_file.read_text())
        assert saved_config == config

    def test_dry_run_generates_summary_file(self, tmp_path, monkeypatch):
        """Test that dry-run mode generates summary file."""
        monkeypatch.chdir(tmp_path)
        config = {"field": "Data Science (Optimizations & Time-Series Analysis)"}
        orchestrator = Orchestrator(config, dry_run=True)
        
        result = orchestrator.run()

        # Verify summary file exists
        run_path = Path(result["run_path"])
        summary_file = run_path / "dry_run_summary.json"
        assert summary_file.exists()
        
        # Verify summary content
        summary = json.loads(summary_file.read_text())
        assert summary["mode"] == "dry_run"
        assert "estimated_costs" in summary
        assert "total_estimated_cost_usd" in summary
        assert "next_steps" in summary

    def test_dry_run_estimates_costs(self, tmp_path, monkeypatch):
        """Test that dry-run mode provides cost estimates."""
        monkeypatch.chdir(tmp_path)
        config = {"field": "Data Science (Optimizations & Time-Series Analysis)"}
        orchestrator = Orchestrator(config, dry_run=True)
        
        result = orchestrator.run()

        assert "estimated_cost_usd" in result
        assert result["estimated_cost_usd"] > 0
        assert result["estimated_cost_usd"] < 1.0  # Should be reasonable estimate
        
        # Check detailed estimates
        summary = result["dry_run_summary"]
        assert "estimated_costs" in summary
        assert "topic_agent" in summary["estimated_costs"]
        assert "writer_agent" in summary["estimated_costs"]
        assert "image_generator_agent" in summary["estimated_costs"]

    def test_dry_run_includes_next_steps(self, tmp_path, monkeypatch):
        """Test that dry-run summary includes next steps information."""
        monkeypatch.chdir(tmp_path)
        config = {"field": "Data Science (Optimizations & Time-Series Analysis)"}
        orchestrator = Orchestrator(config, dry_run=True)
        
        result = orchestrator.run()

        summary = result["dry_run_summary"]
        assert "next_steps" in summary
        assert "first_llm_call" in summary["next_steps"]
        assert "model" in summary["next_steps"]
        assert summary["next_steps"]["model"] == "gemini-2.5-pro"


class TestDryRunIntegration:
    """Integration tests for complete dry-run workflow."""

    def setup_method(self):
        """Reset dry-run state before each test."""
        reset_dry_run()

    def teardown_method(self):
        """Reset dry-run state after each test."""
        reset_dry_run()

    @pytest.mark.integration
    def test_full_dry_run_workflow(self, tmp_path, monkeypatch):
        """Test complete dry-run workflow from main entry point."""
        monkeypatch.chdir(tmp_path)
        
        # Create config.json first
        config_file = tmp_path / "config.json"
        config_file.write_text(
            json.dumps({"field": "Data Science (Optimizations & Time-Series Analysis)"})
        )
        
        # Run pipeline in dry-run mode
        exit_code, result = run_pipeline(
            root=tmp_path,
            non_interactive_field="Data Science (Optimizations & Time-Series Analysis)",
            dry_run=True,
        )

        assert exit_code == 0
        assert result["status"] == "success"
        assert result["mode"] == "dry_run"
        assert "estimated_cost_usd" in result

    @pytest.mark.integration
    def test_dry_run_no_api_calls_made(self, tmp_path, monkeypatch):
        """Test that dry-run mode makes no actual API calls."""
        monkeypatch.chdir(tmp_path)
        
        with patch("google.generativeai.GenerativeModel") as mock_model:
            config = {"field": "Data Science (Optimizations & Time-Series Analysis)"}
            orchestrator = Orchestrator(config, dry_run=True)
            result = orchestrator.run()

            # Verify no API calls were made
            assert mock_model.return_value.generate_content.call_count == 0
            assert result["status"] == "success"
            assert result["mode"] == "dry_run"
