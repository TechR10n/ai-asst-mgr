"""Unit tests for VendorRegistry."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from ai_asst_mgr.adapters import ClaudeAdapter, GeminiAdapter, OpenAIAdapter
from ai_asst_mgr.adapters.base import VendorAdapter
from ai_asst_mgr.vendors import VendorRegistry


class TestVendorRegistryInitialization:
    """Tests for VendorRegistry initialization."""

    def test_initializes_with_default_vendors(self) -> None:
        """Test registry initializes with three default vendors."""
        registry = VendorRegistry()
        vendors = registry.get_all_vendors()

        assert len(vendors) == 3
        assert "claude" in vendors
        assert "gemini" in vendors
        assert "openai" in vendors

    def test_default_vendors_are_correct_types(self) -> None:
        """Test default vendors are instances of correct adapter classes."""
        registry = VendorRegistry()

        assert isinstance(registry.get_vendor("claude"), ClaudeAdapter)
        assert isinstance(registry.get_vendor("gemini"), GeminiAdapter)
        assert isinstance(registry.get_vendor("openai"), OpenAIAdapter)


class TestVendorRegistryRegisterVendor:
    """Tests for register_vendor method."""

    def test_register_new_vendor_success(self) -> None:
        """Test successfully registering a new vendor."""
        registry = VendorRegistry()
        mock_adapter = MagicMock(spec=VendorAdapter)

        registry.register_vendor("custom", mock_adapter)

        assert "custom" in registry.get_all_vendors()
        assert registry.get_vendor("custom") is mock_adapter

    def test_register_vendor_with_empty_name_raises_value_error(self) -> None:
        """Test registering vendor with empty name raises ValueError."""
        registry = VendorRegistry()
        mock_adapter = MagicMock(spec=VendorAdapter)

        with pytest.raises(ValueError, match="Vendor name cannot be empty"):
            registry.register_vendor("", mock_adapter)

    def test_register_vendor_with_non_string_name_raises_type_error(self) -> None:
        """Test registering vendor with non-string name raises TypeError."""
        registry = VendorRegistry()
        mock_adapter = MagicMock(spec=VendorAdapter)

        with pytest.raises(TypeError, match="Vendor name must be a string"):
            registry.register_vendor(123, mock_adapter)  # type: ignore[arg-type]

    def test_register_duplicate_vendor_raises_value_error(self) -> None:
        """Test registering duplicate vendor name raises ValueError."""
        registry = VendorRegistry()
        mock_adapter = MagicMock(spec=VendorAdapter)

        with pytest.raises(ValueError, match="Vendor 'claude' is already registered"):
            registry.register_vendor("claude", mock_adapter)

    def test_register_vendor_after_initialization(self) -> None:
        """Test can register additional vendors after initialization."""
        registry = VendorRegistry()
        mock_adapter1 = MagicMock(spec=VendorAdapter)
        mock_adapter2 = MagicMock(spec=VendorAdapter)

        registry.register_vendor("custom1", mock_adapter1)
        registry.register_vendor("custom2", mock_adapter2)

        vendors = registry.get_all_vendors()
        assert len(vendors) == 5  # 3 default + 2 custom
        assert "custom1" in vendors
        assert "custom2" in vendors


class TestVendorRegistryGetVendor:
    """Tests for get_vendor method."""

    def test_get_existing_vendor_returns_correct_instance(self) -> None:
        """Test getting existing vendor returns correct adapter instance."""
        registry = VendorRegistry()

        claude = registry.get_vendor("claude")
        gemini = registry.get_vendor("gemini")
        openai = registry.get_vendor("openai")

        assert isinstance(claude, ClaudeAdapter)
        assert isinstance(gemini, GeminiAdapter)
        assert isinstance(openai, OpenAIAdapter)

    def test_get_unknown_vendor_raises_key_error(self) -> None:
        """Test getting unknown vendor raises KeyError."""
        registry = VendorRegistry()

        with pytest.raises(KeyError, match="Unknown vendor: nonexistent"):
            registry.get_vendor("nonexistent")

    def test_get_vendor_error_message_includes_vendor_name(self) -> None:
        """Test error message includes the vendor name that was requested."""
        registry = VendorRegistry()

        with pytest.raises(KeyError, match="foobar"):
            registry.get_vendor("foobar")


class TestVendorRegistryGetAllVendors:
    """Tests for get_all_vendors method."""

    def test_returns_all_default_vendors(self) -> None:
        """Test returns dictionary with all three default vendors."""
        registry = VendorRegistry()
        vendors = registry.get_all_vendors()

        assert len(vendors) == 3
        assert "claude" in vendors
        assert "gemini" in vendors
        assert "openai" in vendors

    def test_returns_copy_not_reference(self) -> None:
        """Test returns a copy to prevent external modification."""
        registry = VendorRegistry()
        vendors1 = registry.get_all_vendors()
        vendors2 = registry.get_all_vendors()

        # Modify the returned dict
        mock_adapter = MagicMock(spec=VendorAdapter)
        vendors1["custom"] = mock_adapter

        # Should not affect registry or subsequent calls
        assert "custom" not in registry.get_all_vendors()
        assert "custom" not in vendors2

    def test_returns_dict_with_string_keys(self) -> None:
        """Test returns dictionary with string keys."""
        registry = VendorRegistry()
        vendors = registry.get_all_vendors()

        for key in vendors:
            assert isinstance(key, str)

    def test_returns_dict_with_vendor_adapter_values(self) -> None:
        """Test returns dictionary with VendorAdapter values."""
        registry = VendorRegistry()
        vendors = registry.get_all_vendors()

        for adapter in vendors.values():
            assert isinstance(adapter, VendorAdapter)


class TestVendorRegistryGetInstalledVendors:
    """Tests for get_installed_vendors method."""

    def test_returns_only_installed_vendors(self) -> None:
        """Test returns only vendors that report as installed."""
        registry = VendorRegistry()

        # Mock is_installed to return specific values
        with (
            patch.object(registry.get_vendor("claude"), "is_installed", return_value=True),
            patch.object(registry.get_vendor("gemini"), "is_installed", return_value=False),
            patch.object(registry.get_vendor("openai"), "is_installed", return_value=True),
        ):
            installed = registry.get_installed_vendors()

        assert len(installed) == 2
        assert "claude" in installed
        assert "openai" in installed
        assert "gemini" not in installed

    def test_returns_empty_dict_if_none_installed(self) -> None:
        """Test returns empty dict when no vendors are installed."""
        registry = VendorRegistry()

        # Mock all vendors as not installed
        with (
            patch.object(registry.get_vendor("claude"), "is_installed", return_value=False),
            patch.object(registry.get_vendor("gemini"), "is_installed", return_value=False),
            patch.object(registry.get_vendor("openai"), "is_installed", return_value=False),
        ):
            installed = registry.get_installed_vendors()

        assert len(installed) == 0
        assert installed == {}

    def test_returns_all_if_all_installed(self) -> None:
        """Test returns all vendors when all are installed."""
        registry = VendorRegistry()

        # Mock all vendors as installed
        with (
            patch.object(registry.get_vendor("claude"), "is_installed", return_value=True),
            patch.object(registry.get_vendor("gemini"), "is_installed", return_value=True),
            patch.object(registry.get_vendor("openai"), "is_installed", return_value=True),
        ):
            installed = registry.get_installed_vendors()

        assert len(installed) == 3
        assert "claude" in installed
        assert "gemini" in installed
        assert "openai" in installed


class TestVendorRegistryGetConfiguredVendors:
    """Tests for get_configured_vendors method."""

    def test_returns_only_configured_vendors(self) -> None:
        """Test returns only vendors that report as configured."""
        registry = VendorRegistry()

        # Mock is_configured to return specific values
        with (
            patch.object(registry.get_vendor("claude"), "is_configured", return_value=True),
            patch.object(registry.get_vendor("gemini"), "is_configured", return_value=True),
            patch.object(registry.get_vendor("openai"), "is_configured", return_value=False),
        ):
            configured = registry.get_configured_vendors()

        assert len(configured) == 2
        assert "claude" in configured
        assert "gemini" in configured
        assert "openai" not in configured

    def test_returns_empty_dict_if_none_configured(self) -> None:
        """Test returns empty dict when no vendors are configured."""
        registry = VendorRegistry()

        # Mock all vendors as not configured
        with (
            patch.object(registry.get_vendor("claude"), "is_configured", return_value=False),
            patch.object(registry.get_vendor("gemini"), "is_configured", return_value=False),
            patch.object(registry.get_vendor("openai"), "is_configured", return_value=False),
        ):
            configured = registry.get_configured_vendors()

        assert len(configured) == 0
        assert configured == {}

    def test_returns_all_if_all_configured(self) -> None:
        """Test returns all vendors when all are configured."""
        registry = VendorRegistry()

        # Mock all vendors as configured
        with (
            patch.object(registry.get_vendor("claude"), "is_configured", return_value=True),
            patch.object(registry.get_vendor("gemini"), "is_configured", return_value=True),
            patch.object(registry.get_vendor("openai"), "is_configured", return_value=True),
        ):
            configured = registry.get_configured_vendors()

        assert len(configured) == 3
        assert "claude" in configured
        assert "gemini" in configured
        assert "openai" in configured


class TestVendorRegistryIntegration:
    """Integration tests for VendorRegistry."""

    def test_can_register_and_retrieve_custom_vendor(self) -> None:
        """Test complete workflow of registering and retrieving custom vendor."""
        registry = VendorRegistry()
        mock_adapter = MagicMock(spec=VendorAdapter)
        mock_adapter.is_installed.return_value = True
        mock_adapter.is_configured.return_value = True

        # Register custom vendor
        registry.register_vendor("custom", mock_adapter)

        # Retrieve it
        retrieved = registry.get_vendor("custom")
        assert retrieved is mock_adapter

        # Appears in all vendors
        all_vendors = registry.get_all_vendors()
        assert "custom" in all_vendors

        # Appears in installed vendors
        installed = registry.get_installed_vendors()
        assert "custom" in installed

        # Appears in configured vendors
        configured = registry.get_configured_vendors()
        assert "custom" in configured

    def test_registry_isolation(self) -> None:
        """Test multiple registry instances are independent."""
        registry1 = VendorRegistry()
        registry2 = VendorRegistry()

        mock_adapter = MagicMock(spec=VendorAdapter)
        registry1.register_vendor("custom", mock_adapter)

        # Custom vendor should not appear in registry2
        all_vendors_1 = registry1.get_all_vendors()
        all_vendors_2 = registry2.get_all_vendors()

        assert "custom" in all_vendors_1
        assert "custom" not in all_vendors_2
        assert len(all_vendors_1) == 4
        assert len(all_vendors_2) == 3
