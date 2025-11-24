"""Unit tests for VendorAdapter base class."""

from pathlib import Path

import pytest

from ai_asst_mgr.adapters.base import VendorAdapter, VendorInfo, VendorStatus


def test_vendor_status_enum() -> None:
    """Test VendorStatus enum values."""
    assert VendorStatus.NOT_INSTALLED.value == "not_installed"
    assert VendorStatus.INSTALLED.value == "installed"
    assert VendorStatus.CONFIGURED.value == "configured"
    assert VendorStatus.RUNNING.value == "running"
    assert VendorStatus.ERROR.value == "error"


def test_vendor_status_enum_members() -> None:
    """Test VendorStatus enum has all expected members."""
    expected_members = {
        "NOT_INSTALLED",
        "INSTALLED",
        "CONFIGURED",
        "RUNNING",
        "ERROR",
    }
    actual_members = {member.name for member in VendorStatus}
    assert actual_members == expected_members


def test_vendor_info_creation() -> None:
    """Test VendorInfo dataclass creation."""
    info = VendorInfo(
        name="Test Vendor",
        vendor_id="test",
        config_dir=Path("/test/config"),
        executable="test-cli",
        homepage="https://test.com",
        supports_agents=True,
        supports_mcp=False,
    )

    assert info.name == "Test Vendor"
    assert info.vendor_id == "test"
    assert info.config_dir == Path("/test/config")
    assert info.executable == "test-cli"
    assert info.homepage == "https://test.com"
    assert info.supports_agents is True
    assert info.supports_mcp is False


def test_vendor_info_defaults() -> None:
    """Test VendorInfo default values."""
    info = VendorInfo(
        name="Test",
        vendor_id="test",
        config_dir=Path("/test"),
        executable="test",
        homepage="https://test.com",
    )

    assert info.supports_agents is False
    assert info.supports_mcp is False


def test_vendor_info_immutable() -> None:
    """Test that VendorInfo is frozen (immutable)."""
    info = VendorInfo(
        name="Test",
        vendor_id="test",
        config_dir=Path("/test"),
        executable="test",
        homepage="https://test.com",
    )

    with pytest.raises(Exception):  # FrozenInstanceError in Python 3.10+
        info.name = "Changed"  # type: ignore[misc]


def test_vendor_adapter_is_abstract() -> None:
    """Test that VendorAdapter cannot be instantiated directly."""
    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        VendorAdapter()  # type: ignore[abstract]


def test_vendor_adapter_requires_all_methods() -> None:
    """Test that VendorAdapter subclass must implement all abstract methods."""

    class IncompleteAdapter(VendorAdapter):
        """Incomplete adapter missing some abstract methods."""

        @property
        def info(self) -> VendorInfo:
            """Return vendor info."""
            return VendorInfo(
                name="Test",
                vendor_id="test",
                config_dir=Path("/test"),
                executable="test",
                homepage="https://test.com",
            )

    with pytest.raises(TypeError, match="Can't instantiate abstract class"):
        IncompleteAdapter()  # type: ignore[abstract]


def test_vendor_adapter_concrete_implementation() -> None:
    """Test that a complete VendorAdapter implementation can be instantiated."""

    class CompleteAdapter(VendorAdapter):
        """Complete adapter implementing all abstract methods."""

        @property
        def info(self) -> VendorInfo:
            """Return vendor info."""
            return VendorInfo(
                name="Test",
                vendor_id="test",
                config_dir=Path("/test"),
                executable="test",
                homepage="https://test.com",
            )

        def is_installed(self) -> bool:
            """Check if installed."""
            return True

        def is_configured(self) -> bool:
            """Check if configured."""
            return True

        def get_status(self) -> VendorStatus:
            """Get status."""
            return VendorStatus.CONFIGURED

        def initialize(self) -> None:
            """Initialize."""

        def get_config(self, key: str) -> object:
            """Get config."""
            return None

        def set_config(self, key: str, value: object) -> None:
            """Set config."""

        def backup(self, backup_dir: Path) -> Path:
            """Backup."""
            return backup_dir / "backup"

        def restore(self, backup_path: Path) -> None:
            """Restore."""

        def sync_from_git(self, repo_url: str, branch: str = "main") -> None:
            """Sync from git."""

        def health_check(self) -> dict[str, object]:
            """Health check."""
            return {"healthy": True}

        def audit_config(self) -> dict[str, object]:
            """Audit config."""
            return {"score": 100}

        def get_usage_stats(self) -> dict[str, object]:
            """Get usage stats."""
            return {"session_count": 0}

    adapter = CompleteAdapter()
    assert adapter.info.vendor_id == "test"
    assert adapter.is_installed() is True
    assert adapter.get_status() == VendorStatus.CONFIGURED
