"""Linux cron scheduler implementation.

This module provides backup scheduling for Linux using cron,
the standard Unix job scheduler.
"""

from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path

from ai_asst_mgr.platform.base import (
    IntervalType,
    PlatformScheduler,
    ScheduleInfo,
)

# Cron configuration
CRON_MARKER = "# ai-asst-mgr backup schedule"
LOG_DIR = Path.home() / ".local" / "log" / "ai-asst-mgr"


def _get_crontab_path() -> str:
    """Get the full path to the crontab executable.

    Returns:
        Full path to crontab, or 'crontab' if not found (will fail gracefully).
    """
    path = shutil.which("crontab")
    return path if path else "crontab"


# Cron parsing constants
CRON_FIELDS_COUNT = 5
CRON_LINE_MIN_PARTS = 6
SCRIPT_PATH_INDEX = 5

# Ordinal suffix constants for date formatting
ORDINAL_SPECIAL_START = 11
ORDINAL_SPECIAL_END = 13


class LinuxScheduler(PlatformScheduler):
    """Linux scheduler using cron.

    This scheduler manages crontab entries to run scheduled
    backup tasks using the standard cron daemon.
    """

    def __init__(self) -> None:
        """Initialize the Linux scheduler."""
        self._log_dir = LOG_DIR
        self._marker = CRON_MARKER

    @property
    def platform_name(self) -> str:
        """Get the platform name.

        Returns:
            Platform name string.
        """
        return "Linux"

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
        """Set up a cron job for scheduled backups.

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

        # Ensure log directory exists
        self._log_dir.mkdir(parents=True, exist_ok=True)

        # Build the cron expression
        cron_expr = self._build_cron_expression(
            interval=interval,
            hour=hour,
            minute=minute,
            day_of_week=day_of_week,
            day_of_month=day_of_month,
        )

        # Build the full cron line
        log_file = self._log_dir / "backup.log"
        cron_line = self._build_cron_line(
            cron_expr=cron_expr,
            script_path=script_path,
            log_file=log_file,
            interval=interval,
        )

        # Add to crontab
        return self._add_cron_entry(cron_line)

    def remove_schedule(self) -> bool:
        """Remove the cron job schedule.

        Returns:
            True if removal was successful, False otherwise.
        """
        # Get current crontab
        current_crontab = self._get_crontab()
        if current_crontab is None:
            return True  # No crontab means nothing to remove

        # Filter out our entries
        lines = current_crontab.split("\n")
        filtered_lines = []
        skip_next = False

        for line in lines:
            if self._marker in line:
                skip_next = True
                continue
            if skip_next:
                skip_next = False
                continue
            filtered_lines.append(line)

        # Write back the filtered crontab
        new_crontab = "\n".join(filtered_lines)
        return self._set_crontab(new_crontab)

    def is_scheduled(self) -> bool:
        """Check if a cron job is currently scheduled.

        Returns:
            True if a schedule exists, False otherwise.
        """
        current_crontab = self._get_crontab()
        if current_crontab is None:
            return False
        return self._marker in current_crontab

    def get_schedule_info(self) -> ScheduleInfo:
        """Get information about the current schedule.

        Returns:
            ScheduleInfo with current schedule details.
        """
        if not self.is_scheduled():
            return ScheduleInfo(is_active=False)

        current_crontab = self._get_crontab()
        if current_crontab is None:
            return ScheduleInfo(is_active=False)

        # Find our cron entry
        lines = current_crontab.split("\n")
        marker_line = None
        cron_line = None

        for i, line in enumerate(lines):
            if self._marker in line:
                marker_line = line
                if i + 1 < len(lines):
                    cron_line = lines[i + 1]
                break

        if not cron_line:
            return ScheduleInfo(is_active=False)

        # Parse the cron line
        interval = self._parse_interval_from_marker(marker_line)
        script_path = self._parse_script_path(cron_line)
        cron_expr = self._parse_cron_expression(cron_line)

        return ScheduleInfo(
            is_active=True,
            interval=interval,
            script_path=script_path,
            next_run=self._get_next_run_description(cron_expr, interval),
            platform_details={
                "cron_expression": cron_expr or "unknown",
                "log_dir": str(self._log_dir),
            },
        )

    def _build_cron_expression(
        self,
        interval: IntervalType,
        hour: int,
        minute: int,
        day_of_week: int,
        day_of_month: int,
    ) -> str:
        """Build a cron expression for the given interval.

        Cron format: minute hour day-of-month month day-of-week

        Args:
            interval: Scheduling interval.
            hour: Hour to run.
            minute: Minute to run.
            day_of_week: Day of week (0=Sunday).
            day_of_month: Day of month (1-31).

        Returns:
            Cron expression string.
        """
        if interval == IntervalType.HOURLY:
            return f"{minute} * * * *"

        if interval == IntervalType.DAILY:
            return f"{minute} {hour} * * *"

        if interval == IntervalType.WEEKLY:
            return f"{minute} {hour} * * {day_of_week}"

        # Monthly
        return f"{minute} {hour} {day_of_month} * *"

    def _build_cron_line(
        self,
        cron_expr: str,
        script_path: Path,
        log_file: Path,
        interval: IntervalType,
    ) -> str:
        """Build the full cron line with marker and command.

        Args:
            cron_expr: Cron expression.
            script_path: Path to the script to run.
            log_file: Path to log file.
            interval: Interval type for marker.

        Returns:
            Full cron entry with marker comment.
        """
        marker = f"{self._marker} [interval={interval.value}]"
        command = f"{cron_expr} {script_path} >> {log_file} 2>&1"
        return f"{marker}\n{command}"

    def _get_crontab(self) -> str | None:
        """Get the current user's crontab.

        Returns:
            Crontab contents, or None if no crontab exists.
        """
        crontab_cmd = _get_crontab_path()
        try:
            result = subprocess.run(
                [crontab_cmd, "-l"],
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return None
        else:
            if result.returncode == 0:
                return result.stdout
            # Return code 1 usually means no crontab
            return None

    def _set_crontab(self, content: str) -> bool:
        """Set the current user's crontab.

        Args:
            content: New crontab content.

        Returns:
            True if successful.
        """
        crontab_cmd = _get_crontab_path()
        try:
            result = subprocess.run(
                [crontab_cmd, "-"],
                input=content,
                capture_output=True,
                text=True,
                check=False,
            )
        except OSError:
            return False
        else:
            return result.returncode == 0

    def _add_cron_entry(self, entry: str) -> bool:
        """Add an entry to the crontab.

        Args:
            entry: Cron entry to add.

        Returns:
            True if successful.
        """
        current = self._get_crontab() or ""

        # Ensure trailing newline
        if current and not current.endswith("\n"):
            current += "\n"

        new_crontab = current + entry + "\n"
        return self._set_crontab(new_crontab)

    def _parse_interval_from_marker(self, marker_line: str | None) -> IntervalType | None:
        """Parse the interval type from the marker comment.

        Args:
            marker_line: The marker comment line.

        Returns:
            IntervalType if found, None otherwise.
        """
        if not marker_line:
            return None

        # Look for [interval=xxx] in the marker

        match = re.search(r"\[interval=(\w+)\]", marker_line)
        if match:
            try:
                return IntervalType(match.group(1))
            except ValueError:
                pass

        return None

    def _parse_script_path(self, cron_line: str) -> Path | None:
        """Parse the script path from a cron line.

        Args:
            cron_line: The cron entry line.

        Returns:
            Path to script if found, None otherwise.
        """
        # Cron line format: minute hour day month weekday command
        parts = cron_line.split()
        if len(parts) >= CRON_LINE_MIN_PARTS:
            script = parts[SCRIPT_PATH_INDEX]
            return Path(script)
        return None

    def _parse_cron_expression(self, cron_line: str) -> str | None:
        """Parse the cron expression from a cron line.

        Args:
            cron_line: The cron entry line.

        Returns:
            Cron expression if found, None otherwise.
        """
        parts = cron_line.split()
        if len(parts) >= CRON_FIELDS_COUNT:
            return " ".join(parts[:CRON_FIELDS_COUNT])
        return None

    def _get_next_run_description(
        self, cron_expr: str | None, interval: IntervalType | None
    ) -> str:
        """Get a description of when the next run will occur.

        Args:
            cron_expr: The cron expression.
            interval: The interval type.

        Returns:
            Human-readable description of next run.
        """
        if not cron_expr or not interval:
            return "Unknown"

        parts = cron_expr.split()
        if len(parts) < CRON_FIELDS_COUNT:
            return "Unknown"

        minute = parts[0]
        hour = parts[1]
        day_of_month = parts[2]
        day_of_week = parts[4]

        if interval == IntervalType.HOURLY:
            return f"Every hour at :{minute.zfill(2)}"

        if interval == IntervalType.DAILY:
            return f"Daily at {hour.zfill(2)}:{minute.zfill(2)}"

        if interval == IntervalType.WEEKLY:
            days = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]
            try:
                day_name = days[int(day_of_week)]
            except (ValueError, IndexError):
                day_name = "Unknown day"
            return f"Every {day_name} at {hour.zfill(2)}:{minute.zfill(2)}"

        # Monthly - special case for 11th, 12th, 13th which use "th"
        day_int = int(day_of_month)
        is_special_th = ORDINAL_SPECIAL_START <= day_int <= ORDINAL_SPECIAL_END
        suffix = "th" if is_special_th else {1: "st", 2: "nd", 3: "rd"}.get(day_int % 10, "th")
        return f"Monthly on the {day_of_month}{suffix} at {hour.zfill(2)}:{minute.zfill(2)}"
