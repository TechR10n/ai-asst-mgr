"""Unit tests for CodexCoach."""

import json
from pathlib import Path

import pytest
import toml

from ai_asst_mgr.coaches.base import Priority
from ai_asst_mgr.coaches.openai import CodexCoach


@pytest.fixture
def temp_codex_dir(tmp_path: Path) -> Path:
    """Create a temporary Codex config directory."""
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    return codex_dir


@pytest.fixture
def coach_with_temp_dir(temp_codex_dir: Path) -> CodexCoach:
    """Create CodexCoach with temporary directory."""
    return CodexCoach(config_dir=temp_codex_dir)


class TestCodexCoachProperties:
    """Tests for CodexCoach properties."""

    def test_vendor_id(self) -> None:
        """Test vendor_id returns 'openai'."""
        coach = CodexCoach()
        assert coach.vendor_id == "openai"

    def test_vendor_name(self) -> None:
        """Test vendor_name returns 'OpenAI Codex'."""
        coach = CodexCoach()
        assert coach.vendor_name == "OpenAI Codex"


class TestCodexCoachAnalyze:
    """Tests for CodexCoach.analyze method."""

    def test_analyze_returns_usage_report(self, coach_with_temp_dir: CodexCoach) -> None:
        """Test analyze returns a UsageReport."""
        report = coach_with_temp_dir.analyze()

        assert report.vendor_id == "openai"
        assert report.vendor_name == "OpenAI Codex"
        assert report.generated_at is not None

    def test_analyze_with_period_days(self, coach_with_temp_dir: CodexCoach) -> None:
        """Test analyze accepts period_days parameter."""
        report = coach_with_temp_dir.analyze(period_days=30)

        assert report.vendor_id == "openai"


class TestCodexCoachInsights:
    """Tests for CodexCoach.get_insights method."""

    def test_profile_insights(self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path) -> None:
        """Test profile count insight."""
        config = {
            "profiles": {
                "default": {"api_key": "sk-xxx"},
                "work": {"api_key": "sk-yyy"},
            }
        }
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        insights = coach_with_temp_dir.get_insights()

        profile_insights = [i for i in insights if i.category == "profiles"]
        assert len(profile_insights) >= 1
        assert any(i.metric_value == 2 for i in profile_insights)

    def test_default_profile_insight(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test default profile insight."""
        config = {
            "default_profile": "work",
            "profiles": {
                "default": {"api_key": "sk-xxx"},
                "work": {"api_key": "sk-yyy"},
            },
        }
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        insights = coach_with_temp_dir.get_insights()

        default_insights = [i for i in insights if i.metric_name == "default_profile"]
        assert len(default_insights) >= 1
        assert default_insights[0].metric_value == "work"

    def test_agents_md_insights(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test AGENTS.md size insight."""
        agents_md = temp_codex_dir / "AGENTS.md"
        agents_md.write_text("# Agents\n\n## Agent 1\n\n## Agent 2")

        insights = coach_with_temp_dir.get_insights()

        doc_insights = [i for i in insights if i.category == "documentation"]
        assert len(doc_insights) >= 1
        assert any(i.metric_name == "agents_md_size" for i in doc_insights)

    def test_sandbox_insights(self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path) -> None:
        """Test sandbox configuration insight."""
        config = {"sandbox": {"enabled": True}}
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        insights = coach_with_temp_dir.get_insights()

        sandbox_insights = [i for i in insights if i.category == "security"]
        assert len(sandbox_insights) >= 1

    def test_model_insight(self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path) -> None:
        """Test default model insight."""
        config = {"model": "gpt-4"}
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        insights = coach_with_temp_dir.get_insights()

        model_insights = [i for i in insights if i.category == "model"]
        assert len(model_insights) >= 1
        assert any(i.metric_value == "gpt-4" for i in model_insights)


class TestCodexCoachRecommendations:
    """Tests for CodexCoach.get_recommendations method."""

    def test_no_profiles_recommendation(self, coach_with_temp_dir: CodexCoach) -> None:
        """Test recommendation when no profiles exist."""
        recommendations = coach_with_temp_dir.get_recommendations()

        profile_recs = [r for r in recommendations if r.category == "profiles"]
        assert len(profile_recs) >= 1

    def test_too_many_profiles_recommendation(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test recommendation when too many profiles exist."""
        config = {"profiles": {f"profile{i}": {"api_key": f"sk-{i}"} for i in range(15)}}
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        recommendations = coach_with_temp_dir.get_recommendations()

        consolidate_recs = [r for r in recommendations if "consolidate" in r.title.lower()]
        assert len(consolidate_recs) >= 1

    def test_no_agents_md_recommendation(self, coach_with_temp_dir: CodexCoach) -> None:
        """Test recommendation when no AGENTS.md exists."""
        recommendations = coach_with_temp_dir.get_recommendations()

        doc_recs = [r for r in recommendations if "AGENTS.md" in r.title]
        assert len(doc_recs) >= 1

    def test_large_agents_md_recommendation(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test recommendation when AGENTS.md is too large."""
        agents_md = temp_codex_dir / "AGENTS.md"
        large_content = "# Large File\n" + "x" * 110000
        agents_md.write_text(large_content)

        recommendations = coach_with_temp_dir.get_recommendations()

        large_recs = [r for r in recommendations if "optimize" in r.title.lower()]
        assert len(large_recs) >= 1

    def test_sandbox_disabled_recommendation(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test recommendation when sandbox is disabled."""
        config = {"sandbox": {"enabled": False}}
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        recommendations = coach_with_temp_dir.get_recommendations()

        sandbox_recs = [r for r in recommendations if "sandbox" in r.title.lower()]
        assert len(sandbox_recs) >= 1
        assert any(r.priority == Priority.HIGH for r in sandbox_recs)

    def test_auto_approve_recommendation(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test recommendation when auto-approve is enabled."""
        config = {"auto_approve_exec": True}
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        recommendations = coach_with_temp_dir.get_recommendations()

        approve_recs = [r for r in recommendations if "auto-approve" in r.title.lower()]
        assert len(approve_recs) >= 1

    def test_recommendations_sorted_by_priority(self, coach_with_temp_dir: CodexCoach) -> None:
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


class TestCodexCoachStats:
    """Tests for CodexCoach.get_stats method."""

    def test_stats_include_config_exists(self, coach_with_temp_dir: CodexCoach) -> None:
        """Test stats include config_exists."""
        stats = coach_with_temp_dir.get_stats()

        assert "config_exists" in stats
        assert stats["config_exists"] is True

    def test_stats_include_profile_count(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test stats include profile_count."""
        config = {
            "profiles": {
                "default": {"api_key": "sk-xxx"},
                "work": {"api_key": "sk-yyy"},
            }
        }
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        stats = coach_with_temp_dir.get_stats()

        assert stats["profile_count"] == 2

    def test_stats_include_profiles_list(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test stats include profiles list."""
        config = {
            "profiles": {
                "default": {"api_key": "sk-xxx"},
                "work": {"api_key": "sk-yyy"},
            }
        }
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        stats = coach_with_temp_dir.get_stats()

        assert "profiles" in stats
        assert set(stats["profiles"]) == {"default", "work"}

    def test_stats_include_agents_md_size(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test stats include AGENTS.md size."""
        agents_md = temp_codex_dir / "AGENTS.md"
        # Write substantial content to ensure size > 0
        content = "# Test content\n" + "x" * 1000
        agents_md.write_text(content)

        stats = coach_with_temp_dir.get_stats()

        assert "agents_md_size_kb" in stats
        assert stats["agents_md_size_kb"] >= 0.9  # At least ~1KB

    def test_stats_include_sandbox_enabled(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test stats include sandbox_enabled."""
        config = {"sandbox": {"enabled": True}}
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        stats = coach_with_temp_dir.get_stats()

        assert stats["sandbox_enabled"] is True


class TestCodexCoachExport:
    """Tests for CodexCoach.export_report method."""

    def test_export_json(self, coach_with_temp_dir: CodexCoach, tmp_path: Path) -> None:
        """Test export to JSON format."""
        coach_with_temp_dir.analyze()
        output_path = tmp_path / "report"

        result_path = coach_with_temp_dir.export_report(output_path, format="json")

        assert result_path.exists()
        assert result_path.suffix == ".json"

        with result_path.open() as f:
            data = json.load(f)
            assert data["vendor_id"] == "openai"

    def test_export_markdown(self, coach_with_temp_dir: CodexCoach, tmp_path: Path) -> None:
        """Test export to Markdown format."""
        coach_with_temp_dir.analyze()
        output_path = tmp_path / "report"

        result_path = coach_with_temp_dir.export_report(output_path, format="markdown")

        assert result_path.exists()
        assert result_path.suffix == ".md"

        content = result_path.read_text()
        assert "OpenAI Codex" in content

    def test_export_invalid_format(self, coach_with_temp_dir: CodexCoach, tmp_path: Path) -> None:
        """Test export with invalid format raises ValueError."""
        coach_with_temp_dir.analyze()
        output_path = tmp_path / "report"

        with pytest.raises(ValueError, match="Unsupported format"):
            coach_with_temp_dir.export_report(output_path, format="invalid")

    def test_export_markdown_no_insights(self, tmp_path: Path) -> None:
        """Test markdown export with no insights."""
        # Create coach with non-existent directory (no config at all)
        nonexistent_dir = tmp_path / ".codex_nonexistent"
        coach = CodexCoach(config_dir=nonexistent_dir)
        coach.analyze()
        output_path = tmp_path / "report"

        result_path = coach.export_report(output_path, format="markdown")

        content = result_path.read_text()
        # No insights since no config exists
        assert "_No insights available._" in content
        # Still has sandbox recommendation (always generated when no config)
        assert "## Recommendations" in content


class TestCodexCoachEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_toml_in_config(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test handling of invalid TOML in config file."""
        (temp_codex_dir / "config.toml").write_text("{ invalid toml }")

        insights = coach_with_temp_dir.get_insights()
        assert isinstance(insights, list)

    def test_profiles_not_a_dict(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test handling when profiles is not a dict."""
        (temp_codex_dir / "config.toml").write_text('profiles = ["list", "not", "dict"]')

        insights = coach_with_temp_dir.get_insights()
        assert isinstance(insights, list)
        # Should treat as 0 profiles
        profile_insights = [i for i in insights if i.category == "profiles"]
        assert len(profile_insights) == 0

    def test_sandbox_not_a_dict(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test handling when sandbox is not a dict."""
        (temp_codex_dir / "config.toml").write_text('sandbox = "not a dict"')

        insights = coach_with_temp_dir.get_insights()
        assert isinstance(insights, list)

    def test_agents_md_with_zero_sections(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test AGENTS.md with no sections (no headers)."""
        agents_md = temp_codex_dir / "AGENTS.md"
        agents_md.write_text("Just plain text without any headers")

        insights = coach_with_temp_dir.get_insights()

        section_insights = [i for i in insights if i.metric_name == "section_count"]
        # Should either have 0 or not include the insight
        assert all(i.metric_value == 0 for i in section_insights) or len(section_insights) == 0

    def test_no_model_recommendation(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test recommendation when no default model set."""
        config = {"version": "1.0.0"}
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        recommendations = coach_with_temp_dir.get_recommendations()

        model_recs = [r for r in recommendations if "default model" in r.title.lower()]
        assert len(model_recs) >= 1

    def test_stats_with_config_api_key(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test stats include has_api_key."""
        config = {"api_key": "test-key", "model": "gpt-4"}
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        stats = coach_with_temp_dir.get_stats()

        assert stats["has_api_key"] is True
        assert stats["default_model"] == "gpt-4"

    def test_agents_md_section_count_oserror(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test _count_md_sections handles file that doesn't exist."""
        count = coach_with_temp_dir._count_md_sections(temp_codex_dir / "nonexistent.md")
        assert count == 0

    def test_stats_include_agents_md_sections(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test stats include agents_md_sections."""
        agents_md = temp_codex_dir / "AGENTS.md"
        agents_md.write_text("# Title\n\n## Agent 1\n\n## Agent 2")

        stats = coach_with_temp_dir.get_stats()

        assert "agents_md_sections" in stats
        assert stats["agents_md_sections"] == 3

    def test_no_sandbox_config_recommendation(
        self, coach_with_temp_dir: CodexCoach, temp_codex_dir: Path
    ) -> None:
        """Test recommendation when no sandbox configuration exists."""
        config = {"version": "1.0.0"}
        (temp_codex_dir / "config.toml").write_text(toml.dumps(config))

        recommendations = coach_with_temp_dir.get_recommendations()

        sandbox_recs = [r for r in recommendations if "sandbox" in r.title.lower()]
        assert len(sandbox_recs) >= 1

    def test_stats_config_file_exists_false(self, tmp_path: Path) -> None:
        """Test stats when config file doesn't exist."""
        codex_dir = tmp_path / ".codex"
        codex_dir.mkdir()
        coach = CodexCoach(config_dir=codex_dir)

        stats = coach.get_stats()

        assert stats["config_file_exists"] is False
