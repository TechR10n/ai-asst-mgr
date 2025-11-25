"""Unit tests for GeminiCoach."""

import json
from pathlib import Path

import pytest

from ai_asst_mgr.coaches.base import Priority
from ai_asst_mgr.coaches.gemini import GeminiCoach


@pytest.fixture
def temp_gemini_dir(tmp_path: Path) -> Path:
    """Create a temporary Gemini config directory."""
    gemini_dir = tmp_path / ".gemini"
    gemini_dir.mkdir()
    return gemini_dir


@pytest.fixture
def coach_with_temp_dir(temp_gemini_dir: Path) -> GeminiCoach:
    """Create GeminiCoach with temporary directory."""
    return GeminiCoach(config_dir=temp_gemini_dir)


class TestGeminiCoachProperties:
    """Tests for GeminiCoach properties."""

    def test_vendor_id(self) -> None:
        """Test vendor_id returns 'gemini'."""
        coach = GeminiCoach()
        assert coach.vendor_id == "gemini"

    def test_vendor_name(self) -> None:
        """Test vendor_name returns 'Gemini CLI'."""
        coach = GeminiCoach()
        assert coach.vendor_name == "Gemini CLI"


class TestGeminiCoachAnalyze:
    """Tests for GeminiCoach.analyze method."""

    def test_analyze_returns_usage_report(self, coach_with_temp_dir: GeminiCoach) -> None:
        """Test analyze returns a UsageReport."""
        report = coach_with_temp_dir.analyze()

        assert report.vendor_id == "gemini"
        assert report.vendor_name == "Gemini CLI"
        assert report.generated_at is not None

    def test_analyze_with_period_days(self, coach_with_temp_dir: GeminiCoach) -> None:
        """Test analyze accepts period_days parameter."""
        report = coach_with_temp_dir.analyze(period_days=30)

        assert report.vendor_id == "gemini"


class TestGeminiCoachInsights:
    """Tests for GeminiCoach.get_insights method."""

    def test_gemini_md_insights(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test GEMINI.md size insight."""
        gemini_md = temp_gemini_dir / "GEMINI.md"
        gemini_md.write_text("# Project\n\n## Section 1\n\n## Section 2")

        insights = coach_with_temp_dir.get_insights()

        doc_insights = [i for i in insights if i.category == "documentation"]
        assert len(doc_insights) >= 1
        assert any(i.metric_name == "gemini_md_size" for i in doc_insights)

    def test_gemini_md_section_count(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test GEMINI.md section count insight."""
        gemini_md = temp_gemini_dir / "GEMINI.md"
        gemini_md.write_text("# Title\n\n## Section 1\n\n## Section 2\n\n### Subsection")

        insights = coach_with_temp_dir.get_insights()

        section_insights = [i for i in insights if i.metric_name == "section_count"]
        assert len(section_insights) >= 1
        assert section_insights[0].metric_value == 4  # 4 headers

    def test_mcp_server_insights(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test MCP server count insight."""
        mcp_dir = temp_gemini_dir / "mcp_servers"
        mcp_dir.mkdir()
        (mcp_dir / "server1.json").write_text('{"name": "server1"}')
        (mcp_dir / "server2.json").write_text('{"name": "server2"}')

        insights = coach_with_temp_dir.get_insights()

        mcp_insights = [i for i in insights if i.category == "mcp"]
        assert len(mcp_insights) >= 1
        assert any(i.metric_value == 2 for i in mcp_insights)

    def test_model_insight(self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path) -> None:
        """Test default model insight."""
        settings = {"model": "gemini-pro"}
        (temp_gemini_dir / "settings.json").write_text(json.dumps(settings))

        insights = coach_with_temp_dir.get_insights()

        model_insights = [i for i in insights if i.category == "model"]
        assert len(model_insights) >= 1
        assert any(i.metric_value == "gemini-pro" for i in model_insights)


class TestGeminiCoachRecommendations:
    """Tests for GeminiCoach.get_recommendations method."""

    def test_no_gemini_md_recommendation(self, coach_with_temp_dir: GeminiCoach) -> None:
        """Test recommendation when no GEMINI.md exists."""
        recommendations = coach_with_temp_dir.get_recommendations()

        doc_recs = [r for r in recommendations if "GEMINI.md" in r.title]
        assert len(doc_recs) >= 1
        assert any(r.priority == Priority.MEDIUM for r in doc_recs)

    def test_large_gemini_md_recommendation(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test recommendation when GEMINI.md is too large."""
        gemini_md = temp_gemini_dir / "GEMINI.md"
        # Create a large file (over 100KB)
        large_content = "# Large File\n" + "x" * 110000
        gemini_md.write_text(large_content)

        recommendations = coach_with_temp_dir.get_recommendations()

        large_recs = [r for r in recommendations if "split" in r.title.lower()]
        assert len(large_recs) >= 1
        assert any(r.priority == Priority.HIGH for r in large_recs)

    def test_no_mcp_servers_recommendation(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test recommendation when no MCP servers configured."""
        recommendations = coach_with_temp_dir.get_recommendations()

        mcp_recs = [r for r in recommendations if r.category == "mcp"]
        assert len(mcp_recs) >= 1

    def test_no_default_model_recommendation(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test recommendation when no default model set."""
        settings = {"version": "1.0.0"}
        (temp_gemini_dir / "settings.json").write_text(json.dumps(settings))

        recommendations = coach_with_temp_dir.get_recommendations()

        model_recs = [r for r in recommendations if r.category == "model"]
        assert len(model_recs) >= 1

    def test_recommendations_sorted_by_priority(self, coach_with_temp_dir: GeminiCoach) -> None:
        """Test recommendations are sorted by priority."""
        recommendations = coach_with_temp_dir.get_recommendations()

        if len(recommendations) >= 2:
            priority_order = {
                Priority.CRITICAL: 0,
                Priority.HIGH: 1,
                Priority.MEDIUM: 2,
                Priority.LOW: 3,
            }
            for i in range(len(recommendations) - 1):
                assert (
                    priority_order[recommendations[i].priority]
                    <= priority_order[recommendations[i + 1].priority]
                )


class TestGeminiCoachStats:
    """Tests for GeminiCoach.get_stats method."""

    def test_stats_include_config_exists(self, coach_with_temp_dir: GeminiCoach) -> None:
        """Test stats include config_exists."""
        stats = coach_with_temp_dir.get_stats()

        assert "config_exists" in stats
        assert stats["config_exists"] is True

    def test_stats_include_gemini_md_size(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test stats include GEMINI.md size."""
        gemini_md = temp_gemini_dir / "GEMINI.md"
        # Write substantial content to ensure size > 0
        content = "# Test content\n\n## Section\n" + "x" * 1000
        gemini_md.write_text(content)

        stats = coach_with_temp_dir.get_stats()

        assert "gemini_md_size_kb" in stats
        assert stats["gemini_md_size_kb"] >= 0.9  # At least ~1KB

    def test_stats_include_mcp_server_count(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test stats include MCP server count."""
        mcp_dir = temp_gemini_dir / "mcp_servers"
        mcp_dir.mkdir()
        (mcp_dir / "server1.json").write_text('{"name": "server1"}')

        stats = coach_with_temp_dir.get_stats()

        assert stats["mcp_server_count"] == 1

    def test_stats_include_default_model(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test stats include default model."""
        settings = {"model": "gemini-pro"}
        (temp_gemini_dir / "settings.json").write_text(json.dumps(settings))

        stats = coach_with_temp_dir.get_stats()

        assert stats["default_model"] == "gemini-pro"


class TestGeminiCoachExport:
    """Tests for GeminiCoach.export_report method."""

    def test_export_json(self, coach_with_temp_dir: GeminiCoach, tmp_path: Path) -> None:
        """Test export to JSON format."""
        coach_with_temp_dir.analyze()
        output_path = tmp_path / "report"

        result_path = coach_with_temp_dir.export_report(output_path, format="json")

        assert result_path.exists()
        assert result_path.suffix == ".json"

        with result_path.open() as f:
            data = json.load(f)
            assert data["vendor_id"] == "gemini"

    def test_export_markdown(self, coach_with_temp_dir: GeminiCoach, tmp_path: Path) -> None:
        """Test export to Markdown format."""
        coach_with_temp_dir.analyze()
        output_path = tmp_path / "report"

        result_path = coach_with_temp_dir.export_report(output_path, format="markdown")

        assert result_path.exists()
        assert result_path.suffix == ".md"

        content = result_path.read_text()
        assert "Gemini CLI" in content

    def test_export_invalid_format(self, coach_with_temp_dir: GeminiCoach, tmp_path: Path) -> None:
        """Test export with invalid format raises ValueError."""
        coach_with_temp_dir.analyze()
        output_path = tmp_path / "report"

        with pytest.raises(ValueError, match="Unsupported format"):
            coach_with_temp_dir.export_report(output_path, format="invalid")

    def test_export_markdown_no_insights(self, tmp_path: Path) -> None:
        """Test markdown export with no insights."""
        # Create coach with non-existent directory (no config at all)
        nonexistent_dir = tmp_path / ".gemini_nonexistent"
        coach = GeminiCoach(config_dir=nonexistent_dir)
        coach.analyze()
        output_path = tmp_path / "report"

        result_path = coach.export_report(output_path, format="markdown")

        content = result_path.read_text()
        assert "_No insights available._" in content
        assert "_No recommendations at this time._" in content


class TestGeminiCoachEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_json_in_settings(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test handling of invalid JSON in settings file."""
        (temp_gemini_dir / "settings.json").write_text("{ invalid json }")

        insights = coach_with_temp_dir.get_insights()
        assert isinstance(insights, list)

    def test_settings_json_not_a_dict(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test handling when settings.json is not a dict."""
        (temp_gemini_dir / "settings.json").write_text(json.dumps(["list", "not", "dict"]))

        insights = coach_with_temp_dir.get_insights()
        assert isinstance(insights, list)

    def test_too_many_mcp_servers_recommendation(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test recommendation when too many MCP servers."""
        mcp_dir = temp_gemini_dir / "mcp_servers"
        mcp_dir.mkdir()
        for i in range(20):
            (mcp_dir / f"server{i}.json").write_text(f'{{"name": "server{i}"}}')

        recommendations = coach_with_temp_dir.get_recommendations()

        mcp_recs = [r for r in recommendations if "Review MCP server" in r.title]
        assert len(mcp_recs) >= 1

    def test_no_model_recommendation(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test recommendation when no default model set."""
        settings = {"version": "1.0.0"}
        (temp_gemini_dir / "settings.json").write_text(json.dumps(settings))

        recommendations = coach_with_temp_dir.get_recommendations()

        model_recs = [r for r in recommendations if "default model" in r.title.lower()]
        assert len(model_recs) >= 1

    def test_context_window_recommendation(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test recommendation when context window not configured."""
        settings = {"model": "gemini-pro"}
        (temp_gemini_dir / "settings.json").write_text(json.dumps(settings))

        recommendations = coach_with_temp_dir.get_recommendations()

        context_recs = [r for r in recommendations if "context window" in r.title.lower()]
        assert len(context_recs) >= 1

    def test_gemini_md_with_zero_sections(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test GEMINI.md with no sections (no headers)."""
        gemini_md = temp_gemini_dir / "GEMINI.md"
        gemini_md.write_text("Just plain text without any headers")

        insights = coach_with_temp_dir.get_insights()

        section_insights = [i for i in insights if i.metric_name == "section_count"]
        # Should either have 0 or not include the insight
        assert all(i.metric_value == 0 for i in section_insights) or len(section_insights) == 0

    def test_stats_with_settings_api_key(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test stats include has_api_key."""
        settings = {"api_key": "test-key", "model": "gemini-pro"}
        (temp_gemini_dir / "settings.json").write_text(json.dumps(settings))

        stats = coach_with_temp_dir.get_stats()

        assert stats["has_api_key"] is True
        assert stats["default_model"] == "gemini-pro"

    def test_gemini_md_section_count_oserror(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test _count_md_sections handles file that doesn't exist."""
        # Call on non-existent file
        count = coach_with_temp_dir._count_md_sections(temp_gemini_dir / "nonexistent.md")
        assert count == 0

    def test_stats_include_gemini_md_sections(
        self, coach_with_temp_dir: GeminiCoach, temp_gemini_dir: Path
    ) -> None:
        """Test stats include gemini_md_sections."""
        gemini_md = temp_gemini_dir / "GEMINI.md"
        gemini_md.write_text("# Title\n\n## Section 1\n\n## Section 2")

        stats = coach_with_temp_dir.get_stats()

        assert "gemini_md_sections" in stats
        assert stats["gemini_md_sections"] == 3
