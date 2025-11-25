"""Unit tests for coach CLI command."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ai_asst_mgr.cli import app
from ai_asst_mgr.coaches.base import Insight, Priority, Recommendation

runner = CliRunner()


@pytest.fixture
def mock_coaches() -> MagicMock:
    """Create mock coaches for testing."""
    mock_coach = MagicMock()
    mock_coach.vendor_id = "claude"
    mock_coach.vendor_name = "Claude Code"
    mock_coach.get_insights.return_value = [
        Insight(
            category="agents",
            title="Agent Count",
            description="Found 5 agents",
            metric_name="agent_count",
            metric_value=5,
            metric_unit="agents",
        )
    ]
    mock_coach.get_recommendations.return_value = [
        Recommendation(
            priority=Priority.HIGH,
            category="agents",
            title="Create agents",
            description="No agents found",
            action="Create agents",
            expected_benefit="Better assistance",
        )
    ]
    mock_coach.get_stats.return_value = {
        "agent_count": 5,
        "config_exists": True,
    }
    mock_coach.analyze.return_value = MagicMock()
    mock_coach.export_report.return_value = Path("/tmp/report.json")
    return mock_coach


class TestCoachCommand:
    """Tests for coach CLI command."""

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    @patch("ai_asst_mgr.cli.GeminiCoach")
    @patch("ai_asst_mgr.cli.CodexCoach")
    def test_coach_all_vendors(
        self,
        mock_codex: MagicMock,
        mock_gemini: MagicMock,
        mock_claude: MagicMock,
        mock_coaches: MagicMock,
    ) -> None:
        """Test coach command analyzes all vendors by default."""
        mock_claude.return_value = mock_coaches
        mock_gemini.return_value = mock_coaches
        mock_codex.return_value = mock_coaches

        result = runner.invoke(app, ["coach"])

        assert result.exit_code == 0
        # Should show Claude Code, Gemini CLI, OpenAI Codex
        assert "Claude Code" in result.output or mock_claude.called

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_coach_specific_vendor(self, mock_claude: MagicMock, mock_coaches: MagicMock) -> None:
        """Test coach command with --vendor option."""
        mock_claude.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--vendor", "claude"])

        assert result.exit_code == 0
        mock_claude.assert_called_once()

    def test_coach_invalid_vendor(self) -> None:
        """Test coach command with invalid vendor."""
        result = runner.invoke(app, ["coach", "--vendor", "invalid"])

        assert result.exit_code == 1
        assert "Unknown vendor" in result.output

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    @patch("ai_asst_mgr.cli.GeminiCoach")
    @patch("ai_asst_mgr.cli.CodexCoach")
    def test_coach_compare_mode(
        self,
        mock_codex: MagicMock,
        mock_gemini: MagicMock,
        mock_claude: MagicMock,
        mock_coaches: MagicMock,
    ) -> None:
        """Test coach command with --compare flag."""
        mock_claude.return_value = mock_coaches
        mock_gemini.return_value = mock_coaches
        mock_codex.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--compare"])

        assert result.exit_code == 0
        assert "Cross-Vendor Comparison" in result.output

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_coach_export_json(self, mock_claude: MagicMock, mock_coaches: MagicMock) -> None:
        """Test coach command with --export json."""
        mock_claude.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--vendor", "claude", "--export", "json"])

        assert result.exit_code == 0
        mock_coaches.export_report.assert_called()

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_coach_export_markdown(self, mock_claude: MagicMock, mock_coaches: MagicMock) -> None:
        """Test coach command with --export markdown."""
        mock_claude.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--vendor", "claude", "--export", "markdown"])

        assert result.exit_code == 0
        mock_coaches.export_report.assert_called()

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_coach_export_with_output_path(
        self, mock_claude: MagicMock, mock_coaches: MagicMock, tmp_path: Path
    ) -> None:
        """Test coach command with --export and --output."""
        mock_claude.return_value = mock_coaches
        output_path = tmp_path / "my_report"

        result = runner.invoke(
            app,
            [
                "coach",
                "--vendor",
                "claude",
                "--export",
                "json",
                "--output",
                str(output_path),
            ],
        )

        assert result.exit_code == 0
        mock_coaches.export_report.assert_called_with(output_path, format="json")

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_coach_weekly_report(self, mock_claude: MagicMock, mock_coaches: MagicMock) -> None:
        """Test coach command with --report weekly."""
        mock_claude.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--vendor", "claude", "--report", "weekly"])

        assert result.exit_code == 0
        # Should call analyze with default 7 days
        mock_coaches.analyze.assert_called_with(period_days=7)

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_coach_monthly_report(self, mock_claude: MagicMock, mock_coaches: MagicMock) -> None:
        """Test coach command with --report monthly."""
        mock_claude.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--vendor", "claude", "--report", "monthly"])

        assert result.exit_code == 0
        mock_coaches.analyze.assert_called_with(period_days=30)


class TestCoachHelpers:
    """Tests for coach helper functions."""

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_display_insights_shows_table(
        self, mock_claude: MagicMock, mock_coaches: MagicMock
    ) -> None:
        """Test insights are displayed in a table."""
        mock_claude.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--vendor", "claude"])

        assert result.exit_code == 0
        assert "Insights" in result.output

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_display_recommendations_shows_panels(
        self, mock_claude: MagicMock, mock_coaches: MagicMock
    ) -> None:
        """Test recommendations are displayed in panels."""
        mock_claude.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--vendor", "claude"])

        assert result.exit_code == 0
        assert "Recommendations" in result.output

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_display_stats_shows_grid(
        self, mock_claude: MagicMock, mock_coaches: MagicMock
    ) -> None:
        """Test stats are displayed."""
        mock_claude.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--vendor", "claude"])

        assert result.exit_code == 0
        assert "Statistics" in result.output

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_no_recommendations_shows_good_message(
        self, mock_claude: MagicMock, mock_coaches: MagicMock
    ) -> None:
        """Test message when no recommendations."""
        mock_coaches.get_recommendations.return_value = []
        mock_claude.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--vendor", "claude"])

        assert result.exit_code == 0
        assert "looks good" in result.output

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_no_insights_shows_message(
        self, mock_claude: MagicMock, mock_coaches: MagicMock
    ) -> None:
        """Test message when no insights."""
        mock_coaches.get_insights.return_value = []
        mock_claude.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--vendor", "claude"])

        assert result.exit_code == 0
        assert "No insights" in result.output


class TestCoachExportErrors:
    """Tests for coach export error handling."""

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_export_error_shows_message(
        self, mock_claude: MagicMock, mock_coaches: MagicMock
    ) -> None:
        """Test export error displays message."""
        mock_coaches.export_report.side_effect = RuntimeError("Export failed")
        mock_claude.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--vendor", "claude", "--export", "json"])

        assert result.exit_code == 0  # Command succeeds, export fails gracefully
        assert "Export failed" in result.output

    @patch("ai_asst_mgr.cli.ClaudeCoach")
    def test_export_value_error_shows_message(
        self, mock_claude: MagicMock, mock_coaches: MagicMock
    ) -> None:
        """Test export value error displays message."""
        mock_coaches.export_report.side_effect = ValueError("Invalid format")
        mock_claude.return_value = mock_coaches

        result = runner.invoke(app, ["coach", "--vendor", "claude", "--export", "json"])

        assert result.exit_code == 0
        assert "Export failed" in result.output
