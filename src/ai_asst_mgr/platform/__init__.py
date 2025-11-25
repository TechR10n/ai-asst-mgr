"""Platform-specific scheduling module for AI assistant backups.

This module provides cross-platform support for scheduling automated
backup tasks using platform-native mechanisms (LaunchAgent on macOS,
cron on Linux).
"""

from __future__ import annotations

from ai_asst_mgr.platform.base import (
    IntervalType,
    PlatformScheduler,
    ScheduleInfo,
    UnsupportedPlatformError,
    get_current_platform,
    get_platform_info,
    is_linux,
    is_macos,
)

__all__ = [
    "IntervalType",
    "PlatformScheduler",
    "ScheduleInfo",
    "UnsupportedPlatformError",
    "get_current_platform",
    "get_platform_info",
    "get_scheduler",
    "is_linux",
    "is_macos",
]


def get_scheduler() -> PlatformScheduler:
    """Get the appropriate scheduler for the current platform.

    Returns:
        Platform-specific scheduler instance.

    Raises:
        UnsupportedPlatformError: If the current platform is not supported.
    """
    if is_macos():
        from ai_asst_mgr.platform.macos import MacOSScheduler

        return MacOSScheduler()

    if is_linux():
        from ai_asst_mgr.platform.linux import LinuxScheduler

        return LinuxScheduler()

    current = get_current_platform()
    msg = f"Scheduling is not supported on {current}"
    raise UnsupportedPlatformError(msg)
