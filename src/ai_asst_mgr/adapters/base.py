"""Base classes and interfaces for vendor adapters.

This module defines the abstract base class that all vendor-specific adapters
must implement, along with common data structures and enumerations used across
all vendors.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Any


class VendorStatus(Enum):
    """Status of a vendor installation and configuration.

    Attributes:
        NOT_INSTALLED: Vendor is not installed on the system.
        INSTALLED: Vendor is installed but not configured.
        CONFIGURED: Vendor is installed and configured but not running.
        RUNNING: Vendor is actively running.
        ERROR: Vendor is in an error state.
    """

    NOT_INSTALLED = "not_installed"
    INSTALLED = "installed"
    CONFIGURED = "configured"
    RUNNING = "running"
    ERROR = "error"


@dataclass(frozen=True)
class VendorInfo:
    """Information about a specific AI assistant vendor.

    Attributes:
        name: Human-readable name of the vendor (e.g., "Claude Code").
        vendor_id: Unique identifier for the vendor (e.g., "claude").
        config_dir: Path to the vendor's configuration directory.
        executable: Name of the vendor's executable command.
        homepage: URL to the vendor's homepage or documentation.
        supports_agents: Whether the vendor natively supports agents.
        supports_mcp: Whether the vendor supports MCP servers.
    """

    name: str
    vendor_id: str
    config_dir: Path
    executable: str
    homepage: str
    supports_agents: bool = False
    supports_mcp: bool = False


class VendorAdapter(ABC):
    """Abstract base class for all vendor-specific adapters.

    This class defines the interface that all vendor adapters must implement
    to provide a consistent API for managing different AI assistant platforms.
    Each vendor (Claude, Gemini, OpenAI) will have its own concrete implementation.

    The adapter pattern allows the system to work with multiple vendors while
    keeping vendor-specific logic encapsulated.
    """

    @property
    @abstractmethod
    def info(self) -> VendorInfo:
        """Get vendor information.

        Returns:
            VendorInfo object containing vendor metadata.
        """

    @abstractmethod
    def is_installed(self) -> bool:
        """Check if the vendor's CLI or application is installed.

        Returns:
            True if the vendor is installed, False otherwise.
        """

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if the vendor has been configured.

        A vendor is considered configured if its configuration directory exists
        and contains the necessary configuration files.

        Returns:
            True if the vendor is configured, False otherwise.
        """

    @abstractmethod
    def get_status(self) -> VendorStatus:
        """Get the current status of the vendor.

        Returns:
            Current VendorStatus of the installation.
        """

    @abstractmethod
    def initialize(self) -> None:
        """Initialize the vendor's configuration.

        Creates the necessary directory structure and default configuration files
        if they don't already exist.

        Raises:
            RuntimeError: If initialization fails.
        """

    @abstractmethod
    def get_config(self, key: str) -> Any:
        """Get a configuration value.

        Args:
            key: Configuration key to retrieve.

        Returns:
            The configuration value, or None if not found.

        Raises:
            KeyError: If the configuration key doesn't exist.
        """

    @abstractmethod
    def set_config(self, key: str, value: Any) -> None:
        """Set a configuration value.

        Args:
            key: Configuration key to set.
            value: Value to set for the configuration key.

        Raises:
            ValueError: If the value is invalid for the given key.
            RuntimeError: If unable to save the configuration.
        """

    @abstractmethod
    def backup(self, backup_dir: Path) -> Path:
        """Create a backup of the vendor's configuration.

        Args:
            backup_dir: Directory where the backup should be stored.

        Returns:
            Path to the created backup file or directory.

        Raises:
            RuntimeError: If backup creation fails.
        """

    @abstractmethod
    def restore(self, backup_path: Path) -> None:
        """Restore configuration from a backup.

        Args:
            backup_path: Path to the backup file or directory.

        Raises:
            FileNotFoundError: If the backup path doesn't exist.
            RuntimeError: If restore operation fails.
        """

    @abstractmethod
    def sync_from_git(self, repo_url: str, branch: str = "main") -> None:
        """Sync configuration from a Git repository.

        Args:
            repo_url: URL of the Git repository.
            branch: Git branch to sync from. Defaults to "main".

        Raises:
            RuntimeError: If sync operation fails.
        """

    @abstractmethod
    def health_check(self) -> dict[str, Any]:
        """Perform a health check on the vendor configuration.

        Returns:
            Dictionary containing health check results with at least:
            - healthy: bool indicating overall health
            - checks: dict of individual check results
            - errors: list of error messages if unhealthy
        """

    @abstractmethod
    def audit_config(self) -> dict[str, Any]:
        """Audit the vendor's configuration for security and best practices.

        Returns:
            Dictionary containing audit results with at least:
            - score: int (0-100) representing configuration quality
            - issues: list of identified issues
            - warnings: list of warnings
            - recommendations: list of recommended improvements
        """

    @abstractmethod
    def get_usage_stats(self) -> dict[str, Any]:
        """Get usage statistics for this vendor.

        Returns:
            Dictionary containing usage statistics such as:
            - session_count: number of sessions
            - total_duration: total time spent
            - tool_calls: number of tool invocations
            - last_used: timestamp of last usage
        """
