"""OpenAI Codex vendor adapter implementation.

This module provides the OpenAIAdapter class for managing OpenAI Codex
configurations, including settings, profiles, MCP servers, and backup operations.
"""

from __future__ import annotations

import shutil
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

import toml

from ai_asst_mgr.adapters.base import VendorAdapter, VendorInfo, VendorStatus
from ai_asst_mgr.utils import git_clone, is_command_available, unpack_tar_securely

if TYPE_CHECKING:
    from collections.abc import Iterator

# Constants for audit scoring
_MIN_API_KEY_LENGTH = 10


class OpenAIAdapter(VendorAdapter):
    """Adapter for OpenAI Codex AI assistant.

    OpenAI Codex stores its configuration in ~/.codex/ with the following structure:
    - config.toml - Main configuration file with profiles and API key
    - mcp_servers/ - MCP server configurations
    - AGENTS.md - Documentation and agent hierarchy
    """

    def __init__(self) -> None:
        """Initialize the OpenAI Codex adapter."""
        self._config_dir = Path.home() / ".codex"
        self._config_file = self._config_dir / "config.toml"
        self._agents_md = self._config_dir / "AGENTS.md"

    @property
    def info(self) -> VendorInfo:
        """Get OpenAI Codex vendor information.

        Returns:
            VendorInfo object with OpenAI Codex metadata.
        """
        return VendorInfo(
            name="OpenAI Codex",
            vendor_id="openai",
            config_dir=self._config_dir,
            executable="codex",
            homepage="https://openai.com/codex",
            supports_agents=True,
            supports_mcp=True,
        )

    def is_installed(self) -> bool:
        """Check if OpenAI Codex CLI is installed.

        Returns:
            True if the codex CLI executable is available, False otherwise.
        """
        return is_command_available("codex")

    def is_configured(self) -> bool:
        """Check if OpenAI Codex has been configured.

        A Codex installation is considered configured if:
        1. The config.toml file exists
        2. An API key is present in the configuration

        Returns:
            True if properly configured with API key, False otherwise.
        """
        if not self._config_file.exists():
            return False

        try:
            config = self._load_config()
        except (toml.TomlDecodeError, OSError):
            return False
        else:
            # Check for API key in config (can be at root or in default profile)
            has_root_key = "api_key" in config or "apiKey" in config
            has_profile_key = False
            if "profiles" in config and isinstance(config["profiles"], dict):
                for profile in config["profiles"].values():
                    if isinstance(profile, dict) and ("api_key" in profile or "apiKey" in profile):
                        has_profile_key = True
                        break
            return has_root_key or has_profile_key

    def get_status(self) -> VendorStatus:
        """Get the current status of OpenAI Codex.

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
            self._load_config()
        except (toml.TomlDecodeError, OSError):
            return VendorStatus.ERROR
        else:
            return VendorStatus.CONFIGURED

    def initialize(self) -> None:
        """Initialize OpenAI Codex configuration directory structure.

        Creates the necessary directory structure if it doesn't exist:
        - ~/.codex/
        - ~/.codex/mcp_servers/
        - ~/.codex/config.toml (with default profile)
        - ~/.codex/AGENTS.md

        Raises:
            RuntimeError: If initialization fails.
        """
        try:
            # Create main config directory
            self._config_dir.mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            (self._config_dir / "mcp_servers").mkdir(exist_ok=True)

            # Create default config.toml if it doesn't exist
            if not self._config_file.exists():
                default_config = {
                    "api_key": "",
                    "model": "gpt-4",
                    "temperature": 0.7,
                    "profiles": {
                        "default": {
                            "model": "gpt-4",
                            "temperature": 0.7,
                        },
                    },
                    "mcp_servers_enabled": True,
                }
                self._save_config(default_config)

            # Create default AGENTS.md if it doesn't exist
            if not self._agents_md.exists():
                default_md = """# OpenAI Codex Agent Configuration

## Overview
This directory contains configuration for the OpenAI Codex assistant.

## Configuration Files
- `config.toml` - Main configuration including API key and profiles
- `mcp_servers/` - MCP server configurations

## Profiles
Profiles allow you to define different configurations for different use cases.
Edit `config.toml` to add or modify profiles.

## Setup
1. Add your OpenAI API key to `config.toml`
2. Configure profiles as needed
3. Configure MCP servers as needed
"""
                self._agents_md.write_text(default_md)

        except OSError as e:
            error_msg = f"Failed to initialize OpenAI Codex configuration: {e}"
            raise RuntimeError(error_msg) from e

    def get_config(self, key: str) -> object:
        """Get a configuration value from config.toml.

        Args:
            key: Configuration key to retrieve (supports dot notation).

        Returns:
            The configuration value, or None if not found.

        Raises:
            KeyError: If the configuration key doesn't exist.
        """
        config = self._load_config()

        # Support dot notation for nested keys
        keys = key.split(".")
        value: Any = config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                msg = f"Configuration key not found: {key}"
                raise KeyError(msg)

        return value

    def set_config(self, key: str, value: object) -> None:
        """Set a configuration value in config.toml.

        Args:
            key: Configuration key to set (supports dot notation).
            value: Value to set for the configuration key.

        Raises:
            ValueError: If the value is invalid for the given key.
            RuntimeError: If unable to save the configuration.
        """
        config = self._load_config()

        # Support dot notation for nested keys
        keys = key.split(".")
        current: Any = config

        # Navigate to the parent of the target key
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        # Set the value
        current[keys[-1]] = value

        self._save_config(config)

    def backup(self, backup_dir: Path) -> Path:
        """Create a backup of OpenAI Codex configuration.

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
            backup_file = backup_dir / f"openai_backup_{timestamp}.tar.gz"

            # Create tar.gz archive
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(self._config_dir, arcname="codex")

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
            extracted_dir = temp_dir / "codex"
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

            # Copy relevant items to config
            sync_items = ["mcp_servers", "config.toml", "AGENTS.md"]
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
        """Perform a health check on OpenAI Codex configuration.

        Returns:
            Dictionary containing health check results.
        """
        checks: dict[str, bool] = {}
        errors: list[str] = []

        # Check if CLI is installed
        checks["cli_installed"] = self.is_installed()
        if not checks["cli_installed"]:
            errors.append("Codex CLI not installed")

        # Check if config directory exists
        checks["config_dir_exists"] = self._config_dir.exists()
        if not checks["config_dir_exists"]:
            errors.append("Configuration directory not found")

        # Check if configured
        checks["configured"] = self.is_configured()
        if not checks["configured"]:
            errors.append("No API key configured")

        # Check config.toml is valid TOML
        if self._config_file.exists():
            try:
                self._load_config()
                checks["valid_config"] = True
            except toml.TomlDecodeError:
                checks["valid_config"] = False
                errors.append("config.toml is not valid TOML")
        else:
            checks["valid_config"] = False
            errors.append("config.toml not found")

        # Check for MCP servers directory
        mcp_dir = self._config_dir / "mcp_servers"
        checks["has_mcp_dir"] = mcp_dir.exists()
        if not checks["has_mcp_dir"]:
            errors.append("mcp_servers/ directory not found")

        # Check for AGENTS.md
        checks["has_agents_md"] = self._agents_md.exists()

        healthy = all(checks.values()) and len(errors) == 0

        return {
            "healthy": healthy,
            "checks": checks,
            "errors": errors,
        }

    def audit_config(self) -> dict[str, object]:
        """Audit OpenAI Codex configuration for security and best practices.

        Returns:
            Dictionary containing audit results.
        """
        issues: list[str] = []
        warnings: list[str] = []
        recommendations: list[str] = []
        score = 100

        # Check directory permissions
        score = self._audit_directory_permissions(issues, score)

        # Check config.toml exists and is valid
        score = self._audit_config_file(issues, warnings, score)

        # Check for MCP servers directory and AGENTS.md
        self._audit_optional_components(recommendations)

        return {
            "score": max(0, score),
            "issues": issues,
            "warnings": warnings,
            "recommendations": recommendations,
        }

    def _audit_directory_permissions(self, issues: list[str], score: int) -> int:
        """Audit config directory permissions.

        Args:
            issues: List to append issues to.
            score: Current audit score.

        Returns:
            Updated audit score.
        """
        if self._config_dir.exists():
            mode = self._config_dir.stat().st_mode
            if mode & 0o077:  # Check if group or others have permissions
                issues.append("Config directory has overly permissive permissions")
                score -= 20
        return score

    def _audit_config_file(self, issues: list[str], warnings: list[str], score: int) -> int:
        """Audit config.toml file existence and API key configuration.

        Args:
            issues: List to append issues to.
            warnings: List to append warnings to.
            score: Current audit score.

        Returns:
            Updated audit score.
        """
        if not self._config_file.exists():
            issues.append("No config.toml found")
            return score - 30

        try:
            config = self._load_config()
            return self._audit_api_keys(config, warnings, score)
        except toml.TomlDecodeError:
            issues.append("config.toml is malformed")
            return score - 25

    def _audit_api_keys(self, config: dict[str, Any], warnings: list[str], score: int) -> int:
        """Audit API key configuration in config.toml.

        Args:
            config: Loaded configuration dictionary.
            warnings: List to append warnings to.
            score: Current audit score.

        Returns:
            Updated audit score.
        """
        has_root_key = "api_key" in config or "apiKey" in config
        has_profile_key, score = self._audit_profile_keys(config, warnings, score)

        if not has_root_key and not has_profile_key:
            warnings.append("No API key configured")
            return score - 15

        if has_root_key:
            return self._audit_root_key(config, warnings, score)

        return score

    def _audit_profile_keys(
        self, config: dict[str, Any], warnings: list[str], score: int
    ) -> tuple[bool, int]:
        """Audit API keys in profiles.

        Args:
            config: Loaded configuration dictionary.
            warnings: List to append warnings to.
            score: Current audit score.

        Returns:
            Tuple of (has_profile_key, updated_score).
        """
        has_profile_key = False

        if "profiles" in config and isinstance(config["profiles"], dict):
            for profile_name, profile in config["profiles"].items():
                if isinstance(profile, dict) and ("api_key" in profile or "apiKey" in profile):
                    has_profile_key = True
                    api_key = profile.get("api_key") or profile.get("apiKey")
                    is_long_key = (
                        api_key and isinstance(api_key, str) and len(api_key) > _MIN_API_KEY_LENGTH
                    )
                    if is_long_key:
                        msg = f"Profile '{profile_name}' has plaintext API key"
                        warnings.append(msg)
                        score -= 5

        return has_profile_key, score

    def _audit_root_key(self, config: dict[str, Any], warnings: list[str], score: int) -> int:
        """Audit root-level API key.

        Args:
            config: Loaded configuration dictionary.
            warnings: List to append warnings to.
            score: Current audit score.

        Returns:
            Updated audit score.
        """
        api_key = config.get("api_key") or config.get("apiKey")
        if not api_key or api_key == "":
            warnings.append("Root API key is empty")
            return score - 15

        if isinstance(api_key, str) and len(api_key) > _MIN_API_KEY_LENGTH:
            msg = "API key stored in plaintext (consider using environment variables)"
            warnings.append(msg)
            return score - 10

        return score

    def _audit_optional_components(self, recommendations: list[str]) -> None:
        """Audit optional components like MCP servers and AGENTS.md.

        Args:
            recommendations: List to append recommendations to.
        """
        if not self._config_dir.exists():
            return

        mcp_dir = self._config_dir / "mcp_servers"
        if not mcp_dir.exists():
            recommendations.append("Create mcp_servers/ directory for MCP server configs")

        if not self._agents_md.exists():
            recommendations.append("Create AGENTS.md for agent documentation")

    def get_usage_stats(self) -> dict[str, object]:
        """Get usage statistics for OpenAI Codex.

        Returns:
            Dictionary containing usage statistics.
        """
        stats: dict[str, object] = {
            "cli_available": self.is_installed(),
            "configured": self.is_configured(),
        }

        # Count profiles
        if self._config_file.exists():
            try:
                config = self._load_config()
                if "profiles" in config and isinstance(config["profiles"], dict):
                    stats["profile_count"] = len(config["profiles"])
            except (toml.TomlDecodeError, OSError):
                pass

        # Count MCP servers
        if self._config_dir.exists():
            mcp_dir = self._config_dir / "mcp_servers"
            if mcp_dir.exists():
                mcp_configs = list(self._list_toml_files(mcp_dir))
                stats["mcp_server_count"] = len(mcp_configs)

        return stats

    def _load_config(self) -> dict[str, Any]:
        """Load configuration from config.toml.

        Returns:
            Dictionary containing configuration.

        Raises:
            FileNotFoundError: If config.toml doesn't exist.
            toml.TomlDecodeError: If config.toml is malformed.
        """
        if not self._config_file.exists():
            msg = f"Config file not found: {self._config_file}"
            raise FileNotFoundError(msg)

        with self._config_file.open() as f:
            return toml.load(f)

    def _save_config(self, config: dict[str, Any]) -> None:
        """Save configuration to config.toml.

        Args:
            config: Dictionary of configuration to save.

        Raises:
            RuntimeError: If unable to save configuration.
        """
        try:
            with self._config_file.open("w") as f:
                toml.dump(config, f)
        except OSError as e:
            error_msg = f"Failed to save config: {e}"
            raise RuntimeError(error_msg) from e

    def _list_toml_files(self, directory: Path) -> Iterator[Path]:
        """List all TOML files in a directory.

        Args:
            directory: Directory to search for TOML files.

        Yields:
            Path objects for each TOML file found.
        """
        if directory.exists() and directory.is_dir():
            yield from directory.glob("*.toml")
