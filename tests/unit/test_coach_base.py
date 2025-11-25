"""Unit tests for coach base classes and data models."""

from datetime import UTC, datetime

import pytest

from ai_asst_mgr.coaches.base import (
    Insight,
    Priority,
    Recommendation,
    UsageReport,
)


class TestPriority:
    """Tests for Priority enum."""

    def test_priority_values(self) -> None:
        """Test Priority enum has expected values."""
        assert Priority.LOW.value == "low"
        assert Priority.MEDIUM.value == "medium"
        assert Priority.HIGH.value == "high"
        assert Priority.CRITICAL.value == "critical"

    def test_priority_ordering(self) -> None:
        """Test Priority values can be used for ordering."""
        priorities = [Priority.LOW, Priority.HIGH, Priority.CRITICAL, Priority.MEDIUM]
        priority_order = {
            Priority.CRITICAL: 0,
            Priority.HIGH: 1,
            Priority.MEDIUM: 2,
            Priority.LOW: 3,
        }
        sorted_priorities = sorted(priorities, key=lambda p: priority_order[p])
        assert sorted_priorities == [
            Priority.CRITICAL,
            Priority.HIGH,
            Priority.MEDIUM,
            Priority.LOW,
        ]


class TestInsight:
    """Tests for Insight dataclass."""

    def test_insight_creation(self) -> None:
        """Test Insight can be created with all fields."""
        insight = Insight(
            category="agents",
            title="Agent Configuration",
            description="Found 5 agents",
            metric_name="agent_count",
            metric_value=5,
            metric_unit="agents",
        )

        assert insight.category == "agents"
        assert insight.title == "Agent Configuration"
        assert insight.description == "Found 5 agents"
        assert insight.metric_name == "agent_count"
        assert insight.metric_value == 5
        assert insight.metric_unit == "agents"

    def test_insight_with_string_value(self) -> None:
        """Test Insight with string metric value."""
        insight = Insight(
            category="model",
            title="Default Model",
            description="Using claude-3-opus",
            metric_name="default_model",
            metric_value="claude-3-opus",
            metric_unit="",
        )

        assert insight.metric_value == "claude-3-opus"
        assert insight.metric_unit == ""

    def test_insight_with_float_value(self) -> None:
        """Test Insight with float metric value."""
        insight = Insight(
            category="storage",
            title="File Size",
            description="Total configuration size",
            metric_name="total_size",
            metric_value=2.5,
            metric_unit="KB",
        )

        assert insight.metric_value == 2.5

    def test_insight_is_frozen(self) -> None:
        """Test Insight is immutable."""
        insight = Insight(
            category="test",
            title="Test",
            description="Test",
            metric_name="test",
            metric_value=1,
        )

        with pytest.raises(AttributeError):
            insight.category = "new_category"  # type: ignore[misc]


class TestRecommendation:
    """Tests for Recommendation dataclass."""

    def test_recommendation_creation(self) -> None:
        """Test Recommendation can be created with all fields."""
        rec = Recommendation(
            priority=Priority.HIGH,
            category="agents",
            title="Create custom agents",
            description="No agents found in configuration",
            action="Create ~/.claude/agents/ directory",
            expected_benefit="Better task understanding",
        )

        assert rec.priority == Priority.HIGH
        assert rec.category == "agents"
        assert rec.title == "Create custom agents"
        assert rec.description == "No agents found in configuration"
        assert rec.action == "Create ~/.claude/agents/ directory"
        assert rec.expected_benefit == "Better task understanding"

    def test_recommendation_is_frozen(self) -> None:
        """Test Recommendation is immutable."""
        rec = Recommendation(
            priority=Priority.LOW,
            category="test",
            title="Test",
            description="Test",
            action="Test",
            expected_benefit="Test",
        )

        with pytest.raises(AttributeError):
            rec.priority = Priority.HIGH  # type: ignore[misc]


class TestUsageReport:
    """Tests for UsageReport dataclass."""

    def test_usage_report_creation(self) -> None:
        """Test UsageReport can be created with minimal fields."""
        now = datetime.now(tz=UTC)
        report = UsageReport(
            vendor_id="claude",
            vendor_name="Claude Code",
            generated_at=now,
            period_start=None,
            period_end=now,
        )

        assert report.vendor_id == "claude"
        assert report.vendor_name == "Claude Code"
        assert report.generated_at == now
        assert report.period_start is None
        assert report.period_end == now
        assert report.insights == []
        assert report.recommendations == []
        assert report.stats == {}

    def test_usage_report_with_insights(self) -> None:
        """Test UsageReport with insights."""
        now = datetime.now(tz=UTC)
        insights = [
            Insight(
                category="agents",
                title="Agent Count",
                description="Found agents",
                metric_name="count",
                metric_value=5,
            ),
        ]

        report = UsageReport(
            vendor_id="claude",
            vendor_name="Claude Code",
            generated_at=now,
            period_start=None,
            period_end=now,
            insights=insights,
        )

        assert len(report.insights) == 1
        assert report.insights[0].category == "agents"

    def test_usage_report_with_recommendations(self) -> None:
        """Test UsageReport with recommendations."""
        now = datetime.now(tz=UTC)
        recommendations = [
            Recommendation(
                priority=Priority.HIGH,
                category="agents",
                title="Create agents",
                description="No agents found",
                action="Create agents",
                expected_benefit="Better assistance",
            ),
        ]

        report = UsageReport(
            vendor_id="claude",
            vendor_name="Claude Code",
            generated_at=now,
            period_start=None,
            period_end=now,
            recommendations=recommendations,
        )

        assert len(report.recommendations) == 1
        assert report.recommendations[0].priority == Priority.HIGH

    def test_usage_report_with_stats(self) -> None:
        """Test UsageReport with stats."""
        now = datetime.now(tz=UTC)
        stats = {
            "agent_count": 5,
            "skill_count": 10,
            "config_exists": True,
        }

        report = UsageReport(
            vendor_id="claude",
            vendor_name="Claude Code",
            generated_at=now,
            period_start=None,
            period_end=now,
            stats=stats,
        )

        assert report.stats["agent_count"] == 5
        assert report.stats["config_exists"] is True

    def test_usage_report_is_mutable(self) -> None:
        """Test UsageReport allows modification (not frozen)."""
        now = datetime.now(tz=UTC)
        report = UsageReport(
            vendor_id="claude",
            vendor_name="Claude Code",
            generated_at=now,
            period_start=None,
            period_end=now,
        )

        # Should not raise - UsageReport is not frozen
        report.insights.append(
            Insight(
                category="test",
                title="Test",
                description="Test",
                metric_name="test",
                metric_value=1,
            )
        )
        assert len(report.insights) == 1
