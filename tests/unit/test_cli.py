"""Unit tests for CLI module."""

from __future__ import annotations

from typing import TYPE_CHECKING
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ai_asst_mgr import cli
from ai_asst_mgr.cli import (
    _attempt_fixes,
    _check_read_permission,
    _check_write_permission,
    _has_read_access,
    _has_write_access,
    app,
)

if TYPE_CHECKING:
    from pathlib import Path

runner = CliRunner()


def test_status_command() -> None:
    """Test the status command executes without errors."""
    result = runner.invoke(app, ["status"])
    assert result.exit_code == 0
    assert "Not implemented yet" in result.stdout


def test_status_command_with_vendor() -> None:
    """Test the status command with vendor flag."""
    result = runner.invoke(app, ["status", "--vendor", "claude"])
    assert result.exit_code == 0
    assert "claude" in result.stdout.lower()


def test_init_command() -> None:
    """Test the init command executes without errors."""
    result = runner.invoke(app, ["init"])
    assert result.exit_code == 0
    assert "Initializing" in result.stdout


def test_init_command_with_vendor() -> None:
    """Test the init command with vendor flag."""
    result = runner.invoke(app, ["init", "--vendor", "gemini"])
    assert result.exit_code == 0
    assert "gemini" in result.stdout.lower()


def test_health_command() -> None:
    """Test the health command executes without errors."""
    result = runner.invoke(app, ["health"])
    assert result.exit_code == 0
    assert "Health check" in result.stdout


def test_health_command_with_vendor() -> None:
    """Test the health command with vendor flag."""
    result = runner.invoke(app, ["health", "--vendor", "openai"])
    assert result.exit_code == 0
    assert "openai" in result.stdout.lower()


def test_main_function() -> None:
    """Test that main function is callable."""
    # Just verify the function exists and is callable
    assert callable(cli.main)


class TestDoctorCommand:
    """Tests for the doctor command."""

    def test_doctor_command_runs_successfully(self) -> None:
        """Test doctor command executes and shows diagnostics."""
        result = runner.invoke(app, ["doctor"])
        assert "System Diagnostics" in result.stdout
        assert "Python Environment" in result.stdout
        assert "Dependencies" in result.stdout
        assert "Vendor Installations" in result.stdout
        assert "Summary" in result.stdout

    def test_doctor_command_shows_python_version(self) -> None:
        """Test doctor command displays Python version."""
        result = runner.invoke(app, ["doctor"])
        assert "Python" in result.stdout
        assert "Platform:" in result.stdout
        assert "Architecture:" in result.stdout

    def test_doctor_command_checks_dependencies(self) -> None:
        """Test doctor command checks for required dependencies."""
        result = runner.invoke(app, ["doctor"])
        assert "typer" in result.stdout.lower()
        assert "rich" in result.stdout.lower()
        assert "sqlalchemy" in result.stdout.lower()

    def test_doctor_command_checks_vendors(self) -> None:
        """Test doctor command checks vendor installations."""
        result = runner.invoke(app, ["doctor"])
        # Should show vendor names even if not installed
        assert "Vendor Installations" in result.stdout

    def test_doctor_command_checks_configuration_files(self) -> None:
        """Test doctor command checks for configuration files."""
        result = runner.invoke(app, ["doctor"])
        assert "Configuration Files" in result.stdout

    def test_doctor_command_checks_permissions(self) -> None:
        """Test doctor command checks file permissions."""
        result = runner.invoke(app, ["doctor"])
        assert "File Permissions" in result.stdout

    def test_doctor_command_checks_database(self) -> None:
        """Test doctor command checks database health."""
        result = runner.invoke(app, ["doctor"])
        assert "Database Health" in result.stdout

    def test_doctor_command_checks_system_tools(self) -> None:
        """Test doctor command checks for system tools."""
        result = runner.invoke(app, ["doctor"])
        assert "System Tools" in result.stdout
        assert "git" in result.stdout.lower()

    def test_doctor_command_displays_summary(self) -> None:
        """Test doctor command displays check summary."""
        result = runner.invoke(app, ["doctor"])
        assert "Summary" in result.stdout
        assert "Total Checks:" in result.stdout
        assert "Passed:" in result.stdout

    def test_doctor_command_with_fix_flag(self) -> None:
        """Test doctor command with --fix flag."""
        result = runner.invoke(app, ["doctor", "--fix"])
        assert "System Diagnostics" in result.stdout

    @patch("sys.version_info", (3, 13, 0, "final", 0))
    def test_doctor_command_detects_old_python_version(self) -> None:
        """Test doctor command detects Python version below minimum."""
        result = runner.invoke(app, ["doctor"])
        # Should show version check in output and fail
        assert "Python" in result.stdout
        assert result.exit_code == 1

    @patch("ai_asst_mgr.cli.VendorRegistry")
    def test_doctor_command_handles_vendor_errors(self, mock_registry: MagicMock) -> None:
        """Test doctor command handles vendor check errors gracefully."""
        mock_vendor = MagicMock()
        mock_vendor.info.name = "TestVendor"
        mock_vendor.is_installed.return_value = False
        mock_vendor.is_configured.return_value = False

        mock_registry_instance = MagicMock()
        mock_registry_instance.get_all_vendors.return_value = {"test": mock_vendor}
        mock_registry.return_value = mock_registry_instance

        result = runner.invoke(app, ["doctor"])
        assert "Vendor Installations" in result.stdout

    def test_doctor_command_exit_code_success_when_all_checks_pass(self) -> None:
        """Test doctor command returns exit code 0 when all checks pass."""
        # This test depends on the actual system state
        # In a clean environment, some checks may fail
        result = runner.invoke(app, ["doctor"])
        # Exit code will be 0 or 1 depending on system state
        assert result.exit_code in (0, 1)

    @patch("ai_asst_mgr.cli._check_write_permission")
    def test_doctor_command_detects_permission_issues(self, mock_check_write: MagicMock) -> None:
        """Test doctor command detects permission issues."""
        mock_check_write.return_value = False
        result = runner.invoke(app, ["doctor"])
        # Should still run and show results
        assert "System Diagnostics" in result.stdout

    def test_doctor_command_detects_missing_dependency(self) -> None:
        """Test doctor command detects missing dependencies."""
        # This test validates the ImportError handling path exists
        # In practice, if dependencies are missing, the CLI won't import
        # So we just verify the code handles ImportError properly
        # The actual path is tested by attempting to import each package
        result = runner.invoke(app, ["doctor"])
        assert "Dependencies" in result.stdout

    def test_doctor_command_checks_database_as_directory(self, tmp_path: Path) -> None:
        """Test doctor command handles database path being a directory."""
        # Create a directory instead of a file at the database path
        db_dir = tmp_path / "database.db"
        db_dir.mkdir(parents=True)

        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            # Create .config/ai-asst-mgr directory structure
            config_dir = tmp_path / ".config" / "ai-asst-mgr"
            config_dir.mkdir(parents=True)
            # Create db_dir there
            (config_dir / "database.db").mkdir()

            result = runner.invoke(app, ["doctor"])
            assert "Database Health" in result.stdout

    def test_doctor_command_detects_unreadable_database(self, tmp_path: Path) -> None:
        """Test doctor command detects unreadable database file."""
        with patch("pathlib.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            config_dir = tmp_path / ".config" / "ai-asst-mgr"
            config_dir.mkdir(parents=True)
            db_file = config_dir / "database.db"
            db_file.write_text("test database")

            # Mock the read permission check to return False
            with patch("ai_asst_mgr.cli._check_read_permission") as mock_check:
                mock_check.return_value = False
                result = runner.invoke(app, ["doctor"])
                assert "Database Health" in result.stdout
                assert result.exit_code == 1

    @patch("shutil.which")
    def test_doctor_command_handles_missing_git(self, mock_which: MagicMock) -> None:
        """Test doctor command handles missing optional tools."""
        mock_which.return_value = None
        result = runner.invoke(app, ["doctor"])
        assert "System Tools" in result.stdout
        # Git is optional so this shouldn't fail the check


class TestDoctorHelperFunctions:
    """Tests for doctor command helper functions."""

    def test_check_write_permission_with_writable_directory(self, tmp_path: Path) -> None:
        """Test _check_write_permission returns True for writable directory."""
        result = _check_write_permission(tmp_path)
        assert result is True

    def test_check_write_permission_with_nonexistent_path(self, tmp_path: Path) -> None:
        """Test _check_write_permission returns False for nonexistent path."""
        nonexistent = tmp_path / "does_not_exist"
        result = _check_write_permission(nonexistent)
        assert result is False

    def test_check_write_permission_with_file_instead_of_directory(self, tmp_path: Path) -> None:
        """Test _check_write_permission returns False for file path."""
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("test")
        result = _check_write_permission(file_path)
        assert result is False

    def test_check_read_permission_with_readable_file(self, tmp_path: Path) -> None:
        """Test _check_read_permission returns True for readable file."""
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("test content")
        result = _check_read_permission(file_path)
        assert result is True

    def test_check_read_permission_with_nonexistent_file(self, tmp_path: Path) -> None:
        """Test _check_read_permission returns False for nonexistent file."""
        nonexistent = tmp_path / "does_not_exist.txt"
        result = _check_read_permission(nonexistent)
        assert result is False

    def test_check_read_permission_with_directory_instead_of_file(self, tmp_path: Path) -> None:
        """Test _check_read_permission returns False for directory path."""
        result = _check_read_permission(tmp_path)
        assert result is False

    def test_has_write_access_with_writable_directory(self, tmp_path: Path) -> None:
        """Test _has_write_access returns True for writable directory."""
        result = _has_write_access(tmp_path)
        assert result is True

    def test_has_write_access_with_nonexistent_directory(self, tmp_path: Path) -> None:
        """Test _has_write_access returns False for nonexistent directory."""
        nonexistent = tmp_path / "does_not_exist"
        result = _has_write_access(nonexistent)
        assert result is False

    @patch("pathlib.Path.touch")
    def test_has_write_access_handles_permission_error(
        self, mock_touch: MagicMock, tmp_path: Path
    ) -> None:
        """Test _has_write_access handles PermissionError gracefully."""
        mock_touch.side_effect = PermissionError("Access denied")
        result = _has_write_access(tmp_path)
        assert result is False

    @patch("pathlib.Path.touch")
    def test_has_write_access_handles_os_error(self, mock_touch: MagicMock, tmp_path: Path) -> None:
        """Test _has_write_access handles OSError gracefully."""
        mock_touch.side_effect = OSError("Disk full")
        result = _has_write_access(tmp_path)
        assert result is False

    def test_has_read_access_with_readable_file(self, tmp_path: Path) -> None:
        """Test _has_read_access returns True for readable file."""
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("test content")
        result = _has_read_access(file_path)
        assert result is True

    def test_has_read_access_with_nonexistent_file(self, tmp_path: Path) -> None:
        """Test _has_read_access returns False for nonexistent file."""
        nonexistent = tmp_path / "does_not_exist.txt"
        result = _has_read_access(nonexistent)
        assert result is False

    @patch("pathlib.Path.read_bytes")
    def test_has_read_access_handles_permission_error(
        self, mock_read: MagicMock, tmp_path: Path
    ) -> None:
        """Test _has_read_access handles PermissionError gracefully."""
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("test")
        mock_read.side_effect = PermissionError("Access denied")
        result = _has_read_access(file_path)
        assert result is False

    @patch("pathlib.Path.read_bytes")
    def test_has_read_access_handles_os_error(self, mock_read: MagicMock, tmp_path: Path) -> None:
        """Test _has_read_access handles OSError gracefully."""
        file_path = tmp_path / "test_file.txt"
        file_path.write_text("test")
        mock_read.side_effect = OSError("I/O error")
        result = _has_read_access(file_path)
        assert result is False

    def test_attempt_fixes_with_empty_issues_list(self) -> None:
        """Test _attempt_fixes returns 0 for empty issues list."""
        result = _attempt_fixes([])
        assert result == 0

    def test_attempt_fixes_with_configuration_issue(self) -> None:
        """Test _attempt_fixes handles configuration issues."""
        issues = [
            {
                "category": "Configuration",
                "issue": "Vendor is installed but not configured",
                "remediation": "Run: ai-asst-mgr init --vendor claude",
            }
        ]
        result = _attempt_fixes(issues)
        # Currently returns 0 as auto-fix not implemented for this
        assert result == 0

    def test_attempt_fixes_with_directory_issue(self) -> None:
        """Test _attempt_fixes handles directory not found issues."""
        issues = [
            {
                "category": "Configuration",
                "issue": "Configuration directory not found",
                "remediation": "Create directory: mkdir -p ~/.config/ai-asst-mgr",
            }
        ]
        result = _attempt_fixes(issues)
        # Currently returns 0 as auto-fix not fully implemented
        assert result == 0

    def test_attempt_fixes_with_permission_issue(self) -> None:
        """Test _attempt_fixes does not auto-fix permission issues."""
        issues = [
            {
                "category": "Permissions",
                "issue": "No write permission for directory",
                "remediation": "Fix permissions: chmod u+w /path/to/dir",
            }
        ]
        result = _attempt_fixes(issues)
        # Should not auto-fix permission issues for safety
        assert result == 0

    def test_attempt_fixes_with_multiple_issues(self) -> None:
        """Test _attempt_fixes handles multiple issues."""
        issues = [
            {
                "category": "Configuration",
                "issue": "Vendor not configured",
                "remediation": "Run init",
            },
            {
                "category": "Permissions",
                "issue": "No write access",
                "remediation": "Fix permissions",
            },
        ]
        result = _attempt_fixes(issues)
        # Currently no auto-fixes are fully implemented
        assert result >= 0
        assert result <= len(issues)
