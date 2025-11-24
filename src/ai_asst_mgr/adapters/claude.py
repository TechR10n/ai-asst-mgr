"""Claude Code vendor adapter implementation.

This module provides the ClaudeAdapter class for managing Claude Code
configurations, including settings, agents, skills, and backup operations.
"""

from __future__ import annotations

import json
import shutil
import subprocess  # nosec B404 - needed for git operations
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any, cast

from ai_asst_mgr.adapters.base import VendorAdapter, VendorInfo, VendorStatus

if TYPE_CHECKING:
    from collections.abc import Iterator


class ClaudeAdapter(VendorAdapter):
    """Adapter for Claude Code AI assistant.

    Claude Code stores its configuration in ~/.claude/ with the following structure:
    - settings.json - Main configuration file
    - agents/ - Custom agent definitions (markdown files)
    - skills/ - Custom skill definitions (markdown files)
    - commands/ - Slash command definitions
    - hooks/ - Git hooks and automation
    """

    def __init__(self) -> None:
        """Initialize the Claude Code adapter."""
        self._config_dir = Path.home() / ".claude"
        self._settings_file = self._config_dir / "settings.json"

    @property
    def info(self) -> VendorInfo:
        """Get Claude Code vendor information.

        Returns:
            VendorInfo object with Claude Code metadata.
        """
        return VendorInfo(
            name="Claude Code",
            vendor_id="claude",
            config_dir=self._config_dir,
            executable="claude",
            homepage="https://claude.ai/claude-code",
            supports_agents=True,
            supports_mcp=True,
        )

    def is_installed(self) -> bool:
        """Check if Claude Code is installed.

        Returns:
            True if the ~/.claude/ directory exists, False otherwise.
        """
        return self._config_dir.exists() and self._config_dir.is_dir()

    def is_configured(self) -> bool:
        """Check if Claude Code has been configured.

        Returns:
            True if settings.json exists, False otherwise.
        """
        return self._settings_file.exists() and self._settings_file.is_file()

    def get_status(self) -> VendorStatus:
        """Get the current status of Claude Code.

        Returns:
            VendorStatus indicating the current state.
        """
        if not self.is_installed():
            return VendorStatus.NOT_INSTALLED

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
        """Initialize Claude Code configuration directory structure.

        Creates the necessary directory structure if it doesn't exist:
        - ~/.claude/
        - ~/.claude/agents/
        - ~/.claude/skills/
        - ~/.claude/commands/
        - ~/.claude/hooks/

        Raises:
            RuntimeError: If initialization fails.
        """
        try:
            # Create main config directory
            self._config_dir.mkdir(parents=True, exist_ok=True)

            # Create subdirectories
            subdirs = ["agents", "skills", "commands", "hooks", "templates"]
            for subdir in subdirs:
                (self._config_dir / subdir).mkdir(exist_ok=True)

            # Create default settings.json if it doesn't exist
            if not self._settings_file.exists():
                default_settings = {
                    "version": "1.0.0",
                    "theme": "dark",
                    "autoSave": True,
                }
                self._save_settings(default_settings)

        except OSError as e:
            error_msg = f"Failed to initialize Claude Code configuration: {e}"
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
        """Create a backup of Claude Code configuration.

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
            backup_file = backup_dir / f"claude_backup_{timestamp}.tar.gz"

            # Create tar.gz archive
            with tarfile.open(backup_file, "w:gz") as tar:
                tar.add(self._config_dir, arcname="claude")

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
                # Validate tar members to prevent path traversal attacks
                safe_members = [
                    member
                    for member in tar.getmembers()
                    if not (member.name.startswith("/") or ".." in member.name)
                ]
                tar.extractall(temp_dir, members=safe_members)  # nosec B202 - members validated

            # Move extracted content to config directory
            extracted_dir = temp_dir / "claude"
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

            # Clone repository
            subprocess.run(  # nosec B603 B607 - git command is intentional
                ["git", "clone", "--branch", branch, "--depth", "1", repo_url, str(temp_dir)],
                check=True,
                capture_output=True,
                text=True,
            )

            # Copy relevant directories to config
            sync_dirs = ["agents", "skills", "commands", "hooks", "templates"]
            for dirname in sync_dirs:
                src_dir = temp_dir / dirname
                if src_dir.exists():
                    dest_dir = self._config_dir / dirname
                    if dest_dir.exists():
                        shutil.rmtree(dest_dir)
                    shutil.copytree(src_dir, dest_dir)

            # Copy settings.json if it exists
            src_settings = temp_dir / "settings.json"
            if src_settings.exists():
                shutil.copy(src_settings, self._settings_file)

            # Clean up temp directory
            shutil.rmtree(temp_dir)

        except (subprocess.CalledProcessError, OSError, shutil.Error) as e:
            error_msg = f"Failed to sync from git: {e}"
            raise RuntimeError(error_msg) from e

    def health_check(self) -> dict[str, object]:
        """Perform a health check on Claude Code configuration.

        Returns:
            Dictionary containing health check results.
        """
        checks: dict[str, bool] = {}
        errors: list[str] = []

        # Check if installed
        checks["installed"] = self.is_installed()
        if not checks["installed"]:
            errors.append("Claude Code directory not found")

        # Check if configured
        checks["configured"] = self.is_configured()
        if not checks["configured"]:
            errors.append("settings.json not found")

        # Check settings.json is valid JSON
        if checks["configured"]:
            try:
                self._load_settings()
                checks["valid_settings"] = True
            except json.JSONDecodeError:
                checks["valid_settings"] = False
                errors.append("settings.json is not valid JSON")

        # Check for agents
        agents_dir = self._config_dir / "agents"
        checks["has_agents_dir"] = agents_dir.exists()
        if checks["has_agents_dir"]:
            agent_count = len(list(self._list_markdown_files(agents_dir)))
            checks["agent_count"] = agent_count > 0
        else:
            errors.append("agents/ directory not found")

        # Check for skills
        skills_dir = self._config_dir / "skills"
        checks["has_skills_dir"] = skills_dir.exists()
        if checks["has_skills_dir"]:
            skill_count = len(list(self._list_markdown_files(skills_dir)))
            checks["skill_count"] = skill_count > 0
        else:
            errors.append("skills/ directory not found")

        healthy = all(checks.values()) and len(errors) == 0

        return {
            "healthy": healthy,
            "checks": checks,
            "errors": errors,
        }

    def audit_config(self) -> dict[str, object]:
        """Audit Claude Code configuration for security and best practices.

        Returns:
            Dictionary containing audit results.
        """
        issues: list[str] = []
        warnings: list[str] = []
        recommendations: list[str] = []
        score = 100

        # Check directory permissions
        if self.is_installed():
            mode = self._config_dir.stat().st_mode
            if mode & 0o077:  # Check if group or others have permissions
                issues.append("Config directory has overly permissive permissions")
                score -= 20

        # Check settings.json exists and is valid
        if not self.is_configured():
            issues.append("No settings.json found")
            score -= 30
        else:
            try:
                settings = self._load_settings()

                # Check for sensitive data in settings
                sensitive_keys = ["api_key", "token", "password", "secret"]
                for key in sensitive_keys:
                    if key in str(settings).lower():
                        warnings.append(f"Possible sensitive data found: {key}")
                        score -= 10

            except json.JSONDecodeError:
                issues.append("settings.json is malformed")
                score -= 25

        # Check for agents and skills
        if self.is_installed():
            agents_dir = self._config_dir / "agents"
            if not agents_dir.exists():
                recommendations.append("Create agents/ directory for custom agents")

            skills_dir = self._config_dir / "skills"
            if not skills_dir.exists():
                recommendations.append("Create skills/ directory for custom skills")

        return {
            "score": max(0, score),
            "issues": issues,
            "warnings": warnings,
            "recommendations": recommendations,
        }

    def get_usage_stats(self) -> dict[str, object]:
        """Get usage statistics for Claude Code.

        Returns:
            Dictionary containing usage statistics.
        """
        stats: dict[str, object] = {
            "session_count": 0,
            "total_duration": 0,
            "tool_calls": 0,
            "last_used": None,
        }

        # Count agents and skills
        if self.is_installed():
            agents_dir = self._config_dir / "agents"
            if agents_dir.exists():
                stats["agent_count"] = len(list(self._list_markdown_files(agents_dir)))

            skills_dir = self._config_dir / "skills"
            if skills_dir.exists():
                stats["skill_count"] = len(list(self._list_markdown_files(skills_dir)))

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

    def _list_markdown_files(self, directory: Path) -> Iterator[Path]:
        """List all markdown files in a directory.

        Args:
            directory: Directory to search for markdown files.

        Yields:
            Path objects for each markdown file found.
        """
        if directory.exists() and directory.is_dir():
            yield from directory.glob("*.md")
