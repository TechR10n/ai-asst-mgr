"""Unit tests for BackupManager."""

import json
import tarfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from ai_asst_mgr.adapters.base import VendorInfo
from ai_asst_mgr.operations.backup import (
    BackupManager,
    BackupMetadata,
    BackupResult,
    BackupSummary,
)


@pytest.fixture
def temp_backup_dir(tmp_path: Path) -> Path:
    """Create a temporary backup directory."""
    backup_dir = tmp_path / "backups"
    backup_dir.mkdir()
    return backup_dir


@pytest.fixture
def backup_manager(temp_backup_dir: Path) -> BackupManager:
    """Create a BackupManager with temporary directory."""
    return BackupManager(temp_backup_dir, retention_count=3)


@pytest.fixture
def mock_adapter(tmp_path: Path) -> Mock:
    """Create a mock VendorAdapter."""
    config_dir = tmp_path / ".claude"
    config_dir.mkdir()
    (config_dir / "settings.json").write_text('{"test": "value"}')
    (config_dir / "agents").mkdir()
    (config_dir / "agents" / "test_agent.md").write_text("# Test Agent")

    info = Mock(spec=VendorInfo)
    info.vendor_id = "claude"
    info.name = "Claude Code"
    info.config_dir = config_dir

    adapter = Mock()
    adapter.info = info
    adapter.is_installed.return_value = True

    def mock_backup(dest_dir: Path) -> Path:
        """Create a mock backup archive."""
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        backup_path = dest_dir / f"claude_backup_{timestamp}.tar.gz"
        with tarfile.open(backup_path, "w:gz") as tar:
            tar.add(config_dir, arcname="claude")
        return backup_path

    adapter.backup.side_effect = mock_backup
    return adapter


class TestBackupMetadata:
    """Tests for BackupMetadata dataclass."""

    def test_metadata_fields(self, tmp_path: Path) -> None:
        """Test BackupMetadata contains all required fields."""
        backup_path = tmp_path / "test.tar.gz"
        backup_path.touch()

        metadata = BackupMetadata(
            vendor_id="claude",
            timestamp=datetime.now(tz=UTC),
            backup_path=backup_path,
            size_bytes=1024,
            checksum="abc123",
            file_count=10,
            config_dir="/test/path",
        )

        assert metadata.vendor_id == "claude"
        assert metadata.size_bytes == 1024
        assert metadata.checksum == "abc123"
        assert metadata.file_count == 10


class TestBackupResult:
    """Tests for BackupResult dataclass."""

    def test_successful_result(self, tmp_path: Path) -> None:
        """Test successful backup result."""
        backup_path = tmp_path / "test.tar.gz"
        backup_path.touch()

        metadata = BackupMetadata(
            vendor_id="claude",
            timestamp=datetime.now(tz=UTC),
            backup_path=backup_path,
            size_bytes=1024,
            checksum="abc123",
            file_count=10,
            config_dir="/test/path",
        )

        result = BackupResult(success=True, metadata=metadata, duration_seconds=1.5)

        assert result.success is True
        assert result.metadata is not None
        assert result.error is None
        assert result.duration_seconds == 1.5

    def test_failed_result(self) -> None:
        """Test failed backup result."""
        result = BackupResult(success=False, error="Test error", duration_seconds=0.5)

        assert result.success is False
        assert result.metadata is None
        assert result.error == "Test error"


class TestBackupSummary:
    """Tests for BackupSummary dataclass."""

    def test_summary_fields(self) -> None:
        """Test BackupSummary contains all required fields."""
        summary = BackupSummary(
            total_vendors=3,
            successful=2,
            failed=1,
            total_size_bytes=2048,
            duration_seconds=3.0,
        )

        assert summary.total_vendors == 3
        assert summary.successful == 2
        assert summary.failed == 1
        assert summary.total_size_bytes == 2048


class TestBackupManagerInit:
    """Tests for BackupManager initialization."""

    def test_init_with_defaults(self, temp_backup_dir: Path) -> None:
        """Test initialization with default retention count."""
        manager = BackupManager(temp_backup_dir)
        assert manager.backup_dir == temp_backup_dir
        assert manager.retention_count == 5

    def test_init_with_custom_retention(self, temp_backup_dir: Path) -> None:
        """Test initialization with custom retention count."""
        manager = BackupManager(temp_backup_dir, retention_count=10)
        assert manager.retention_count == 10

    def test_init_expands_home(self) -> None:
        """Test that home directory is expanded."""
        manager = BackupManager(Path("~/backups"))
        assert "~" not in str(manager.backup_dir)


class TestBackupVendor:
    """Tests for backup_vendor method."""

    def test_backup_vendor_success(self, backup_manager: BackupManager, mock_adapter: Mock) -> None:
        """Test successful vendor backup."""
        result = backup_manager.backup_vendor(mock_adapter)

        assert result.success is True
        assert result.metadata is not None
        assert result.metadata.vendor_id == "claude"
        assert result.metadata.backup_path.exists()
        assert result.error is None

    def test_backup_vendor_not_installed(
        self, backup_manager: BackupManager, mock_adapter: Mock
    ) -> None:
        """Test backup fails when vendor not installed."""
        mock_adapter.is_installed.return_value = False

        result = backup_manager.backup_vendor(mock_adapter)

        assert result.success is False
        assert "not installed" in result.error.lower()

    def test_backup_vendor_with_progress_callback(
        self, backup_manager: BackupManager, mock_adapter: Mock
    ) -> None:
        """Test backup with progress callback."""
        progress_messages: list[str] = []

        def callback(msg: str) -> None:
            progress_messages.append(msg)

        result = backup_manager.backup_vendor(mock_adapter, progress_callback=callback)

        assert result.success is True
        assert len(progress_messages) > 0
        assert any("Starting" in msg for msg in progress_messages)

    def test_backup_vendor_creates_vendor_dir(
        self, backup_manager: BackupManager, mock_adapter: Mock
    ) -> None:
        """Test backup creates vendor-specific directory."""
        result = backup_manager.backup_vendor(mock_adapter)

        assert result.success is True
        vendor_dir = backup_manager.backup_dir / "claude"
        assert vendor_dir.exists()

    def test_backup_vendor_error_handling(
        self, backup_manager: BackupManager, mock_adapter: Mock
    ) -> None:
        """Test backup handles errors gracefully."""
        mock_adapter.backup.side_effect = OSError("Test error")

        result = backup_manager.backup_vendor(mock_adapter)

        assert result.success is False
        assert "Test error" in result.error


class TestBackupAllVendors:
    """Tests for backup_all_vendors method."""

    def test_backup_all_vendors_success(
        self, backup_manager: BackupManager, mock_adapter: Mock
    ) -> None:
        """Test backup all vendors."""
        adapters = {"claude": mock_adapter}

        summary = backup_manager.backup_all_vendors(adapters)

        assert summary.total_vendors == 1
        assert summary.successful == 1
        assert summary.failed == 0

    def test_backup_all_vendors_with_failure(
        self, backup_manager: BackupManager, mock_adapter: Mock
    ) -> None:
        """Test backup handles mixed success/failure."""
        mock_adapter2 = Mock()
        mock_adapter2.info = Mock()
        mock_adapter2.info.vendor_id = "gemini"
        mock_adapter2.info.name = "Gemini"
        mock_adapter2.is_installed.return_value = False

        adapters = {"claude": mock_adapter, "gemini": mock_adapter2}

        summary = backup_manager.backup_all_vendors(adapters)

        assert summary.total_vendors == 2
        assert summary.successful == 1
        assert summary.failed == 1


class TestListBackups:
    """Tests for list_backups method."""

    def test_list_backups_empty(self, backup_manager: BackupManager) -> None:
        """Test list_backups returns empty list when no backups."""
        backups = backup_manager.list_backups()
        assert backups == []

    def test_list_backups_after_backup(
        self, backup_manager: BackupManager, mock_adapter: Mock
    ) -> None:
        """Test list_backups returns backups after creation."""
        backup_manager.backup_vendor(mock_adapter)

        backups = backup_manager.list_backups()

        assert len(backups) == 1
        assert backups[0].vendor_id == "claude"

    def test_list_backups_filter_by_vendor(
        self, backup_manager: BackupManager, mock_adapter: Mock
    ) -> None:
        """Test list_backups filters by vendor."""
        backup_manager.backup_vendor(mock_adapter)

        # Test filter matches
        claude_backups = backup_manager.list_backups("claude")
        assert len(claude_backups) == 1

        # Test filter doesn't match
        gemini_backups = backup_manager.list_backups("gemini")
        assert len(gemini_backups) == 0

    def test_list_backups_sorted_by_timestamp(
        self, backup_manager: BackupManager, mock_adapter: Mock
    ) -> None:
        """Test list_backups returns newest first."""
        backup_manager.backup_vendor(mock_adapter)
        backup_manager.backup_vendor(mock_adapter)

        backups = backup_manager.list_backups()

        assert len(backups) == 2
        assert backups[0].timestamp >= backups[1].timestamp


class TestGetLatestBackup:
    """Tests for get_latest_backup method."""

    def test_get_latest_backup_none(self, backup_manager: BackupManager) -> None:
        """Test get_latest_backup returns None when no backups."""
        result = backup_manager.get_latest_backup("claude")
        assert result is None

    def test_get_latest_backup_success(
        self, backup_manager: BackupManager, mock_adapter: Mock
    ) -> None:
        """Test get_latest_backup returns most recent."""
        backup_manager.backup_vendor(mock_adapter)
        backup_manager.backup_vendor(mock_adapter)

        latest = backup_manager.get_latest_backup("claude")

        assert latest is not None
        assert latest.vendor_id == "claude"


class TestVerifyBackup:
    """Tests for verify_backup method."""

    def test_verify_backup_valid(self, backup_manager: BackupManager, mock_adapter: Mock) -> None:
        """Test verify_backup returns True for valid backup."""
        result = backup_manager.backup_vendor(mock_adapter)
        assert result.metadata is not None

        is_valid, message = backup_manager.verify_backup(result.metadata.backup_path)

        assert is_valid is True
        assert "valid" in message.lower()

    def test_verify_backup_not_found(self, backup_manager: BackupManager, tmp_path: Path) -> None:
        """Test verify_backup returns False for missing file."""
        fake_path = tmp_path / "nonexistent.tar.gz"

        is_valid, message = backup_manager.verify_backup(fake_path)

        assert is_valid is False
        assert "not found" in message.lower()

    def test_verify_backup_invalid_format(
        self, backup_manager: BackupManager, tmp_path: Path
    ) -> None:
        """Test verify_backup returns False for non-tar file."""
        fake_path = tmp_path / "not_a_tar.tar.gz"
        fake_path.write_text("not a tar file")

        is_valid, message = backup_manager.verify_backup(fake_path)

        assert is_valid is False
        assert "invalid" in message.lower()


class TestDeleteBackup:
    """Tests for delete_backup method."""

    def test_delete_backup_success(self, backup_manager: BackupManager, mock_adapter: Mock) -> None:
        """Test delete_backup removes backup file."""
        result = backup_manager.backup_vendor(mock_adapter)
        assert result.metadata is not None
        backup_path = result.metadata.backup_path

        assert backup_path.exists()
        deleted = backup_manager.delete_backup(backup_path)

        assert deleted is True
        assert not backup_path.exists()

    def test_delete_backup_not_found(self, backup_manager: BackupManager, tmp_path: Path) -> None:
        """Test delete_backup returns False for missing file."""
        fake_path = tmp_path / "nonexistent.tar.gz"

        deleted = backup_manager.delete_backup(fake_path)

        assert deleted is False


class TestRetentionPolicy:
    """Tests for retention policy."""

    def test_retention_policy_applied(self, tmp_path: Path) -> None:
        """Test old backups are deleted when retention exceeded."""
        backup_dir = tmp_path / "backups"
        backup_dir.mkdir()
        manager = BackupManager(backup_dir, retention_count=2)

        # Create mock adapter with unique backup filenames using counter
        config_dir = tmp_path / ".claude"
        config_dir.mkdir()
        (config_dir / "settings.json").write_text('{"test": "value"}')

        info = Mock(spec=VendorInfo)
        info.vendor_id = "claude"
        info.name = "Claude Code"
        info.config_dir = config_dir

        mock_adapter = Mock()
        mock_adapter.info = info
        mock_adapter.is_installed.return_value = True

        # Use counter to ensure unique filenames
        backup_counter = [0]

        def mock_backup(dest_dir: Path) -> Path:
            """Create a mock backup archive with unique name."""
            backup_counter[0] += 1
            backup_path = dest_dir / f"claude_backup_{backup_counter[0]:03d}.tar.gz"
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(config_dir, arcname="claude")
            return backup_path

        mock_adapter.backup.side_effect = mock_backup

        # Create 3 backups
        manager.backup_vendor(mock_adapter)
        manager.backup_vendor(mock_adapter)
        manager.backup_vendor(mock_adapter)

        backups = manager.list_backups("claude")

        # Should only keep 2 due to retention policy
        assert len(backups) == 2


class TestBackupEdgeCases:
    """Additional edge case tests for BackupManager."""

    def test_list_backups_with_corrupt_manifest(
        self, backup_manager: BackupManager, tmp_path: Path
    ) -> None:
        """Test list_backups handles corrupt manifest gracefully."""
        vendor_dir = backup_manager.backup_dir / "claude"
        vendor_dir.mkdir(parents=True)

        # Create corrupt manifest
        manifest_path = vendor_dir / "backup_manifest.json"
        manifest_path.write_text("not valid json{")

        backups = backup_manager.list_backups("claude")
        assert backups == []

    def test_list_backups_with_missing_backup_file(
        self, backup_manager: BackupManager, tmp_path: Path
    ) -> None:
        """Test list_backups handles missing backup files gracefully."""
        vendor_dir = backup_manager.backup_dir / "claude"
        vendor_dir.mkdir(parents=True)

        # Create manifest pointing to non-existent backup
        manifest_path = vendor_dir / "backup_manifest.json"
        manifest_content = {
            "vendor_id": "claude",
            "backups": [
                {
                    "vendor_id": "claude",
                    "timestamp": "2025-01-01T00:00:00+00:00",
                    "backup_path": str(vendor_dir / "nonexistent.tar.gz"),
                    "size_bytes": 1024,
                    "checksum": "abc123",
                    "file_count": 10,
                    "config_dir": "/test/path",
                }
            ],
        }
        manifest_path.write_text(json.dumps(manifest_content))

        backups = backup_manager.list_backups("claude")
        # Backup file doesn't exist so not included
        assert backups == []

    def test_verify_backup_empty_archive(
        self, backup_manager: BackupManager, tmp_path: Path
    ) -> None:
        """Test verify_backup returns False for empty archive."""
        # Create empty tar.gz
        empty_archive = tmp_path / "empty.tar.gz"
        with tarfile.open(empty_archive, "w:gz"):
            pass  # Create empty archive

        is_valid, message = backup_manager.verify_backup(empty_archive)

        assert is_valid is False
        assert "empty" in message.lower()

    def test_verify_backup_checksum_mismatch(
        self, backup_manager: BackupManager, mock_adapter: Mock, tmp_path: Path
    ) -> None:
        """Test verify_backup detects checksum mismatch."""
        # Create a backup
        result = backup_manager.backup_vendor(mock_adapter)
        assert result.success is True
        assert result.metadata is not None

        backup_path = result.metadata.backup_path

        # Corrupt the backup by modifying it
        original_content = backup_path.read_bytes()
        # Append some bytes to corrupt it
        backup_path.write_bytes(original_content + b"corrupted")

        is_valid, message = backup_manager.verify_backup(backup_path)

        # Should detect checksum mismatch
        assert is_valid is False
        assert "mismatch" in message.lower() or "corrupted" in message.lower()

    def test_backup_vendor_calculates_duration(
        self, backup_manager: BackupManager, mock_adapter: Mock
    ) -> None:
        """Test backup_vendor calculates duration correctly."""
        result = backup_manager.backup_vendor(mock_adapter)

        assert result.success is True
        assert result.duration_seconds >= 0

    def test_backup_all_vendors_with_progress(
        self, backup_manager: BackupManager, mock_adapter: Mock
    ) -> None:
        """Test backup_all_vendors with progress callback."""
        progress_messages: list[str] = []

        def callback(msg: str) -> None:
            progress_messages.append(msg)

        adapters = {"claude": mock_adapter}
        summary = backup_manager.backup_all_vendors(adapters, progress_callback=callback)

        assert summary.successful == 1
        assert len(progress_messages) > 0

    def test_list_backups_nonexistent_vendor_dir(self, backup_manager: BackupManager) -> None:
        """Test list_backups handles nonexistent vendor directory gracefully."""
        # Try to list backups for vendor that doesn't exist
        backups = backup_manager.list_backups("nonexistent_vendor")
        assert backups == []

    def test_verify_backup_tar_error(self, backup_manager: BackupManager, tmp_path: Path) -> None:
        """Test verify_backup handles TarError during archive read."""
        corrupt_archive = tmp_path / "corrupt.tar.gz"
        # Create a file that starts like a tar.gz but is corrupted
        corrupt_archive.write_bytes(
            b"\x1f\x8b\x08\x00\x00\x00\x00\x00" + b"corrupted tar data" * 100
        )

        is_valid, message = backup_manager.verify_backup(corrupt_archive)

        assert is_valid is False
        assert "error" in message.lower() or "invalid" in message.lower()

    def test_count_files_tar_error(self, backup_manager: BackupManager, tmp_path: Path) -> None:
        """Test _count_files_in_archive handles TarError gracefully."""
        corrupt_archive = tmp_path / "corrupt.tar.gz"
        corrupt_archive.write_bytes(b"not a tar file at all")

        count = backup_manager._count_files_in_archive(corrupt_archive)
        assert count == 0

    def test_load_manifest_non_dict(self, backup_manager: BackupManager, tmp_path: Path) -> None:
        """Test _load_manifest handles non-dict JSON gracefully."""
        manifest_path = tmp_path / "manifest.json"
        manifest_path.write_text("[]")  # JSON array instead of dict

        result = backup_manager._load_manifest(manifest_path)
        assert result == {"backups": []}

    def test_get_stored_checksum_no_match(
        self, backup_manager: BackupManager, mock_adapter: Mock, tmp_path: Path
    ) -> None:
        """Test _get_stored_checksum returns None when backup path doesn't match."""
        # Create a backup
        result = backup_manager.backup_vendor(mock_adapter)
        assert result.success is True
        assert result.metadata is not None

        # Try to get checksum for a different path
        different_path = tmp_path / "different_backup.tar.gz"
        checksum = backup_manager._get_stored_checksum(different_path)
        assert checksum is None

    def test_get_stored_checksum_corrupt_manifest(
        self, backup_manager: BackupManager, tmp_path: Path
    ) -> None:
        """Test _get_stored_checksum handles corrupt manifest gracefully."""
        vendor_dir = backup_manager.backup_dir / "claude"
        vendor_dir.mkdir(parents=True)

        manifest_path = vendor_dir / "backup_manifest.json"
        manifest_path.write_text("{invalid json")

        backup_path = vendor_dir / "backup.tar.gz"
        checksum = backup_manager._get_stored_checksum(backup_path)
        assert checksum is None

    def test_remove_from_manifest_nonexistent(
        self, backup_manager: BackupManager, tmp_path: Path
    ) -> None:
        """Test _remove_from_manifest handles nonexistent manifest gracefully."""
        backup_path = tmp_path / "nonexistent.tar.gz"
        # Should not raise exception
        backup_manager._remove_from_manifest("claude", backup_path)

    def test_remove_from_manifest_corrupt(
        self, backup_manager: BackupManager, tmp_path: Path
    ) -> None:
        """Test _remove_from_manifest handles corrupt manifest gracefully."""
        vendor_dir = backup_manager.backup_dir / "claude"
        vendor_dir.mkdir(parents=True)

        manifest_path = vendor_dir / "backup_manifest.json"
        manifest_path.write_text("{invalid json")

        backup_path = vendor_dir / "backup.tar.gz"
        # Should not raise exception
        backup_manager._remove_from_manifest("claude", backup_path)
