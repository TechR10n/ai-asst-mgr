"""Base classes and interfaces for coaching system.

This module defines the abstract base class that all vendor-specific coaches
must implement, along with common data structures for insights and recommendations.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from datetime import datetime
    from pathlib import Path


class Priority(Enum):
    """Priority levels for recommendations.

    Attributes:
        LOW: Minor optimization, nice to have.
        MEDIUM: Moderate improvement opportunity.
        HIGH: Significant improvement needed.
        CRITICAL: Urgent action required.
    """

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass(frozen=True)
class Insight:
    """A data-driven insight from usage analysis.

    Attributes:
        category: Category of the insight (e.g., "agents", "tools", "sessions").
        title: Short title describing the insight.
        description: Detailed description of what was observed.
        metric_name: Name of the metric analyzed.
        metric_value: Value of the metric.
        metric_unit: Unit of measurement (e.g., "count", "hours", "percent").
    """

    category: str
    title: str
    description: str
    metric_name: str
    metric_value: float | int | str
    metric_unit: str = ""


@dataclass(frozen=True)
class Recommendation:
    """An actionable recommendation for improving AI assistant usage.

    Attributes:
        priority: Priority level for this recommendation.
        category: Category of the recommendation.
        title: Short title for the recommendation.
        description: Detailed explanation of the recommendation.
        action: Specific action the user should take.
        expected_benefit: What improvement the user can expect.
    """

    priority: Priority
    category: str
    title: str
    description: str
    action: str
    expected_benefit: str


@dataclass
class UsageReport:
    """Complete usage report from a coach.

    Attributes:
        vendor_id: Identifier for the vendor (e.g., "claude", "gemini").
        vendor_name: Human-readable vendor name.
        generated_at: Timestamp when the report was generated.
        period_start: Start of the analysis period.
        period_end: End of the analysis period.
        insights: List of insights discovered.
        recommendations: List of recommendations.
        stats: Dictionary of raw statistics.
    """

    vendor_id: str
    vendor_name: str
    generated_at: datetime
    period_start: datetime | None
    period_end: datetime | None
    insights: list[Insight] = field(default_factory=list)
    recommendations: list[Recommendation] = field(default_factory=list)
    stats: dict[str, object] = field(default_factory=dict)


class CoachBase(ABC):
    """Abstract base class for all vendor-specific coaches.

    This class defines the interface that all coach implementations must follow
    to provide consistent usage analysis and recommendations across vendors.
    """

    @property
    @abstractmethod
    def vendor_id(self) -> str:
        """Get the vendor identifier.

        Returns:
            Unique identifier for this vendor (e.g., "claude", "gemini", "openai").
        """

    @property
    @abstractmethod
    def vendor_name(self) -> str:
        """Get the human-readable vendor name.

        Returns:
            Human-readable vendor name (e.g., "Claude Code", "Gemini CLI").
        """

    @abstractmethod
    def analyze(self, period_days: int = 7) -> UsageReport:
        """Analyze usage patterns and generate a report.

        Args:
            period_days: Number of days to analyze. Defaults to 7.

        Returns:
            UsageReport containing insights and recommendations.
        """

    @abstractmethod
    def get_insights(self) -> list[Insight]:
        """Get current insights from analysis.

        Returns:
            List of Insight objects.
        """

    @abstractmethod
    def get_recommendations(self) -> list[Recommendation]:
        """Get current recommendations from analysis.

        Returns:
            List of Recommendation objects sorted by priority.
        """

    @abstractmethod
    def get_stats(self) -> dict[str, object]:
        """Get raw usage statistics.

        Returns:
            Dictionary containing raw statistics.
        """

    @abstractmethod
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
