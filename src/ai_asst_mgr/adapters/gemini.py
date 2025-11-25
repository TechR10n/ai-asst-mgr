"""Gemini CLI vendor adapter implementation.

This module provides the GeminiAdapter class for managing Gemini CLI
configurations, including settings, API keys, MCP servers, and backup operations.
"""

from __future__ import annotations

import json
import shutil
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ai_asst_mgr.adapters.base import VendorAdapter, VendorInfo, VendorStatus
from ai_asst_mgr.utils import git_clone, is_command_available, unpack_tar_securely

if TYPE_CHECKING:
    from collections.abc import Iterator

# Constants for audit scoring
_MIN_API_KEY_LENGTH = 10


class GeminiAdapter(VendorAdapter):
    """Adapter for Gemini CLI AI assistant.

    Gemini CLI stores its configuration in ~/.gemini/ with the following structure:
    - settings.json - Main configuration file with API key
    - mcp_servers/ - MCP server configurations
    - GEMINI.md - Documentation and hierarchy
    """

    def __init__(self) -> None:
        """Initialize the Gemini CLI adapter."""
        self._config_dir = Path.home() / ".gemini"
        self._settings_file = self._config_dir / "settings.json"
        self._gemini_md = self._config_dir / "GEMINI.md"

    @property
    def info(self) -> VendorInfo:
        """Get Gemini CLI vendor information.

        Returns:
            VendorInfo object with Gemini CLI metadata.
        """
        return VendorInfo(
            name="Gemini CLI",
            vendor_id="gemini",
            config_dir=self._config_dir,
            executable="gemini",
            homepage="https://ai.google.dev/gemini-api",
            supports_agents=False,
            supports_mcp=True,
        )

    def is_installed(self) -> bool:
        """Check if Gemini CLI is installed.

        Returns:
            True if the gemini CLI executable is available, False otherwise.
        """
        return is_command_available("gemini")

    def is_configured(self) -> bool:
        """Check if Gemini CLI has been configured.

        A Gemini installation is considered configured if:
        1. The settings.json file exists
        2. An API key is present in the configuration

        Returns:
            True if properly configured with API key, False otherwise.
        """
        if not self._settings_file.exists():
            return False

        try:
            settings = self._load_settings()
        except (json.JSONDecodeError, OSError):
            return False
        else:
            # Check for API key in settings
            return "api_key" in settings or "apiKey" in settings

    def get_status(self) -> VendorStatus:
        """Get the current status of Gemini CLI.

        Returns:
            VendorStatus indicating the current state.
        """
        if not self.is_installed():
            return VendorStatus.NOT_INSTALLED

        if not self._config_dir.exists():
            return VendorStatus.INSTALLED

        if not self.is_configured():
            return VendorStatus.INSTALLED

        # Check if configuration is valid
        try:
            self._load_settings()
        except (json.JSONDecodeError, OSError):
            return VendorStatus.ERROR
        else:
            return VendorStatus.CONFIGURED

    def initialize(self) -> None:
        """Initialize Gemini CLI configuration directory structure.

        Creates the necessary directory structure if it doesn't exist:
        - ~/.gemini/
        - ~/.gemini/mcp_servers/
        - ~/.gemini/settings.json (with placeholder for API key)
        - ~/.gemini/GEMINI.md

        Raises:
            RuntimeError: If initialization fails.
        """
        try:
            # Create main config directory
            self._config_dir.mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            (self._config_dir / "mcp_servers").mkdir(exist_ok=True)

            # Create default settings.json if it doesn't exist
            if not self._settings_file.exists():
                default_settings = {
                    "api_key": "",
                    "model": "gemini-pro",
                    "temperature": 0.7,
                    "mcp_servers_enabled": True,
                }
                self._save_settings(default_settings)

            # Create default GEMINI.md if it doesn't exist
            if not self._gemini_md.exists():
                default_md = """# Gemini CLI Configuration

## Overview
This directory contains configuration for the Gemini CLI assistant.

## Configuration Files
- `settings.json` - Main configuration including API key
- `mcp_servers/` - MCP server configurations

## Setup
1. Add your Google API key to `settings.json`
2. Configure MCP servers as needed
"""
                self._gemini_md.write_text(default_md)

        except OSError as e:
            error_msg = f"Failed to initialize Gemini CLI configuration: {e}"
            raise RuntimeError(error_msg) from e

    def get_config(self, key: str) -> object:
        """Get a configuration value from settings.json.

        Args:
            key: Configuration key to retrieve (supports dot notation).

        Returns:
            The configuration value, or None if not found.

        Raises:
            KeyError: If the configuration key doesn't exist.
        """
        settings = self._load_settings()

        # Support dot notation for nested keys
        keys = key.split(".")
        value: Any = settings

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                msg = f"Configuration key not found: {key}"
                raise KeyError(msg)

        return value

    def set_config(self, key: str, value: object) -> None:
        """Set a configuration value in settings.json.

        Args:
            key: Configuration key to set (supports dot notation).
            value: Value to set for the configuration key.

        Raises:
            ValueError: If the value is invalid for the given key.
            RuntimeError: If unable to save the configuration.
        """
        settings = self._load_settings()

        # Support dot notation for nested keys
        keys = key.split(".")
        current: Any = settings

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set the value
        current[keys[-1]] = value

        self._save_settings(settings)

    def backup(self, backup_dir: Path) -> Path:
        """Create a backup of Gemini CLI configuration.

        Args:
            backup_dir: Directory where the backup should be stored.

        Returns:
            Path to the created backup tar.gz file.

        Raises:
            RuntimeError: If backup creation fails.
        """
        try:
            backup_dir.mkdir(parents=True, exist_ok=True)

            # Create timestamped backup filename
            timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
            backup_file = backup_dir / f"gemini_backup_{timestamp}.tar.gz"

            # Create tar.gz archive
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(self._config_dir, arcname="gemini")

        except (OSError, tarfile.TarError) as e:
            error_msg = f"Failed to create backup: {e}"
            raise RuntimeError(error_msg) from e
        else:
            return backup_file

    def restore(self, backup_path: Path) -> None:
        """Restore configuration from a backup.

        Args:
            backup_path: Path to the backup tar.gz file.

        Raises:
            FileNotFoundError: If the backup path doesn't exist.
            RuntimeError: If restore operation fails.
        """
        if not backup_path.exists():
            msg = f"Backup file not found: {backup_path}"
            raise FileNotFoundError(msg)

        try:
            # Extract to temporary directory first
            temp_dir = backup_path.parent / "temp_restore"
            temp_dir.mkdir(exist_ok=True)

            with tarfile.open(backup_path, "r:gz") as tar:
                # Use secure unpacking to prevent path traversal attacks
                unpack_tar_securely(tar, temp_dir)

            # Move extracted content to config directory
            extracted_dir = temp_dir / "gemini"
            if extracted_dir.exists():
                # Remove existing config if it exists
                if self._config_dir.exists():
                    shutil.rmtree(self._config_dir)

                # Move extracted directory
                shutil.move(str(extracted_dir), str(self._config_dir))

            # Clean up temp directory
            shutil.rmtree(temp_dir)

        except (OSError, tarfile.TarError, shutil.Error) as e:
            error_msg = f"Failed to restore backup: {e}"
            raise RuntimeError(error_msg) from e

    def sync_from_git(self, repo_url: str, branch: str = "main") -> None:
        """Sync configuration from a Git repository.

        Args:
            repo_url: URL of the Git repository.
            branch: Git branch to sync from. Defaults to "main".

        Raises:
            RuntimeError: If sync operation fails.
        """
        try:
            # Clone to temporary directory
            temp_dir = self._config_dir.parent / "temp_git_clone"

            # Remove temp dir if it exists
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

            # Clone repository using secure git_clone utility
            if not git_clone(repo_url, temp_dir, branch):
                msg = f"Failed to clone repository: {repo_url}"
                raise RuntimeError(msg)

            # Copy relevant directories to config
            sync_items = ["mcp_servers", "settings.json", "GEMINI.md"]
            for item_name in sync_items:
                src_item = temp_dir / item_name
                if src_item.exists():
                    dest_item = self._config_dir / item_name
                    if src_item.is_dir():
                        if dest_item.exists():
                            shutil.rmtree(dest_item)
                        shutil.copytree(src_item, dest_item)
                    else:
                        shutil.copy(src_item, dest_item)

            # Clean up temp directory
            shutil.rmtree(temp_dir)

        except (OSError, shutil.Error) as e:
            error_msg = f"Failed to sync from git: {e}"
            raise RuntimeError(error_msg) from e

    def health_check(self) -> dict[str, object]:
        """Perform a health check on Gemini CLI configuration.

        Returns:
            Dictionary containing health check results.
        """
        checks: dict[str, bool] = {}
        errors: list[str] = []

        # Check if CLI is installed
        checks["cli_installed"] = self.is_installed()
        if not checks["cli_installed"]:
            errors.append("Gemini CLI not installed")

        # Check if config directory exists
        checks["config_dir_exists"] = self._config_dir.exists()
        if not checks["config_dir_exists"]:
            errors.append("Configuration directory not found")

        # Check if configured
        checks["configured"] = self.is_configured()
        if not checks["configured"]:
            errors.append("No API key configured")

        # Check settings.json is valid JSON
        if self._settings_file.exists():
            try:
                self._load_settings()
                checks["valid_settings"] = True
            except json.JSONDecodeError:
                checks["valid_settings"] = False
                errors.append("settings.json is not valid JSON")
        else:
            checks["valid_settings"] = False
            errors.append("settings.json not found")

        # Check for MCP servers directory
        mcp_dir = self._config_dir / "mcp_servers"
        checks["has_mcp_dir"] = mcp_dir.exists()
        if not checks["has_mcp_dir"]:
            errors.append("mcp_servers/ directory not found")

        # Check for GEMINI.md
        checks["has_gemini_md"] = self._gemini_md.exists()

        healthy = all(checks.values()) and len(errors) == 0

        return {
            "healthy": healthy,
            "checks": checks,
            "errors": errors,
        }

    def audit_config(self) -> dict[str, object]:
        """Audit Gemini CLI configuration for security and best practices.

        Returns:
            Dictionary containing audit results.
        """
        issues: list[str] = []
        warnings: list[str] = []
        recommendations: list[str] = []
        score = 100

        # Check directory permissions
        if self._config_dir.exists():
            mode = self._config_dir.stat().st_mode
            if mode & 0o077:  # Check if group or others have permissions
                issues.append("Config directory has overly permissive permissions")
                score -= 20

        # Check settings.json exists and is valid
        if not self._settings_file.exists():
            issues.append("No settings.json found")
            score -= 30
        else:
            try:
                settings = self._load_settings()

                # Check for API key
                if not ("api_key" in settings or "apiKey" in settings):
                    warnings.append("No API key configured")
                    score -= 15
                elif settings.get("api_key") == "" or settings.get("apiKey") == "":
                    warnings.append("API key is empty")
                    score -= 15

                # Warn if API key appears to be in plaintext
                api_key = settings.get("api_key") or settings.get("apiKey")
                if api_key and isinstance(api_key, str) and len(api_key) > _MIN_API_KEY_LENGTH:
                    msg = "API key stored in plaintext (consider using environment variables)"
                    warnings.append(msg)
                    score -= 10

            except json.JSONDecodeError:
                issues.append("settings.json is malformed")
                score -= 25

        # Check for MCP servers directory
        if self._config_dir.exists():
            mcp_dir = self._config_dir / "mcp_servers"
            if not mcp_dir.exists():
                recommendations.append("Create mcp_servers/ directory for MCP server configs")

        # Check for GEMINI.md
        if self._config_dir.exists() and not self._gemini_md.exists():
            recommendations.append("Create GEMINI.md for documentation")

        return {
            "score": max(0, score),
            "issues": issues,
            "warnings": warnings,
            "recommendations": recommendations,
        }

    def get_usage_stats(self) -> dict[str, object]:
        """Get usage statistics for Gemini CLI.

        Returns:
            Dictionary containing usage statistics.
        """
        stats: dict[str, object] = {
            "cli_available": self.is_installed(),
            "configured": self.is_configured(),
        }

        # Count MCP servers
        if self._config_dir.exists():
            mcp_dir = self._config_dir / "mcp_servers"
            if mcp_dir.exists():
                mcp_configs = list(self._list_json_files(mcp_dir))
                stats["mcp_server_count"] = len(mcp_configs)

        return stats

    def _load_settings(self) -> dict[str, Any]:
        """Load settings from settings.json.

        Returns:
            Dictionary containing settings.

        Raises:
            FileNotFoundError: If settings.json doesn't exist.
            json.JSONDecodeError: If settings.json is malformed.
        """
        if not self._settings_file.exists():
            msg = f"Settings file not found: {self._settings_file}"
            raise FileNotFoundError(msg)

        with self._settings_file.open() as f:
            return cast("dict[str, Any]", json.load(f))

    def _save_settings(self, settings: dict[str, Any]) -> None:
        """Save settings to settings.json.

        Args:
            settings: Dictionary of settings to save.

        Raises:
            RuntimeError: If unable to save settings.
        """
        try:
            with self._settings_file.open("w") as f:
                json.dump(settings, f, indent=2)
        except OSError as e:
            error_msg = f"Failed to save settings: {e}"
            raise RuntimeError(error_msg) from e

    def _list_json_files(self, directory: Path) -> Iterator[Path]:
        """List all JSON files in a directory.

        Args:
            directory: Directory to search for JSON files.

        Yields:
            Path objects for each JSON file found.
        """
        if directory.exists() and directory.is_dir():
            yield from directory.glob("*.json")
