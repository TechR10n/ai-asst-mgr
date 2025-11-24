"""Unit tests for CLI module."""

from typer.testing import CliRunner

from ai_asst_mgr import cli
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
