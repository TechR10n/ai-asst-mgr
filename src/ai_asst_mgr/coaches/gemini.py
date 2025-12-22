"""Gemini CLI coaching implementation.

This module provides the GeminiCoach class for analyzing Gemini CLI usage
patterns and generating optimization recommendations based on both
static configuration and runtime telemetry.
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
from ai_asst_mgr.database.manager import DatabaseManager
from ai_asst_mgr.database.sync import DEFAULT_DB_PATH


class GeminiCoach(CoachBase):
    """Coach for optimizing Gemini CLI usage.

    Analyzes Gemini CLI configuration, GEMINI.md files, and runtime session data
    to provide actionable recommendations for workflow optimization.
    """

    # Thresholds for recommendations
    LARGE_GEMINI_MD_KB = 100
    MAX_MCP_SERVERS_RECOMMENDED = 15
    MIN_MCP_SERVERS_FOR_EFFICIENCY = 1
    
    # Efficiency Thresholds
    HIGH_CHAT_LOW_ACTION_RATIO = 5.0  # 5 messages per 1 tool call is suspicious
    LONG_SESSION_SECONDS = 1800 # 30 minutes

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize the Gemini Coach.

        Args:
            config_dir: Path to Gemini config directory. Defaults to ~/.gemini/.
        """
        self._config_dir = config_dir or Path.home() / ".gemini"
        self._settings_file = self._config_dir / "settings.json"
        self._gemini_md = self._config_dir / "GEMINI.md"
        self._mcp_servers_dir = self._config_dir / "mcp_servers"
        
        # Database connection
        self._db = None
        if DEFAULT_DB_PATH.exists():
            self._db = DatabaseManager(DEFAULT_DB_PATH)

        # Cache for analysis results
        self._last_report: UsageReport | None = None

    @property
    def vendor_id(self) -> str:
        """Get the vendor identifier."""
        return "gemini"

    @property
    def vendor_name(self) -> str:
        """Get the human-readable vendor name."""
        return "Gemini CLI"

    def analyze(self, period_days: int = 7) -> UsageReport:
        """Analyze Gemini CLI usage patterns and generate a report.

        Args:
            period_days: Number of days to analyze.

        Returns:
            UsageReport containing insights and recommendations.
        """
        now = datetime.now(tz=UTC)
        
        # Gather insights from multiple sources
        config_insights = self._get_config_insights()
        runtime_insights = self._get_runtime_insights(period_days)
        insights = config_insights + runtime_insights
        
        # Generate recommendations based on insights
        recommendations = self.get_recommendations() # Refreshed logic inside
        
        # Gather stats
        stats = self.get_stats()

        self._last_report = UsageReport(
            vendor_id=self.vendor_id,
            vendor_name=self.vendor_name,
            generated_at=now,
            period_start=None, # Todo: Calculate from period_days
            period_end=now,
            insights=insights,
            recommendations=recommendations,
            stats=stats,
        )

        return self._last_report

    def get_insights(self) -> list[Insight]:
        """Wrapper to get all insights (backward compatibility)."""
        return self._get_config_insights() + self._get_runtime_insights()

    def _get_config_insights(self) -> list[Insight]:
        """Get insights from static configuration analysis."""
        insights: list[Insight] = []

        # GEMINI.md insights
        if self._gemini_md.exists():
            size_kb = self._gemini_md.stat().st_size / 1024
            insights.append(
                Insight(
                    category="documentation",
                    title="GEMINI.md Presence",
                    description=f"GEMINI.md found ({size_kb:.1f}KB)",
                    metric_name="gemini_md_size",
                    metric_value=round(size_kb, 1),
                    metric_unit="KB",
                )
            )

            # Count sections in GEMINI.md
            section_count = self._count_md_sections(self._gemini_md)
            if section_count > 0:
                insights.append(
                    Insight(
                        category="documentation",
                        title="GEMINI.md Structure",
                        description=f"Found {section_count} sections in GEMINI.md",
                        metric_name="section_count",
                        metric_value=section_count,
                        metric_unit="sections",
                    )
                )

        # MCP server insights
        mcp_servers = self._get_mcp_server_configs()
        if mcp_servers:
            insights.append(
                Insight(
                    category="mcp",
                    title="MCP Servers",
                    description=f"Found {len(mcp_servers)} MCP server configurations",
                    metric_name="mcp_server_count",
                    metric_value=len(mcp_servers),
                    metric_unit="servers",
                )
            )

        # Settings insights
        settings = self._load_settings()
        if settings:
            model = settings.get("model", settings.get("defaultModel"))
            if model:
                insights.append(
                    Insight(
                        category="model",
                        title="Default Model",
                        description=f"Using {model} as default model",
                        metric_name="default_model",
                        metric_value=str(model),
                        metric_unit="",
                    )
                )

        return insights

    def _get_runtime_insights(self, days: int = 30) -> list[Insight]:
        """Get insights from runtime telemetry (database)."""
        insights: list[Insight] = []
        if not self._db:
            return insights

        # 1. Tool Activation Rate
        stats = self._db.get_vendor_stats(self.vendor_id, days)
        if stats and stats.total_sessions > 0:
            avg_tools = stats.total_tool_calls / stats.total_sessions
            insights.append(
                Insight(
                    category="performance",
                    title="Tool Activation Rate",
                    description=f"Average of {avg_tools:.1f} tool calls per session",
                    metric_name="avg_tool_calls",
                    metric_value=round(avg_tools, 1),
                    metric_unit="calls/session"
                )
            )

        # 2. Tool Diversity ("One-Trick Pony" Check)
        tool_stats = self._db.get_tool_stats(self.vendor_id)
        if tool_stats:
            top_tools = sorted(tool_stats.items(), key=lambda x: x[1], reverse=True)[:3]
            top_tool_names = ", ".join(t[0] for t in top_tools)
            insights.append(
                Insight(
                    category="usage",
                    title="Top Tools",
                    description=f"Most frequently used tools: {top_tool_names}",
                    metric_name="unique_tools_used",
                    metric_value=len(tool_stats),
                    metric_unit="tools"
                )
            )

        # 3. Longitudinal Trends (Skill & Efficiency)
        trends = self._db.get_longitudinal_stats(self.vendor_id, weeks=4)
        if len(trends) >= 2:
            latest = trends[-1]
            previous = trends[-2]
            
            # PLR Trend (Skill)
            plr_change = latest["plr"] - previous["plr"]
            direction = "improving" if plr_change > 0 else "declining"
            insights.append(
                Insight(
                    category="skill",
                    title="Prompt Leverage Trend",
                    description=f"Your Prompt Leverage Ratio is {direction} ({previous['plr']} -> {latest['plr']}). Higher is better.",
                    metric_name="plr_current",
                    metric_value=latest["plr"],
                    metric_unit="actions/prompt"
                )
            )
            
            # Action Density Trend (Efficiency)
            density_change = latest["action_density"] - previous["action_density"]
            insights.append(
                Insight(
                    category="performance",
                    title="Action Density Trend",
                    description=f"Action Density (speed) is {latest['action_density']} actions/min (prev: {previous['action_density']}).",
                    metric_name="action_density",
                    metric_value=latest["action_density"],
                    metric_unit="actions/min"
                )
            )

        return insights

    def get_recommendations(self) -> list[Recommendation]:
        """Get recommendations for optimizing Gemini CLI usage."""
        recommendations: list[Recommendation] = []

        # Static Config Recommendations
        self._add_config_recommendations(recommendations)
        
        # Runtime/Telemetry Recommendations
        if self._db:
            self._add_runtime_recommendations(recommendations)

        # Sort by priority
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }
        recommendations.sort(key=lambda r: priority_order[r.priority])

        return recommendations

    def _add_config_recommendations(self, recommendations: list[Recommendation]) -> None:
        """Add recommendations based on static files."""
        settings = self._load_settings()
        mcp_servers = self._get_mcp_server_configs()

        # GEMINI.md checks
        if self._gemini_md.exists():
            size_kb = self._gemini_md.stat().st_size / 1024
            if size_kb > self.LARGE_GEMINI_MD_KB:
                recommendations.append(
                    Recommendation(
                        priority=Priority.HIGH,
                        category="documentation",
                        title="Split large GEMINI.md file",
                        description=(
                            f"GEMINI.md is {size_kb:.1f}KB. Large context files increase "
                            "latency and costs."
                        ),
                        action="Split GEMINI.md into topic-specific files referenced by @import",
                        expected_benefit="Faster context loading, reduced token usage",
                    )
                )
        elif self._config_dir.exists():
            recommendations.append(
                Recommendation(
                    priority=Priority.MEDIUM,
                    category="documentation",
                    title="Create GEMINI.md file",
                    description="No GEMINI.md found. This is your 'system prompt' for the project.",
                    action="Create ~/.gemini/GEMINI.md with project overview and coding standards",
                    expected_benefit="Better project understanding, consistent code style",
                )
            )

        # Check MCP servers
        if len(mcp_servers) == 0 and self._config_dir.exists():
            recommendations.append(
                Recommendation(
                    priority=Priority.MEDIUM,
                    category="mcp",
                    title="Consider adding MCP servers",
                    description=(
                        "No MCP servers configured. MCP servers extend "
                        "Gemini's capabilities with external tools."
                    ),
                    action="Add MCP server configurations to expand capabilities",
                    expected_benefit="Extended tool access, better integrations",
                )
            )
        elif len(mcp_servers) > self.MAX_MCP_SERVERS_RECOMMENDED:
            recommendations.append(
                Recommendation(
                    priority=Priority.LOW,
                    category="mcp",
                    title="Review MCP server usage",
                    description=(
                        f"You have {len(mcp_servers)} MCP servers. "
                        "Consider auditing for unused servers."
                    ),
                    action="Remove unused MCP server configurations",
                    expected_benefit="Faster startup, cleaner configuration",
                )
            )

        # Check model configuration
        if settings:
            model = settings.get("model", settings.get("defaultModel", ""))
            if not model:
                recommendations.append(
                    Recommendation(
                        priority=Priority.LOW,
                        category="model",
                        title="Set a default model",
                        description=(
                            "No default model configured. Setting a default "
                            "can streamline your workflow."
                        ),
                        action="Set 'model' or 'defaultModel' in settings.json",
                        expected_benefit="Consistent model usage, fewer prompts",
                    )
                )

            # Check for context window optimization
            if "contextWindow" not in settings and "context_window" not in settings:
                recommendations.append(
                    Recommendation(
                        priority=Priority.LOW,
                        category="model",
                        title="Configure context window",
                        description=(
                            "Context window not explicitly configured. "
                            "Explicit configuration helps optimize token usage."
                        ),
                        action="Set 'contextWindow' in settings.json",
                        expected_benefit="Better token management, cost optimization",
                    )
                )

    def _add_runtime_recommendations(self, recommendations: list[Recommendation]) -> None:
        """Add recommendations based on database telemetry."""
        # 1. "Game Tape" Analysis (Inefficient Sessions)
        # Look for sessions with many messages but few/no tool calls
        inefficient_sessions = self._db.get_inefficient_sessions(
            vendor_id=self.vendor_id, 
            min_messages=6, 
            max_tools=0
        )
        
        if inefficient_sessions:
            count = len(inefficient_sessions)
            recommendations.append(
                Recommendation(
                    priority=Priority.HIGH,
                    category="performance",
                    title="Review 'Talk-Only' Sessions",
                    description=(
                        f"Found {count} sessions with high message counts but ZERO tool calls. "
                        "The model may be talking in circles or hallucinating actions."
                    ),
                    action=f"Review session {inefficient_sessions[0]['session_id']} in the dashboard",
                    expected_benefit="Identify prompts that fail to trigger tools",
                )
            )

        # 2. "The ROI Metric" (Tool Usage vs Session Count)
        # If we have many sessions but very low unique tool usage
        tool_stats = self._db.get_tool_stats(self.vendor_id)
        unique_tools = len(tool_stats)
        
        if unique_tools < 3 and unique_tools > 0:
             recommendations.append(
                Recommendation(
                    priority=Priority.MEDIUM,
                    category="skills",
                    title="Expand Tool Usage",
                    description=(
                        f"You are primarily using only {unique_tools} tools. "
                        "Gemini has many more capabilities."
                    ),
                    action="Try using 'search_file_content' or 'glob' instead of just 'read_file'",
                    expected_benefit="More efficient navigation and refactoring",
                )
            )

    def get_stats(self) -> dict[str, object]:
        """Get raw statistics about Gemini CLI configuration."""
        stats: dict[str, object] = {}

        # Static stats
        stats["config_exists"] = self._config_dir.exists()
        stats["gemini_md_exists"] = self._gemini_md.exists()

        if self._gemini_md.exists():
            stats["gemini_md_size_kb"] = round(self._gemini_md.stat().st_size / 1024, 1)
            stats["gemini_md_sections"] = self._count_md_sections(self._gemini_md)

        mcp_servers = self._get_mcp_server_configs()
        stats["mcp_server_count"] = len(mcp_servers)

        settings = self._load_settings()
        if settings:
            stats["has_api_key"] = "api_key" in settings or "apiKey" in settings
            stats["default_model"] = settings.get("model", settings.get("defaultModel", "not set"))
        
        # Runtime stats (if DB available)
        if self._db:
            vendor_stats = self._db.get_vendor_stats(self.vendor_id)
            if vendor_stats:
                stats["total_sessions"] = vendor_stats.total_sessions
                stats["total_tool_calls"] = vendor_stats.total_tool_calls
                stats["avg_duration_sec"] = round(vendor_stats.avg_duration_seconds, 1)

        return stats

    def _count_md_sections(self, md_file: Path) -> int:
        """Count markdown sections (headers) in a file.

        Args:
            md_file: Path to markdown file.

        Returns:
            Number of headers found.
        """
        if not md_file.exists():
            return 0

        try:
            content = md_file.read_text()
            return len([line for line in content.split("\n") if line.startswith("#")])
        except OSError:
            return 0

    # ... [Export methods remain the same] ...
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
        """Export report as JSON."""
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
        """Export report as Markdown."""
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

        lines.extend(["## Recommendations", ""])

        if report.recommendations:
            priority_emoji = {
                Priority.CRITICAL: "🔴",
                Priority.HIGH: "🟠",
                Priority.MEDIUM: "🟡",
                Priority.LOW: "🟢",
            }
            for rec in report.recommendations:
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

        lines.extend(["## Statistics", ""])
        for key, value in report.stats.items():
            lines.append(f"- **{key}:** {value}")

        md_path = output_path.with_suffix(".md")
        with md_path.open("w") as f:
            f.write("\n".join(lines))

        return md_path

    def _load_settings(self) -> dict[str, Any]:
        """Load Gemini settings.json."""
        if not self._settings_file.exists():
            return {}
        try:
            with self._settings_file.open() as f:
                result = json.load(f)
                return result if isinstance(result, dict) else {}
        except (json.JSONDecodeError, OSError):
            return {}

    def _get_mcp_server_configs(self) -> list[Path]:
        """Get MCP server configuration files."""
        if not self._mcp_servers_dir.exists():
            return []
        return list(self._mcp_servers_dir.glob("*.json"))