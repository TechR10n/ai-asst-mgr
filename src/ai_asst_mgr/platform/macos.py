"""macOS LaunchAgent scheduler implementation.

This module provides backup scheduling for macOS using LaunchAgent,
the native macOS mechanism for running scheduled tasks.
"""

from __future__ import annotations

import plistlib
import shutil
import subprocess
from pathlib import Path
from typing import Any

from ai_asst_mgr.platform.base import (
    IntervalType,
    PlatformScheduler,
    ScheduleInfo,
)

# LaunchAgent configuration
LAUNCH_AGENT_LABEL = "com.ai-asst-mgr.backup"
LAUNCH_AGENTS_DIR = Path.home() / "Library" / "LaunchAgents"
PLIST_FILENAME = f"{LAUNCH_AGENT_LABEL}.plist"
LOG_DIR = Path.home() / "Library" / "Logs" / "ai-asst-mgr"


def _get_launchctl_path() -> str:
    """Get the full path to the launchctl executable.

    Returns:
        Full path to launchctl, or 'launchctl' if not found (will fail gracefully).
    """
    path = shutil.which("launchctl")
    return path if path else "launchctl"


# Ordinal suffix constants for date formatting
ORDINAL_SPECIAL_START = 11
ORDINAL_SPECIAL_END = 13


class MacOSScheduler(PlatformScheduler):
    """macOS scheduler using LaunchAgent.

    This scheduler creates a LaunchAgent plist file to run scheduled
    backup tasks using macOS's native launchd system.
    """

    def __init__(self) -> None:
        """Initialize the macOS scheduler."""
        self._plist_path = LAUNCH_AGENTS_DIR / PLIST_FILENAME
        self._log_dir = LOG_DIR

    @property
    def platform_name(self) -> str:
        """Get the platform name.

        Returns:
            Platform name string.
        """
        return "macOS"

    @property
    def plist_path(self) -> Path:
        """Get the path to the LaunchAgent plist file.

        Returns:
            Path to the plist file.
        """
        return self._plist_path

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
        """Set up a LaunchAgent for scheduled backups.

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
        # Remove existing schedule first
        if self.is_scheduled():
            self.remove_schedule()

        # Ensure directories exist
        LAUNCH_AGENTS_DIR.mkdir(parents=True, exist_ok=True)
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Build the plist content
        plist_content = self._build_plist(
            script_path=script_path,
            interval=interval,
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
        )

        # Write the plist file
        try:
            with self._plist_path.open("wb") as f:
                plistlib.dump(plist_content, f)
        except OSError:
            return False

        # Load the LaunchAgent
        return self._load_agent()

    def remove_schedule(self) -> bool:
        """Remove the LaunchAgent schedule.

        Returns:
            True if removal was successful, False otherwise.
        """
        success = True

        # Unload the agent first
        if self.is_scheduled():
            success = self._unload_agent()

        # Remove the plist file
        if self._plist_path.exists():
            try:
                self._plist_path.unlink()
            except OSError:
                success = False

        return success

    def is_scheduled(self) -> bool:
        """Check if the LaunchAgent is currently loaded.

        Returns:
            True if the agent is loaded, False otherwise.
        """
        launchctl_cmd = _get_launchctl_path()
        try:
            result = subprocess.run(
                [launchctl_cmd, "list", LAUNCH_AGENT_LABEL],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return False
        else:
            return result.returncode == 0

    def get_schedule_info(self) -> ScheduleInfo:
        """Get information about the current schedule.

        Returns:
            ScheduleInfo with current schedule details.
        """
        if not self._plist_path.exists():
            return ScheduleInfo(is_active=False)

        try:
            with self._plist_path.open("rb") as f:
                plist_data = plistlib.load(f)
        except (OSError, plistlib.InvalidFileException):
            return ScheduleInfo(is_active=False)

        # Extract schedule information
        interval = self._parse_interval(plist_data)
        script_path = self._parse_script_path(plist_data)
        is_active = self.is_scheduled()

        return ScheduleInfo(
            is_active=is_active,
            interval=interval,
            script_path=script_path,
            next_run=self._get_next_run_description(plist_data) if is_active else None,
            platform_details={
                "label": LAUNCH_AGENT_LABEL,
                "plist_path": str(self._plist_path),
                "log_dir": str(self._log_dir),
            },
        )

    def _build_plist(
        self,
        script_path: Path,
        interval: IntervalType,
        hour: int,
        minute: int,
        day_of_week: int,
        day_of_month: int,
    ) -> dict[str, Any]:
        """Build the LaunchAgent plist content.

        Args:
            script_path: Path to the script to run.
            interval: Scheduling interval.
            hour: Hour to run.
            minute: Minute to run.
            day_of_week: Day of week for weekly schedules.
            day_of_month: Day of month for monthly schedules.

        Returns:
            Dictionary suitable for plist serialization.
        """
        log_stdout = self._log_dir / "backup.log"
        log_stderr = self._log_dir / "backup-error.log"

        plist: dict[str, Any] = {
            "Label": LAUNCH_AGENT_LABEL,
            "ProgramArguments": [str(script_path)],
            "StandardOutPath": str(log_stdout),
            "StandardErrorPath": str(log_stderr),
            "RunAtLoad": False,
        }

        # Build StartCalendarInterval based on interval type
        calendar_interval = self._build_calendar_interval(
            interval=interval,
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
        )
        plist["StartCalendarInterval"] = calendar_interval

        # Store interval type for later retrieval
        plist["ai_asst_mgr_interval"] = interval.value

        return plist

    def _build_calendar_interval(
        self,
        interval: IntervalType,
        hour: int,
        minute: int,
        day_of_week: int,
        day_of_month: int,
    ) -> dict[str, int]:
        """Build the StartCalendarInterval dictionary.

        Args:
            interval: Scheduling interval.
            hour: Hour to run.
            minute: Minute to run.
            day_of_week: Day of week (0=Sunday).
            day_of_month: Day of month (1-31).

        Returns:
            Calendar interval dictionary.
        """
        if interval == IntervalType.HOURLY:
            return {"Minute": minute}

        if interval == IntervalType.DAILY:
            return {"Hour": hour, "Minute": minute}

        if interval == IntervalType.WEEKLY:
            return {"Weekday": day_of_week, "Hour": hour, "Minute": minute}

        # Monthly
        return {"Day": day_of_month, "Hour": hour, "Minute": minute}

    def _load_agent(self) -> bool:
        """Load the LaunchAgent using launchctl.

        Returns:
            True if loading was successful.
        """
        launchctl_cmd = _get_launchctl_path()
        try:
            result = subprocess.run(
                [launchctl_cmd, "load", str(self._plist_path)],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return False
        else:
            return result.returncode == 0

    def _unload_agent(self) -> bool:
        """Unload the LaunchAgent using launchctl.

        Returns:
            True if unloading was successful.
        """
        launchctl_cmd = _get_launchctl_path()
        try:
            result = subprocess.run(
                [launchctl_cmd, "unload", str(self._plist_path)],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return False
        else:
            return result.returncode == 0

    def _parse_interval(self, plist_data: dict[str, Any]) -> IntervalType | None:
        """Parse the interval type from plist data.

        Args:
            plist_data: Parsed plist dictionary.

        Returns:
            IntervalType if found, None otherwise.
        """
        interval_str = plist_data.get("ai_asst_mgr_interval")
        if interval_str:
            try:
                return IntervalType(interval_str)
            except ValueError:
                pass

        # Fallback: infer from StartCalendarInterval
        calendar = plist_data.get("StartCalendarInterval", {})
        if "Day" in calendar:
            return IntervalType.MONTHLY
        if "Weekday" in calendar:
            return IntervalType.WEEKLY
        if "Hour" in calendar:
            return IntervalType.DAILY
        if "Minute" in calendar:
            return IntervalType.HOURLY

        return None

    def _parse_script_path(self, plist_data: dict[str, Any]) -> Path | None:
        """Parse the script path from plist data.

        Args:
            plist_data: Parsed plist dictionary.

        Returns:
            Path to script if found, None otherwise.
        """
        program_args = plist_data.get("ProgramArguments", [])
        if program_args:
            return Path(program_args[0])
        return None

    def _get_next_run_description(self, plist_data: dict[str, Any]) -> str:
        """Get a description of when the next run will occur.

        Args:
            plist_data: Parsed plist dictionary.

        Returns:
            Human-readable description of next run.
        """
        calendar = plist_data.get("StartCalendarInterval", {})
        interval = self._parse_interval(plist_data)

        if not interval:
            return "Unknown"

        hour = calendar.get("Hour", 0)
        minute = calendar.get("Minute", 0)
        time_str = f"{hour:02d}:{minute:02d}"

        if interval == IntervalType.HOURLY:
            return f"Every hour at :{minute:02d}"

        if interval == IntervalType.DAILY:
            return f"Daily at {time_str}"

        if interval == IntervalType.WEEKLY:
            days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            weekday = calendar.get("Weekday", 0)
            return f"Every {days[weekday]} at {time_str}"

        # Monthly - special case for 11th, 12th, 13th which use "th"
        day = calendar.get("Day", 1)
        is_special_th = ORDINAL_SPECIAL_START <= day <= ORDINAL_SPECIAL_END
        suffix = "th" if is_special_th else {1: "st", 2: "nd", 3: "rd"}.get(day % 10, "th")
        return f"Monthly on the {day}{suffix} at {time_str}"
