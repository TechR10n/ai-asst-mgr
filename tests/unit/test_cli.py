"""Unit tests for CLI module."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ai_asst_mgr import cli
from ai_asst_mgr.adapters.base import VendorAdapter
from ai_asst_mgr.cli import app

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
