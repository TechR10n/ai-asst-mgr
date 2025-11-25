"""OpenAI Codex coaching implementation.

This module provides the CodexCoach class for analyzing OpenAI Codex usage
patterns and generating optimization recommendations.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import toml

from ai_asst_mgr.coaches.base import (
    CoachBase,
    Insight,
    Priority,
    Recommendation,
    UsageReport,
)


class CodexCoach(CoachBase):
    """Coach for optimizing OpenAI Codex usage.

    Analyzes Codex configuration, profiles, AGENTS.md, and sandbox settings
    to provide actionable recommendations for workflow optimization.
    """

    # Thresholds for recommendations
    MAX_PROFILES_RECOMMENDED = 10
    LARGE_AGENTS_MD_KB = 100
    MIN_PROFILES_FOR_EFFICIENCY = 1

    def __init__(self, config_dir: Path | None = None) -> None:
        """Initialize the Codex Coach.

        Args:
            config_dir: Path to Codex config directory. Defaults to ~/.codex/.
        """
        self._config_dir = config_dir or Path.home() / ".codex"
        self._config_file = self._config_dir / "config.toml"
        self._agents_md = self._config_dir / "AGENTS.md"
        self._mcp_servers_dir = self._config_dir / "mcp_servers"

        # Cache for analysis results
        self._last_report: UsageReport | None = None

    @property
    def vendor_id(self) -> str:
        """Get the vendor identifier.

        Returns:
            "openai" as the vendor identifier.
        """
        return "openai"

    @property
    def vendor_name(self) -> str:
        """Get the human-readable vendor name.

        Returns:
            "OpenAI Codex" as the vendor name.
        """
        return "OpenAI Codex"

    def analyze(self, period_days: int = 7) -> UsageReport:
        """Analyze Codex usage patterns and generate a report.

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
            period_start=None,
            period_end=now,
            insights=insights,
            recommendations=recommendations,
            stats=stats,
        )

        return self._last_report

    def get_insights(self) -> list[Insight]:
        """Get insights from Codex configuration analysis.

        Returns:
            List of Insight objects based on current configuration.
        """
        insights: list[Insight] = []

        config = self._load_config()

        # Profile insights
        profiles = self._get_profiles(config)
        if profiles:
            insights.append(
                Insight(
                    category="profiles",
                    title="Profile Configuration",
                    description=f"Found {len(profiles)} configured profiles",
                    metric_name="profile_count",
                    metric_value=len(profiles),
                    metric_unit="profiles",
                )
            )

            # Check for default profile
            default_profile = config.get("default_profile", config.get("defaultProfile"))
            if default_profile:
                insights.append(
                    Insight(
                        category="profiles",
                        title="Default Profile",
                        description=f"Using '{default_profile}' as default profile",
                        metric_name="default_profile",
                        metric_value=str(default_profile),
                        metric_unit="",
                    )
                )

        # AGENTS.md insights
        if self._agents_md.exists():
            size_kb = self._agents_md.stat().st_size / 1024
            insights.append(
                Insight(
                    category="documentation",
                    title="AGENTS.md Configuration",
                    description=f"AGENTS.md file is {size_kb:.1f}KB",
                    metric_name="agents_md_size",
                    metric_value=round(size_kb, 1),
                    metric_unit="KB",
                )
            )

            section_count = self._count_md_sections(self._agents_md)
            if section_count > 0:
                insights.append(
                    Insight(
                        category="documentation",
                        title="AGENTS.md Structure",
                        description=f"Found {section_count} sections in AGENTS.md",
                        metric_name="section_count",
                        metric_value=section_count,
                        metric_unit="sections",
                    )
                )

        # Sandbox configuration insights
        sandbox_config = self._get_sandbox_config(config)
        if sandbox_config:
            sandbox_enabled = sandbox_config.get("enabled", True)
            insights.append(
                Insight(
                    category="security",
                    title="Sandbox Configuration",
                    description=(
                        "Sandbox is enabled" if sandbox_enabled else "Sandbox is disabled"
                    ),
                    metric_name="sandbox_enabled",
                    metric_value=sandbox_enabled,
                    metric_unit="",
                )
            )

        # Model insights
        model = config.get("model", config.get("defaultModel"))
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

    def get_recommendations(self) -> list[Recommendation]:
        """Get recommendations for optimizing Codex usage.

        Returns:
            List of Recommendation objects sorted by priority.
        """
        recommendations: list[Recommendation] = []

        config = self._load_config()
        profiles = self._get_profiles(config)

        # Check profiles
        if len(profiles) == 0 and self._config_dir.exists():
            recommendations.append(
                Recommendation(
                    priority=Priority.MEDIUM,
                    category="profiles",
                    title="Create profiles for different contexts",
                    description=(
                        "No profiles configured. Profiles help manage different "
                        "API keys and settings for various projects."
                    ),
                    action="Add profiles to config.toml for different use cases",
                    expected_benefit="Better organization, context-specific settings",
                )
            )
        elif len(profiles) > self.MAX_PROFILES_RECOMMENDED:
            recommendations.append(
                Recommendation(
                    priority=Priority.LOW,
                    category="profiles",
                    title="Consolidate profiles",
                    description=(
                        f"You have {len(profiles)} profiles. "
                        "Consider consolidating similar profiles."
                    ),
                    action="Review and merge profiles with similar settings",
                    expected_benefit="Easier management, clearer organization",
                )
            )

        # Check AGENTS.md
        if self._agents_md.exists():
            size_kb = self._agents_md.stat().st_size / 1024
            if size_kb > self.LARGE_AGENTS_MD_KB:
                recommendations.append(
                    Recommendation(
                        priority=Priority.HIGH,
                        category="documentation",
                        title="Optimize AGENTS.md file",
                        description=(
                            f"AGENTS.md is {size_kb:.1f}KB which may slow context processing. "
                            "Consider trimming or splitting the file."
                        ),
                        action="Split AGENTS.md into smaller, focused files",
                        expected_benefit="Faster context loading, clearer organization",
                    )
                )
        elif self._config_dir.exists():
            recommendations.append(
                Recommendation(
                    priority=Priority.MEDIUM,
                    category="documentation",
                    title="Create AGENTS.md file",
                    description=(
                        "No AGENTS.md found. This file provides context about "
                        "your agents and project structure."
                    ),
                    action="Create ~/.codex/AGENTS.md with project documentation",
                    expected_benefit="Better project understanding, more relevant responses",
                )
            )

        # Check sandbox configuration
        sandbox_config = self._get_sandbox_config(config)
        if sandbox_config:
            if not sandbox_config.get("enabled", True):
                recommendations.append(
                    Recommendation(
                        priority=Priority.HIGH,
                        category="security",
                        title="Enable sandbox mode",
                        description=(
                            "Sandbox is disabled. This allows Codex to execute "
                            "commands without restrictions."
                        ),
                        action="Set sandbox.enabled = true in config.toml",
                        expected_benefit="Safer code execution, reduced risk",
                    )
                )
        else:
            recommendations.append(
                Recommendation(
                    priority=Priority.LOW,
                    category="security",
                    title="Configure sandbox settings",
                    description=(
                        "No explicit sandbox configuration. Consider setting "
                        "explicit sandbox policies."
                    ),
                    action="Add [sandbox] section to config.toml",
                    expected_benefit="Clear security boundaries, explicit policies",
                )
            )

        # Check for exec approval settings
        if config:
            auto_approve = config.get("auto_approve_exec", config.get("autoApproveExec"))
            if auto_approve:
                recommendations.append(
                    Recommendation(
                        priority=Priority.MEDIUM,
                        category="security",
                        title="Review auto-approve settings",
                        description=(
                            "Automatic command approval is enabled. "
                            "Review which commands are auto-approved."
                        ),
                        action="Audit auto_approve_exec patterns for security",
                        expected_benefit="Better security awareness, controlled execution",
                    )
                )

        # Check model configuration
        if config and not config.get("model") and not config.get("defaultModel"):
            recommendations.append(
                Recommendation(
                    priority=Priority.LOW,
                    category="model",
                    title="Set a default model",
                    description=(
                        "No default model configured. Setting a default "
                        "can streamline your workflow."
                    ),
                    action="Set 'model' or 'defaultModel' in config.toml",
                    expected_benefit="Consistent model usage, fewer prompts",
                )
            )

        # Sort by priority
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }
        recommendations.sort(key=lambda r: priority_order[r.priority])

        return recommendations

    def get_stats(self) -> dict[str, object]:
        """Get raw statistics about Codex configuration.

        Returns:
            Dictionary containing configuration statistics.
        """
        stats: dict[str, object] = {}

        stats["config_exists"] = self._config_dir.exists()
        stats["config_file_exists"] = self._config_file.exists()
        stats["agents_md_exists"] = self._agents_md.exists()

        if self._agents_md.exists():
            stats["agents_md_size_kb"] = round(self._agents_md.stat().st_size / 1024, 1)
            stats["agents_md_sections"] = self._count_md_sections(self._agents_md)

        config = self._load_config()
        profiles = self._get_profiles(config)
        stats["profile_count"] = len(profiles)

        if profiles:
            stats["profiles"] = list(profiles.keys())

        sandbox_config = self._get_sandbox_config(config)
        if sandbox_config:
            stats["sandbox_enabled"] = sandbox_config.get("enabled", True)

        if config:
            stats["has_api_key"] = "api_key" in config or "apiKey" in config
            stats["default_model"] = config.get("model", config.get("defaultModel", "not set"))

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

    def _load_config(self) -> dict[str, Any]:
        """Load Codex config.toml.

        Returns:
            Dictionary of configuration, or empty dict if not found.
        """
        if not self._config_file.exists():
            return {}

        try:
            with self._config_file.open() as f:
                return toml.load(f)
        except (toml.TomlDecodeError, OSError):
            return {}

    def _get_profiles(self, config: dict[str, Any]) -> dict[str, Any]:
        """Get profiles from configuration.

        Args:
            config: Configuration dictionary.

        Returns:
            Dictionary of profiles.
        """
        profiles = config.get("profiles", {})
        if isinstance(profiles, dict):
            return profiles
        return {}

    def _get_sandbox_config(self, config: dict[str, Any]) -> dict[str, Any]:
        """Get sandbox configuration.

        Args:
            config: Configuration dictionary.

        Returns:
            Sandbox configuration dictionary.
        """
        sandbox = config.get("sandbox", {})
        if isinstance(sandbox, dict):
            return sandbox
        return {}

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
