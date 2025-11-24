"""Unit tests for CLI module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ai_asst_mgr import cli
from ai_asst_mgr.adapters.base import VendorStatus
from ai_asst_mgr.cli import _get_notes_for_status, _get_status_display, app

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
