"""Base classes for platform-specific scheduling.

This module defines the abstract interface for platform schedulers
and provides utilities for platform detection.
"""

from __future__ import annotations

import platform
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path


class IntervalType(Enum):
    """Supported scheduling intervals."""

    HOURLY = "hourly"
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"

    @property
    def description(self) -> str:
        """Get human-readable description of the interval.

        Returns:
            Description string.
        """
        descriptions = {
            IntervalType.HOURLY: "Every hour",
            IntervalType.DAILY: "Once per day",
            IntervalType.WEEKLY: "Once per week",
            IntervalType.MONTHLY: "Once per month",
        }
        return descriptions[self]


@dataclass
class ScheduleInfo:
    """Information about a scheduled task.

    Attributes:
        is_active: Whether the schedule is currently active.
        interval: The scheduling interval, if active.
        script_path: Path to the scheduled script, if active.
        next_run: Human-readable next run time, if available.
        platform_details: Platform-specific details about the schedule.
    """

    is_active: bool
    interval: IntervalType | None = None
    script_path: Path | None = None
    next_run: str | None = None
    platform_details: dict[str, str] | None = None


class PlatformScheduler(ABC):
    """Abstract base class for platform-specific schedulers.

    This class defines the interface for scheduling backup tasks
    on different operating systems.
    """

    @property
    @abstractmethod
    def platform_name(self) -> str:
        """Get the name of the platform.

        Returns:
            Platform name string.
        """

    @abstractmethod
    def setup_schedule(
        self,
        script_path: Path,
        interval: IntervalType,
        *,
        hour: int = 2,
        minute: int = 0,
        day_of_week: int = 0,
        day_of_month: int = 1,
    ) -> bool:
        """Set up a scheduled backup task.

        Args:
            script_path: Path to the backup script to run.
            interval: How often to run the backup.
            hour: Hour to run (0-23), default 2 AM.
            minute: Minute to run (0-59), default 0.
            day_of_week: Day of week for weekly (0=Sunday), default Sunday.
            day_of_month: Day of month for monthly (1-31), default 1st.

        Returns:
            True if setup was successful, False otherwise.
        """

    @abstractmethod
    def remove_schedule(self) -> bool:
        """Remove the scheduled backup task.

        Returns:
            True if removal was successful, False otherwise.
        """

    @abstractmethod
    def is_scheduled(self) -> bool:
        """Check if a backup schedule is currently active.

        Returns:
            True if a schedule exists, False otherwise.
        """

    @abstractmethod
    def get_schedule_info(self) -> ScheduleInfo:
        """Get information about the current schedule.

        Returns:
            ScheduleInfo with current schedule details.
        """


class UnsupportedPlatformError(Exception):
    """Raised when the current platform is not supported for scheduling."""


def get_current_platform() -> str:
    """Get the current operating system platform.

    Returns:
        Platform name: 'darwin' for macOS, 'linux' for Linux, 'windows' for Windows.
    """
    return sys.platform


def is_macos() -> bool:
    """Check if running on macOS.

    Returns:
        True if running on macOS.
    """
    return sys.platform == "darwin"


def is_linux() -> bool:
    """Check if running on Linux.

    Returns:
        True if running on Linux.
    """
    return sys.platform.startswith("linux")


def is_windows() -> bool:
    """Check if running on Windows.

    Returns:
        True if running on Windows.
    """
    return sys.platform == "win32"


def get_platform_info() -> dict[str, str]:
    """Get detailed platform information.

    Returns:
        Dictionary with platform details.
    """
    return {
        "system": platform.system(),
        "release": platform.release(),
        "version": platform.version(),
        "machine": platform.machine(),
        "python_version": platform.python_version(),
    }
