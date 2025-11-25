"""Unit tests for platform-specific scheduling module."""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_asst_mgr.platform import (
    IntervalType,
    PlatformScheduler,
    ScheduleInfo,
    UnsupportedPlatformError,
    get_current_platform,
    get_platform_info,
    get_scheduler,
    is_linux,
    is_macos,
)
from ai_asst_mgr.platform.base import is_windows
from ai_asst_mgr.platform.linux import LinuxScheduler
from ai_asst_mgr.platform.macos import MacOSScheduler


class TestIntervalType:
    """Tests for IntervalType enum."""

    def test_interval_values(self) -> None:
        """Test that interval types have correct values."""
        assert IntervalType.HOURLY.value == "hourly"
        assert IntervalType.DAILY.value == "daily"
        assert IntervalType.WEEKLY.value == "weekly"
        assert IntervalType.MONTHLY.value == "monthly"

    def test_interval_descriptions(self) -> None:
        """Test that intervals have human-readable descriptions."""
        assert IntervalType.HOURLY.description == "Every hour"
        assert IntervalType.DAILY.description == "Once per day"
        assert IntervalType.WEEKLY.description == "Once per week"
        assert IntervalType.MONTHLY.description == "Once per month"

    def test_interval_from_string(self) -> None:
        """Test creating interval from string value."""
        assert IntervalType("hourly") == IntervalType.HOURLY
        assert IntervalType("daily") == IntervalType.DAILY
        assert IntervalType("weekly") == IntervalType.WEEKLY
        assert IntervalType("monthly") == IntervalType.MONTHLY

    def test_invalid_interval_raises(self) -> None:
        """Test that invalid interval string raises ValueError."""
        with pytest.raises(ValueError, match="invalid"):
            IntervalType("invalid")


class TestScheduleInfo:
    """Tests for ScheduleInfo dataclass."""

    def test_inactive_schedule(self) -> None:
        """Test creating an inactive schedule info."""
        info = ScheduleInfo(is_active=False)
        assert info.is_active is False
        assert info.interval is None
        assert info.script_path is None
        assert info.next_run is None
        assert info.platform_details is None

    def test_active_schedule(self, tmp_path: Path) -> None:
        """Test creating an active schedule info."""
        script = tmp_path / "backup.sh"
        info = ScheduleInfo(
            is_active=True,
            interval=IntervalType.DAILY,
            script_path=script,
            next_run="Daily at 02:00",
            platform_details={"key": "value"},
        )
        assert info.is_active is True
        assert info.interval == IntervalType.DAILY
        assert info.script_path == script
        assert info.next_run == "Daily at 02:00"
        assert info.platform_details == {"key": "value"}


class TestPlatformDetection:
    """Tests for platform detection functions."""

    def test_get_current_platform(self) -> None:
        """Test get_current_platform returns sys.platform."""
        assert get_current_platform() == sys.platform

    @patch("ai_asst_mgr.platform.base.sys.platform", "darwin")
    def test_is_macos_true(self) -> None:
        """Test is_macos returns True on macOS."""
        assert is_macos() is True

    @patch("ai_asst_mgr.platform.base.sys.platform", "linux")
    def test_is_macos_false(self) -> None:
        """Test is_macos returns False on non-macOS."""
        assert is_macos() is False

    @patch("ai_asst_mgr.platform.base.sys.platform", "linux")
    def test_is_linux_true(self) -> None:
        """Test is_linux returns True on Linux."""
        assert is_linux() is True

    @patch("ai_asst_mgr.platform.base.sys.platform", "linux2")
    def test_is_linux_true_linux2(self) -> None:
        """Test is_linux returns True for linux2 platform."""
        assert is_linux() is True

    @patch("ai_asst_mgr.platform.base.sys.platform", "darwin")
    def test_is_linux_false(self) -> None:
        """Test is_linux returns False on non-Linux."""
        assert is_linux() is False

    @patch("ai_asst_mgr.platform.base.sys.platform", "win32")
    def test_is_windows_true(self) -> None:
        """Test is_windows returns True on Windows."""
        assert is_windows() is True

    @patch("ai_asst_mgr.platform.base.sys.platform", "darwin")
    def test_is_windows_false(self) -> None:
        """Test is_windows returns False on non-Windows."""
        assert is_windows() is False

    def test_get_platform_info(self) -> None:
        """Test get_platform_info returns expected keys."""
        info = get_platform_info()
        assert "system" in info
        assert "release" in info
        assert "version" in info
        assert "machine" in info
        assert "python_version" in info


class TestGetScheduler:
    """Tests for get_scheduler factory function."""

    @patch("ai_asst_mgr.platform.is_macos")
    def test_get_scheduler_macos(self, mock_is_macos: MagicMock) -> None:
        """Test get_scheduler returns MacOSScheduler on macOS."""
        mock_is_macos.return_value = True
        scheduler = get_scheduler()
        assert isinstance(scheduler, MacOSScheduler)

    @patch("ai_asst_mgr.platform.is_macos")
    @patch("ai_asst_mgr.platform.is_linux")
    def test_get_scheduler_linux(self, mock_is_linux: MagicMock, mock_is_macos: MagicMock) -> None:
        """Test get_scheduler returns LinuxScheduler on Linux."""
        mock_is_macos.return_value = False
        mock_is_linux.return_value = True
        scheduler = get_scheduler()
        assert isinstance(scheduler, LinuxScheduler)

    @patch("ai_asst_mgr.platform.is_macos")
    @patch("ai_asst_mgr.platform.is_linux")
    @patch("ai_asst_mgr.platform.get_current_platform")
    def test_get_scheduler_unsupported(
        self,
        mock_get_platform: MagicMock,
        mock_is_linux: MagicMock,
        mock_is_macos: MagicMock,
    ) -> None:
        """Test get_scheduler raises on unsupported platform."""
        mock_is_macos.return_value = False
        mock_is_linux.return_value = False
        mock_get_platform.return_value = "win32"
        with pytest.raises(UnsupportedPlatformError, match="win32"):
            get_scheduler()


class TestMacOSScheduler:
    """Tests for MacOSScheduler."""

    @pytest.fixture
    def scheduler(self, tmp_path: Path) -> MacOSScheduler:
        """Create a MacOSScheduler with mocked paths."""
        scheduler = MacOSScheduler()
        scheduler._plist_path = tmp_path / "test.plist"
        scheduler._log_dir = tmp_path / "logs"
        return scheduler

    def test_platform_name(self, scheduler: MacOSScheduler) -> None:
        """Test platform_name property."""
        assert scheduler.platform_name == "macOS"

    def test_plist_path_property(self, scheduler: MacOSScheduler, tmp_path: Path) -> None:
        """Test plist_path property returns correct path."""
        assert scheduler.plist_path == tmp_path / "test.plist"

    def test_is_scheduled_false_when_not_loaded(self, scheduler: MacOSScheduler) -> None:
        """Test is_scheduled returns False when agent not loaded."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert scheduler.is_scheduled() is False

    def test_is_scheduled_true_when_loaded(self, scheduler: MacOSScheduler) -> None:
        """Test is_scheduled returns True when agent is loaded."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert scheduler.is_scheduled() is True

    def test_is_scheduled_handles_oserror(self, scheduler: MacOSScheduler) -> None:
        """Test is_scheduled handles OSError gracefully."""
        with patch("subprocess.run", side_effect=OSError):
            assert scheduler.is_scheduled() is False

    def test_get_schedule_info_not_exists(self, scheduler: MacOSScheduler) -> None:
        """Test get_schedule_info when plist doesn't exist."""
        info = scheduler.get_schedule_info()
        assert info.is_active is False
        assert info.interval is None

    def test_build_calendar_interval_hourly(self, scheduler: MacOSScheduler) -> None:
        """Test _build_calendar_interval for hourly schedule."""
        result = scheduler._build_calendar_interval(
            interval=IntervalType.HOURLY,
            hour=2,
            minute=30,
            day_of_week=0,
            day_of_month=1,
        )
        assert result == {"Minute": 30}

    def test_build_calendar_interval_daily(self, scheduler: MacOSScheduler) -> None:
        """Test _build_calendar_interval for daily schedule."""
        result = scheduler._build_calendar_interval(
            interval=IntervalType.DAILY,
            hour=14,
            minute=30,
            day_of_week=0,
            day_of_month=1,
        )
        assert result == {"Hour": 14, "Minute": 30}

    def test_build_calendar_interval_weekly(self, scheduler: MacOSScheduler) -> None:
        """Test _build_calendar_interval for weekly schedule."""
        result = scheduler._build_calendar_interval(
            interval=IntervalType.WEEKLY,
            hour=9,
            minute=0,
            day_of_week=1,
            day_of_month=1,
        )
        assert result == {"Weekday": 1, "Hour": 9, "Minute": 0}

    def test_build_calendar_interval_monthly(self, scheduler: MacOSScheduler) -> None:
        """Test _build_calendar_interval for monthly schedule."""
        result = scheduler._build_calendar_interval(
            interval=IntervalType.MONTHLY,
            hour=3,
            minute=15,
            day_of_week=0,
            day_of_month=15,
        )
        assert result == {"Day": 15, "Hour": 3, "Minute": 15}

    def test_build_plist(self, scheduler: MacOSScheduler, tmp_path: Path) -> None:
        """Test _build_plist creates correct structure."""
        script = tmp_path / "backup.sh"
        script.touch()
        plist = scheduler._build_plist(
            script_path=script,
            interval=IntervalType.DAILY,
            hour=2,
            minute=0,
            day_of_week=0,
            day_of_month=1,
        )
        assert plist["Label"] == "com.ai-asst-mgr.backup"
        assert plist["ProgramArguments"] == [str(script)]
        assert plist["RunAtLoad"] is False
        assert plist["ai_asst_mgr_interval"] == "daily"
        assert "StartCalendarInterval" in plist

    def test_parse_interval(self, scheduler: MacOSScheduler) -> None:
        """Test _parse_interval extracts interval from plist data."""
        plist_data = {"ai_asst_mgr_interval": "weekly"}
        assert scheduler._parse_interval(plist_data) == IntervalType.WEEKLY

    def test_parse_interval_fallback(self, scheduler: MacOSScheduler) -> None:
        """Test _parse_interval falls back to calendar inference."""
        plist_data = {"StartCalendarInterval": {"Weekday": 0, "Hour": 2, "Minute": 0}}
        assert scheduler._parse_interval(plist_data) == IntervalType.WEEKLY

    def test_parse_script_path(self, scheduler: MacOSScheduler) -> None:
        """Test _parse_script_path extracts path from plist data."""
        plist_data = {"ProgramArguments": ["/path/to/script.sh"]}
        result = scheduler._parse_script_path(plist_data)
        assert result == Path("/path/to/script.sh")

    def test_parse_script_path_empty(self, scheduler: MacOSScheduler) -> None:
        """Test _parse_script_path returns None for empty args."""
        plist_data = {"ProgramArguments": []}
        assert scheduler._parse_script_path(plist_data) is None

    def test_get_next_run_description_hourly(self, scheduler: MacOSScheduler) -> None:
        """Test next run description for hourly schedule."""
        plist_data = {
            "ai_asst_mgr_interval": "hourly",
            "StartCalendarInterval": {"Minute": 30},
        }
        result = scheduler._get_next_run_description(plist_data)
        assert result == "Every hour at :30"

    def test_get_next_run_description_daily(self, scheduler: MacOSScheduler) -> None:
        """Test next run description for daily schedule."""
        plist_data = {
            "ai_asst_mgr_interval": "daily",
            "StartCalendarInterval": {"Hour": 14, "Minute": 30},
        }
        result = scheduler._get_next_run_description(plist_data)
        assert result == "Daily at 14:30"

    def test_get_next_run_description_weekly(self, scheduler: MacOSScheduler) -> None:
        """Test next run description for weekly schedule."""
        plist_data = {
            "ai_asst_mgr_interval": "weekly",
            "StartCalendarInterval": {"Weekday": 1, "Hour": 9, "Minute": 0},
        }
        result = scheduler._get_next_run_description(plist_data)
        assert result == "Every Monday at 09:00"

    def test_get_next_run_description_monthly(self, scheduler: MacOSScheduler) -> None:
        """Test next run description for monthly schedule."""
        plist_data = {
            "ai_asst_mgr_interval": "monthly",
            "StartCalendarInterval": {"Day": 1, "Hour": 3, "Minute": 0},
        }
        result = scheduler._get_next_run_description(plist_data)
        assert result == "Monthly on the 1st at 03:00"

    def test_get_next_run_description_monthly_ordinals(self, scheduler: MacOSScheduler) -> None:
        """Test monthly ordinal suffixes are correct."""
        test_cases = [
            (1, "1st"),
            (2, "2nd"),
            (3, "3rd"),
            (4, "4th"),
            (11, "11th"),
            (12, "12th"),
            (13, "13th"),
            (21, "21st"),
            (22, "22nd"),
            (23, "23rd"),
        ]
        for day, expected_suffix in test_cases:
            plist_data = {
                "ai_asst_mgr_interval": "monthly",
                "StartCalendarInterval": {"Day": day, "Hour": 2, "Minute": 0},
            }
            result = scheduler._get_next_run_description(plist_data)
            assert expected_suffix in result, f"Expected {expected_suffix} for day {day}"


class TestLinuxScheduler:
    """Tests for LinuxScheduler."""

    @pytest.fixture
    def scheduler(self) -> LinuxScheduler:
        """Create a LinuxScheduler."""
        return LinuxScheduler()

    def test_platform_name(self, scheduler: LinuxScheduler) -> None:
        """Test platform_name property."""
        assert scheduler.platform_name == "Linux"

    def test_build_cron_expression_hourly(self, scheduler: LinuxScheduler) -> None:
        """Test cron expression for hourly schedule."""
        result = scheduler._build_cron_expression(
            interval=IntervalType.HOURLY,
            hour=2,
            minute=30,
            day_of_week=0,
            day_of_month=1,
        )
        assert result == "30 * * * *"

    def test_build_cron_expression_daily(self, scheduler: LinuxScheduler) -> None:
        """Test cron expression for daily schedule."""
        result = scheduler._build_cron_expression(
            interval=IntervalType.DAILY,
            hour=14,
            minute=30,
            day_of_week=0,
            day_of_month=1,
        )
        assert result == "30 14 * * *"

    def test_build_cron_expression_weekly(self, scheduler: LinuxScheduler) -> None:
        """Test cron expression for weekly schedule."""
        result = scheduler._build_cron_expression(
            interval=IntervalType.WEEKLY,
            hour=9,
            minute=0,
            day_of_week=1,
            day_of_month=1,
        )
        assert result == "0 9 * * 1"

    def test_build_cron_expression_monthly(self, scheduler: LinuxScheduler) -> None:
        """Test cron expression for monthly schedule."""
        result = scheduler._build_cron_expression(
            interval=IntervalType.MONTHLY,
            hour=3,
            minute=15,
            day_of_week=0,
            day_of_month=15,
        )
        assert result == "15 3 15 * *"

    def test_build_cron_line(self, scheduler: LinuxScheduler, tmp_path: Path) -> None:
        """Test _build_cron_line creates correct format."""
        script = tmp_path / "backup.sh"
        log = tmp_path / "backup.log"
        result = scheduler._build_cron_line(
            cron_expr="0 2 * * *",
            script_path=script,
            log_file=log,
            interval=IntervalType.DAILY,
        )
        assert "# ai-asst-mgr backup schedule" in result
        assert "[interval=daily]" in result
        assert "0 2 * * *" in result
        assert str(script) in result
        assert str(log) in result

    def test_is_scheduled_false_no_crontab(self, scheduler: LinuxScheduler) -> None:
        """Test is_scheduled returns False when no crontab."""
        with patch.object(scheduler, "_get_crontab", return_value=None):
            assert scheduler.is_scheduled() is False

    def test_is_scheduled_false_no_marker(self, scheduler: LinuxScheduler) -> None:
        """Test is_scheduled returns False when marker not in crontab."""
        with patch.object(scheduler, "_get_crontab", return_value="0 * * * * /some/other"):
            assert scheduler.is_scheduled() is False

    def test_is_scheduled_true_with_marker(self, scheduler: LinuxScheduler) -> None:
        """Test is_scheduled returns True when marker present."""
        crontab = "# ai-asst-mgr backup schedule [interval=daily]\n0 2 * * * /path"
        with patch.object(scheduler, "_get_crontab", return_value=crontab):
            assert scheduler.is_scheduled() is True

    def test_get_crontab_success(self, scheduler: LinuxScheduler) -> None:
        """Test _get_crontab returns content on success."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0, stdout="cron content")
            result = scheduler._get_crontab()
            assert result == "cron content"

    def test_get_crontab_no_crontab(self, scheduler: LinuxScheduler) -> None:
        """Test _get_crontab returns None when no crontab."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            result = scheduler._get_crontab()
            assert result is None

    def test_get_crontab_handles_oserror(self, scheduler: LinuxScheduler) -> None:
        """Test _get_crontab handles OSError gracefully."""
        with patch("subprocess.run", side_effect=OSError):
            result = scheduler._get_crontab()
            assert result is None

    def test_set_crontab_success(self, scheduler: LinuxScheduler) -> None:
        """Test _set_crontab returns True on success."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert scheduler._set_crontab("content") is True

    def test_set_crontab_failure(self, scheduler: LinuxScheduler) -> None:
        """Test _set_crontab returns False on failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert scheduler._set_crontab("content") is False

    def test_parse_interval_from_marker(self, scheduler: LinuxScheduler) -> None:
        """Test _parse_interval_from_marker extracts interval."""
        marker = "# ai-asst-mgr backup schedule [interval=weekly]"
        result = scheduler._parse_interval_from_marker(marker)
        assert result == IntervalType.WEEKLY

    def test_parse_interval_from_marker_none(self, scheduler: LinuxScheduler) -> None:
        """Test _parse_interval_from_marker returns None for invalid."""
        assert scheduler._parse_interval_from_marker(None) is None
        assert scheduler._parse_interval_from_marker("no marker") is None

    def test_parse_script_path(self, scheduler: LinuxScheduler) -> None:
        """Test _parse_script_path extracts path from cron line."""
        cron_line = "0 2 * * * /path/to/backup.sh >> /log 2>&1"
        result = scheduler._parse_script_path(cron_line)
        assert result == Path("/path/to/backup.sh")

    def test_parse_script_path_short_line(self, scheduler: LinuxScheduler) -> None:
        """Test _parse_script_path returns None for short line."""
        result = scheduler._parse_script_path("0 2 * *")
        assert result is None

    def test_parse_cron_expression(self, scheduler: LinuxScheduler) -> None:
        """Test _parse_cron_expression extracts cron timing."""
        cron_line = "30 14 * * 1 /path/to/script >> /log"
        result = scheduler._parse_cron_expression(cron_line)
        assert result == "30 14 * * 1"

    def test_get_next_run_description_hourly(self, scheduler: LinuxScheduler) -> None:
        """Test next run description for hourly schedule."""
        result = scheduler._get_next_run_description("30 * * * *", IntervalType.HOURLY)
        assert result == "Every hour at :30"

    def test_get_next_run_description_daily(self, scheduler: LinuxScheduler) -> None:
        """Test next run description for daily schedule."""
        result = scheduler._get_next_run_description("30 14 * * *", IntervalType.DAILY)
        assert result == "Daily at 14:30"

    def test_get_next_run_description_weekly(self, scheduler: LinuxScheduler) -> None:
        """Test next run description for weekly schedule."""
        result = scheduler._get_next_run_description("0 9 * * 1", IntervalType.WEEKLY)
        assert result == "Every Monday at 09:00"

    def test_get_next_run_description_monthly(self, scheduler: LinuxScheduler) -> None:
        """Test next run description for monthly schedule."""
        result = scheduler._get_next_run_description("0 3 15 * *", IntervalType.MONTHLY)
        assert result == "Monthly on the 15th at 03:00"

    def test_get_next_run_description_unknown(self, scheduler: LinuxScheduler) -> None:
        """Test next run description handles invalid input."""
        assert scheduler._get_next_run_description(None, IntervalType.DAILY) == "Unknown"
        assert scheduler._get_next_run_description("* *", IntervalType.DAILY) == "Unknown"

    def test_remove_schedule_no_crontab(self, scheduler: LinuxScheduler) -> None:
        """Test remove_schedule when no crontab exists."""
        with patch.object(scheduler, "_get_crontab", return_value=None):
            assert scheduler.remove_schedule() is True

    def test_remove_schedule_success(self, scheduler: LinuxScheduler) -> None:
        """Test remove_schedule removes entries correctly."""
        crontab = (
            "# other entry\n"
            "0 * * * * /other\n"
            "# ai-asst-mgr backup schedule [interval=daily]\n"
            "0 2 * * * /backup\n"
        )
        with (
            patch.object(scheduler, "_get_crontab", return_value=crontab),
            patch.object(scheduler, "_set_crontab", return_value=True) as mock_set,
        ):
            result = scheduler.remove_schedule()
            assert result is True
            # Verify our entries were removed
            new_crontab = mock_set.call_args[0][0]
            assert "ai-asst-mgr" not in new_crontab
            assert "# other entry" in new_crontab


class TestPlatformSchedulerABC:
    """Tests for PlatformScheduler abstract base class."""

    def test_abstract_methods(self) -> None:
        """Test that PlatformScheduler is abstract."""
        # Cannot instantiate abstract class
        with pytest.raises(TypeError):
            PlatformScheduler()  # type: ignore[abstract]

    def test_macos_implements_interface(self) -> None:
        """Test MacOSScheduler implements all abstract methods."""
        scheduler = MacOSScheduler()
        assert hasattr(scheduler, "platform_name")
        assert hasattr(scheduler, "setup_schedule")
        assert hasattr(scheduler, "remove_schedule")
        assert hasattr(scheduler, "is_scheduled")
        assert hasattr(scheduler, "get_schedule_info")

    def test_linux_implements_interface(self) -> None:
        """Test LinuxScheduler implements all abstract methods."""
        scheduler = LinuxScheduler()
        assert hasattr(scheduler, "platform_name")
        assert hasattr(scheduler, "setup_schedule")
        assert hasattr(scheduler, "remove_schedule")
        assert hasattr(scheduler, "is_scheduled")
        assert hasattr(scheduler, "get_schedule_info")


class TestMacOSSchedulerIntegration:
    """Integration tests for MacOSScheduler setup and remove."""

    @pytest.fixture
    def scheduler(self, tmp_path: Path) -> MacOSScheduler:
        """Create a MacOSScheduler with mocked paths."""
        scheduler = MacOSScheduler()
        scheduler._plist_path = tmp_path / "LaunchAgents" / "test.plist"
        scheduler._log_dir = tmp_path / "logs"
        return scheduler

    def test_setup_schedule_success(self, scheduler: MacOSScheduler, tmp_path: Path) -> None:
        """Test setup_schedule creates plist and loads agent."""
        script = tmp_path / "backup.sh"
        script.write_text("#!/bin/bash\necho backup")
        script.chmod(0o755)

        # Ensure LaunchAgents dir exists
        scheduler._plist_path.parent.mkdir(parents=True, exist_ok=True)

        with (
            patch.object(scheduler, "is_scheduled", return_value=False),
            patch.object(scheduler, "_load_agent", return_value=True),
        ):
            result = scheduler.setup_schedule(
                script_path=script,
                interval=IntervalType.DAILY,
            )
            assert result is True
            assert scheduler._plist_path.exists()

    def test_setup_schedule_removes_existing(
        self, scheduler: MacOSScheduler, tmp_path: Path
    ) -> None:
        """Test setup_schedule removes existing schedule first."""
        script = tmp_path / "backup.sh"
        script.write_text("#!/bin/bash")
        script.chmod(0o755)
        scheduler._plist_path.parent.mkdir(parents=True, exist_ok=True)

        with (
            patch.object(scheduler, "is_scheduled", return_value=True),
            patch.object(scheduler, "remove_schedule", return_value=True) as mock_remove,
            patch.object(scheduler, "_load_agent", return_value=True),
        ):
            scheduler.setup_schedule(script_path=script, interval=IntervalType.DAILY)
            mock_remove.assert_called_once()

    def test_setup_schedule_write_failure(self, scheduler: MacOSScheduler, tmp_path: Path) -> None:
        """Test setup_schedule returns False on write failure."""
        script = tmp_path / "backup.sh"
        script.write_text("#!/bin/bash")
        # Don't create LaunchAgents directory - will cause write failure
        with patch.object(scheduler, "is_scheduled", return_value=False):
            result = scheduler.setup_schedule(script_path=script, interval=IntervalType.DAILY)
            assert result is False

    def test_remove_schedule_unloads_and_deletes(
        self, scheduler: MacOSScheduler, tmp_path: Path
    ) -> None:
        """Test remove_schedule unloads agent and removes plist."""
        scheduler._plist_path.parent.mkdir(parents=True, exist_ok=True)
        scheduler._plist_path.write_text("plist content")

        with (
            patch.object(scheduler, "is_scheduled", return_value=True),
            patch.object(scheduler, "_unload_agent", return_value=True),
        ):
            result = scheduler.remove_schedule()
            assert result is True
            assert not scheduler._plist_path.exists()

    def test_remove_schedule_handles_unload_failure(
        self, scheduler: MacOSScheduler, tmp_path: Path
    ) -> None:
        """Test remove_schedule continues after unload failure."""
        scheduler._plist_path.parent.mkdir(parents=True, exist_ok=True)
        scheduler._plist_path.write_text("plist content")

        with (
            patch.object(scheduler, "is_scheduled", return_value=True),
            patch.object(scheduler, "_unload_agent", return_value=False),
        ):
            result = scheduler.remove_schedule()
            # File should still be removed even if unload fails
            assert not scheduler._plist_path.exists()
            assert result is False

    def test_get_schedule_info_with_plist(self, scheduler: MacOSScheduler, tmp_path: Path) -> None:
        """Test get_schedule_info reads from existing plist."""
        import plistlib

        scheduler._plist_path.parent.mkdir(parents=True, exist_ok=True)
        plist_data = {
            "Label": "com.ai-asst-mgr.backup",
            "ProgramArguments": ["/path/to/script.sh"],
            "ai_asst_mgr_interval": "daily",
            "StartCalendarInterval": {"Hour": 2, "Minute": 0},
        }
        with scheduler._plist_path.open("wb") as f:
            plistlib.dump(plist_data, f)

        with patch.object(scheduler, "is_scheduled", return_value=True):
            info = scheduler.get_schedule_info()
            assert info.is_active is True
            assert info.interval == IntervalType.DAILY
            assert info.script_path == Path("/path/to/script.sh")

    def test_get_schedule_info_invalid_plist(
        self, scheduler: MacOSScheduler, tmp_path: Path
    ) -> None:
        """Test get_schedule_info handles invalid plist."""
        scheduler._plist_path.parent.mkdir(parents=True, exist_ok=True)
        scheduler._plist_path.write_text("invalid plist content")

        info = scheduler.get_schedule_info()
        assert info.is_active is False

    def test_load_agent_success(self, scheduler: MacOSScheduler) -> None:
        """Test _load_agent returns True on success."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert scheduler._load_agent() is True

    def test_load_agent_failure(self, scheduler: MacOSScheduler) -> None:
        """Test _load_agent returns False on failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert scheduler._load_agent() is False

    def test_load_agent_oserror(self, scheduler: MacOSScheduler) -> None:
        """Test _load_agent handles OSError."""
        with patch("subprocess.run", side_effect=OSError):
            assert scheduler._load_agent() is False

    def test_unload_agent_success(self, scheduler: MacOSScheduler) -> None:
        """Test _unload_agent returns True on success."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            assert scheduler._unload_agent() is True

    def test_unload_agent_failure(self, scheduler: MacOSScheduler) -> None:
        """Test _unload_agent returns False on failure."""
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=1)
            assert scheduler._unload_agent() is False

    def test_unload_agent_oserror(self, scheduler: MacOSScheduler) -> None:
        """Test _unload_agent handles OSError."""
        with patch("subprocess.run", side_effect=OSError):
            assert scheduler._unload_agent() is False

    def test_parse_interval_invalid_value(self, scheduler: MacOSScheduler) -> None:
        """Test _parse_interval returns None for invalid interval value."""
        plist_data = {"ai_asst_mgr_interval": "invalid"}
        result = scheduler._parse_interval(plist_data)
        # Should fall back to calendar inference, which returns None
        assert result is None

    def test_parse_interval_from_calendar_hourly(self, scheduler: MacOSScheduler) -> None:
        """Test _parse_interval infers hourly from calendar."""
        plist_data = {"StartCalendarInterval": {"Minute": 30}}
        assert scheduler._parse_interval(plist_data) == IntervalType.HOURLY

    def test_parse_interval_from_calendar_daily(self, scheduler: MacOSScheduler) -> None:
        """Test _parse_interval infers daily from calendar."""
        plist_data = {"StartCalendarInterval": {"Hour": 2, "Minute": 0}}
        assert scheduler._parse_interval(plist_data) == IntervalType.DAILY

    def test_parse_interval_from_calendar_monthly(self, scheduler: MacOSScheduler) -> None:
        """Test _parse_interval infers monthly from calendar."""
        plist_data = {"StartCalendarInterval": {"Day": 1, "Hour": 2, "Minute": 0}}
        assert scheduler._parse_interval(plist_data) == IntervalType.MONTHLY

    def test_get_next_run_no_interval(self, scheduler: MacOSScheduler) -> None:
        """Test _get_next_run_description returns Unknown for no interval."""
        plist_data: dict[str, object] = {}
        assert scheduler._get_next_run_description(plist_data) == "Unknown"


class TestLinuxSchedulerIntegration:
    """Integration tests for LinuxScheduler setup and remove."""

    @pytest.fixture
    def scheduler(self, tmp_path: Path) -> LinuxScheduler:
        """Create a LinuxScheduler with mocked paths."""
        scheduler = LinuxScheduler()
        scheduler._log_dir = tmp_path / "logs"
        return scheduler

    def test_setup_schedule_success(self, scheduler: LinuxScheduler, tmp_path: Path) -> None:
        """Test setup_schedule creates cron entry."""
        script = tmp_path / "backup.sh"
        script.write_text("#!/bin/bash\necho backup")
        script.chmod(0o755)

        with (
            patch.object(scheduler, "is_scheduled", return_value=False),
            patch.object(scheduler, "_add_cron_entry", return_value=True) as mock_add,
        ):
            result = scheduler.setup_schedule(
                script_path=script,
                interval=IntervalType.DAILY,
            )
            assert result is True
            mock_add.assert_called_once()

    def test_setup_schedule_removes_existing(
        self, scheduler: LinuxScheduler, tmp_path: Path
    ) -> None:
        """Test setup_schedule removes existing schedule first."""
        script = tmp_path / "backup.sh"
        script.write_text("#!/bin/bash")
        script.chmod(0o755)

        with (
            patch.object(scheduler, "is_scheduled", return_value=True),
            patch.object(scheduler, "remove_schedule", return_value=True) as mock_remove,
            patch.object(scheduler, "_add_cron_entry", return_value=True),
        ):
            scheduler.setup_schedule(script_path=script, interval=IntervalType.DAILY)
            mock_remove.assert_called_once()

    def test_add_cron_entry_appends(self, scheduler: LinuxScheduler) -> None:
        """Test _add_cron_entry appends to existing crontab."""
        existing = "0 * * * * /existing\n"
        with (
            patch.object(scheduler, "_get_crontab", return_value=existing),
            patch.object(scheduler, "_set_crontab", return_value=True) as mock_set,
        ):
            scheduler._add_cron_entry("# new entry\n0 2 * * * /new")
            new_crontab = mock_set.call_args[0][0]
            assert "/existing" in new_crontab
            assert "# new entry" in new_crontab

    def test_add_cron_entry_empty_crontab(self, scheduler: LinuxScheduler) -> None:
        """Test _add_cron_entry works with empty crontab."""
        with (
            patch.object(scheduler, "_get_crontab", return_value=None),
            patch.object(scheduler, "_set_crontab", return_value=True) as mock_set,
        ):
            scheduler._add_cron_entry("# new entry\n0 2 * * * /new")
            new_crontab = mock_set.call_args[0][0]
            assert "# new entry" in new_crontab

    def test_add_cron_entry_no_trailing_newline(self, scheduler: LinuxScheduler) -> None:
        """Test _add_cron_entry adds newline if missing."""
        existing = "0 * * * * /existing"  # No trailing newline
        with (
            patch.object(scheduler, "_get_crontab", return_value=existing),
            patch.object(scheduler, "_set_crontab", return_value=True) as mock_set,
        ):
            scheduler._add_cron_entry("# new")
            new_crontab = mock_set.call_args[0][0]
            # Should have added newline between entries
            assert "/existing\n# new" in new_crontab

    def test_get_schedule_info_not_scheduled(self, scheduler: LinuxScheduler) -> None:
        """Test get_schedule_info when not scheduled."""
        with patch.object(scheduler, "is_scheduled", return_value=False):
            info = scheduler.get_schedule_info()
            assert info.is_active is False

    def test_get_schedule_info_with_crontab(self, scheduler: LinuxScheduler) -> None:
        """Test get_schedule_info reads from crontab."""
        crontab = (
            "# ai-asst-mgr backup schedule [interval=weekly]\n"
            "0 9 * * 1 /path/to/script.sh >> /log 2>&1\n"
        )
        with (
            patch.object(scheduler, "is_scheduled", return_value=True),
            patch.object(scheduler, "_get_crontab", return_value=crontab),
        ):
            info = scheduler.get_schedule_info()
            assert info.is_active is True
            assert info.interval == IntervalType.WEEKLY
            assert info.script_path == Path("/path/to/script.sh")

    def test_get_schedule_info_no_crontab(self, scheduler: LinuxScheduler) -> None:
        """Test get_schedule_info when crontab is None."""
        with (
            patch.object(scheduler, "is_scheduled", return_value=True),
            patch.object(scheduler, "_get_crontab", return_value=None),
        ):
            info = scheduler.get_schedule_info()
            assert info.is_active is False

    def test_get_schedule_info_no_cron_line(self, scheduler: LinuxScheduler) -> None:
        """Test get_schedule_info when marker exists but no cron line."""
        crontab = "# ai-asst-mgr backup schedule [interval=daily]\n"
        with (
            patch.object(scheduler, "is_scheduled", return_value=True),
            patch.object(scheduler, "_get_crontab", return_value=crontab),
        ):
            info = scheduler.get_schedule_info()
            assert info.is_active is False

    def test_set_crontab_oserror(self, scheduler: LinuxScheduler) -> None:
        """Test _set_crontab handles OSError."""
        with patch("subprocess.run", side_effect=OSError):
            assert scheduler._set_crontab("content") is False

    def test_parse_interval_invalid_marker(self, scheduler: LinuxScheduler) -> None:
        """Test _parse_interval_from_marker with invalid interval."""
        marker = "# ai-asst-mgr backup schedule [interval=invalid]"
        result = scheduler._parse_interval_from_marker(marker)
        assert result is None

    def test_get_next_run_weekly_invalid_day(self, scheduler: LinuxScheduler) -> None:
        """Test weekly next run with invalid day of week."""
        result = scheduler._get_next_run_description("0 9 * * 99", IntervalType.WEEKLY)
        assert "Unknown day" in result

    def test_get_next_run_none_interval(self, scheduler: LinuxScheduler) -> None:
        """Test next run with None interval."""
        result = scheduler._get_next_run_description("0 9 * * 1", None)
        assert result == "Unknown"
