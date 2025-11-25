"""Base audit framework for AI assistant configuration validation.

This module provides the foundation for auditing AI assistant configurations
across all supported vendors, including security, configuration quality,
and usage pattern checks.
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path


class AuditCategory(Enum):
    """Categories of audit checks."""

    SECURITY = "security"
    CONFIG = "config"
    USAGE = "usage"
    QUALITY = "quality"


class AuditSeverity(Enum):
    """Severity levels for audit findings."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

    def __lt__(self, other: object) -> bool:
        """Compare severity levels."""
        if not isinstance(other, AuditSeverity):
            return NotImplemented
        order = [
            AuditSeverity.INFO,
            AuditSeverity.WARNING,
            AuditSeverity.ERROR,
            AuditSeverity.CRITICAL,
        ]
        return order.index(self) < order.index(other)

    def __ge__(self, other: object) -> bool:
        """Compare severity levels for greater than or equal."""
        if not isinstance(other, AuditSeverity):
            return NotImplemented
        return not self.__lt__(other)


@dataclass
class AuditCheck:
    """Result of a single audit check."""

    name: str
    category: AuditCategory
    severity: AuditSeverity
    passed: bool
    message: str
    recommendation: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass
class AuditReport:
    """Complete audit report for a vendor."""

    vendor_id: str
    timestamp: str
    checks: list[AuditCheck] = field(default_factory=list)

    @property
    def total_checks(self) -> int:
        """Get total number of checks performed."""
        return len(self.checks)

    @property
    def passed_checks(self) -> int:
        """Get number of passed checks."""
        return sum(1 for c in self.checks if c.passed)

    @property
    def failed_checks(self) -> int:
        """Get number of failed checks."""
        return sum(1 for c in self.checks if not c.passed)

    @property
    def critical_count(self) -> int:
        """Get count of critical severity findings."""
        return sum(1 for c in self.checks if not c.passed and c.severity == AuditSeverity.CRITICAL)

    @property
    def error_count(self) -> int:
        """Get count of error severity findings."""
        return sum(1 for c in self.checks if not c.passed and c.severity == AuditSeverity.ERROR)

    @property
    def warning_count(self) -> int:
        """Get count of warning severity findings."""
        return sum(1 for c in self.checks if not c.passed and c.severity == AuditSeverity.WARNING)

    @property
    def info_count(self) -> int:
        """Get count of info severity findings."""
        return sum(1 for c in self.checks if not c.passed and c.severity == AuditSeverity.INFO)

    @property
    def score(self) -> float:
        """Calculate audit score (0-100)."""
        if self.total_checks == 0:
            return 100.0
        return (self.passed_checks / self.total_checks) * 100

    def filter_by_severity(self, min_severity: AuditSeverity) -> list[AuditCheck]:
        """Filter checks by minimum severity level.

        Args:
            min_severity: Minimum severity to include.

        Returns:
            List of checks at or above the severity level.
        """
        return [c for c in self.checks if not c.passed and c.severity >= min_severity]

    def filter_by_category(self, category: AuditCategory) -> list[AuditCheck]:
        """Filter checks by category.

        Args:
            category: Category to filter by.

        Returns:
            List of checks in the specified category.
        """
        return [c for c in self.checks if c.category == category]

    def to_dict(self) -> dict[str, Any]:
        """Convert report to dictionary.

        Returns:
            Dictionary representation of the report.
        """
        return {
            "vendor_id": self.vendor_id,
            "timestamp": self.timestamp,
            "summary": {
                "total_checks": self.total_checks,
                "passed": self.passed_checks,
                "failed": self.failed_checks,
                "score": round(self.score, 2),
                "by_severity": {
                    "critical": self.critical_count,
                    "error": self.error_count,
                    "warning": self.warning_count,
                    "info": self.info_count,
                },
            },
            "checks": [
                {
                    "name": c.name,
                    "category": c.category.value,
                    "severity": c.severity.value,
                    "passed": c.passed,
                    "message": c.message,
                    "recommendation": c.recommendation,
                    "details": c.details,
                }
                for c in self.checks
            ],
        }

    def to_json(self, indent: int = 2) -> str:
        """Convert report to JSON string.

        Args:
            indent: JSON indentation level.

        Returns:
            JSON string representation.
        """
        return json.dumps(self.to_dict(), indent=indent)


class BaseAuditor(ABC):
    """Base class for vendor-specific auditors.

    This abstract class defines the interface for auditing AI assistant
    configurations. Each vendor implementation should override the
    audit methods to perform vendor-specific checks.
    """

    def __init__(self, vendor_id: str, config_dir: Path) -> None:
        """Initialize the auditor.

        Args:
            vendor_id: Vendor identifier.
            config_dir: Path to vendor configuration directory.
        """
        self.vendor_id = vendor_id
        self.config_dir = config_dir
        self._checks: list[AuditCheck] = []

    def run_audit(self) -> AuditReport:
        """Run all audit checks and generate report.

        Returns:
            Complete audit report.
        """
        self._checks = []

        self.audit_security()
        self.audit_configuration()
        self.audit_quality()
        self.audit_usage()

        return AuditReport(
            vendor_id=self.vendor_id,
            timestamp=datetime.now(tz=UTC).isoformat(),
            checks=self._checks,
        )

    def _add_check(self, check: AuditCheck) -> None:
        """Add a check result to the audit.

        Args:
            check: The audit check result to add.
        """
        self._checks.append(check)

    @abstractmethod
    def audit_security(self) -> None:
        """Run security-related audit checks."""

    @abstractmethod
    def audit_configuration(self) -> None:
        """Run configuration validity checks."""

    @abstractmethod
    def audit_quality(self) -> None:
        """Run quality assessment checks."""

    @abstractmethod
    def audit_usage(self) -> None:
        """Run usage pattern checks."""
