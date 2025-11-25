"""Claude Code coaching implementation.

This module provides the ClaudeCoach class for analyzing Claude Code usage
patterns and generating optimization recommendations.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from ai_asst_mgr.coaches.base import (
    CoachBase,
    Insight,
    Priority,
    Recommendation,
    UsageReport,
)


class ClaudeCoach(CoachBase):
    """Coach for optimizing Claude Code usage.

    Analyzes Claude Code configuration, agents, skills, and usage patterns
    to provide actionable recommendations for workflow optimization.
    """

    # Thresholds for recommendations
    MAX_AGENTS_RECOMMENDED = 20
    MAX_SKILLS_RECOMMENDED = 30
    MIN_AGENTS_FOR_EFFICIENCY = 3
    LARGE_FILE_THRESHOLD_KB = 50
    MAX_MCP_SERVERS_RECOMMENDED = 10

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize the Claude Coach.

        Args:
            config_dir: Path to Claude config directory. Defaults to ~/.claude/.
        """
        self._config_dir = config_dir or Path.home() / ".claude"
        self._settings_file = self._config_dir / "settings.json"
        self._agents_dir = self._config_dir / "agents"
        self._skills_dir = self._config_dir / "skills"
        self._commands_dir = self._config_dir / "commands"

        # Cache for analysis results
        self._last_report: UsageReport | None = None

    @property
    def vendor_id(self) -> str:
        """Get the vendor identifier.

        Returns:
            "claude" as the vendor identifier.
        """
        return "claude"

    @property
    def vendor_name(self) -> str:
        """Get the human-readable vendor name.

        Returns:
            "Claude Code" as the vendor name.
        """
        return "Claude Code"

    def analyze(self, period_days: int = 7) -> UsageReport:
        """Analyze Claude Code usage patterns and generate a report.

        Args:
            period_days: Number of days to analyze (reserved for future use).

        Returns:
            UsageReport containing insights and recommendations.
        """
        _ = period_days  # Reserved for future session-based analysis
        now = datetime.now(tz=UTC)
        insights = self.get_insights()
        recommendations = self.get_recommendations()
        stats = self.get_stats()

        self._last_report = UsageReport(
            vendor_id=self.vendor_id,
            vendor_name=self.vendor_name,
            generated_at=now,
            period_start=None,  # No session tracking yet
            period_end=now,
            insights=insights,
            recommendations=recommendations,
            stats=stats,
        )

        return self._last_report

    def get_insights(self) -> list[Insight]:
        """Get insights from Claude Code configuration analysis.

        Returns:
            List of Insight objects based on current configuration.
        """
        insights: list[Insight] = []

        # Agent insights
        agents = self._get_agent_files()
        if agents:
            insights.append(
                Insight(
                    category="agents",
                    title="Agent Configuration",
                    description=f"Found {len(agents)} custom agent definitions",
                    metric_name="agent_count",
                    metric_value=len(agents),
                    metric_unit="agents",
                )
            )

            # Find largest agent file
            largest = self._find_largest_file(agents)
            if largest:
                size_kb = largest.stat().st_size / 1024
                insights.append(
                    Insight(
                        category="agents",
                        title="Largest Agent Definition",
                        description=f"{largest.stem} is the largest agent ({size_kb:.1f}KB)",
                        metric_name="largest_agent_size",
                        metric_value=round(size_kb, 1),
                        metric_unit="KB",
                    )
                )

        # Skill insights
        skills = self._get_skill_files()
        if skills:
            insights.append(
                Insight(
                    category="skills",
                    title="Skill Configuration",
                    description=f"Found {len(skills)} custom skill definitions",
                    metric_name="skill_count",
                    metric_value=len(skills),
                    metric_unit="skills",
                )
            )

        # Command insights
        commands = self._get_command_files()
        if commands:
            insights.append(
                Insight(
                    category="commands",
                    title="Custom Commands",
                    description=f"Found {len(commands)} custom slash commands",
                    metric_name="command_count",
                    metric_value=len(commands),
                    metric_unit="commands",
                )
            )

        # Settings insights
        settings = self._load_settings()
        if settings:
            mcp_servers = self._count_mcp_servers(settings)
            if mcp_servers > 0:
                insights.append(
                    Insight(
                        category="mcp",
                        title="MCP Server Configuration",
                        description=f"Configured {mcp_servers} MCP servers",
                        metric_name="mcp_server_count",
                        metric_value=mcp_servers,
                        metric_unit="servers",
                    )
                )

        return insights

    def get_recommendations(self) -> list[Recommendation]:
        """Get recommendations for optimizing Claude Code usage.

        Returns:
            List of Recommendation objects sorted by priority.
        """
        recommendations: list[Recommendation] = []

        agents = self._get_agent_files()
        skills = self._get_skill_files()
        commands = self._get_command_files()
        settings = self._load_settings()

        # Check for too many agents
        if len(agents) > self.MAX_AGENTS_RECOMMENDED:
            recommendations.append(
                Recommendation(
                    priority=Priority.MEDIUM,
                    category="agents",
                    title="Consider consolidating agents",
                    description=(
                        f"You have {len(agents)} agents, which may cause confusion. "
                        f"Consider consolidating similar agents."
                    ),
                    action="Review agents and merge those with overlapping purposes",
                    expected_benefit="Faster agent selection, clearer workflows",
                )
            )

        # Check for too few agents
        if 0 < len(agents) < self.MIN_AGENTS_FOR_EFFICIENCY:
            recommendations.append(
                Recommendation(
                    priority=Priority.LOW,
                    category="agents",
                    title="Consider adding specialized agents",
                    description=(
                        f"You only have {len(agents)} agent(s). "
                        "Specialized agents can improve workflow efficiency."
                    ),
                    action="Create agents for common tasks (code review, testing, docs)",
                    expected_benefit="Faster task completion, better context retention",
                )
            )

        # Check for no agents
        if len(agents) == 0 and self._config_dir.exists():
            recommendations.append(
                Recommendation(
                    priority=Priority.HIGH,
                    category="agents",
                    title="Create custom agents",
                    description=(
                        "No custom agents found. Agents help Claude understand "
                        "your specific workflows and preferences."
                    ),
                    action="Create ~/.claude/agents/ directory and add .md agent files",
                    expected_benefit="Personalized assistance, better task understanding",
                )
            )

        # Check for large agent files
        for agent in agents:
            size_kb = agent.stat().st_size / 1024
            if size_kb > self.LARGE_FILE_THRESHOLD_KB:
                recommendations.append(
                    Recommendation(
                        priority=Priority.MEDIUM,
                        category="agents",
                        title=f"Optimize large agent: {agent.stem}",
                        description=(
                            f"Agent '{agent.stem}' is {size_kb:.1f}KB. "
                            "Large agents may slow down context processing."
                        ),
                        action="Split into smaller, focused agents or convert to skills",
                        expected_benefit="Faster response times, clearer responsibilities",
                    )
                )

        # Check for no skills
        if len(skills) == 0 and len(agents) > 0:
            recommendations.append(
                Recommendation(
                    priority=Priority.LOW,
                    category="skills",
                    title="Consider creating reusable skills",
                    description=(
                        "No skills found. Skills are reusable components that "
                        "can be shared across agents."
                    ),
                    action="Extract common patterns from agents into skills",
                    expected_benefit="DRY principle, easier maintenance",
                )
            )

        # Check for too many skills
        if len(skills) > self.MAX_SKILLS_RECOMMENDED:
            recommendations.append(
                Recommendation(
                    priority=Priority.MEDIUM,
                    category="skills",
                    title="Consolidate skill library",
                    description=(
                        f"You have {len(skills)} skills. "
                        "Consider organizing or consolidating related skills."
                    ),
                    action="Group related skills, remove unused ones",
                    expected_benefit="Easier discovery, reduced maintenance",
                )
            )

        # Check for no custom commands
        if len(commands) == 0 and self._config_dir.exists():
            recommendations.append(
                Recommendation(
                    priority=Priority.LOW,
                    category="commands",
                    title="Create custom slash commands",
                    description=(
                        "No custom commands found. Slash commands provide "
                        "quick access to common operations."
                    ),
                    action="Create ~/.claude/commands/ and add command templates",
                    expected_benefit="Faster workflow triggers, standardized operations",
                )
            )

        # Check MCP configuration
        if settings:
            mcp_servers = self._count_mcp_servers(settings)
            if mcp_servers == 0:
                recommendations.append(
                    Recommendation(
                        priority=Priority.MEDIUM,
                        category="mcp",
                        title="Consider adding MCP servers",
                        description=(
                            "No MCP servers configured. MCP servers extend "
                            "Claude's capabilities with external tools."
                        ),
                        action="Add useful MCP servers to settings.json",
                        expected_benefit="Extended capabilities, tool integrations",
                    )
                )
            elif mcp_servers > self.MAX_MCP_SERVERS_RECOMMENDED:
                recommendations.append(
                    Recommendation(
                        priority=Priority.LOW,
                        category="mcp",
                        title="Review MCP server usage",
                        description=(
                            f"You have {mcp_servers} MCP servers configured. "
                            "Consider reviewing which ones are actively used."
                        ),
                        action="Audit MCP servers and disable unused ones",
                        expected_benefit="Faster startup, cleaner configuration",
                    )
                )

        # Sort by priority (CRITICAL > HIGH > MEDIUM > LOW)
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }
        recommendations.sort(key=lambda r: priority_order[r.priority])

        return recommendations

    def get_stats(self) -> dict[str, object]:
        """Get raw statistics about Claude Code configuration.

        Returns:
            Dictionary containing configuration statistics.
        """
        stats: dict[str, object] = {}

        # Configuration directory stats
        stats["config_exists"] = self._config_dir.exists()
        stats["settings_exists"] = self._settings_file.exists()

        # Agent stats
        agents = self._get_agent_files()
        stats["agent_count"] = len(agents)
        if agents:
            stats["total_agent_size_kb"] = round(sum(a.stat().st_size for a in agents) / 1024, 1)

        # Skill stats
        skills = self._get_skill_files()
        stats["skill_count"] = len(skills)
        if skills:
            stats["total_skill_size_kb"] = round(sum(s.stat().st_size for s in skills) / 1024, 1)

        # Command stats
        commands = self._get_command_files()
        stats["command_count"] = len(commands)

        # MCP server stats
        settings = self._load_settings()
        if settings:
            stats["mcp_server_count"] = self._count_mcp_servers(settings)

        return stats

    def export_report(self, output_path: Path, format: str = "json") -> Path:
        """Export the usage report to a file.

        Args:
            output_path: Path where the report should be saved.
            format: Output format ("json" or "markdown").

        Returns:
            Path to the created report file.

        Raises:
            ValueError: If format is not supported.
            RuntimeError: If export fails.
        """
        if format not in ("json", "markdown"):
            msg = f"Unsupported format: {format}. Use 'json' or 'markdown'."
            raise ValueError(msg)

        # Generate report if not cached
        if self._last_report is None:
            self.analyze()

        report = self._last_report
        if report is None:
            msg = "Failed to generate report"
            raise RuntimeError(msg)

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if format == "json":
                return self._export_json(report, output_path)
            return self._export_markdown(report, output_path)

        except OSError as e:
            msg = f"Failed to export report: {e}"
            raise RuntimeError(msg) from e

    def _export_json(self, report: UsageReport, output_path: Path) -> Path:
        """Export report as JSON.

        Args:
            report: UsageReport to export.
            output_path: Path for output file.

        Returns:
            Path to created file.
        """
        data = {
            "vendor_id": report.vendor_id,
            "vendor_name": report.vendor_name,
            "generated_at": report.generated_at.isoformat(),
            "period_start": (report.period_start.isoformat() if report.period_start else None),
            "period_end": (report.period_end.isoformat() if report.period_end else None),
            "insights": [
                {
                    "category": i.category,
                    "title": i.title,
                    "description": i.description,
                    "metric_name": i.metric_name,
                    "metric_value": i.metric_value,
                    "metric_unit": i.metric_unit,
                }
                for i in report.insights
            ],
            "recommendations": [
                {
                    "priority": r.priority.value,
                    "category": r.category,
                    "title": r.title,
                    "description": r.description,
                    "action": r.action,
                    "expected_benefit": r.expected_benefit,
                }
                for r in report.recommendations
            ],
            "stats": report.stats,
        }

        json_path = output_path.with_suffix(".json")
        with json_path.open("w") as f:
            json.dump(data, f, indent=2)

        return json_path

    def _export_markdown(self, report: UsageReport, output_path: Path) -> Path:
        """Export report as Markdown.

        Args:
            report: UsageReport to export.
            output_path: Path for output file.

        Returns:
            Path to created file.
        """
        lines = [
            f"# {report.vendor_name} Usage Report",
            "",
            f"**Generated:** {report.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}",
            "",
            "## Insights",
            "",
        ]

        if report.insights:
            for insight in report.insights:
                lines.extend(
                    [
                        f"### {insight.title}",
                        "",
                        f"**Category:** {insight.category}",
                        "",
                        insight.description,
                        "",
                        f"- **{insight.metric_name}:** "
                        f"{insight.metric_value} {insight.metric_unit}",
                        "",
                    ]
                )
        else:
            lines.append("_No insights available._\n")

        lines.extend(
            [
                "## Recommendations",
                "",
            ]
        )

        if report.recommendations:
            for rec in report.recommendations:
                priority_emoji = {
                    Priority.CRITICAL: "🔴",
                    Priority.HIGH: "🟠",
                    Priority.MEDIUM: "🟡",
                    Priority.LOW: "🟢",
                }
                lines.extend(
                    [
                        f"### {priority_emoji.get(rec.priority, '⚪')} {rec.title}",
                        "",
                        f"**Priority:** {rec.priority.value.upper()}",
                        f"**Category:** {rec.category}",
                        "",
                        rec.description,
                        "",
                        f"**Action:** {rec.action}",
                        "",
                        f"**Expected Benefit:** {rec.expected_benefit}",
                        "",
                    ]
                )
        else:
            lines.append("_No recommendations at this time._\n")

        lines.extend(
            [
                "## Statistics",
                "",
            ]
        )

        for key, value in report.stats.items():
            lines.append(f"- **{key}:** {value}")

        md_path = output_path.with_suffix(".md")
        with md_path.open("w") as f:
            f.write("\n".join(lines))

        return md_path

    def _get_agent_files(self) -> list[Path]:
        """Get all agent definition files.

        Returns:
            List of paths to agent markdown files.
        """
        if not self._agents_dir.exists():
            return []
        return list(self._agents_dir.glob("*.md"))

    def _get_skill_files(self) -> list[Path]:
        """Get all skill definition files.

        Returns:
            List of paths to skill markdown files.
        """
        if not self._skills_dir.exists():
            return []
        return list(self._skills_dir.glob("*.md"))

    def _get_command_files(self) -> list[Path]:
        """Get all custom command files.

        Returns:
            List of paths to command definition files.
        """
        if not self._commands_dir.exists():
            return []
        return list(self._commands_dir.glob("*.md"))

    def _load_settings(self) -> dict[str, Any]:
        """Load Claude settings.json.

        Returns:
            Dictionary of settings, or empty dict if not found.
        """
        if not self._settings_file.exists():
            return {}

        try:
            with self._settings_file.open() as f:
                result = json.load(f)
                if isinstance(result, dict):
                    return result
                return {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _count_mcp_servers(self, settings: dict[str, Any]) -> int:
        """Count configured MCP servers.

        Args:
            settings: Settings dictionary.

        Returns:
            Number of MCP servers configured.
        """
        mcp_config = settings.get("mcpServers", {})
        if isinstance(mcp_config, dict):
            return len(mcp_config)
        return 0

    def _find_largest_file(self, files: list[Path]) -> Path | None:
        """Find the largest file from a list.

        Args:
            files: List of file paths.

        Returns:
            Path to the largest file, or None if list is empty.
        """
        if not files:
            return None
        return max(files, key=lambda f: f.stat().st_size)
