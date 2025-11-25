"""Unit tests for ClaudeCoach."""

import json
from pathlib import Path

import pytest

from ai_asst_mgr.coaches.base import Priority
from ai_asst_mgr.coaches.claude import ClaudeCoach


@pytest.fixture
def temp_claude_dir(tmp_path: Path) -> Path:
    """Create a temporary Claude config directory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    return claude_dir


@pytest.fixture
def coach_with_temp_dir(temp_claude_dir: Path) -> ClaudeCoach:
    """Create ClaudeCoach with temporary directory."""
    return ClaudeCoach(config_dir=temp_claude_dir)


class TestClaudeCoachProperties:
    """Tests for ClaudeCoach properties."""

    def test_vendor_id(self) -> None:
        """Test vendor_id returns 'claude'."""
        coach = ClaudeCoach()
        assert coach.vendor_id == "claude"

    def test_vendor_name(self) -> None:
        """Test vendor_name returns 'Claude Code'."""
        coach = ClaudeCoach()
        assert coach.vendor_name == "Claude Code"


class TestClaudeCoachAnalyze:
    """Tests for ClaudeCoach.analyze method."""

    def test_analyze_returns_usage_report(self, coach_with_temp_dir: ClaudeCoach) -> None:
        """Test analyze returns a UsageReport."""
        report = coach_with_temp_dir.analyze()

        assert report.vendor_id == "claude"
        assert report.vendor_name == "Claude Code"
        assert report.generated_at is not None

    def test_analyze_with_period_days(self, coach_with_temp_dir: ClaudeCoach) -> None:
        """Test analyze accepts period_days parameter."""
        report = coach_with_temp_dir.analyze(period_days=30)

        assert report.vendor_id == "claude"


class TestClaudeCoachInsights:
    """Tests for ClaudeCoach.get_insights method."""

    def test_no_insights_when_empty(self, coach_with_temp_dir: ClaudeCoach) -> None:
        """Test no insights when no config exists."""
        insights = coach_with_temp_dir.get_insights()

        # Should have no insights for empty directory
        assert isinstance(insights, list)

    def test_agent_insights(self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path) -> None:
        """Test agent count insight."""
        agents_dir = temp_claude_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.md").write_text("# Agent 1")
        (agents_dir / "agent2.md").write_text("# Agent 2")

        insights = coach_with_temp_dir.get_insights()

        agent_insights = [i for i in insights if i.category == "agents"]
        assert len(agent_insights) >= 1
        assert any(i.metric_name == "agent_count" for i in agent_insights)

    def test_skill_insights(self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path) -> None:
        """Test skill count insight."""
        skills_dir = temp_claude_dir / "skills"
        skills_dir.mkdir()
        (skills_dir / "skill1.md").write_text("# Skill 1")

        insights = coach_with_temp_dir.get_insights()

        skill_insights = [i for i in insights if i.category == "skills"]
        assert len(skill_insights) >= 1
        assert any(i.metric_name == "skill_count" for i in skill_insights)

    def test_command_insights(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test command count insight."""
        commands_dir = temp_claude_dir / "commands"
        commands_dir.mkdir()
        (commands_dir / "cmd1.md").write_text("# Command 1")

        insights = coach_with_temp_dir.get_insights()

        cmd_insights = [i for i in insights if i.category == "commands"]
        assert len(cmd_insights) >= 1

    def test_mcp_server_insights(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test MCP server count insight."""
        settings = {
            "mcpServers": {
                "server1": {"command": "npx server1"},
                "server2": {"command": "npx server2"},
            }
        }
        (temp_claude_dir / "settings.json").write_text(json.dumps(settings))

        insights = coach_with_temp_dir.get_insights()

        mcp_insights = [i for i in insights if i.category == "mcp"]
        assert len(mcp_insights) >= 1
        assert any(i.metric_value == 2 for i in mcp_insights)


class TestClaudeCoachRecommendations:
    """Tests for ClaudeCoach.get_recommendations method."""

    def test_no_agents_recommendation(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test recommendation when no agents exist."""
        # Create agents directory but no agents
        (temp_claude_dir / "agents").mkdir()

        recommendations = coach_with_temp_dir.get_recommendations()

        agent_recs = [r for r in recommendations if r.category == "agents"]
        assert len(agent_recs) >= 1
        assert any(r.priority == Priority.HIGH for r in agent_recs)

    def test_too_many_agents_recommendation(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test recommendation when too many agents exist."""
        agents_dir = temp_claude_dir / "agents"
        agents_dir.mkdir()

        # Create more than MAX_AGENTS_RECOMMENDED agents
        for i in range(25):
            (agents_dir / f"agent{i}.md").write_text(f"# Agent {i}")

        recommendations = coach_with_temp_dir.get_recommendations()

        agent_recs = [r for r in recommendations if "consolidating" in r.title.lower()]
        assert len(agent_recs) >= 1

    def test_large_agent_file_recommendation(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test recommendation for large agent files."""
        agents_dir = temp_claude_dir / "agents"
        agents_dir.mkdir()

        # Create a large agent file (over 50KB)
        large_content = "# Large Agent\n" + "x" * 60000
        (agents_dir / "large_agent.md").write_text(large_content)

        recommendations = coach_with_temp_dir.get_recommendations()

        large_recs = [r for r in recommendations if "large_agent" in r.title.lower()]
        assert len(large_recs) >= 1

    def test_no_skills_recommendation(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test recommendation when agents exist but no skills."""
        agents_dir = temp_claude_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.md").write_text("# Agent 1")

        recommendations = coach_with_temp_dir.get_recommendations()

        skill_recs = [r for r in recommendations if r.category == "skills"]
        assert len(skill_recs) >= 1

    def test_no_mcp_servers_recommendation(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test recommendation when no MCP servers configured."""
        settings = {"version": "1.0.0"}
        (temp_claude_dir / "settings.json").write_text(json.dumps(settings))

        recommendations = coach_with_temp_dir.get_recommendations()

        mcp_recs = [r for r in recommendations if r.category == "mcp"]
        assert len(mcp_recs) >= 1

    def test_recommendations_sorted_by_priority(self, coach_with_temp_dir: ClaudeCoach) -> None:
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


class TestClaudeCoachStats:
    """Tests for ClaudeCoach.get_stats method."""

    def test_stats_include_config_exists(self, coach_with_temp_dir: ClaudeCoach) -> None:
        """Test stats include config_exists."""
        stats = coach_with_temp_dir.get_stats()

        assert "config_exists" in stats
        assert stats["config_exists"] is True

    def test_stats_include_agent_count(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test stats include agent_count."""
        agents_dir = temp_claude_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.md").write_text("# Agent 1")
        (agents_dir / "agent2.md").write_text("# Agent 2")

        stats = coach_with_temp_dir.get_stats()

        assert stats["agent_count"] == 2

    def test_stats_include_skill_count(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test stats include skill_count."""
        skills_dir = temp_claude_dir / "skills"
        skills_dir.mkdir()
        (skills_dir / "skill1.md").write_text("# Skill 1")

        stats = coach_with_temp_dir.get_stats()

        assert stats["skill_count"] == 1

    def test_stats_include_total_size(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test stats include total size for agents."""
        agents_dir = temp_claude_dir / "agents"
        agents_dir.mkdir()
        # Write substantial content to ensure size > 0
        content = "# Agent 1\n" + "x" * 1000
        (agents_dir / "agent1.md").write_text(content)

        stats = coach_with_temp_dir.get_stats()

        assert "total_agent_size_kb" in stats
        assert stats["total_agent_size_kb"] >= 0.9  # At least ~1KB


class TestClaudeCoachRecommendationsEdgeCases:
    """Additional edge case tests for recommendations."""

    def test_few_agents_recommendation(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test recommendation when only 1-2 agents exist."""
        agents_dir = temp_claude_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "agent1.md").write_text("# Agent 1")

        recommendations = coach_with_temp_dir.get_recommendations()

        agent_recs = [r for r in recommendations if "specialized" in r.title.lower()]
        assert len(agent_recs) >= 1
        assert any(r.priority == Priority.LOW for r in agent_recs)

    def test_too_many_skills_recommendation(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test recommendation when too many skills exist."""
        skills_dir = temp_claude_dir / "skills"
        skills_dir.mkdir()

        # Create more than MAX_SKILLS_RECOMMENDED skills
        for i in range(35):
            (skills_dir / f"skill{i}.md").write_text(f"# Skill {i}")

        recommendations = coach_with_temp_dir.get_recommendations()

        skill_recs = [r for r in recommendations if r.category == "skills"]
        assert len(skill_recs) >= 1

    def test_no_commands_recommendation(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test recommendation when no custom commands exist."""
        # Just have agents dir but no commands
        (temp_claude_dir / "agents").mkdir()

        recommendations = coach_with_temp_dir.get_recommendations()

        cmd_recs = [r for r in recommendations if r.category == "commands"]
        assert len(cmd_recs) >= 1

    def test_largest_agent_insight(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test largest agent file insight."""
        agents_dir = temp_claude_dir / "agents"
        agents_dir.mkdir()
        (agents_dir / "small.md").write_text("# Small")
        (agents_dir / "large.md").write_text("# Large\n" + "x" * 5000)

        insights = coach_with_temp_dir.get_insights()

        largest_insights = [i for i in insights if "largest" in i.title.lower()]
        assert len(largest_insights) >= 1
        assert largest_insights[0].description.startswith("large")


class TestClaudeCoachExport:
    """Tests for ClaudeCoach.export_report method."""

    def test_export_json(self, coach_with_temp_dir: ClaudeCoach, tmp_path: Path) -> None:
        """Test export to JSON format."""
        coach_with_temp_dir.analyze()
        output_path = tmp_path / "report"

        result_path = coach_with_temp_dir.export_report(output_path, format="json")

        assert result_path.exists()
        assert result_path.suffix == ".json"

        # Verify JSON is valid
        with result_path.open() as f:
            data = json.load(f)
            assert data["vendor_id"] == "claude"
            assert data["vendor_name"] == "Claude Code"

    def test_export_markdown(self, coach_with_temp_dir: ClaudeCoach, tmp_path: Path) -> None:
        """Test export to Markdown format."""
        coach_with_temp_dir.analyze()
        output_path = tmp_path / "report"

        result_path = coach_with_temp_dir.export_report(output_path, format="markdown")

        assert result_path.exists()
        assert result_path.suffix == ".md"

        content = result_path.read_text()
        assert "Claude Code" in content
        assert "# Claude Code Usage Report" in content

    def test_export_markdown_no_insights(self, tmp_path: Path) -> None:
        """Test markdown export with no insights."""
        # Create coach with non-existent directory (no config at all)
        nonexistent_dir = tmp_path / ".claude_nonexistent"
        coach = ClaudeCoach(config_dir=nonexistent_dir)
        coach.analyze()
        output_path = tmp_path / "report"

        result_path = coach.export_report(output_path, format="markdown")

        content = result_path.read_text()
        assert "_No insights available._" in content
        assert "_No recommendations at this time._" in content

    def test_export_invalid_format(self, coach_with_temp_dir: ClaudeCoach, tmp_path: Path) -> None:
        """Test export with invalid format raises ValueError."""
        coach_with_temp_dir.analyze()
        output_path = tmp_path / "report"

        with pytest.raises(ValueError, match="Unsupported format"):
            coach_with_temp_dir.export_report(output_path, format="invalid")

    def test_export_creates_parent_dirs(
        self, coach_with_temp_dir: ClaudeCoach, tmp_path: Path
    ) -> None:
        """Test export creates parent directories."""
        coach_with_temp_dir.analyze()
        output_path = tmp_path / "nested" / "dir" / "report"

        result_path = coach_with_temp_dir.export_report(output_path, format="json")

        assert result_path.exists()
        assert result_path.parent.exists()

    def test_export_without_prior_analyze(
        self, coach_with_temp_dir: ClaudeCoach, tmp_path: Path
    ) -> None:
        """Test export calls analyze if not previously called."""
        output_path = tmp_path / "report"

        # Should not raise - analyze should be called internally
        result_path = coach_with_temp_dir.export_report(output_path, format="json")

        assert result_path.exists()


class TestClaudeCoachEdgeCases:
    """Tests for edge cases and error handling."""

    def test_invalid_json_in_settings(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test handling of invalid JSON in settings file."""
        (temp_claude_dir / "settings.json").write_text("{ invalid json }")

        insights = coach_with_temp_dir.get_insights()
        # Should not crash, just return no MCP insights
        assert isinstance(insights, list)

    def test_settings_json_not_a_dict(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test handling when settings.json is not a dict."""
        (temp_claude_dir / "settings.json").write_text(json.dumps(["list", "not", "dict"]))

        insights = coach_with_temp_dir.get_insights()
        # Should not crash, treat as empty settings
        assert isinstance(insights, list)

    def test_mcp_servers_not_a_dict(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test handling when mcpServers is not a dict."""
        settings = {"mcpServers": ["list", "instead", "of", "dict"]}
        (temp_claude_dir / "settings.json").write_text(json.dumps(settings))

        insights = coach_with_temp_dir.get_insights()
        # Should not crash, count as 0 servers
        mcp_insights = [i for i in insights if i.category == "mcp"]
        assert len(mcp_insights) == 0

    def test_too_many_mcp_servers_recommendation(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test recommendation when too many MCP servers."""
        settings = {"mcpServers": {f"server{i}": {"command": f"npx server{i}"} for i in range(15)}}
        (temp_claude_dir / "settings.json").write_text(json.dumps(settings))

        recommendations = coach_with_temp_dir.get_recommendations()

        mcp_recs = [r for r in recommendations if "Review MCP server" in r.title]
        assert len(mcp_recs) >= 1

    def test_total_skill_size_in_stats(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test total_skill_size_kb is included in stats."""
        skills_dir = temp_claude_dir / "skills"
        skills_dir.mkdir()
        (skills_dir / "skill1.md").write_text("# Skill 1\n" + "x" * 1000)
        (skills_dir / "skill2.md").write_text("# Skill 2\n" + "x" * 1000)

        stats = coach_with_temp_dir.get_stats()

        assert "total_skill_size_kb" in stats
        assert stats["total_skill_size_kb"] >= 1.9  # At least ~2KB

    def test_mcp_server_count_in_stats(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test mcp_server_count is included in stats."""
        settings = {
            "mcpServers": {
                "server1": {"command": "npx server1"},
            }
        }
        (temp_claude_dir / "settings.json").write_text(json.dumps(settings))

        stats = coach_with_temp_dir.get_stats()

        assert stats["mcp_server_count"] == 1

    def test_no_commands_dir_recommendation(
        self, coach_with_temp_dir: ClaudeCoach, temp_claude_dir: Path
    ) -> None:
        """Test recommendation when commands directory doesn't exist."""
        # Directory exists but no commands dir
        recommendations = coach_with_temp_dir.get_recommendations()

        cmd_recs = [r for r in recommendations if r.category == "commands"]
        assert len(cmd_recs) >= 1

    def test_stats_settings_exists_false(self, tmp_path: Path) -> None:
        """Test stats when settings file doesn't exist."""
        claude_dir = tmp_path / ".claude"
        claude_dir.mkdir()
        coach = ClaudeCoach(config_dir=claude_dir)

        stats = coach.get_stats()

        assert stats["settings_exists"] is False
