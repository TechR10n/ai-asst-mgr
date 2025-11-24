"""Vendor registry for managing AI assistant adapters.

This module provides the VendorRegistry class for centralized management
of AI assistant vendor adapters.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from ai_asst_mgr.adapters import ClaudeAdapter, GeminiAdapter, OpenAIAdapter

if TYPE_CHECKING:
    from ai_asst_mgr.adapters.base import VendorAdapter


class VendorRegistry:
    """Central registry for managing vendor adapters.

    The VendorRegistry provides a centralized way to access and manage
    AI assistant vendor adapters. It maintains a registry of all available
    vendors and provides methods to query vendors by various criteria.

    Example:
        >>> registry = VendorRegistry()
        >>> claude = registry.get_vendor("claude")
        >>> installed = registry.get_installed_vendors()
    """

    def __init__(self) -> None:
        """Initialize the vendor registry with default vendors."""
        self._vendors: dict[str, VendorAdapter] = {}

        # Register default vendors
        self.register_vendor("claude", ClaudeAdapter())
        self.register_vendor("gemini", GeminiAdapter())
        self.register_vendor("openai", OpenAIAdapter())

    def register_vendor(self, name: object, adapter: VendorAdapter) -> None:
        """Register a new vendor adapter.

        Args:
            name: Unique identifier for the vendor (must be non-empty string).
            adapter: VendorAdapter instance to register.

        Raises:
            ValueError: If the vendor name is invalid or already registered.
            TypeError: If name is not a string.
        """
        if not isinstance(name, str):
            msg = "Vendor name must be a string"
            raise TypeError(msg)

        if not name:
            msg = "Vendor name cannot be empty"
            raise ValueError(msg)

        if name in self._vendors:
            msg = f"Vendor '{name}' is already registered"
            raise ValueError(msg)

        self._vendors[name] = adapter

    def get_vendor(self, name: str) -> VendorAdapter:
        """Get a vendor adapter by name.

        Args:
            name: Name of the vendor to retrieve.

        Returns:
            The VendorAdapter instance for the specified vendor.

        Raises:
            KeyError: If the vendor is not registered.
        """
        if name not in self._vendors:
            msg = f"Unknown vendor: {name}"
            raise KeyError(msg)

        return self._vendors[name]

    def get_all_vendors(self) -> dict[str, VendorAdapter]:
        """Get all registered vendors.

        Returns:
            Dictionary mapping vendor names to their adapter instances.
            Returns a copy to prevent external modification.
        """
        return dict(self._vendors)

    def get_installed_vendors(self) -> dict[str, VendorAdapter]:
        """Get all vendors that are installed on the system.

        A vendor is considered installed if its CLI tool is available.

        Returns:
            Dictionary mapping vendor names to installed adapter instances.
        """
        return {name: adapter for name, adapter in self._vendors.items() if adapter.is_installed()}

    def get_configured_vendors(self) -> dict[str, VendorAdapter]:
        """Get all vendors that are configured with credentials.

        A vendor is considered configured if it has valid configuration
        including API keys or authentication tokens.

        Returns:
            Dictionary mapping vendor names to configured adapter instances.
        """
        return {name: adapter for name, adapter in self._vendors.items() if adapter.is_configured()}


__all__ = ["VendorRegistry"]
