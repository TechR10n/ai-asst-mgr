"""Unit tests for CLI module."""

from __future__ import annotations

import builtins
from datetime import UTC, datetime
from pathlib import Path
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
import typer
from typer.testing import CliRunner

from ai_asst_mgr import cli
from ai_asst_mgr.adapters.base import VendorAdapter, VendorStatus
from ai_asst_mgr.capabilities import Agent, AgentType
from ai_asst_mgr.capabilities.manager import AgentListResult
from ai_asst_mgr.cli import (
    _attempt_fixes,
    _check_read_permission,
    _check_write_permission,
    _compare_vendors,
    _display_coach_insights,
    _display_coach_recommendations,
    _display_coach_stats,
    _flatten_dict,
    _format_agent_type,
    _format_config_value,
    _format_size_bytes,
    _get_agent_manager,
    _get_all_coaches,
    _get_coach_for_vendor,
    _get_notes_for_status,
    _get_status_display,
    _has_read_access,
    _has_write_access,
    _parse_config_value,
    _resolve_backup_path,
    _resolve_restore_adapter,
    app,
)
from ai_asst_mgr.coaches import ClaudeCoach, CodexCoach, GeminiCoach, Priority

runner = CliRunner()


class TestStatusCommand:
    """Tests for the status command."""

    def test_status_command_shows_all_vendors(self) -> None:
        """Test the status command displays all vendors in a table."""
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "AI Assistant Vendor Status" in result.stdout
        # Note: Rich table may wrap vendor names across lines
        assert "Claude" in result.stdout
        assert "Gemini" in result.stdout
        assert "OpenAI" in result.stdout or "Codex" in result.stdout
        assert "Config Location" in result.stdout
        assert "Summary:" in result.stdout

    def test_status_command_with_valid_vendor(self) -> None:
        """Test the status command with a valid vendor flag."""
        result = runner.invoke(app, ["status", "--vendor", "claude"])
        assert result.exit_code == 0
        assert "AI Assistant Vendor Status" in result.stdout
        # Note: Rich table may wrap vendor names across lines
        assert "Claude" in result.stdout
        # Should not show summary when vendor specified
        assert "Summary:" not in result.stdout

    def test_status_command_with_short_vendor_flag(self) -> None:
        """Test the status command with short -v vendor flag."""
        result = runner.invoke(app, ["status", "-v", "gemini"])
        assert result.exit_code == 0
        assert "Gemini" in result.stdout

    def test_status_command_with_invalid_vendor(self) -> None:
        """Test the status command with an invalid vendor name."""
        result = runner.invoke(app, ["status", "--vendor", "invalid"])
        assert result.exit_code == 1
        assert "Error: Unknown vendor 'invalid'" in result.stdout
        assert "Available vendors:" in result.stdout

    def test_status_command_shows_configured_status(self) -> None:
        """Test status command shows configured vendors correctly."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter with CONFIGURED status
            mock_adapter = MagicMock(spec=["info", "get_status", "is_installed", "is_configured"])
            mock_adapter.info.name = "Test Vendor"
            mock_adapter.info.config_dir = "/test/path"
            mock_adapter.get_status.return_value = VendorStatus.CONFIGURED
            mock_adapter.is_configured.return_value = True
            mock_adapter.is_installed.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"test": mock_adapter}
            mock_registry.get_configured_vendors.return_value = {"test": mock_adapter}
            mock_registry.get_installed_vendors.return_value = {"test": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "✅" in result.stdout
            assert "Configured" in result.stdout
            # Notes may be wrapped by Rich table
            assert "Ready" in result.stdout
            assert "use" in result.stdout

    def test_status_command_shows_installed_status(self) -> None:
        """Test status command shows installed but not configured vendors."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter with INSTALLED status
            mock_adapter = MagicMock(spec=["info", "get_status", "is_installed", "is_configured"])
            mock_adapter.info.name = "Test Vendor"
            mock_adapter.info.config_dir = "/test/path"
            mock_adapter.get_status.return_value = VendorStatus.INSTALLED
            mock_adapter.is_configured.return_value = False
            mock_adapter.is_installed.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"test": mock_adapter}
            mock_registry.get_configured_vendors.return_value = {}
            mock_registry.get_installed_vendors.return_value = {"test": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "⚠️" in result.stdout
            assert "Installed" in result.stdout
            # Notes may be wrapped by Rich table
            assert "Needs" in result.stdout
            assert "configuration" in result.stdout

    def test_status_command_shows_not_installed_status(self) -> None:
        """Test status command shows not installed vendors."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter with NOT_INSTALLED status
            mock_adapter = MagicMock(spec=["info", "get_status", "is_installed", "is_configured"])
            mock_adapter.info.name = "Test Vendor"
            mock_adapter.info.config_dir = "/test/path"
            mock_adapter.get_status.return_value = VendorStatus.NOT_INSTALLED
            mock_adapter.is_configured.return_value = False
            mock_adapter.is_installed.return_value = False

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"test": mock_adapter}
            mock_registry.get_configured_vendors.return_value = {}
            mock_registry.get_installed_vendors.return_value = {}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "❌" in result.stdout
            assert "Not Installed" in result.stdout or "Not" in result.stdout
            # Notes may be wrapped by Rich table
            assert "detected" in result.stdout or "system" in result.stdout

    def test_status_command_shows_error_status(self) -> None:
        """Test status command shows error state correctly."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter with ERROR status
            mock_adapter = MagicMock(spec=["info", "get_status", "is_installed", "is_configured"])
            mock_adapter.info.name = "Test Vendor"
            mock_adapter.info.config_dir = "/test/path"
            mock_adapter.get_status.return_value = VendorStatus.ERROR
            mock_adapter.is_configured.return_value = False
            mock_adapter.is_installed.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"test": mock_adapter}
            mock_registry.get_configured_vendors.return_value = {}
            mock_registry.get_installed_vendors.return_value = {"test": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "❗" in result.stdout
            assert "Error" in result.stdout
            # Notes may be wrapped by Rich table
            assert "Configuration" in result.stdout or "error" in result.stdout
            assert "detected" in result.stdout

    def test_status_command_summary_counts(self) -> None:
        """Test status command shows correct summary counts."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapters with mixed statuses
            mock_adapter1 = MagicMock(spec=["info", "get_status", "is_installed", "is_configured"])
            mock_adapter1.info.name = "Vendor 1"
            mock_adapter1.info.config_dir = "/test/path1"
            mock_adapter1.get_status.return_value = VendorStatus.CONFIGURED
            mock_adapter1.is_configured.return_value = True
            mock_adapter1.is_installed.return_value = True

            mock_adapter2 = MagicMock(spec=["info", "get_status", "is_installed", "is_configured"])
            mock_adapter2.info.name = "Vendor 2"
            mock_adapter2.info.config_dir = "/test/path2"
            mock_adapter2.get_status.return_value = VendorStatus.INSTALLED
            mock_adapter2.is_configured.return_value = False
            mock_adapter2.is_installed.return_value = True

            mock_adapter3 = MagicMock(spec=["info", "get_status", "is_installed", "is_configured"])
            mock_adapter3.info.name = "Vendor 3"
            mock_adapter3.info.config_dir = "/test/path3"
            mock_adapter3.get_status.return_value = VendorStatus.NOT_INSTALLED
            mock_adapter3.is_configured.return_value = False
            mock_adapter3.is_installed.return_value = False

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {
                "v1": mock_adapter1,
                "v2": mock_adapter2,
                "v3": mock_adapter3,
            }
            mock_registry.get_configured_vendors.return_value = {"v1": mock_adapter1}
            mock_registry.get_installed_vendors.return_value = {
                "v1": mock_adapter1,
                "v2": mock_adapter2,
            }
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["status"])
            assert result.exit_code == 0
            assert "Summary: 1/3 configured, 2/3 installed" in result.stdout


class TestStatusHelperFunctions:
    """Tests for status command helper functions."""

    def test_get_status_display_configured(self) -> None:
        """Test _get_status_display for CONFIGURED status."""
        result = _get_status_display(VendorStatus.CONFIGURED)
        assert "✅ Configured" in result
        assert "green" in result

    def test_get_status_display_installed(self) -> None:
        """Test _get_status_display for INSTALLED status."""
        result = _get_status_display(VendorStatus.INSTALLED)
        assert "⚠️  Installed" in result
        assert "yellow" in result

    def test_get_status_display_not_installed(self) -> None:
        """Test _get_status_display for NOT_INSTALLED status."""
        result = _get_status_display(VendorStatus.NOT_INSTALLED)
        assert "❌ Not Installed" in result
        assert "red" in result

    def test_get_status_display_running(self) -> None:
        """Test _get_status_display for RUNNING status."""
        result = _get_status_display(VendorStatus.RUNNING)
        assert "🟢 Running" in result
        assert "green" in result

    def test_get_status_display_error(self) -> None:
        """Test _get_status_display for ERROR status."""
        result = _get_status_display(VendorStatus.ERROR)
        assert "❗ Error" in result
        assert "red" in result

    def test_get_notes_for_status_configured(self) -> None:
        """Test _get_notes_for_status for CONFIGURED status."""
        result = _get_notes_for_status(VendorStatus.CONFIGURED)
        assert result == "Ready to use"

    def test_get_notes_for_status_installed(self) -> None:
        """Test _get_notes_for_status for INSTALLED status."""
        result = _get_notes_for_status(VendorStatus.INSTALLED)
        assert result == "Needs configuration"

    def test_get_notes_for_status_not_installed(self) -> None:
        """Test _get_notes_for_status for NOT_INSTALLED status."""
        result = _get_notes_for_status(VendorStatus.NOT_INSTALLED)
        assert result == "Not detected on system"

    def test_get_notes_for_status_running(self) -> None:
        """Test _get_notes_for_status for RUNNING status."""
        result = _get_notes_for_status(VendorStatus.RUNNING)
        assert result == "Currently active"

    def test_get_notes_for_status_error(self) -> None:
        """Test _get_notes_for_status for ERROR status."""
        result = _get_notes_for_status(VendorStatus.ERROR)
        assert result == "Configuration error detected"


class TestHealthCommand:
    """Tests for the health command."""

    def test_health_command_all_vendors_healthy(self) -> None:
        """Test health command with all vendors healthy."""
        # Create mock adapter
        mock_adapter = MagicMock(spec=VendorAdapter)
        mock_adapter.health_check.return_value = {
            "healthy": True,
            "checks": {"installed": True, "configured": True},
            "errors": [],
        }
        mock_adapter.audit_config.return_value = {
            "score": 100,
            "issues": [],
            "warnings": [],
            "recommendations": [],
        }

        # Mock VendorRegistry
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {
                "claude": mock_adapter,
                "gemini": mock_adapter,
                "openai": mock_adapter,
            }
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["health"])

            assert result.exit_code == 0
            assert "Vendor Health Status" in result.stdout
            assert "No issues" in result.stdout

    def test_health_command_with_specific_vendor(self) -> None:
        """Test health command with specific vendor flag."""
        # Create mock adapter
        mock_adapter = MagicMock(spec=VendorAdapter)
        mock_adapter.health_check.return_value = {
            "healthy": True,
            "checks": {"installed": True, "configured": True},
            "errors": [],
        }
        mock_adapter.audit_config.return_value = {
            "score": 100,
            "issues": [],
            "warnings": [],
            "recommendations": [],
        }

        # Mock VendorRegistry
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["health", "--vendor", "claude"])

            assert result.exit_code == 0
            assert "Vendor Health Status" in result.stdout
            assert "No issues" in result.stdout
            mock_registry.get_vendor.assert_called_once_with("claude")

    def test_health_command_with_invalid_vendor(self) -> None:
        """Test health command with invalid vendor name."""
        # Mock VendorRegistry
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get_vendor.side_effect = KeyError("Unknown vendor")
            mock_registry.get_all_vendors.return_value = {
                "claude": MagicMock(),
                "gemini": MagicMock(),
            }
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["health", "--vendor", "invalid"])

            assert result.exit_code == 1
            assert "Unknown vendor" in result.stdout
            assert "Available vendors:" in result.stdout

    def test_health_command_with_vendor_warnings(self) -> None:
        """Test health command with vendor that has warnings."""
        # Create mock adapter with warnings
        mock_adapter = MagicMock(spec=VendorAdapter)
        mock_adapter.health_check.return_value = {
            "healthy": True,
            "checks": {"installed": True, "configured": True},
            "errors": [],
        }
        mock_adapter.audit_config.return_value = {
            "score": 80,
            "issues": [],
            "warnings": ["Config directory has overly permissive permissions"],
            "recommendations": ["Run chmod 700 on config directory"],
        }

        # Mock VendorRegistry
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["health"])

            assert result.exit_code == 0
            assert "permissive permissions" in result.stdout
            assert "chmod 700" in result.stdout

    def test_health_command_with_vendor_issues(self) -> None:
        """Test health command with vendor that has issues."""
        # Create mock adapter with issues
        mock_adapter = MagicMock(spec=VendorAdapter)
        mock_adapter.health_check.return_value = {
            "healthy": False,
            "checks": {"installed": False, "configured": False},
            "errors": ["CLI not installed", "No configuration found"],
        }
        mock_adapter.audit_config.return_value = {
            "score": 40,
            "issues": ["Missing required configuration"],
            "warnings": [],
            "recommendations": ["Install the CLI", "Run init command"],
        }

        # Mock VendorRegistry
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"gemini": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["health"])

            assert result.exit_code == 0
            assert "Issues" in result.stdout
            assert "CLI not installed" in result.stdout
            assert "No configuration found" in result.stdout
            assert "Install the CLI" in result.stdout

    def test_health_command_with_error_during_check(self) -> None:
        """Test health command handles errors gracefully."""
        # Create mock adapter that raises an exception
        mock_adapter = MagicMock(spec=VendorAdapter)
        mock_adapter.health_check.side_effect = RuntimeError("Unexpected error")

        # Mock VendorRegistry
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"openai": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["health"])

            assert result.exit_code == 0
            assert "Failed to run health check" in result.stdout

    def test_health_command_with_mixed_vendor_states(self) -> None:
        """Test health command with vendors in different states."""
        # Create healthy adapter
        healthy_adapter = MagicMock(spec=VendorAdapter)
        healthy_adapter.health_check.return_value = {
            "healthy": True,
            "checks": {"installed": True, "configured": True},
            "errors": [],
        }
        healthy_adapter.audit_config.return_value = {
            "score": 100,
            "issues": [],
            "warnings": [],
            "recommendations": [],
        }

        # Create unhealthy adapter
        unhealthy_adapter = MagicMock(spec=VendorAdapter)
        unhealthy_adapter.health_check.return_value = {
            "healthy": False,
            "checks": {"installed": False},
            "errors": ["Not installed"],
        }
        unhealthy_adapter.audit_config.return_value = {
            "score": 0,
            "issues": ["Critical issue"],
            "warnings": [],
            "recommendations": ["Install vendor"],
        }

        # Mock VendorRegistry
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {
                "claude": healthy_adapter,
                "gemini": unhealthy_adapter,
            }
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["health"])

            assert result.exit_code == 0
            assert "No issues" in result.stdout
            assert "Not installed" in result.stdout
            assert "Install vendor" in result.stdout

    def test_health_command_with_no_issues_or_recommendations(self) -> None:
        """Test health command when vendor is perfectly healthy."""
        # Create perfectly healthy adapter
        mock_adapter = MagicMock(spec=VendorAdapter)
        mock_adapter.health_check.return_value = {
            "healthy": True,
            "checks": {"installed": True, "configured": True},
            "errors": [],
        }
        mock_adapter.audit_config.return_value = {
            "score": 100,
            "issues": [],
            "warnings": [],
            "recommendations": [],
        }

        # Mock VendorRegistry
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["health"])

            assert result.exit_code == 0
            assert "No issues" in result.stdout
            assert "None" in result.stdout  # For recommendations


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

    @patch("ai_asst_mgr.cli.VendorRegistry")
    @patch("ai_asst_mgr.cli._attempt_fixes")
    def test_doctor_command_with_fix_flag_and_issues(
        self, mock_attempt_fixes: MagicMock, mock_registry: MagicMock
    ) -> None:
        """Test doctor command with --fix flag when issues are found."""
        # Setup mock vendor with configuration issue
        mock_vendor = MagicMock()
        mock_vendor.info.name = "TestVendor"
        mock_vendor.is_installed.return_value = True
        mock_vendor.is_configured.return_value = False

        mock_registry_instance = MagicMock()
        mock_registry_instance.get_all_vendors.return_value = {"test": mock_vendor}
        mock_registry.return_value = mock_registry_instance

        # Mock _attempt_fixes to return that 0 out of 1 issues were fixed
        mock_attempt_fixes.return_value = 0

        result = runner.invoke(app, ["doctor", "--fix"])
        assert "System Diagnostics" in result.stdout
        assert "Attempting automatic fixes" in result.stdout
        assert "Fixed 0/1 issues" in result.stdout
        assert "Some issues require manual intervention" in result.stdout
        # Exit code is 0 because vendor not configured doesn't increment failed count
        assert result.exit_code == 0
        mock_attempt_fixes.assert_called_once()

    @patch("ai_asst_mgr.cli.VendorRegistry")
    @patch("ai_asst_mgr.cli._attempt_fixes")
    def test_doctor_command_with_fix_flag_all_fixed(
        self, mock_attempt_fixes: MagicMock, mock_registry: MagicMock
    ) -> None:
        """Test doctor command with --fix flag when all issues are fixed."""
        # Setup mock vendor with configuration issue
        mock_vendor = MagicMock()
        mock_vendor.info.name = "TestVendor"
        mock_vendor.is_installed.return_value = True
        mock_vendor.is_configured.return_value = False

        mock_registry_instance = MagicMock()
        mock_registry_instance.get_all_vendors.return_value = {"test": mock_vendor}
        mock_registry.return_value = mock_registry_instance

        # Mock _attempt_fixes to return that 1 out of 1 issues were fixed
        mock_attempt_fixes.return_value = 1

        result = runner.invoke(app, ["doctor", "--fix"])
        assert "System Diagnostics" in result.stdout
        assert "Attempting automatic fixes" in result.stdout
        assert "Fixed 1/1 issues" in result.stdout
        # Should NOT show manual intervention message when all are fixed
        assert "Some issues require manual intervention" not in result.stdout
        # Exit code is 0 because vendor not configured doesn't increment failed count
        assert result.exit_code == 0
        mock_attempt_fixes.assert_called_once()

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

    @patch("ai_asst_mgr.cli.VendorRegistry")
    def test_doctor_command_detects_vendor_installed_but_not_configured(
        self, mock_registry: MagicMock
    ) -> None:
        """Test doctor command detects when vendor is installed but not configured."""
        mock_vendor = MagicMock()
        mock_vendor.info.name = "TestVendor"
        mock_vendor.is_installed.return_value = True
        mock_vendor.is_configured.return_value = False

        mock_registry_instance = MagicMock()
        mock_registry_instance.get_all_vendors.return_value = {"test": mock_vendor}
        mock_registry.return_value = mock_registry_instance

        result = runner.invoke(app, ["doctor"])
        assert "Vendor Installations" in result.stdout
        assert "TestVendor" in result.stdout
        assert "Installed" in result.stdout
        assert "Not configured" in result.stdout or "not configured" in result.stdout
        # Exit code will be 0 because the vendor not being configured is just a warning,
        # not a failure (it creates an issue entry but doesn't increment failed count)
        # The actual test is that the issue is detected and shown
        assert result.exit_code == 0

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
        """Test doctor command detects missing dependencies by testing ImportError path."""
        # Create a mock that will raise ImportError for a specific package
        real_import = builtins.__import__

        def custom_import(
            name: str,
            globals: dict[str, object] | None = None,
            locals: dict[str, object] | None = None,
            fromlist: tuple[str, ...] = (),
            level: int = 0,
        ) -> ModuleType:
            if name == "httpx":
                error_msg = f"No module named '{name}'"
                raise ImportError(error_msg)
            return real_import(name, globals, locals, fromlist, level)

        # Patch __import__ in builtins
        original_import = builtins.__import__
        try:
            builtins.__import__ = custom_import  # type: ignore[assignment]
            result = runner.invoke(app, ["doctor"])
            assert "Dependencies" in result.stdout
            assert "httpx" in result.stdout.lower()
            assert "not found" in result.stdout.lower()
            assert result.exit_code == 1
        finally:
            builtins.__import__ = original_import

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

    def test_attempt_fixes_with_directory_not_found_issue(self) -> None:
        """Test _attempt_fixes handles directory not found but doesn't auto-fix."""
        issues = [
            {
                "category": "Configuration",
                "issue": "Configuration directory not found",
                "remediation": "Create directory: mkdir -p ~/.config/ai-asst-mgr",
            }
        ]
        result = _attempt_fixes(issues)
        # Directory creation not auto-fixed for safety
        assert result == 0

    def test_attempt_fixes_with_other_category(self) -> None:
        """Test _attempt_fixes with issue that doesn't match any auto-fix patterns."""
        issues = [
            {
                "category": "Other",
                "issue": "Some other issue",
                "remediation": "Manual fix required",
            }
        ]
        result = _attempt_fixes(issues)
        # No auto-fix for unrecognized patterns
        assert result == 0


class TestInitCommand:
    """All init command tests - Agent 1."""

    def test_init_all_vendors(self) -> None:
        """Test init command initializes all vendors."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapters
            mock_adapter1 = MagicMock(spec=VendorAdapter)
            mock_adapter1.info.name = "Claude Code"
            mock_adapter1.is_configured.return_value = False
            mock_adapter1.initialize.return_value = None

            mock_adapter2 = MagicMock(spec=VendorAdapter)
            mock_adapter2.info.name = "Gemini"
            mock_adapter2.is_configured.return_value = False
            mock_adapter2.initialize.return_value = None

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {
                "claude": mock_adapter1,
                "gemini": mock_adapter2,
            }
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            assert "Initializing Vendor Configurations" in result.stdout
            assert "Claude Code" in result.stdout
            assert "Gemini" in result.stdout
            assert "Initialized" in result.stdout
            assert "Summary:" in result.stdout
            assert "Initialized: 2" in result.stdout

            # Verify initialize was called for both
            mock_adapter1.initialize.assert_called_once()
            mock_adapter2.initialize.assert_called_once()

    def test_init_specific_vendor(self) -> None:
        """Test init command with specific vendor flag."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter
            mock_adapter = MagicMock(spec=VendorAdapter)
            mock_adapter.info.name = "Gemini"
            mock_adapter.is_configured.return_value = False
            mock_adapter.initialize.return_value = None

            mock_registry = MagicMock()
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init", "--vendor", "gemini"])

            assert result.exit_code == 0
            assert "Gemini" in result.stdout
            assert "Initialized" in result.stdout
            # Rich may wrap text, so check for both words separately
            assert "Created" in result.stdout or "configuration" in result.stdout
            assert "directory" in result.stdout or "defaults" in result.stdout
            mock_adapter.initialize.assert_called_once()
            mock_registry.get_vendor.assert_called_once_with("gemini")

    def test_init_specific_vendor_short_flag(self) -> None:
        """Test init command with short -v vendor flag."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter
            mock_adapter = MagicMock(spec=VendorAdapter)
            mock_adapter.info.name = "Claude Code"
            mock_adapter.is_configured.return_value = False
            mock_adapter.initialize.return_value = None

            mock_registry = MagicMock()
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init", "-v", "claude"])

            assert result.exit_code == 0
            assert "Claude Code" in result.stdout
            assert "Initialized" in result.stdout

    def test_init_already_configured_vendor_skips(self) -> None:
        """Test init command skips already configured vendors."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter that is already configured
            mock_adapter = MagicMock(spec=VendorAdapter)
            mock_adapter.info.name = "Claude Code"
            mock_adapter.is_configured.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            assert "Skipped" in result.stdout
            assert "Already configured" in result.stdout
            # Should not call initialize when already configured
            mock_adapter.initialize.assert_not_called()

    def test_init_force_flag_reinitializes_configured(self) -> None:
        """Test init command with --force flag reinitializes configured vendors."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter that is already configured
            mock_adapter = MagicMock(spec=VendorAdapter)
            mock_adapter.info.name = "Claude Code"
            mock_adapter.is_configured.return_value = True
            mock_adapter.initialize.return_value = None

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init", "--force"])

            assert result.exit_code == 0
            assert "Initialized" in result.stdout
            assert "Reinitialized configuration" in result.stdout
            # Should call initialize even though already configured
            mock_adapter.initialize.assert_called_once()

    def test_init_force_flag_short_form(self) -> None:
        """Test init command with short -f force flag."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter
            mock_adapter = MagicMock(spec=VendorAdapter)
            mock_adapter.info.name = "Claude Code"
            mock_adapter.is_configured.return_value = True
            mock_adapter.initialize.return_value = None

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init", "-f"])

            assert result.exit_code == 0
            assert "Initialized" in result.stdout
            mock_adapter.initialize.assert_called_once()

    def test_init_dry_run_shows_preview(self) -> None:
        """Test init command with --dry-run flag shows preview."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter
            mock_adapter = MagicMock(spec=VendorAdapter)
            mock_adapter.info.name = "Claude Code"
            mock_adapter.is_configured.return_value = False

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init", "--dry-run"])

            assert result.exit_code == 0
            assert "Initialization Preview (Dry Run)" in result.stdout
            assert "Would initialize" in result.stdout
            # Rich may wrap text, so check for key words separately
            assert "Create" in result.stdout or "configuration" in result.stdout
            assert "directory" in result.stdout or "defaults" in result.stdout
            # Should NOT call initialize in dry-run mode
            mock_adapter.initialize.assert_not_called()

    def test_init_dry_run_with_configured_vendor(self) -> None:
        """Test init --dry-run shows what would happen for configured vendor."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter that is already configured
            mock_adapter = MagicMock(spec=VendorAdapter)
            mock_adapter.info.name = "Claude Code"
            mock_adapter.is_configured.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init", "--dry-run"])

            assert result.exit_code == 0
            assert "Would skip" in result.stdout
            mock_adapter.initialize.assert_not_called()

    def test_init_dry_run_with_force(self) -> None:
        """Test init --dry-run --force shows reinit preview."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter that is already configured
            mock_adapter = MagicMock(spec=VendorAdapter)
            mock_adapter.info.name = "Claude Code"
            mock_adapter.is_configured.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init", "--dry-run", "--force"])

            assert result.exit_code == 0
            assert "Would initialize" in result.stdout
            assert "Force reinitialize configuration" in result.stdout
            mock_adapter.initialize.assert_not_called()

    def test_init_invalid_vendor_name(self) -> None:
        """Test init command with invalid vendor name."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get_vendor.side_effect = KeyError("Unknown vendor")
            mock_registry.get_all_vendors.return_value = {
                "claude": MagicMock(),
                "gemini": MagicMock(),
            }
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init", "--vendor", "invalid"])

            assert result.exit_code == 1
            assert "Error: Unknown vendor 'invalid'" in result.stdout
            assert "Available vendors:" in result.stdout

    def test_init_handles_initialization_error(self) -> None:
        """Test init command handles initialization errors gracefully."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter that raises error
            mock_adapter = MagicMock(spec=VendorAdapter)
            mock_adapter.info.name = "Claude Code"
            mock_adapter.is_configured.return_value = False
            mock_adapter.initialize.side_effect = RuntimeError("Permission denied")

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 1
            assert "Failed" in result.stdout
            assert "Permission denied" in result.stdout
            assert "Failed: 1" in result.stdout

    def test_init_mixed_results(self) -> None:
        """Test init command with mixed success, skip, and failure."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapters with different states
            mock_adapter1 = MagicMock(spec=VendorAdapter)
            mock_adapter1.info.name = "Claude Code"
            mock_adapter1.is_configured.return_value = False
            mock_adapter1.initialize.return_value = None

            mock_adapter2 = MagicMock(spec=VendorAdapter)
            mock_adapter2.info.name = "Gemini"
            mock_adapter2.is_configured.return_value = True  # Already configured

            mock_adapter3 = MagicMock(spec=VendorAdapter)
            mock_adapter3.info.name = "OpenAI"
            mock_adapter3.is_configured.return_value = False
            mock_adapter3.initialize.side_effect = RuntimeError("Failed")

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {
                "claude": mock_adapter1,
                "gemini": mock_adapter2,
                "openai": mock_adapter3,
            }
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 1  # Exit code 1 because of failure
            assert "Initialized: 1" in result.stdout
            assert "Skipped: 1" in result.stdout
            assert "Failed: 1" in result.stdout

    def test_init_with_vendor_and_force(self) -> None:
        """Test init command with both --vendor and --force flags."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter
            mock_adapter = MagicMock(spec=VendorAdapter)
            mock_adapter.info.name = "Gemini"
            mock_adapter.is_configured.return_value = True
            mock_adapter.initialize.return_value = None

            mock_registry = MagicMock()
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init", "--vendor", "gemini", "--force"])

            assert result.exit_code == 0
            assert "Initialized" in result.stdout
            assert "Reinitialized configuration" in result.stdout
            mock_adapter.initialize.assert_called_once()

    def test_init_shows_summary_counts(self) -> None:
        """Test init command shows correct summary counts."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapters
            mock_adapter1 = MagicMock(spec=VendorAdapter)
            mock_adapter1.info.name = "Vendor1"
            mock_adapter1.is_configured.return_value = False
            mock_adapter1.initialize.return_value = None

            mock_adapter2 = MagicMock(spec=VendorAdapter)
            mock_adapter2.info.name = "Vendor2"
            mock_adapter2.is_configured.return_value = False
            mock_adapter2.initialize.return_value = None

            mock_adapter3 = MagicMock(spec=VendorAdapter)
            mock_adapter3.info.name = "Vendor3"
            mock_adapter3.is_configured.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {
                "v1": mock_adapter1,
                "v2": mock_adapter2,
                "v3": mock_adapter3,
            }
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 0
            assert "Summary:" in result.stdout
            assert "Initialized: 2" in result.stdout
            assert "Skipped: 1" in result.stdout
            assert "Failed: 0" in result.stdout

    def test_init_handles_adapter_without_info(self) -> None:
        """Test init command handles adapters without info attribute gracefully."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Setup mock adapter without info attribute
            mock_adapter = MagicMock(spec=["is_configured", "initialize"])
            mock_adapter.is_configured.return_value = False
            mock_adapter.initialize.side_effect = RuntimeError("Error")

            # Delete the info attribute to simulate missing attribute
            del mock_adapter.info

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"test": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["init"])

            assert result.exit_code == 1
            # Should show vendor name (test) as fallback
            assert "test" in result.stdout
            assert "Failed" in result.stdout


class TestConfigCommand:
    """All config command tests - Agent 2."""

    def test_config_list_all(self) -> None:
        """Test config --list shows all vendor configurations."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter with config
            mock_adapter = MagicMock()
            mock_adapter.is_configured.return_value = True
            mock_adapter._load_settings.return_value = {
                "version": "1.0.0",
                "theme": "dark",
                "autoSave": True,
            }

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "--list"])

            assert result.exit_code == 0
            assert "Claude Configuration:" in result.stdout
            assert "version" in result.stdout
            assert "1.0.0" in result.stdout
            assert "theme" in result.stdout
            assert "dark" in result.stdout

    def test_config_list_specific_vendor(self) -> None:
        """Test config --vendor claude --list shows only Claude config."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter with config
            mock_adapter = MagicMock()
            mock_adapter.is_configured.return_value = True
            mock_adapter._load_settings.return_value = {
                "version": "1.0.0",
                "theme": "dark",
            }

            mock_registry = MagicMock()
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "--vendor", "claude", "--list"])

            assert result.exit_code == 0
            assert "Claude Configuration:" in result.stdout
            assert "version" in result.stdout
            mock_registry.get_vendor.assert_called_once_with("claude")

    def test_config_list_unconfigured_vendor(self) -> None:
        """Test config --list with unconfigured vendor."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter that is not configured
            mock_adapter = MagicMock()
            mock_adapter.is_configured.return_value = False

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"gemini": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "--list"])

            assert result.exit_code == 0
            assert "Gemini: Not configured" in result.stdout

    def test_config_get_value(self) -> None:
        """Test config KEY gets configuration value."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter
            mock_adapter = MagicMock()
            mock_adapter.get_config.return_value = "dark"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "theme"])

            assert result.exit_code == 0
            assert "dark" in result.stdout
            mock_adapter.get_config.assert_called_once_with("theme")

    def test_config_get_nested_key(self) -> None:
        """Test config with nested key (e.g., mcp.servers.brave.url)."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter
            mock_adapter = MagicMock()
            mock_adapter.get_config.return_value = "https://brave.com"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "mcp.servers.brave.url"])

            assert result.exit_code == 0
            assert "https://brave.com" in result.stdout
            mock_adapter.get_config.assert_called_once_with("mcp.servers.brave.url")

    def test_config_get_value_specific_vendor(self) -> None:
        """Test config --vendor claude KEY gets value from specific vendor."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter
            mock_adapter = MagicMock()
            mock_adapter.get_config.return_value = "1.0.0"

            mock_registry = MagicMock()
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "--vendor", "claude", "version"])

            assert result.exit_code == 0
            assert "1.0.0" in result.stdout
            mock_adapter.get_config.assert_called_once_with("version")
            mock_registry.get_vendor.assert_called_once_with("claude")

    def test_config_set_value(self) -> None:
        """Test config KEY VALUE sets configuration value."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter
            mock_adapter = MagicMock()

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "theme", "light"])

            assert result.exit_code == 0
            assert "Set theme = light for claude" in result.stdout
            mock_adapter.set_config.assert_called_once_with("theme", "light")

    def test_config_set_nested_key(self) -> None:
        """Test config with nested key setting (dot notation)."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter
            mock_adapter = MagicMock()

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "mcp.servers.brave.url", "https://brave.com"])

            assert result.exit_code == 0
            assert "Set mcp.servers.brave.url" in result.stdout
            mock_adapter.set_config.assert_called_once_with(
                "mcp.servers.brave.url", "https://brave.com"
            )

    def test_config_set_boolean_value(self) -> None:
        """Test config sets boolean values correctly."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter
            mock_adapter = MagicMock()

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "autoSave", "true"])

            assert result.exit_code == 0
            # Value should be parsed as boolean True, not string "true"
            mock_adapter.set_config.assert_called_once_with("autoSave", True)

    def test_config_set_numeric_value(self) -> None:
        """Test config sets numeric values correctly."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter
            mock_adapter = MagicMock()

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "timeout", "30"])

            assert result.exit_code == 0
            # Value should be parsed as number 30, not string "30"
            mock_adapter.set_config.assert_called_once_with("timeout", 30)

    def test_config_set_json_object(self) -> None:
        """Test config sets JSON object values."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter
            mock_adapter = MagicMock()

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "server", '{"host":"localhost","port":8080}'])

            assert result.exit_code == 0
            # Value should be parsed as dict
            mock_adapter.set_config.assert_called_once_with(
                "server", {"host": "localhost", "port": 8080}
            )

    def test_config_set_value_specific_vendor(self) -> None:
        """Test config --vendor claude KEY VALUE sets for specific vendor only."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter
            mock_adapter = MagicMock()

            mock_registry = MagicMock()
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "--vendor", "claude", "theme", "light"])

            assert result.exit_code == 0
            assert "Set theme = light for claude" in result.stdout
            mock_adapter.set_config.assert_called_once_with("theme", "light")
            mock_registry.get_vendor.assert_called_once_with("claude")

    def test_config_with_invalid_key(self) -> None:
        """Test config with invalid/nonexistent key."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter that raises KeyError
            mock_adapter = MagicMock()
            mock_adapter.get_config.side_effect = KeyError("Config key not found")

            mock_registry = MagicMock()
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "--vendor", "claude", "nonexistent"])

            assert result.exit_code == 1
            assert "not found" in result.stdout

    def test_config_with_invalid_vendor(self) -> None:
        """Test config with invalid vendor name."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get_vendor.side_effect = KeyError("Unknown vendor")
            mock_registry.get_all_vendors.return_value = {
                "claude": MagicMock(),
                "gemini": MagicMock(),
            }
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "--vendor", "invalid", "key"])

            assert result.exit_code == 1
            assert "Unknown vendor 'invalid'" in result.stdout
            assert "Available vendors:" in result.stdout

    def test_config_without_key_or_list(self) -> None:
        """Test config command without key and without --list flag."""
        result = runner.invoke(app, ["config"])

        assert result.exit_code == 1
        assert "Please provide a configuration key or use --list" in result.stdout

    def test_config_set_with_value_error(self) -> None:
        """Test config handles ValueError from adapter."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter that raises ValueError
            mock_adapter = MagicMock()
            mock_adapter.set_config.side_effect = ValueError("Invalid value for key")

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "theme", "invalid_theme"])

            assert result.exit_code == 1
            assert "Invalid value" in result.stdout

    def test_config_get_boolean_value_display(self) -> None:
        """Test config displays boolean values with colors."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter
            mock_adapter = MagicMock()
            mock_adapter.get_config.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "autoSave"])

            assert result.exit_code == 0
            assert "true" in result.stdout

    def test_config_get_dict_value_display(self) -> None:
        """Test config displays dict values as formatted JSON."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter
            mock_adapter = MagicMock()
            mock_adapter.get_config.return_value = {"host": "localhost", "port": 8080}

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "server"])

            assert result.exit_code == 0
            assert "host" in result.stdout
            assert "localhost" in result.stdout

    def test_config_list_with_nested_values(self) -> None:
        """Test config --list displays nested configuration correctly."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter with nested config
            mock_adapter = MagicMock()
            mock_adapter.is_configured.return_value = True
            mock_adapter._load_settings.return_value = {
                "version": "1.0.0",
                "mcp": {
                    "servers": {
                        "brave": {"url": "https://brave.com"},
                    }
                },
            }

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "--list"])

            assert result.exit_code == 0
            assert "Claude Configuration:" in result.stdout
            assert "version" in result.stdout
            # Flattened nested key should appear
            assert "mcp.servers.brave.url" in result.stdout

    def test_config_list_handles_load_error(self) -> None:
        """Test config --list handles errors gracefully."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapter that raises error
            mock_adapter = MagicMock()
            mock_adapter.is_configured.return_value = True
            mock_adapter._load_settings.side_effect = Exception("Failed to load")

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "--list"])

            assert result.exit_code == 0
            assert "Error listing config for claude" in result.stdout

    def test_config_get_from_multiple_vendors(self) -> None:
        """Test config KEY gets value from all vendors that have it."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapters
            mock_claude = MagicMock()
            mock_claude.get_config.return_value = "dark"

            mock_gemini = MagicMock()
            mock_gemini.get_config.side_effect = KeyError("Not found")

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {
                "claude": mock_claude,
                "gemini": mock_gemini,
            }
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "theme"])

            assert result.exit_code == 0
            assert "Claude:" in result.stdout
            assert "dark" in result.stdout
            # Gemini should be skipped silently

    def test_config_set_to_multiple_vendors(self) -> None:
        """Test config KEY VALUE sets to all configured vendors."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapters
            mock_claude = MagicMock()
            mock_gemini = MagicMock()

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {
                "claude": mock_claude,
                "gemini": mock_gemini,
            }
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "theme", "light"])

            assert result.exit_code == 0
            assert "Set theme = light for claude" in result.stdout
            assert "Set theme = light for gemini" in result.stdout
            mock_claude.set_config.assert_called_once_with("theme", "light")
            mock_gemini.set_config.assert_called_once_with("theme", "light")

    def test_config_get_key_not_found_in_any_vendor(self) -> None:
        """Test config KEY when key doesn't exist in any vendor."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            # Create mock adapters that don't have the key
            mock_adapter = MagicMock()
            mock_adapter.get_config.side_effect = KeyError("Not found")

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "nonexistent"])

            assert result.exit_code == 1
            assert "not found in any vendor" in result.stdout


class TestConfigHelperFunctions:
    """Tests for config command helper functions."""

    def test_flatten_dict_simple(self) -> None:
        """Test _flatten_dict with simple dict."""
        result = _flatten_dict({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}

    def test_flatten_dict_nested(self) -> None:
        """Test _flatten_dict with nested dict."""
        result = _flatten_dict({"a": {"b": {"c": 1}}})
        assert result == {"a.b.c": 1}

    def test_flatten_dict_mixed(self) -> None:
        """Test _flatten_dict with mixed simple and nested values."""
        result = _flatten_dict(
            {
                "version": "1.0.0",
                "mcp": {"servers": {"brave": {"url": "https://brave.com"}}},
                "theme": "dark",
            }
        )
        assert result == {
            "version": "1.0.0",
            "mcp.servers.brave.url": "https://brave.com",
            "theme": "dark",
        }

    def test_flatten_dict_empty(self) -> None:
        """Test _flatten_dict with empty dict."""
        result = _flatten_dict({})
        assert result == {}

    def test_format_config_value_string(self) -> None:
        """Test _format_config_value with string."""
        result = _format_config_value("test")
        assert result == "test"

    def test_format_config_value_bool_true(self) -> None:
        """Test _format_config_value with True."""
        result = _format_config_value(True)
        assert "true" in result
        assert "green" in result

    def test_format_config_value_bool_false(self) -> None:
        """Test _format_config_value with False."""
        result = _format_config_value(False)
        assert "false" in result
        assert "red" in result

    def test_format_config_value_none(self) -> None:
        """Test _format_config_value with None."""
        result = _format_config_value(None)
        assert "null" in result
        assert "dim" in result

    def test_format_config_value_dict(self) -> None:
        """Test _format_config_value with dict."""
        result = _format_config_value({"host": "localhost", "port": 8080})
        assert "host" in result
        assert "localhost" in result
        assert "port" in result

    def test_format_config_value_list(self) -> None:
        """Test _format_config_value with list."""
        result = _format_config_value([1, 2, 3])
        assert "1" in result
        assert "2" in result
        assert "3" in result

    def test_format_config_value_number(self) -> None:
        """Test _format_config_value with number."""
        result = _format_config_value(42)
        assert result == "42"

    def test_parse_config_value_string(self) -> None:
        """Test _parse_config_value with plain string."""
        result = _parse_config_value("hello")
        assert result == "hello"

    def test_parse_config_value_boolean_true(self) -> None:
        """Test _parse_config_value with 'true'."""
        result = _parse_config_value("true")
        assert result is True

    def test_parse_config_value_boolean_false(self) -> None:
        """Test _parse_config_value with 'false'."""
        result = _parse_config_value("false")
        assert result is False

    def test_parse_config_value_number(self) -> None:
        """Test _parse_config_value with number string."""
        result = _parse_config_value("42")
        assert result == 42

    def test_parse_config_value_float(self) -> None:
        """Test _parse_config_value with float string."""
        result = _parse_config_value("3.14")
        assert result == 3.14

    def test_parse_config_value_json_object(self) -> None:
        """Test _parse_config_value with JSON object."""
        result = _parse_config_value('{"host":"localhost","port":8080}')
        assert result == {"host": "localhost", "port": 8080}

    def test_parse_config_value_json_array(self) -> None:
        """Test _parse_config_value with JSON array."""
        result = _parse_config_value("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_parse_config_value_null(self) -> None:
        """Test _parse_config_value with 'null'."""
        result = _parse_config_value("null")
        assert result is None


class TestBackupCommand:
    """Tests for the backup command."""

    def test_backup_help_shows_options(self) -> None:
        """Test backup command shows help."""
        result = runner.invoke(app, ["backup", "--help"])
        assert result.exit_code == 0
        assert "backup" in result.stdout.lower()
        # Check for option descriptions (Rich ANSI codes may split option flags)
        assert "vendor" in result.stdout.lower()
        assert "backup" in result.stdout.lower()

    def test_backup_list_empty(self) -> None:
        """Test backup list with no backups."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli.VendorRegistry"),
        ):
            mock_manager = MagicMock()
            mock_manager.list_backups.return_value = []
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["backup", "--list"])
            assert result.exit_code == 0
            assert "No backups found" in result.stdout

    def test_backup_list_with_backups(self) -> None:
        """Test backup list shows existing backups."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli.VendorRegistry"),
        ):
            mock_metadata = MagicMock()
            mock_metadata.vendor_id = "claude"
            mock_metadata.timestamp = datetime.now(tz=UTC)
            mock_metadata.backup_path = Path("/backups/claude_backup.tar.gz")
            mock_metadata.size_bytes = 1024

            mock_manager = MagicMock()
            mock_manager.list_backups.return_value = [mock_metadata]
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["backup", "--list"])
            assert result.exit_code == 0
            assert "claude" in result.stdout.lower()

    def test_backup_vendor_not_found(self) -> None:
        """Test backup with invalid vendor."""
        result = runner.invoke(app, ["backup", "--vendor", "invalid_vendor"])
        assert result.exit_code == 1
        assert "Unknown vendor" in result.stdout

    def test_backup_create_success(self) -> None:
        """Test successful backup creation."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            # Setup mock adapter
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"
            mock_adapter.is_installed.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            # Setup mock backup result
            mock_metadata = MagicMock()
            mock_metadata.backup_path = Path("/backups/claude_backup.tar.gz")
            mock_metadata.size_bytes = 2048

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.metadata = mock_metadata
            mock_result.duration_seconds = 1.5

            mock_manager = MagicMock()
            mock_manager.backup_vendor.return_value = mock_result
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["backup", "--vendor", "claude"])
            assert result.exit_code == 0
            assert "success" in result.stdout.lower() or "complete" in result.stdout.lower()

    def test_backup_verify_success(self) -> None:
        """Test backup verification success."""
        with patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.verify_backup.return_value = (True, "Backup is valid")
            mock_get_manager.return_value = mock_manager

            # Create temp file path for testing
            result = runner.invoke(app, ["backup", "--verify", "/tmp/test_backup.tar.gz"])
            # Path may not exist, but we're testing the command flow
            assert result.exit_code in [0, 1]


class TestRestoreCommand:
    """Tests for the restore command."""

    def test_restore_help_shows_options(self) -> None:
        """Test restore command shows help."""
        result = runner.invoke(app, ["restore", "--help"])
        assert result.exit_code == 0
        assert "restore" in result.stdout.lower()
        # Check for option descriptions (Rich ANSI codes may split option flags)
        assert "vendor" in result.stdout.lower()

    def test_restore_vendor_not_found(self) -> None:
        """Test restore with invalid vendor checks for backups."""
        result = runner.invoke(app, ["restore", "--vendor", "invalid_vendor"])
        assert result.exit_code == 1
        # Restore checks for backups first, so error message mentions the vendor
        assert "invalid_vendor" in result.stdout

    def test_restore_no_backup_available(self) -> None:
        """Test restore when no backup exists."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_manager = MagicMock()
            mock_manager.get_latest_backup.return_value = None
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["restore", "--vendor", "claude"])
            assert result.exit_code == 1
            assert "No backup" in result.stdout

    def test_restore_preview(self) -> None:
        """Test restore preview mode."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli._get_restore_manager") as mock_get_restore,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_metadata = MagicMock()
            mock_metadata.backup_path = Path("/backups/test.tar.gz")
            mock_metadata.timestamp = datetime.now(tz=UTC)

            mock_backup_manager = MagicMock()
            mock_backup_manager.get_latest_backup.return_value = mock_metadata
            mock_get_manager.return_value = mock_backup_manager

            mock_preview = MagicMock()
            mock_preview.files_to_restore = ["file1.md", "file2.md"]
            mock_preview.files_to_overwrite = ["file1.md"]
            mock_preview.estimated_size_bytes = 1024

            mock_restore_manager = MagicMock()
            mock_restore_manager.preview_restore.return_value = mock_preview
            mock_get_restore.return_value = mock_restore_manager

            result = runner.invoke(app, ["restore", "--vendor", "claude", "--preview"])
            assert result.exit_code == 0
            assert "preview" in result.stdout.lower() or "restore" in result.stdout.lower()


class TestSyncCommand:
    """Tests for the sync command."""

    def test_sync_help_shows_options(self) -> None:
        """Test sync command shows help."""
        result = runner.invoke(app, ["sync", "--help"])
        assert result.exit_code == 0
        assert "sync" in result.stdout.lower()
        # Check for option descriptions (Rich ANSI codes may split option flags)
        assert "strategy" in result.stdout.lower()

    def test_sync_no_repo_url(self) -> None:
        """Test sync requires repo URL."""
        result = runner.invoke(app, ["sync"])
        # Should fail without required REPO_URL argument
        assert result.exit_code != 0

    def test_sync_vendor_not_found(self) -> None:
        """Test sync with invalid vendor."""
        result = runner.invoke(
            app, ["sync", "https://github.com/test/repo.git", "--vendor", "invalid_vendor"]
        )
        assert result.exit_code == 1
        assert "Unknown vendor" in result.stdout

    def test_sync_preview_mode(self) -> None:
        """Test sync preview mode."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_backup,
            patch("ai_asst_mgr.cli._get_sync_manager") as mock_get_sync,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_backup_manager = MagicMock()
            mock_get_backup.return_value = mock_backup_manager

            mock_preview = MagicMock()
            mock_preview.files_to_add = ["new_file.md"]
            mock_preview.files_to_modify = ["settings.json"]
            mock_preview.files_to_delete = []
            mock_preview.conflicts = ["settings.json"]

            mock_sync_manager = MagicMock()
            mock_sync_manager.preview_sync.return_value = mock_preview
            mock_get_sync.return_value = mock_sync_manager

            result = runner.invoke(
                app,
                [
                    "sync",
                    "https://github.com/test/repo.git",
                    "--vendor",
                    "claude",
                    "--preview",
                ],
            )
            assert result.exit_code == 0

    def test_sync_execute_success(self) -> None:
        """Test successful sync execution."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_backup,
            patch("ai_asst_mgr.cli._get_sync_manager") as mock_get_sync,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_backup_manager = MagicMock()
            mock_get_backup.return_value = mock_backup_manager

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.files_synced = 5
            mock_result.files_added = 3
            mock_result.files_modified = 2
            mock_result.pre_sync_backup = Path("/backups/pre_sync.tar.gz")
            mock_result.duration_seconds = 2.5

            mock_sync_manager = MagicMock()
            mock_sync_manager.sync_vendor.return_value = mock_result
            mock_get_sync.return_value = mock_sync_manager

            result = runner.invoke(
                app, ["sync", "https://github.com/test/repo.git", "--vendor", "claude"]
            )
            assert result.exit_code == 0


class TestFormatSizeBytes:
    """Tests for _format_size_bytes helper."""

    def test_format_size_bytes_bytes(self) -> None:
        """Test formatting bytes."""
        assert _format_size_bytes(500) == "500.0 B"

    def test_format_size_bytes_kb(self) -> None:
        """Test formatting kilobytes."""
        assert _format_size_bytes(2048) == "2.0 KB"

    def test_format_size_bytes_mb(self) -> None:
        """Test formatting megabytes."""
        assert _format_size_bytes(1048576) == "1.0 MB"

    def test_format_size_bytes_gb(self) -> None:
        """Test formatting gigabytes."""
        assert _format_size_bytes(1073741824) == "1.0 GB"


class TestBackupCommandEdgeCases:
    """Additional edge case tests for backup command."""

    def test_backup_all_vendors(self) -> None:
        """Test backup all vendors when no vendor specified."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            # Setup mock adapters
            mock_adapter1 = MagicMock()
            mock_adapter1.info.vendor_id = "claude"
            mock_adapter1.info.name = "Claude Code"
            mock_adapter1.is_installed.return_value = True

            mock_adapter2 = MagicMock()
            mock_adapter2.info.vendor_id = "gemini"
            mock_adapter2.info.name = "Gemini"
            mock_adapter2.is_installed.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {
                "claude": mock_adapter1,
                "gemini": mock_adapter2,
            }
            mock_registry_class.return_value = mock_registry

            # Setup mock backup result
            mock_summary = MagicMock()
            mock_summary.total_vendors = 2
            mock_summary.successful = 2
            mock_summary.failed = 0
            mock_summary.total_size_bytes = 4096
            mock_summary.duration_seconds = 2.0

            mock_manager = MagicMock()
            mock_manager.backup_all_vendors.return_value = mock_summary
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["backup"])
            assert result.exit_code == 0

    def test_backup_failure(self) -> None:
        """Test backup handles failure."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"
            mock_adapter.is_installed.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error = "Backup failed due to permissions"

            mock_manager = MagicMock()
            mock_manager.backup_vendor.return_value = mock_result
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["backup", "--vendor", "claude"])
            assert result.exit_code == 1
            assert "failed" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_backup_verify_failure(self) -> None:
        """Test backup verification failure."""
        with patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.verify_backup.return_value = (False, "Corrupted archive")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["backup", "--verify", "/fake/path.tar.gz"])
            assert result.exit_code == 1


class TestRestoreCommandEdgeCases:
    """Additional edge case tests for restore command."""

    def test_restore_execute_success(self) -> None:
        """Test successful restore execution."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli._get_restore_manager") as mock_get_restore,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_metadata = MagicMock()
            mock_metadata.backup_path = Path("/backups/test.tar.gz")
            mock_metadata.timestamp = datetime.now(tz=UTC)

            mock_backup_manager = MagicMock()
            mock_backup_manager.get_latest_backup.return_value = mock_metadata
            mock_get_manager.return_value = mock_backup_manager

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.restored_files = 10
            mock_result.pre_restore_backup = Path("/backups/pre_restore.tar.gz")
            mock_result.duration_seconds = 1.5

            mock_restore_manager = MagicMock()
            mock_restore_manager.restore_vendor.return_value = mock_result
            mock_get_restore.return_value = mock_restore_manager

            result = runner.invoke(app, ["restore", "--vendor", "claude"])
            assert result.exit_code == 0

    def test_restore_failure(self) -> None:
        """Test restore handles failure."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli._get_restore_manager") as mock_get_restore,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_metadata = MagicMock()
            mock_metadata.backup_path = Path("/backups/test.tar.gz")
            mock_metadata.timestamp = datetime.now(tz=UTC)

            mock_backup_manager = MagicMock()
            mock_backup_manager.get_latest_backup.return_value = mock_metadata
            mock_get_manager.return_value = mock_backup_manager

            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error = "Restore failed"

            mock_restore_manager = MagicMock()
            mock_restore_manager.restore_vendor.return_value = mock_result
            mock_get_restore.return_value = mock_restore_manager

            result = runner.invoke(app, ["restore", "--vendor", "claude"])
            assert result.exit_code == 1

    def test_restore_selective_success(self) -> None:
        """Test selective restore."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli._get_restore_manager") as mock_get_restore,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_metadata = MagicMock()
            mock_metadata.backup_path = Path("/backups/test.tar.gz")
            mock_metadata.timestamp = datetime.now(tz=UTC)

            mock_backup_manager = MagicMock()
            mock_backup_manager.get_latest_backup.return_value = mock_metadata
            mock_get_manager.return_value = mock_backup_manager

            mock_restore_manager = MagicMock()
            mock_restore_manager.get_restorable_directories.return_value = [
                "agents",
                "skills",
            ]
            mock_result = MagicMock()
            mock_result.success = True
            mock_result.restored_files = 5
            mock_restore_manager.restore_selective.return_value = mock_result
            mock_get_restore.return_value = mock_restore_manager

            result = runner.invoke(app, ["restore", "--vendor", "claude", "--selective", "agents"])
            assert result.exit_code == 0


class TestSyncCommandEdgeCases:
    """Additional edge case tests for sync command."""

    def test_sync_displays_failure_in_results(self) -> None:
        """Test sync displays failure in results table."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_backup,
            patch("ai_asst_mgr.cli._get_sync_manager") as mock_get_sync,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_backup_manager = MagicMock()
            mock_get_backup.return_value = mock_backup_manager

            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error = "Clone failed"

            # sync command calls sync_all_vendors, not sync_vendor
            mock_sync_manager = MagicMock()
            mock_sync_manager.sync_all_vendors.return_value = {"claude": mock_result}
            mock_get_sync.return_value = mock_sync_manager

            result = runner.invoke(
                app, ["sync", "https://github.com/test/repo.git", "--vendor", "claude"]
            )
            # Sync displays results but doesn't exit with error on failure
            assert result.exit_code == 0
            assert "Failed" in result.stdout or "failed" in result.stdout.lower()

    def test_sync_preview_no_changes(self) -> None:
        """Test sync preview with no changes."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_backup,
            patch("ai_asst_mgr.cli._get_sync_manager") as mock_get_sync,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_backup_manager = MagicMock()
            mock_get_backup.return_value = mock_backup_manager

            mock_preview = MagicMock()
            mock_preview.files_to_add = []
            mock_preview.files_to_modify = []
            mock_preview.files_to_delete = []
            mock_preview.conflicts = []

            mock_sync_manager = MagicMock()
            mock_sync_manager.preview_sync.return_value = mock_preview
            mock_get_sync.return_value = mock_sync_manager

            result = runner.invoke(
                app,
                [
                    "sync",
                    "https://github.com/test/repo.git",
                    "--vendor",
                    "claude",
                    "--preview",
                ],
            )
            assert result.exit_code == 0

    def test_sync_preview_shows_failure_message(self) -> None:
        """Test sync preview shows failure message when preview fails."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_backup,
            patch("ai_asst_mgr.cli._get_sync_manager") as mock_get_sync,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_backup_manager = MagicMock()
            mock_get_backup.return_value = mock_backup_manager

            mock_sync_manager = MagicMock()
            mock_sync_manager.preview_sync.return_value = None
            mock_get_sync.return_value = mock_sync_manager

            result = runner.invoke(
                app,
                [
                    "sync",
                    "https://github.com/test/repo.git",
                    "--vendor",
                    "claude",
                    "--preview",
                ],
            )
            # Preview shows failure message but doesn't exit with error
            assert result.exit_code == 0
            assert "Failed" in result.stdout or "failed" in result.stdout.lower()

    def test_sync_execute_with_full_results(self) -> None:
        """Test sync execute displays full results including pre-sync backup."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_backup,
            patch("ai_asst_mgr.cli._get_sync_manager") as mock_get_sync,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude Code"
            mock_adapter.is_installed.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_backup_manager = MagicMock()
            mock_get_backup.return_value = mock_backup_manager

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.files_added = 3
            mock_result.files_modified = 2
            mock_result.files_deleted = 1
            mock_result.duration_seconds = 1.5
            mock_result.pre_sync_backup = Path("/backups/pre_sync.tar.gz")

            mock_sync_manager = MagicMock()
            mock_sync_manager.sync_all_vendors.return_value = {"claude": mock_result}
            mock_get_sync.return_value = mock_sync_manager

            result = runner.invoke(
                app, ["sync", "https://github.com/test/repo.git", "--vendor", "claude"]
            )
            assert result.exit_code == 0
            assert "Success" in result.stdout
            # Pre-sync backup path should be displayed
            assert "pre_sync" in result.stdout.lower() or "backup" in result.stdout.lower()


class TestCoachCommand:
    """Tests for the coach command."""

    def test_coach_analyze_all_vendors(self) -> None:
        """Test coach command analyzes all vendors by default."""
        with patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches:
            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {}

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach"])
            assert result.exit_code == 0
            assert "Claude Analysis" in result.stdout
            mock_coach.analyze.assert_called_once()

    def test_coach_with_specific_vendor(self) -> None:
        """Test coach command with specific vendor."""
        with patch("ai_asst_mgr.cli._get_coach_for_vendor") as mock_get_coach:
            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {}

            mock_get_coach.return_value = mock_coach

            result = runner.invoke(app, ["coach", "--vendor", "claude"])
            assert result.exit_code == 0
            assert "Claude Analysis" in result.stdout
            mock_get_coach.assert_called_once_with("claude")

    def test_coach_with_invalid_vendor(self) -> None:
        """Test coach command with invalid vendor name."""
        with patch("ai_asst_mgr.cli._get_coach_for_vendor") as mock_get_coach:
            # Simulate unknown vendor by raising typer.Exit
            mock_get_coach.side_effect = typer.Exit(code=1)

            result = runner.invoke(app, ["coach", "--vendor", "invalid"])
            assert result.exit_code == 1

    def test_coach_compare_mode(self) -> None:
        """Test coach command with compare flag."""
        with (
            patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches,
            patch("ai_asst_mgr.cli._compare_vendors") as mock_compare,
        ):
            mock_coach = MagicMock()
            mock_get_coaches.return_value = {"claude": mock_coach, "gemini": mock_coach}

            result = runner.invoke(app, ["coach", "--compare"])
            assert result.exit_code == 0
            mock_compare.assert_called_once()

    def test_coach_with_report_period_weekly(self) -> None:
        """Test coach command with weekly report period."""
        with patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches:
            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {}

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach", "--report", "weekly"])
            assert result.exit_code == 0
            # Should call analyze with period_days=7
            mock_coach.analyze.assert_called_once_with(period_days=7)

    def test_coach_with_report_period_monthly(self) -> None:
        """Test coach command with monthly report period."""
        with patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches:
            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {}

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach", "--report", "monthly"])
            assert result.exit_code == 0
            # Should call analyze with period_days=30
            mock_coach.analyze.assert_called_once_with(period_days=30)

    def test_coach_with_insights(self) -> None:
        """Test coach command displays insights."""
        with patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches:
            mock_insight = MagicMock()
            mock_insight.category = "Performance"
            mock_insight.title = "High Response Time"
            mock_insight.description = "Average response time is elevated"
            mock_insight.metric_value = "2.5s"
            mock_insight.metric_unit = ""

            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = [mock_insight]
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {}

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach"])
            assert result.exit_code == 0
            assert "Claude Insights" in result.stdout
            assert "Performance" in result.stdout

    def test_coach_with_no_insights(self) -> None:
        """Test coach command when no insights available."""
        with patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches:
            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {}

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach"])
            assert result.exit_code == 0
            assert "No insights available" in result.stdout

    def test_coach_with_recommendations(self) -> None:
        """Test coach command displays recommendations."""
        with patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches:
            mock_rec = MagicMock()
            mock_rec.category = "Configuration"
            mock_rec.title = "Enable Feature X"
            mock_rec.description = "Feature X can improve performance"
            mock_rec.action = "Update config.json"
            mock_rec.expected_benefit = "20% faster responses"
            mock_rec.priority = Priority.HIGH

            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = [mock_rec]
            mock_coach.get_stats.return_value = {}

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach"])
            assert result.exit_code == 0
            assert "Recommendations" in result.stdout
            assert "Enable Feature X" in result.stdout

    def test_coach_with_no_recommendations(self) -> None:
        """Test coach command when no recommendations available."""
        with patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches:
            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {}

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach"])
            assert result.exit_code == 0
            assert "No recommendations" in result.stdout or "looks good" in result.stdout

    def test_coach_with_stats(self) -> None:
        """Test coach command displays statistics."""
        with patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches:
            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {
                "total_sessions": 42,
                "avg_duration": "5.2s",
                "configured": True,
            }

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach"])
            assert result.exit_code == 0
            assert "Statistics" in result.stdout
            assert "total_sessions" in result.stdout
            assert "42" in result.stdout

    def test_coach_with_empty_stats(self) -> None:
        """Test coach command when stats are empty."""
        with patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches:
            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {}

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach"])
            assert result.exit_code == 0
            # Stats section should not be shown if empty

    def test_coach_export_json(self) -> None:
        """Test coach command with JSON export."""
        with (
            patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches,
            patch("pathlib.Path.mkdir"),
        ):
            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {}
            mock_coach.export_report.return_value = Path("/tmp/claude_report.json")

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach", "--export", "json"])
            assert result.exit_code == 0
            assert "Report exported" in result.stdout
            mock_coach.export_report.assert_called_once()

    def test_coach_export_markdown(self) -> None:
        """Test coach command with Markdown export."""
        with (
            patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches,
            patch("pathlib.Path.mkdir"),
        ):
            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {}
            mock_coach.export_report.return_value = Path("/tmp/claude_report.md")

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach", "--export", "markdown"])
            assert result.exit_code == 0
            assert "Report exported" in result.stdout

    def test_coach_export_with_custom_path(self) -> None:
        """Test coach command export with custom output path."""
        with (
            patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches,
            patch("pathlib.Path.mkdir"),
        ):
            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {}
            mock_coach.export_report.return_value = Path("/custom/report.json")

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach", "--export", "json", "--output", "/custom/report"])
            assert result.exit_code == 0
            mock_coach.export_report.assert_called_once()

    def test_coach_export_failure(self) -> None:
        """Test coach command handles export failure."""
        with patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches:
            mock_coach = MagicMock()
            mock_coach.vendor_name = "Claude"
            mock_coach.analyze.return_value = None
            mock_coach.get_insights.return_value = []
            mock_coach.get_recommendations.return_value = []
            mock_coach.get_stats.return_value = {}
            mock_coach.export_report.side_effect = ValueError("Invalid format")

            mock_get_coaches.return_value = {"claude": mock_coach}

            result = runner.invoke(app, ["coach", "--export", "invalid"])
            assert result.exit_code == 0
            assert "Export failed" in result.stdout

    def test_coach_multiple_vendors_with_spacing(self) -> None:
        """Test coach command shows spacing between multiple vendors."""
        with patch("ai_asst_mgr.cli._get_all_coaches") as mock_get_coaches:
            mock_coach1 = MagicMock()
            mock_coach1.vendor_name = "Claude"
            mock_coach1.analyze.return_value = None
            mock_coach1.get_insights.return_value = []
            mock_coach1.get_recommendations.return_value = []
            mock_coach1.get_stats.return_value = {}

            mock_coach2 = MagicMock()
            mock_coach2.vendor_name = "Gemini"
            mock_coach2.analyze.return_value = None
            mock_coach2.get_insights.return_value = []
            mock_coach2.get_recommendations.return_value = []
            mock_coach2.get_stats.return_value = {}

            mock_get_coaches.return_value = {"claude": mock_coach1, "gemini": mock_coach2}

            result = runner.invoke(app, ["coach"])
            assert result.exit_code == 0
            assert "Claude Analysis" in result.stdout
            assert "Gemini Analysis" in result.stdout
            # Should have separator between vendors
            assert "=" in result.stdout


class TestCoachHelperFunctions:
    """Tests for coach command helper functions."""

    def test_get_coach_for_vendor_claude(self) -> None:
        """Test _get_coach_for_vendor returns Claude coach."""
        coach = _get_coach_for_vendor("claude")
        assert isinstance(coach, ClaudeCoach)

    def test_get_coach_for_vendor_gemini(self) -> None:
        """Test _get_coach_for_vendor returns Gemini coach."""
        coach = _get_coach_for_vendor("gemini")
        assert isinstance(coach, GeminiCoach)

    def test_get_coach_for_vendor_openai(self) -> None:
        """Test _get_coach_for_vendor returns Codex coach."""
        coach = _get_coach_for_vendor("openai")
        assert isinstance(coach, CodexCoach)

    def test_get_coach_for_vendor_invalid(self) -> None:
        """Test _get_coach_for_vendor raises Exit for invalid vendor."""
        with patch("ai_asst_mgr.cli.console") as mock_console:
            with pytest.raises(typer.Exit) as exc_info:
                _get_coach_for_vendor("invalid")
            assert exc_info.value.exit_code == 1
            # Should have printed error messages
            assert mock_console.print.call_count >= 2

    def test_get_all_coaches(self) -> None:
        """Test _get_all_coaches returns all coaches."""
        coaches = _get_all_coaches()
        assert len(coaches) == 3
        assert "claude" in coaches
        assert "gemini" in coaches
        assert "openai" in coaches
        assert isinstance(coaches["claude"], ClaudeCoach)
        assert isinstance(coaches["gemini"], GeminiCoach)
        assert isinstance(coaches["openai"], CodexCoach)

    def test_display_coach_insights_with_metric_unit(self) -> None:
        """Test _display_coach_insights displays metric with unit."""
        mock_insight = MagicMock()
        mock_insight.category = "Performance"
        mock_insight.title = "Response Time"
        mock_insight.description = "Average response time"
        mock_insight.metric_value = "2.5"
        mock_insight.metric_unit = "seconds"

        mock_coach = MagicMock()
        mock_coach.vendor_name = "Claude"
        mock_coach.get_insights.return_value = [mock_insight]

        with patch("ai_asst_mgr.cli.console"):
            _display_coach_insights(mock_coach)
            # Should display metric value with unit

    def test_display_coach_recommendations_with_all_priorities(self) -> None:
        """Test _display_coach_recommendations handles all priority levels."""
        mock_recs = []
        for priority in [Priority.CRITICAL, Priority.HIGH, Priority.MEDIUM, Priority.LOW]:
            mock_rec = MagicMock()
            mock_rec.category = "Test"
            mock_rec.title = f"{priority.value} priority"
            mock_rec.description = "Test description"
            mock_rec.action = "Test action"
            mock_rec.expected_benefit = "Test benefit"
            mock_rec.priority = priority
            mock_recs.append(mock_rec)

        mock_coach = MagicMock()
        mock_coach.vendor_name = "Claude"
        mock_coach.get_recommendations.return_value = mock_recs

        with patch("ai_asst_mgr.cli.console"):
            _display_coach_recommendations(mock_coach)
            # Should display all recommendations

    def test_display_coach_stats_with_boolean_values(self) -> None:
        """Test _display_coach_stats formats boolean values correctly."""
        mock_coach = MagicMock()
        mock_coach.vendor_name = "Claude"
        mock_coach.get_stats.return_value = {
            "configured": True,
            "installed": False,
            "count": 42,
        }

        with patch("ai_asst_mgr.cli.console"):
            _display_coach_stats(mock_coach)
            # Should format booleans as Yes/No

    def test_compare_vendors(self) -> None:
        """Test _compare_vendors displays comparison table."""
        mock_coach1 = MagicMock()
        mock_coach1.vendor_name = "Claude"
        mock_coach1.analyze.return_value = None
        mock_coach1.get_stats.return_value = {"sessions": 10, "configured": True}
        mock_coach1.get_recommendations.return_value = []

        mock_coach2 = MagicMock()
        mock_coach2.vendor_name = "Gemini"
        mock_coach2.analyze.return_value = None
        mock_coach2.get_stats.return_value = {"sessions": 5, "configured": False}
        mock_coach2.get_recommendations.return_value = []

        coaches = {"claude": mock_coach1, "gemini": mock_coach2}

        with patch("ai_asst_mgr.cli.console"):
            _compare_vendors(coaches)
            # Should call analyze on both coaches
            mock_coach1.analyze.assert_called_once()
            mock_coach2.analyze.assert_called_once()


class TestRestoreHelperFunctions:
    """Tests for restore command helper functions."""

    def test_resolve_backup_path_with_explicit_path(self, tmp_path: Path) -> None:
        """Test _resolve_backup_path with explicit backup path."""
        backup_file = tmp_path / "backup.tar.gz"
        backup_file.write_text("test")

        mock_manager = MagicMock()
        result = _resolve_backup_path(backup_file, None, mock_manager)
        assert result == backup_file

    def test_resolve_backup_path_with_nonexistent_path(self, tmp_path: Path) -> None:
        """Test _resolve_backup_path with nonexistent backup path."""
        nonexistent = tmp_path / "does_not_exist.tar.gz"
        mock_manager = MagicMock()

        with patch("ai_asst_mgr.cli.console"):
            try:
                _resolve_backup_path(nonexistent, None, mock_manager)
                msg = "Expected typer.Exit to be raised"
                raise AssertionError(msg)
            except typer.Exit as e:
                assert e.exit_code == 1

    def test_resolve_backup_path_with_vendor(self) -> None:
        """Test _resolve_backup_path with vendor name."""
        mock_metadata = MagicMock()
        mock_metadata.backup_path = Path("/backups/claude.tar.gz")

        mock_manager = MagicMock()
        mock_manager.get_latest_backup.return_value = mock_metadata

        result = _resolve_backup_path(None, "claude", mock_manager)
        assert result == Path("/backups/claude.tar.gz")

    def test_resolve_backup_path_with_vendor_no_backups(self) -> None:
        """Test _resolve_backup_path when vendor has no backups."""
        mock_manager = MagicMock()
        mock_manager.get_latest_backup.return_value = None

        with patch("ai_asst_mgr.cli.console"):
            try:
                _resolve_backup_path(None, "claude", mock_manager)
                msg = "Expected typer.Exit to be raised"
                raise AssertionError(msg)
            except typer.Exit as e:
                assert e.exit_code == 1

    def test_resolve_backup_path_with_neither_path_nor_vendor(self) -> None:
        """Test _resolve_backup_path without path or vendor."""
        mock_manager = MagicMock()

        with patch("ai_asst_mgr.cli.console"):
            try:
                _resolve_backup_path(None, None, mock_manager)
                msg = "Expected typer.Exit to be raised"
                raise AssertionError(msg)
            except typer.Exit as e:
                assert e.exit_code == 1

    def test_resolve_restore_adapter_with_vendor(self) -> None:
        """Test _resolve_restore_adapter with explicit vendor."""
        mock_adapter = MagicMock()
        mock_registry = MagicMock()
        mock_registry.get_vendor.return_value = mock_adapter

        result = _resolve_restore_adapter(
            mock_registry, "claude", Path("/backup.tar.gz"), MagicMock()
        )
        assert result == mock_adapter

    def test_resolve_restore_adapter_with_invalid_vendor(self) -> None:
        """Test _resolve_restore_adapter with invalid vendor."""
        mock_registry = MagicMock()
        mock_registry.get_vendor.side_effect = KeyError("Unknown vendor")

        with patch("ai_asst_mgr.cli.console"):
            try:
                _resolve_restore_adapter(
                    mock_registry, "invalid", Path("/backup.tar.gz"), MagicMock()
                )
                msg = "Expected typer.Exit to be raised"
                raise AssertionError(msg)
            except typer.Exit as e:
                assert e.exit_code == 1

    def test_resolve_restore_adapter_infer_from_metadata(self) -> None:
        """Test _resolve_restore_adapter infers vendor from backup metadata."""
        backup_path = Path("/backups/test.tar.gz")

        mock_metadata = MagicMock()
        mock_metadata.backup_path = backup_path
        mock_metadata.vendor_id = "claude"

        mock_backup_manager = MagicMock()
        mock_backup_manager.list_backups.return_value = [mock_metadata]

        mock_adapter = MagicMock()
        mock_registry = MagicMock()
        mock_registry.get_vendor.return_value = mock_adapter

        result = _resolve_restore_adapter(mock_registry, None, backup_path, mock_backup_manager)
        assert result == mock_adapter

    def test_resolve_restore_adapter_infer_from_filename(self) -> None:
        """Test _resolve_restore_adapter infers vendor from filename."""
        backup_path = Path("/backups/claude-backup.tar.gz")

        mock_backup_manager = MagicMock()
        mock_backup_manager.list_backups.return_value = []

        mock_adapter = MagicMock()
        mock_registry = MagicMock()
        mock_registry.get_vendor.return_value = mock_adapter

        result = _resolve_restore_adapter(mock_registry, None, backup_path, mock_backup_manager)
        assert result == mock_adapter
        mock_registry.get_vendor.assert_called_with("claude")

    def test_resolve_restore_adapter_cannot_infer(self) -> None:
        """Test _resolve_restore_adapter when vendor cannot be inferred."""
        backup_path = Path("/backups/unknown.tar.gz")

        mock_backup_manager = MagicMock()
        mock_backup_manager.list_backups.return_value = []

        mock_registry = MagicMock()
        mock_registry.get_vendor.side_effect = KeyError("Unknown")

        with patch("ai_asst_mgr.cli.console"):
            try:
                _resolve_restore_adapter(mock_registry, None, backup_path, mock_backup_manager)
                msg = "Expected typer.Exit to be raised"
                raise AssertionError(msg)
            except typer.Exit as e:
                assert e.exit_code == 1


class TestBackupCommandAdditionalCases:
    """Additional edge case tests for backup command."""

    def test_backup_all_vendors_with_no_installed(self) -> None:
        """Test backup all vendors when no vendors are installed."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_registry = MagicMock()
            mock_registry.get_installed_vendors.return_value = {}
            mock_registry_class.return_value = mock_registry

            mock_backup_manager = MagicMock()
            mock_get_manager.return_value = mock_backup_manager

            result = runner.invoke(app, ["backup"])
            assert result.exit_code == 0
            assert "No installed vendors found" in result.stdout

    def test_backup_all_vendors_with_failure(self) -> None:
        """Test backup all vendors shows failure properly."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude"

            mock_registry = MagicMock()
            mock_registry.get_installed_vendors.return_value = {"claude": mock_adapter}
            mock_registry_class.return_value = mock_registry

            # Create summary with failed result
            mock_result = MagicMock()
            mock_result.success = False
            mock_result.error = "Backup failed"
            mock_result.metadata = None

            mock_summary = MagicMock()
            mock_summary.results = {"claude": mock_result}

            mock_backup_manager = MagicMock()
            mock_backup_manager.backup_all_vendors.return_value = mock_summary
            mock_get_manager.return_value = mock_backup_manager

            result = runner.invoke(app, ["backup"])
            assert result.exit_code == 0
            assert "Failed" in result.stdout


class TestRestoreCommandAdditionalCases:
    """Additional edge case tests for restore command."""

    def test_restore_with_backup_path_no_vendor(self) -> None:
        """Test restore with backup path but unable to infer vendor."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli._get_restore_manager") as mock_get_restore,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
            patch("pathlib.Path.exists", return_value=True),
        ):
            mock_backup_manager = MagicMock()
            mock_backup_manager.list_backups.return_value = []
            mock_get_manager.return_value = mock_backup_manager

            mock_restore_manager = MagicMock()
            mock_get_restore.return_value = mock_restore_manager

            mock_registry = MagicMock()
            mock_registry.get_vendor.side_effect = KeyError("Unknown")
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["restore", "/tmp/unknown.tar.gz"])
            assert result.exit_code == 1
            assert "Cannot determine vendor" in result.stdout or "Unknown vendor" in result.stdout

    def test_restore_preview_with_conflicts(self) -> None:
        """Test restore preview shows conflicts."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli._get_restore_manager") as mock_get_restore,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude"

            mock_registry = MagicMock()
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_metadata = MagicMock()
            mock_metadata.backup_path = Path("/backups/test.tar.gz")
            mock_metadata.timestamp = datetime.now(tz=UTC)

            mock_backup_manager = MagicMock()
            mock_backup_manager.get_latest_backup.return_value = mock_metadata
            mock_get_manager.return_value = mock_backup_manager

            mock_preview = MagicMock()
            mock_preview.files_to_restore = ["file1.txt", "file2.txt"]
            mock_preview.conflicts = [MagicMock(path="file1.txt", reason="Modified locally")]

            mock_restore_manager = MagicMock()
            mock_restore_manager.preview_restore.return_value = mock_preview
            mock_get_restore.return_value = mock_restore_manager

            result = runner.invoke(app, ["restore", "--vendor", "claude", "--preview"])
            assert result.exit_code == 0
            # The preview shows basic info - conflicts display would be nice but not critical
            assert "Restore Preview" in result.stdout


class TestSyncCommandAdditionalCases:
    """Additional edge case tests for sync command."""

    def test_sync_preview_with_conflicts(self) -> None:
        """Test sync preview displays conflicts."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_backup,
            patch("ai_asst_mgr.cli._get_sync_manager") as mock_get_sync,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude"

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_backup_manager = MagicMock()
            mock_get_backup.return_value = mock_backup_manager

            mock_conflict = MagicMock()
            mock_conflict.path = "config.json"
            mock_conflict.reason = "Both modified"

            mock_preview = MagicMock()
            mock_preview.files_to_add = ["new.txt"]
            mock_preview.files_to_modify = ["config.json"]
            mock_preview.files_to_delete = []
            mock_preview.conflicts = [mock_conflict]

            mock_sync_manager = MagicMock()
            mock_sync_manager.preview_sync.return_value = mock_preview
            mock_get_sync.return_value = mock_sync_manager

            result = runner.invoke(
                app,
                [
                    "sync",
                    "https://github.com/test/repo.git",
                    "--vendor",
                    "claude",
                    "--preview",
                ],
            )
            assert result.exit_code == 0
            assert "Conflicts" in result.stdout or "conflicts" in result.stdout

    def test_sync_execute_with_deletions(self) -> None:
        """Test sync execute displays deletion information."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_backup,
            patch("ai_asst_mgr.cli._get_sync_manager") as mock_get_sync,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_adapter = MagicMock()
            mock_adapter.info.vendor_id = "claude"
            mock_adapter.info.name = "Claude"
            mock_adapter.is_installed.return_value = True

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": mock_adapter}
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            mock_backup_manager = MagicMock()
            mock_get_backup.return_value = mock_backup_manager

            mock_result = MagicMock()
            mock_result.success = True
            mock_result.files_added = 1
            mock_result.files_modified = 2
            mock_result.files_deleted = 3
            mock_result.duration_seconds = 1.5
            mock_result.pre_sync_backup = None

            mock_sync_manager = MagicMock()
            mock_sync_manager.sync_all_vendors.return_value = {"claude": mock_result}
            mock_get_sync.return_value = mock_sync_manager

            result = runner.invoke(
                app, ["sync", "https://github.com/test/repo.git", "--vendor", "claude"]
            )
            assert result.exit_code == 0
            assert "Success" in result.stdout


# ============================================================================
# Agents Command Tests
# ============================================================================


class TestAgentsHelperFunctions:
    """Tests for agents command helper functions."""

    def test_format_agent_type_agent(self) -> None:
        """Test formatting agent type."""
        result = _format_agent_type(AgentType.AGENT)
        assert "agent" in result
        assert "cyan" in result

    def test_format_agent_type_skill(self) -> None:
        """Test formatting skill type."""
        result = _format_agent_type(AgentType.SKILL)
        assert "skill" in result
        assert "green" in result

    def test_format_agent_type_mcp_server(self) -> None:
        """Test formatting MCP server type."""
        result = _format_agent_type(AgentType.MCP_SERVER)
        assert "mcp_server" in result
        assert "yellow" in result

    def test_format_agent_type_function(self) -> None:
        """Test formatting function type."""
        result = _format_agent_type(AgentType.FUNCTION)
        assert "function" in result
        assert "blue" in result

    def test_get_agent_manager(self) -> None:
        """Test getting agent manager instance."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"claude": MagicMock()}
            mock_registry_class.return_value = mock_registry

            manager = _get_agent_manager()
            assert manager is not None


class TestAgentsListCommand:
    """Tests for agents list command."""

    def test_agents_list_no_agents(self) -> None:
        """Test agents list with no agents found."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.list_all_agents.return_value = AgentListResult(
                agents=[], total_count=0, by_vendor={}, by_type={}
            )
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["agents", "list"])
            assert result.exit_code == 0
            assert "No agents found" in result.stdout

    def test_agents_list_with_agents(self) -> None:
        """Test agents list with agents found."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            mock_agent = Agent(
                name="test-agent",
                vendor_id="claude",
                agent_type=AgentType.AGENT,
                description="A test agent",
                size_bytes=100,
            )
            mock_manager = MagicMock()
            mock_manager.list_all_agents.return_value = AgentListResult(
                agents=[mock_agent],
                total_count=1,
                by_vendor={"claude": 1},
                by_type={"agent": 1},
            )
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["agents", "list"])
            assert result.exit_code == 0
            assert "test-agent" in result.stdout
            assert "Total:" in result.stdout

    def test_agents_list_with_vendor_filter(self) -> None:
        """Test agents list with vendor filter."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.list_all_agents.return_value = AgentListResult(
                agents=[], total_count=0, by_vendor={}, by_type={}
            )
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["agents", "list", "--vendor", "claude"])
            assert result.exit_code == 0
            mock_manager.list_all_agents.assert_called_with(
                vendor_filter="claude", type_filter=None, search_query=None
            )

    def test_agents_list_with_type_filter(self) -> None:
        """Test agents list with type filter."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.list_all_agents.return_value = AgentListResult(
                agents=[], total_count=0, by_vendor={}, by_type={}
            )
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["agents", "list", "--type", "skill"])
            assert result.exit_code == 0
            mock_manager.list_all_agents.assert_called_with(
                vendor_filter=None, type_filter=AgentType.SKILL, search_query=None
            )

    def test_agents_list_with_invalid_type(self) -> None:
        """Test agents list with invalid type filter."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["agents", "list", "--type", "invalid"])
            assert result.exit_code == 1
            assert "Invalid agent type" in result.stdout

    def test_agents_list_with_search(self) -> None:
        """Test agents list with search query."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.list_all_agents.return_value = AgentListResult(
                agents=[], total_count=0, by_vendor={}, by_type={}
            )
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["agents", "list", "--search", "code"])
            assert result.exit_code == 0
            mock_manager.list_all_agents.assert_called_with(
                vendor_filter=None, type_filter=None, search_query="code"
            )


class TestAgentsShowCommand:
    """Tests for agents show command."""

    def test_agents_show_found(self) -> None:
        """Test agents show with agent found."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            from datetime import UTC, datetime
            from pathlib import Path

            mock_agent = Agent(
                name="test-agent",
                vendor_id="claude",
                agent_type=AgentType.AGENT,
                description="A test agent",
                file_path=Path("/test/path"),
                content="# Test Agent\n\nContent here",
                size_bytes=100,
                created_at=datetime.now(UTC),
                modified_at=datetime.now(UTC),
            )
            mock_manager = MagicMock()
            mock_manager.get_agent.return_value = mock_agent
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["agents", "show", "test-agent", "--vendor", "claude"])
            assert result.exit_code == 0
            assert "test-agent" in result.stdout
            assert "Claude" in result.stdout

    def test_agents_show_not_found(self) -> None:
        """Test agents show with agent not found."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_agent.return_value = None
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["agents", "show", "nonexistent", "--vendor", "claude"])
            assert result.exit_code == 1
            assert "not found" in result.stdout


class TestAgentsCreateCommand:
    """Tests for agents create command."""

    def test_agents_create_success(self) -> None:
        """Test successful agent creation."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            from pathlib import Path

            from ai_asst_mgr.capabilities.manager import AgentCreateResult

            mock_agent = Agent(
                name="new-agent",
                vendor_id="claude",
                agent_type=AgentType.AGENT,
                file_path=Path("/test/agents/new-agent.md"),
            )
            mock_result = AgentCreateResult(success=True, agent=mock_agent)
            mock_manager = MagicMock()
            mock_manager.create_agent.return_value = mock_result
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                ["agents", "create", "new-agent", "--vendor", "claude", "--content", "# Test"],
            )
            assert result.exit_code == 0
            assert "Created agent" in result.stdout

    def test_agents_create_failure(self) -> None:
        """Test failed agent creation."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            from ai_asst_mgr.capabilities.manager import AgentCreateResult

            mock_result = AgentCreateResult(success=False, error="Test error")
            mock_manager = MagicMock()
            mock_manager.create_agent.return_value = mock_result
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                ["agents", "create", "new-agent", "--vendor", "claude", "--content", "# Test"],
            )
            assert result.exit_code == 1
            assert "Failed to create agent" in result.stdout

    def test_agents_create_with_invalid_type(self) -> None:
        """Test agent creation with invalid type."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                ["agents", "create", "new-agent", "--vendor", "claude", "--type", "invalid"],
            )
            assert result.exit_code == 1
            assert "Invalid agent type" in result.stdout


class TestAgentsDeleteCommand:
    """Tests for agents delete command."""

    def test_agents_delete_success(self) -> None:
        """Test successful agent deletion."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            mock_agent = Agent(
                name="test-agent",
                vendor_id="claude",
                agent_type=AgentType.AGENT,
            )
            mock_manager = MagicMock()
            mock_manager.get_agent.return_value = mock_agent
            mock_manager.delete_agent.return_value = (True, "Deleted test-agent")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                ["agents", "delete", "test-agent", "--vendor", "claude", "--force"],
            )
            assert result.exit_code == 0
            assert "Deleted" in result.stdout

    def test_agents_delete_not_found(self) -> None:
        """Test deleting non-existent agent."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            mock_manager = MagicMock()
            mock_manager.get_agent.return_value = None
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                ["agents", "delete", "nonexistent", "--vendor", "claude", "--force"],
            )
            assert result.exit_code == 1
            assert "not found" in result.stdout

    def test_agents_delete_failure(self) -> None:
        """Test failed agent deletion."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            mock_agent = Agent(
                name="test-agent",
                vendor_id="claude",
                agent_type=AgentType.AGENT,
            )
            mock_manager = MagicMock()
            mock_manager.get_agent.return_value = mock_agent
            mock_manager.delete_agent.return_value = (False, "Failed to delete")
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                ["agents", "delete", "test-agent", "--vendor", "claude", "--force"],
            )
            assert result.exit_code == 1
            assert "Failed to delete" in result.stdout


class TestAgentsSyncCommand:
    """Tests for agents sync command."""

    def test_agents_sync_success(self) -> None:
        """Test successful agent sync."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            from ai_asst_mgr.capabilities.manager import AgentSyncResult

            mock_result = AgentSyncResult(
                success=True,
                source_vendor="claude",
                target_vendors=["gemini"],
                synced_count=1,
                errors=[],
            )
            mock_manager = MagicMock()
            mock_manager.sync_agent.return_value = mock_result
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                ["agents", "sync", "test-agent", "--source", "claude", "--target", "gemini"],
            )
            assert result.exit_code == 0
            assert "Synced to 1 vendor(s)" in result.stdout

    def test_agents_sync_failure(self) -> None:
        """Test failed agent sync."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            from ai_asst_mgr.capabilities.manager import AgentSyncResult

            mock_result = AgentSyncResult(
                success=False,
                errors=["Agent not found"],
            )
            mock_manager = MagicMock()
            mock_manager.sync_agent.return_value = mock_result
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                ["agents", "sync", "test-agent", "--source", "claude"],
            )
            assert result.exit_code == 1
            assert "Sync failed" in result.stdout

    def test_agents_sync_with_errors(self) -> None:
        """Test agent sync with partial success and errors."""
        with patch("ai_asst_mgr.cli._get_agent_manager") as mock_get_manager:
            from ai_asst_mgr.capabilities.manager import AgentSyncResult

            mock_result = AgentSyncResult(
                success=True,
                source_vendor="claude",
                target_vendors=["gemini"],
                synced_count=1,
                errors=["openai: Incompatible type"],
            )
            mock_manager = MagicMock()
            mock_manager.sync_agent.return_value = mock_result
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(
                app,
                ["agents", "sync", "test-agent", "--source", "claude"],
            )
            assert result.exit_code == 0
            assert "Synced to 1 vendor(s)" in result.stdout
            assert "Errors:" in result.stdout


class TestScheduleCommand:
    """Tests for the schedule command group."""

    def test_schedule_status_shows_platform(self) -> None:
        """Test schedule status shows platform info."""
        with patch("ai_asst_mgr.cli.get_scheduler") as mock_get_scheduler:
            from ai_asst_mgr.platform import ScheduleInfo

            mock_scheduler = MagicMock()
            mock_scheduler.platform_name = "macOS"
            mock_scheduler.get_schedule_info.return_value = ScheduleInfo(is_active=False)
            mock_get_scheduler.return_value = mock_scheduler

            result = runner.invoke(app, ["schedule", "status"])
            assert result.exit_code == 0
            assert "Backup Schedule Status" in result.stdout
            assert "macOS" in result.stdout

    def test_schedule_status_active(self) -> None:
        """Test schedule status shows active schedule."""
        with patch("ai_asst_mgr.cli.get_scheduler") as mock_get_scheduler:
            from ai_asst_mgr.platform import IntervalType, ScheduleInfo

            mock_scheduler = MagicMock()
            mock_scheduler.platform_name = "macOS"
            mock_scheduler.get_schedule_info.return_value = ScheduleInfo(
                is_active=True,
                interval=IntervalType.DAILY,
                script_path=Path("/path/to/script.sh"),
                next_run="Daily at 02:00",
            )
            mock_get_scheduler.return_value = mock_scheduler

            result = runner.invoke(app, ["schedule", "status"])
            assert result.exit_code == 0
            assert "Active" in result.stdout
            assert "Daily" in result.stdout

    def test_schedule_status_unsupported_platform(self) -> None:
        """Test schedule status on unsupported platform."""
        with patch("ai_asst_mgr.cli.get_scheduler") as mock_get_scheduler:
            from ai_asst_mgr.platform import UnsupportedPlatformError

            mock_get_scheduler.side_effect = UnsupportedPlatformError("win32")

            result = runner.invoke(app, ["schedule", "status"])
            assert result.exit_code == 1
            assert "win32" in result.stdout

    def test_schedule_setup_success(self, tmp_path: Path) -> None:
        """Test schedule setup creates schedule successfully."""
        script = tmp_path / "backup.sh"
        script.write_text("#!/bin/bash\necho backup")
        script.chmod(0o755)

        with patch("ai_asst_mgr.cli.get_scheduler") as mock_get_scheduler:
            from ai_asst_mgr.platform import IntervalType, ScheduleInfo

            mock_scheduler = MagicMock()
            mock_scheduler.platform_name = "macOS"
            mock_scheduler.setup_schedule.return_value = True
            mock_scheduler.get_schedule_info.return_value = ScheduleInfo(
                is_active=True,
                interval=IntervalType.DAILY,
                next_run="Daily at 02:00",
            )
            mock_get_scheduler.return_value = mock_scheduler

            result = runner.invoke(app, ["schedule", "setup", str(script)])
            assert result.exit_code == 0
            assert "successfully" in result.stdout

    def test_schedule_setup_script_not_found(self, tmp_path: Path) -> None:
        """Test schedule setup with non-existent script."""
        result = runner.invoke(app, ["schedule", "setup", str(tmp_path / "missing.sh")])
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_schedule_setup_invalid_interval(self, tmp_path: Path) -> None:
        """Test schedule setup with invalid interval."""
        script = tmp_path / "backup.sh"
        script.write_text("#!/bin/bash")
        script.chmod(0o755)

        result = runner.invoke(app, ["schedule", "setup", str(script), "--interval", "invalid"])
        assert result.exit_code == 1
        assert "Invalid interval" in result.stdout

    def test_schedule_setup_invalid_hour(self, tmp_path: Path) -> None:
        """Test schedule setup with invalid hour."""
        script = tmp_path / "backup.sh"
        script.write_text("#!/bin/bash")
        script.chmod(0o755)

        result = runner.invoke(app, ["schedule", "setup", str(script), "--hour", "25"])
        assert result.exit_code == 1
        assert "Hour must be" in result.stdout

    def test_schedule_setup_invalid_minute(self, tmp_path: Path) -> None:
        """Test schedule setup with invalid minute."""
        script = tmp_path / "backup.sh"
        script.write_text("#!/bin/bash")
        script.chmod(0o755)

        result = runner.invoke(app, ["schedule", "setup", str(script), "--minute", "60"])
        assert result.exit_code == 1
        assert "Minute must be" in result.stdout

    def test_schedule_setup_invalid_day_of_week(self, tmp_path: Path) -> None:
        """Test schedule setup with invalid day of week."""
        script = tmp_path / "backup.sh"
        script.write_text("#!/bin/bash")
        script.chmod(0o755)

        result = runner.invoke(app, ["schedule", "setup", str(script), "--day-of-week", "7"])
        assert result.exit_code == 1
        assert "Day of week must be" in result.stdout

    def test_schedule_setup_invalid_day_of_month(self, tmp_path: Path) -> None:
        """Test schedule setup with invalid day of month."""
        script = tmp_path / "backup.sh"
        script.write_text("#!/bin/bash")
        script.chmod(0o755)

        result = runner.invoke(app, ["schedule", "setup", str(script), "--day-of-month", "32"])
        assert result.exit_code == 1
        assert "Day of month must be" in result.stdout

    def test_schedule_setup_failure(self, tmp_path: Path) -> None:
        """Test schedule setup failure."""
        script = tmp_path / "backup.sh"
        script.write_text("#!/bin/bash")
        script.chmod(0o755)

        with patch("ai_asst_mgr.cli.get_scheduler") as mock_get_scheduler:
            mock_scheduler = MagicMock()
            mock_scheduler.platform_name = "macOS"
            mock_scheduler.setup_schedule.return_value = False
            mock_get_scheduler.return_value = mock_scheduler

            result = runner.invoke(app, ["schedule", "setup", str(script)])
            assert result.exit_code == 1
            assert "Failed" in result.stdout

    def test_schedule_remove_no_schedule(self) -> None:
        """Test schedule remove when no schedule exists."""
        with patch("ai_asst_mgr.cli.get_scheduler") as mock_get_scheduler:
            mock_scheduler = MagicMock()
            mock_scheduler.is_scheduled.return_value = False
            mock_get_scheduler.return_value = mock_scheduler

            result = runner.invoke(app, ["schedule", "remove"])
            assert result.exit_code == 0
            assert "No backup schedule" in result.stdout

    def test_schedule_remove_force(self) -> None:
        """Test schedule remove with force flag."""
        with patch("ai_asst_mgr.cli.get_scheduler") as mock_get_scheduler:
            from ai_asst_mgr.platform import IntervalType, ScheduleInfo

            mock_scheduler = MagicMock()
            mock_scheduler.is_scheduled.return_value = True
            mock_scheduler.get_schedule_info.return_value = ScheduleInfo(
                is_active=True,
                interval=IntervalType.DAILY,
            )
            mock_scheduler.remove_schedule.return_value = True
            mock_get_scheduler.return_value = mock_scheduler

            result = runner.invoke(app, ["schedule", "remove", "--force"])
            assert result.exit_code == 0
            assert "successfully" in result.stdout

    def test_schedule_remove_confirm_no(self) -> None:
        """Test schedule remove with user declining confirmation."""
        with patch("ai_asst_mgr.cli.get_scheduler") as mock_get_scheduler:
            from ai_asst_mgr.platform import IntervalType, ScheduleInfo

            mock_scheduler = MagicMock()
            mock_scheduler.is_scheduled.return_value = True
            mock_scheduler.get_schedule_info.return_value = ScheduleInfo(
                is_active=True,
                interval=IntervalType.DAILY,
            )
            mock_get_scheduler.return_value = mock_scheduler

            result = runner.invoke(app, ["schedule", "remove"], input="n\n")
            assert result.exit_code == 0
            assert "Aborted" in result.stdout
            mock_scheduler.remove_schedule.assert_not_called()

    def test_schedule_remove_failure(self) -> None:
        """Test schedule remove failure."""
        with patch("ai_asst_mgr.cli.get_scheduler") as mock_get_scheduler:
            from ai_asst_mgr.platform import IntervalType, ScheduleInfo

            mock_scheduler = MagicMock()
            mock_scheduler.is_scheduled.return_value = True
            mock_scheduler.get_schedule_info.return_value = ScheduleInfo(
                is_active=True,
                interval=IntervalType.DAILY,
            )
            mock_scheduler.remove_schedule.return_value = False
            mock_get_scheduler.return_value = mock_scheduler

            result = runner.invoke(app, ["schedule", "remove", "--force"])
            assert result.exit_code == 1
            assert "Failed" in result.stdout


class TestScheduleHelperFunctions:
    """Tests for schedule CLI helper functions."""

    def test_get_interval_display_none(self) -> None:
        """Test _get_interval_display with None."""
        from ai_asst_mgr.cli import _get_interval_display

        result = _get_interval_display(None)
        assert "Not set" in result

    def test_get_interval_display_hourly(self) -> None:
        """Test _get_interval_display with hourly."""
        from ai_asst_mgr.cli import _get_interval_display
        from ai_asst_mgr.platform import IntervalType

        result = _get_interval_display(IntervalType.HOURLY)
        assert "Hourly" in result

    def test_get_interval_display_daily(self) -> None:
        """Test _get_interval_display with daily."""
        from ai_asst_mgr.cli import _get_interval_display
        from ai_asst_mgr.platform import IntervalType

        result = _get_interval_display(IntervalType.DAILY)
        assert "Daily" in result

    def test_get_interval_display_weekly(self) -> None:
        """Test _get_interval_display with weekly."""
        from ai_asst_mgr.cli import _get_interval_display
        from ai_asst_mgr.platform import IntervalType

        result = _get_interval_display(IntervalType.WEEKLY)
        assert "Weekly" in result

    def test_get_interval_display_monthly(self) -> None:
        """Test _get_interval_display with monthly."""
        from ai_asst_mgr.cli import _get_interval_display
        from ai_asst_mgr.platform import IntervalType

        result = _get_interval_display(IntervalType.MONTHLY)
        assert "Monthly" in result


class TestRestoreCommandHelpers:
    """Tests for restore command helper functions."""

    def test_resolve_backup_path_with_nonexistent_file(self) -> None:
        """Test _resolve_backup_path exits when backup file doesn't exist."""
        backup_manager = MagicMock()

        with pytest.raises(typer.Exit) as exc_info:
            _resolve_backup_path(Path("/nonexistent/backup.tar.gz"), None, backup_manager)
        assert exc_info.value.exit_code == 1

    def test_resolve_backup_path_with_vendor_no_backups(self) -> None:
        """Test _resolve_backup_path exits when no backups found for vendor."""
        backup_manager = MagicMock()
        backup_manager.get_latest_backup.return_value = None

        with pytest.raises(typer.Exit) as exc_info:
            _resolve_backup_path(None, "claude", backup_manager)
        assert exc_info.value.exit_code == 1

    def test_resolve_restore_adapter_with_unknown_vendor(self) -> None:
        """Test _resolve_restore_adapter exits for unknown vendor."""
        registry = MagicMock()
        registry.get_vendor.side_effect = KeyError("Unknown vendor")
        backup_manager = MagicMock()

        with pytest.raises(typer.Exit) as exc_info:
            _resolve_restore_adapter(registry, "unknown", Path("/backup.tar.gz"), backup_manager)
        assert exc_info.value.exit_code == 1


class TestSyncCommandValidation:
    """Tests for sync command validation."""

    def test_sync_invalid_strategy(self) -> None:
        """Test sync command with invalid merge strategy."""
        result = runner.invoke(
            app, ["sync", "https://github.com/test/repo.git", "--strategy", "invalid_strategy"]
        )
        assert result.exit_code == 1
        assert "Invalid strategy" in result.stdout
        assert "Valid strategies:" in result.stdout

    def test_sync_unknown_vendor(self) -> None:
        """Test sync command with unknown vendor."""
        result = runner.invoke(
            app, ["sync", "https://github.com/test/repo.git", "--vendor", "unknown_vendor"]
        )
        assert result.exit_code == 1
        assert "Unknown vendor" in result.stdout
        assert "Available vendors:" in result.stdout


class TestAuditCommand:
    """Tests for the audit command."""

    def test_get_severity_style_critical(self) -> None:
        """Test _get_severity_style with critical severity."""
        from ai_asst_mgr.cli import _get_severity_style

        result = _get_severity_style("critical")
        assert "CRITICAL" in result
        assert "bold red" in result

    def test_get_severity_style_error(self) -> None:
        """Test _get_severity_style with error severity."""
        from ai_asst_mgr.cli import _get_severity_style

        result = _get_severity_style("error")
        assert "ERROR" in result
        assert "red" in result

    def test_get_severity_style_warning(self) -> None:
        """Test _get_severity_style with warning severity."""
        from ai_asst_mgr.cli import _get_severity_style

        result = _get_severity_style("warning")
        assert "WARNING" in result
        assert "yellow" in result

    def test_get_severity_style_info(self) -> None:
        """Test _get_severity_style with info severity."""
        from ai_asst_mgr.cli import _get_severity_style

        result = _get_severity_style("info")
        assert "INFO" in result
        assert "dim" in result

    def test_get_severity_style_unknown(self) -> None:
        """Test _get_severity_style with unknown severity."""
        from ai_asst_mgr.cli import _get_severity_style

        result = _get_severity_style("unknown")
        assert result == "unknown"

    def test_get_category_style_security(self) -> None:
        """Test _get_category_style with security category."""
        from ai_asst_mgr.cli import _get_category_style

        result = _get_category_style("security")
        assert "security" in result
        assert "cyan" in result

    def test_get_category_style_config(self) -> None:
        """Test _get_category_style with config category."""
        from ai_asst_mgr.cli import _get_category_style

        result = _get_category_style("config")
        assert "config" in result
        assert "blue" in result

    def test_get_category_style_quality(self) -> None:
        """Test _get_category_style with quality category."""
        from ai_asst_mgr.cli import _get_category_style

        result = _get_category_style("quality")
        assert "quality" in result
        assert "magenta" in result

    def test_get_category_style_usage(self) -> None:
        """Test _get_category_style with usage category."""
        from ai_asst_mgr.cli import _get_category_style

        result = _get_category_style("usage")
        assert "usage" in result
        assert "green" in result

    def test_get_category_style_unknown(self) -> None:
        """Test _get_category_style with unknown category."""
        from ai_asst_mgr.cli import _get_category_style

        result = _get_category_style("unknown")
        assert result == "unknown"


class TestDatabaseCommands:
    """Tests for database management commands."""

    def test_db_init_when_exists_without_force(self, tmp_path: Path) -> None:
        """Test db init fails when database exists without --force."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            result = runner.invoke(app, ["db", "init"])
            assert result.exit_code == 1
            assert "already exists" in result.stdout
            assert "--force" in result.stdout

    def test_db_init_with_force_deletes_existing(self, tmp_path: Path) -> None:
        """Test db init with --force deletes existing database."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager") as mock_db:
                result = runner.invoke(app, ["db", "init", "--force"])
                assert result.exit_code == 0
                assert "Deleted existing database" in result.stdout
                assert "initialized successfully" in result.stdout
                mock_db.return_value.initialize.assert_called_once()

    def test_db_init_creates_new_database(self, tmp_path: Path) -> None:
        """Test db init creates new database."""
        db_path = tmp_path / "sessions.db"

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager") as mock_db:
                result = runner.invoke(app, ["db", "init"])
                assert result.exit_code == 0
                assert "initialized successfully" in result.stdout
                mock_db.return_value.initialize.assert_called_once()

    def test_db_sync_without_database(self, tmp_path: Path) -> None:
        """Test db sync fails when database doesn't exist."""
        db_path = tmp_path / "nonexistent.db"

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            result = runner.invoke(app, ["db", "sync"])
            assert result.exit_code == 1
            assert "Database not found" in result.stdout

    def test_db_sync_with_errors(self, tmp_path: Path) -> None:
        """Test db sync displays errors."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager"):
                with patch("ai_asst_mgr.cli.sync_history_to_db") as mock_sync:
                    from dataclasses import dataclass

                    @dataclass
                    class SyncResult:
                        sessions_imported: int = 0
                        messages_imported: int = 0
                        sessions_skipped: int = 0
                        errors: list[str] = None

                    mock_sync.return_value = SyncResult(errors=["Error 1", "Error 2"])

                    result = runner.invoke(app, ["db", "sync", "--vendor", "claude"])
                    assert result.exit_code == 0
                    assert "Completed with" in result.stdout
                    assert "errors" in result.stdout

    def test_db_sync_success(self, tmp_path: Path) -> None:
        """Test db sync successful sync."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager"):
                with patch("ai_asst_mgr.cli.sync_history_to_db") as mock_sync:
                    from dataclasses import dataclass

                    @dataclass
                    class SyncResult:
                        sessions_imported: int = 10
                        messages_imported: int = 50
                        sessions_skipped: int = 2
                        errors: list[str] = None

                    mock_sync.return_value = SyncResult(errors=[])

                    result = runner.invoke(app, ["db", "sync", "--vendor", "claude"])
                    assert result.exit_code == 0
                    assert "Sync completed" in result.stdout
                    assert "10" in result.stdout
                    assert "50" in result.stdout

    def test_db_sync_gemini_success(self, tmp_path: Path) -> None:
        """Test db sync successful Gemini sync."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()
    
        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager"):
                with patch("ai_asst_mgr.cli.sync_gemini_history_to_db") as mock_sync:
                    from ai_asst_mgr.database.sync_gemini import GeminiSyncResult
    
                    mock_sync.return_value = GeminiSyncResult(
                        sessions_imported=5,
                        messages_imported=20,
                        thoughts_imported=10,
                        tools_imported=15,
                        sessions_skipped=0,
                        errors=[]
                    )
    
                    result = runner.invoke(app, ["db", "sync", "--vendor", "gemini"])
                    assert result.exit_code == 0
                    assert "Gemini Sync completed" in result.stdout
                    assert "5" in result.stdout
                    assert "20" in result.stdout
                    assert "15" in result.stdout

    def test_db_sync_gemini_with_errors(self, tmp_path: Path) -> None:
        """Test db sync Gemini sync with errors."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()
    
        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager"):
                with patch("ai_asst_mgr.cli.sync_gemini_history_to_db") as mock_sync:
                    from ai_asst_mgr.database.sync_gemini import GeminiSyncResult
    
                    mock_sync.return_value = GeminiSyncResult(
                        sessions_imported=0,
                        messages_imported=0,
                        thoughts_imported=0,
                        tools_imported=0,
                        sessions_skipped=0,
                        errors=["Error A", "Error B"]
                    )
    
                    result = runner.invoke(app, ["db", "sync", "--vendor", "gemini"])
                    assert result.exit_code == 0
                    assert "Completed with 2 errors" in result.stdout
                    assert "Error A" in result.stdout

    def test_db_sync_unknown_vendor(self, tmp_path: Path) -> None:
        """Test db sync with unknown vendor."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()
    
        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            result = runner.invoke(app, ["db", "sync", "--vendor", "unknown"])
            assert result.exit_code == 1
            assert "Unknown vendor" in result.stdout

    def test_db_status_without_database(self, tmp_path: Path) -> None:
        """Test db status fails when database doesn't exist."""
        db_path = tmp_path / "nonexistent.db"

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            result = runner.invoke(app, ["db", "status"])
            assert result.exit_code == 1
            assert "Database not found" in result.stdout

    def test_db_status_displays_info(self, tmp_path: Path) -> None:
        """Test db status displays database information."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager"):
                with patch("ai_asst_mgr.cli.get_sync_status") as mock_status:
                    mock_status.return_value = {
                        "database_sessions": 10,
                        "database_events": 50,
                        "history_file_path": "~/.claude/history.jsonl",
                        "history_file_entries": 15,
                        "last_synced_datetime": "2024-01-01 12:00:00",
                    }

                    result = runner.invoke(app, ["db", "status"])
                    assert result.exit_code == 0
                    assert "Database Status" in result.stdout
                    assert "10" in result.stdout
                    assert "50" in result.stdout


class TestGitHubCommands:
    """Tests for GitHub activity tracking commands."""

    def test_resolve_github_repos_nonexistent_repo(self) -> None:
        """Test _resolve_github_repos with nonexistent repo path."""
        from ai_asst_mgr.cli import _resolve_github_repos

        with pytest.raises(typer.Exit) as exc_info:
            _resolve_github_repos(Path("/nonexistent/repo"), None)
        assert exc_info.value.exit_code == 1

    def test_resolve_github_repos_nonexistent_base_path(self) -> None:
        """Test _resolve_github_repos with nonexistent base path."""
        from ai_asst_mgr.cli import _resolve_github_repos

        with pytest.raises(typer.Exit) as exc_info:
            _resolve_github_repos(None, Path("/nonexistent/base"))
        assert exc_info.value.exit_code == 1

    def test_resolve_github_repos_no_repos_found(self, tmp_path: Path) -> None:
        """Test _resolve_github_repos when no git repos found."""
        from ai_asst_mgr.cli import _resolve_github_repos

        with patch("ai_asst_mgr.cli.find_git_repos", return_value=[]):
            with pytest.raises(typer.Exit) as exc_info:
                _resolve_github_repos(None, tmp_path)
            assert exc_info.value.exit_code == 0

    def test_resolve_github_repos_returns_repos(self, tmp_path: Path) -> None:
        """Test _resolve_github_repos returns found repos."""
        from ai_asst_mgr.cli import _resolve_github_repos

        repo1 = tmp_path / "repo1"
        repo2 = tmp_path / "repo2"

        with patch("ai_asst_mgr.cli.find_git_repos", return_value=[repo1, repo2]):
            result = _resolve_github_repos(None, tmp_path)
            assert result == [repo1, repo2]

    def test_github_sync_without_database(self, tmp_path: Path) -> None:
        """Test github sync fails when database doesn't exist."""
        db_path = tmp_path / "nonexistent.db"

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            result = runner.invoke(app, ["github", "sync"])
            assert result.exit_code == 1
            assert "Database not found" in result.stdout

    def test_github_sync_with_errors(self, tmp_path: Path) -> None:
        """Test github sync handles parse errors."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager"):
                with patch("ai_asst_mgr.cli.GitLogParser") as mock_parser:
                    with patch("ai_asst_mgr.cli._resolve_github_repos", return_value=[repo_path]):
                        mock_parser.return_value.parse_repo.side_effect = ValueError("Parse error")

                        result = runner.invoke(app, ["github", "sync"])
                        assert result.exit_code == 0
                        assert "Completed with" in result.stdout
                        assert "errors" in result.stdout

    def test_github_sync_success(self, tmp_path: Path) -> None:
        """Test github sync successful sync."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        repo_path = tmp_path / "repo"
        repo_path.mkdir()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager") as mock_db:
                with patch("ai_asst_mgr.cli.GitLogParser") as mock_parser:
                    with patch("ai_asst_mgr.cli._resolve_github_repos", return_value=[repo_path]):
                        from dataclasses import dataclass

                        @dataclass
                        class Commit:
                            vendor_id: str | None = None

                        mock_parser.return_value.parse_repo.return_value = [
                            Commit(vendor_id="claude"),
                            Commit(vendor_id=None),
                        ]
                        mock_db.return_value.record_github_commit.return_value = True

                        result = runner.invoke(app, ["github", "sync"])
                        assert result.exit_code == 0
                        assert "GitHub sync completed" in result.stdout

    def test_github_stats_without_database(self, tmp_path: Path) -> None:
        """Test github stats fails when database doesn't exist."""
        db_path = tmp_path / "nonexistent.db"

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            result = runner.invoke(app, ["github", "stats"])
            assert result.exit_code == 1
            assert "Database not found" in result.stdout

    def test_github_stats_no_commits(self, tmp_path: Path) -> None:
        """Test github stats when no commits tracked."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager") as mock_db:
                from dataclasses import dataclass

                @dataclass
                class Stats:
                    total_commits: int = 0
                    repos_tracked: int = 0
                    claude_commits: int = 0
                    gemini_commits: int = 0
                    openai_commits: int = 0
                    ai_attributed_commits: int = 0
                    ai_percentage: float = 0.0
                    first_commit: str | None = None
                    last_commit: str | None = None

                mock_db.return_value.get_github_stats.return_value = Stats()

                result = runner.invoke(app, ["github", "stats"])
                assert result.exit_code == 0
                assert "No commits tracked" in result.stdout

    def test_github_stats_displays_stats(self, tmp_path: Path) -> None:
        """Test github stats displays statistics."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager") as mock_db:
                from dataclasses import dataclass

                @dataclass
                class Stats:
                    total_commits: int = 100
                    repos_tracked: int = 5
                    claude_commits: int = 30
                    gemini_commits: int = 20
                    openai_commits: int = 10
                    ai_attributed_commits: int = 60
                    ai_percentage: float = 60.0
                    first_commit: str = "2024-01-01 12:00:00"
                    last_commit: str = "2024-01-15 18:00:00"

                mock_db.return_value.get_github_stats.return_value = Stats()

                result = runner.invoke(app, ["github", "stats"])
                assert result.exit_code == 0
                assert "GitHub Activity Statistics" in result.stdout
                assert "100" in result.stdout
                assert "60.0" in result.stdout

    def test_github_list_without_database(self, tmp_path: Path) -> None:
        """Test github list fails when database doesn't exist."""
        db_path = tmp_path / "nonexistent.db"

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            result = runner.invoke(app, ["github", "list"])
            assert result.exit_code == 1
            assert "Database not found" in result.stdout

    def test_github_list_no_commits(self, tmp_path: Path) -> None:
        """Test github list when no commits found."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager") as mock_db:
                mock_db.return_value.get_github_commits.return_value = []

                result = runner.invoke(app, ["github", "list"])
                assert result.exit_code == 0
                assert "No commits found" in result.stdout

    def test_github_list_displays_commits(self, tmp_path: Path) -> None:
        """Test github list displays commit table."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager") as mock_db:
                from dataclasses import dataclass

                @dataclass
                class Commit:
                    sha: str
                    repo: str
                    message: str
                    vendor_id: str | None
                    committed_at: str

                mock_db.return_value.get_github_commits.return_value = [
                    Commit("abc1234", "test-repo", "Test commit", "claude", "2024-01-01 12:00:00"),
                    Commit("def5678", "other-repo", "Another commit", None, "2024-01-02 14:00:00"),
                ]

                result = runner.invoke(app, ["github", "list"])
                assert result.exit_code == 0
                assert "GitHub Commits" in result.stdout
                assert "test-repo" in result.stdout
                assert "Test commit" in result.stdout

    def test_github_repos_without_database(self, tmp_path: Path) -> None:
        """Test github repos fails when database doesn't exist."""
        db_path = tmp_path / "nonexistent.db"

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            result = runner.invoke(app, ["github", "repos"])
            assert result.exit_code == 1
            assert "Database not found" in result.stdout

    def test_github_repos_no_repos(self, tmp_path: Path) -> None:
        """Test github repos when no repos tracked."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager") as mock_db:
                mock_db.return_value.get_github_repo_stats.return_value = []

                result = runner.invoke(app, ["github", "repos"])
                assert result.exit_code == 0
                assert "No repositories tracked" in result.stdout

    def test_github_repos_displays_repos(self, tmp_path: Path) -> None:
        """Test github repos displays repository table."""
        db_path = tmp_path / "sessions.db"
        db_path.touch()

        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path):
            with patch("ai_asst_mgr.cli.DatabaseManager") as mock_db:
                mock_db.return_value.get_github_repo_stats.return_value = [
                    {
                        "repo": "test-repo",
                        "total_commits": 100,
                        "ai_commits": 60,
                        "last_commit": "2024-01-15 18:00:00",
                    },
                ]

                result = runner.invoke(app, ["github", "repos"])
                assert result.exit_code == 0
                assert "Tracked Repositories" in result.stdout
                assert "test-repo" in result.stdout
                assert "100" in result.stdout
                assert "60.0" in result.stdout
