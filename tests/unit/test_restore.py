"""Unit tests for RestoreManager."""

import tarfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import Mock

import pytest

from ai_asst_mgr.adapters.base import VendorInfo
from ai_asst_mgr.operations.backup import BackupManager
from ai_asst_mgr.operations.restore import (
    RestoreManager,
    RestorePreview,
    RestoreResult,
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
def restore_manager(backup_manager: BackupManager) -> RestoreManager:
    """Create a RestoreManager with BackupManager."""
    return RestoreManager(backup_manager)


@pytest.fixture
def mock_adapter(tmp_path: Path) -> Mock:
    """Create a mock VendorAdapter with config directory."""
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

    return adapter


@pytest.fixture
def sample_backup(tmp_path: Path) -> Path:
    """Create a sample backup archive."""
    # Create source directory structure
    source_dir = tmp_path / "source" / "claude"
    source_dir.mkdir(parents=True)
    (source_dir / "settings.json").write_text('{"test": "value"}')
    (source_dir / "agents").mkdir()
    (source_dir / "agents" / "test_agent.md").write_text("# Test Agent")
    (source_dir / "skills").mkdir()
    (source_dir / "skills" / "test_skill.md").write_text("# Test Skill")

    # Create archive
    backup_path = tmp_path / "claude_backup.tar.gz"
    with tarfile.open(backup_path, "w:gz") as tar:
        tar.add(source_dir, arcname="claude")

    return backup_path


class TestRestoreResult:
    """Tests for RestoreResult dataclass."""

    def test_successful_result(self, tmp_path: Path) -> None:
        """Test successful restore result."""
        backup_path = tmp_path / "backup.tar.gz"
        backup_path.touch()

        result = RestoreResult(
            success=True,
            restored_files=10,
            pre_restore_backup=backup_path,
            duration_seconds=1.5,
        )

        assert result.success is True
        assert result.restored_files == 10
        assert result.pre_restore_backup == backup_path
        assert result.error is None

    def test_failed_result(self) -> None:
        """Test failed restore result."""
        result = RestoreResult(success=False, error="Restore failed", duration_seconds=0.5)

        assert result.success is False
        assert result.restored_files == 0
        assert result.error == "Restore failed"


class TestRestorePreview:
    """Tests for RestorePreview dataclass."""

    def test_preview_fields(self) -> None:
        """Test RestorePreview contains all required fields."""
        preview = RestorePreview(
            vendor_id="claude",
            backup_timestamp=datetime.now(tz=UTC),
            files_to_restore=["file1.txt", "file2.txt"],
            files_to_overwrite=["file1.txt"],
            directories_to_create=["new_dir"],
            estimated_size_bytes=1024,
        )

        assert preview.vendor_id == "claude"
        assert len(preview.files_to_restore) == 2
        assert len(preview.files_to_overwrite) == 1
        assert len(preview.directories_to_create) == 1
        assert preview.estimated_size_bytes == 1024


class TestRestoreManagerInit:
    """Tests for RestoreManager initialization."""

    def test_init_with_backup_manager(self, backup_manager: BackupManager) -> None:
        """Test initialization with backup manager."""
        manager = RestoreManager(backup_manager)
        assert manager._backup_manager == backup_manager


class TestPreviewRestore:
    """Tests for preview_restore method."""

    def test_preview_restore_success(
        self, restore_manager: RestoreManager, mock_adapter: Mock, sample_backup: Path
    ) -> None:
        """Test successful restore preview."""
        preview = restore_manager.preview_restore(sample_backup, mock_adapter)

        assert preview is not None
        assert preview.vendor_id == "claude"
        assert len(preview.files_to_restore) > 0
        assert preview.estimated_size_bytes > 0

    def test_preview_restore_nonexistent_backup(
        self, restore_manager: RestoreManager, mock_adapter: Mock, tmp_path: Path
    ) -> None:
        """Test preview returns None for nonexistent backup."""
        fake_path = tmp_path / "nonexistent.tar.gz"
        preview = restore_manager.preview_restore(fake_path, mock_adapter)

        assert preview is None

    def test_preview_restore_invalid_archive(
        self, restore_manager: RestoreManager, mock_adapter: Mock, tmp_path: Path
    ) -> None:
        """Test preview returns None for invalid archive."""
        invalid_path = tmp_path / "invalid.tar.gz"
        invalid_path.write_text("not a tar file")

        preview = restore_manager.preview_restore(invalid_path, mock_adapter)

        assert preview is None

    def test_preview_restore_shows_files_to_overwrite(
        self, restore_manager: RestoreManager, mock_adapter: Mock, sample_backup: Path
    ) -> None:
        """Test preview identifies files that will be overwritten."""
        preview = restore_manager.preview_restore(sample_backup, mock_adapter)

        assert preview is not None
        # settings.json exists in mock_adapter, so should be in files_to_overwrite
        assert any("settings.json" in f for f in preview.files_to_overwrite)


class TestRestoreVendor:
    """Tests for restore_vendor method."""

    def test_restore_vendor_success(
        self, restore_manager: RestoreManager, mock_adapter: Mock, sample_backup: Path
    ) -> None:
        """Test successful vendor restore."""
        mock_adapter.restore = Mock()

        result = restore_manager.restore_vendor(
            sample_backup, mock_adapter, create_pre_restore_backup=False
        )

        assert result.success is True
        assert result.restored_files > 0
        mock_adapter.restore.assert_called_once_with(sample_backup)

    def test_restore_vendor_invalid_backup(
        self, restore_manager: RestoreManager, mock_adapter: Mock, tmp_path: Path
    ) -> None:
        """Test restore fails with invalid backup."""
        fake_path = tmp_path / "nonexistent.tar.gz"

        result = restore_manager.restore_vendor(fake_path, mock_adapter)

        assert result.success is False
        assert "not found" in result.error.lower()

    def test_restore_vendor_creates_pre_restore_backup(
        self,
        restore_manager: RestoreManager,
        mock_adapter: Mock,
        sample_backup: Path,
        tmp_path: Path,
    ) -> None:
        """Test restore creates pre-restore backup when requested."""
        config_dir = mock_adapter.info.config_dir

        # Set up mock adapter backup method
        def mock_backup_method(dest_dir: Path) -> Path:
            backup_path = dest_dir / "pre_restore_backup.tar.gz"
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(config_dir, arcname="claude")
            return backup_path

        mock_adapter.backup = Mock(side_effect=mock_backup_method)
        mock_adapter.restore = Mock()

        result = restore_manager.restore_vendor(
            sample_backup, mock_adapter, create_pre_restore_backup=True
        )

        assert result.success is True
        assert result.pre_restore_backup is not None
        assert result.pre_restore_backup.exists()

    def test_restore_vendor_with_progress_callback(
        self, restore_manager: RestoreManager, mock_adapter: Mock, sample_backup: Path
    ) -> None:
        """Test restore with progress callback."""
        mock_adapter.restore = Mock()
        progress_messages: list[str] = []

        def callback(msg: str) -> None:
            progress_messages.append(msg)

        result = restore_manager.restore_vendor(
            sample_backup,
            mock_adapter,
            create_pre_restore_backup=False,
            progress_callback=callback,
        )

        assert result.success is True
        assert len(progress_messages) > 0
        assert any("Starting" in msg for msg in progress_messages)

    def test_restore_vendor_handles_restore_error(
        self, restore_manager: RestoreManager, mock_adapter: Mock, sample_backup: Path
    ) -> None:
        """Test restore handles adapter errors gracefully."""
        mock_adapter.restore = Mock(side_effect=OSError("Restore failed"))

        result = restore_manager.restore_vendor(
            sample_backup, mock_adapter, create_pre_restore_backup=False
        )

        assert result.success is False
        assert "Restore failed" in result.error


class TestRestoreSelective:
    """Tests for restore_selective method."""

    def test_restore_selective_success(
        self, restore_manager: RestoreManager, mock_adapter: Mock, sample_backup: Path
    ) -> None:
        """Test selective restore of specific directories."""
        result = restore_manager.restore_selective(
            sample_backup, mock_adapter, directories=["agents"]
        )

        assert result.success is True
        assert result.restored_files > 0

        # Verify agents directory was restored
        agents_dir = mock_adapter.info.config_dir / "agents"
        assert agents_dir.exists()

    def test_restore_selective_multiple_directories(
        self, restore_manager: RestoreManager, mock_adapter: Mock, sample_backup: Path
    ) -> None:
        """Test selective restore of multiple directories."""
        result = restore_manager.restore_selective(
            sample_backup, mock_adapter, directories=["agents", "skills"]
        )

        assert result.success is True
        config_dir = mock_adapter.info.config_dir
        assert (config_dir / "agents").exists()
        assert (config_dir / "skills").exists()

    def test_restore_selective_nonexistent_directory(
        self, restore_manager: RestoreManager, mock_adapter: Mock, sample_backup: Path
    ) -> None:
        """Test selective restore handles nonexistent directory gracefully."""
        result = restore_manager.restore_selective(
            sample_backup, mock_adapter, directories=["nonexistent"]
        )

        assert result.success is True
        assert result.restored_files == 0

    def test_restore_selective_invalid_backup(
        self, restore_manager: RestoreManager, mock_adapter: Mock, tmp_path: Path
    ) -> None:
        """Test selective restore fails with invalid backup."""
        fake_path = tmp_path / "nonexistent.tar.gz"

        result = restore_manager.restore_selective(fake_path, mock_adapter, directories=["agents"])

        assert result.success is False

    def test_restore_selective_with_progress_callback(
        self, restore_manager: RestoreManager, mock_adapter: Mock, sample_backup: Path
    ) -> None:
        """Test selective restore with progress callback."""
        progress_messages: list[str] = []

        def callback(msg: str) -> None:
            progress_messages.append(msg)

        result = restore_manager.restore_selective(
            sample_backup, mock_adapter, directories=["agents"], progress_callback=callback
        )

        assert result.success is True
        assert len(progress_messages) > 0
        assert any("selective" in msg.lower() for msg in progress_messages)


class TestRollback:
    """Tests for rollback method."""

    def test_rollback_success(
        self, restore_manager: RestoreManager, mock_adapter: Mock, sample_backup: Path
    ) -> None:
        """Test successful rollback."""
        mock_adapter.restore = Mock()

        result = restore_manager.rollback(sample_backup, mock_adapter)

        assert result.success is True
        # Rollback should not create pre-restore backup
        assert result.pre_restore_backup is None
        mock_adapter.restore.assert_called_once()

    def test_rollback_with_progress(
        self, restore_manager: RestoreManager, mock_adapter: Mock, sample_backup: Path
    ) -> None:
        """Test rollback with progress callback."""
        mock_adapter.restore = Mock()
        progress_messages: list[str] = []

        def callback(msg: str) -> None:
            progress_messages.append(msg)

        result = restore_manager.rollback(sample_backup, mock_adapter, progress_callback=callback)

        assert result.success is True
        assert any("Rolling back" in msg for msg in progress_messages)


class TestGetRestorableDirectories:
    """Tests for get_restorable_directories method."""

    def test_get_restorable_directories(
        self, restore_manager: RestoreManager, sample_backup: Path
    ) -> None:
        """Test getting restorable directories from backup."""
        directories = restore_manager.get_restorable_directories(sample_backup)

        assert "agents" in directories
        assert "skills" in directories

    def test_get_restorable_directories_nonexistent(
        self, restore_manager: RestoreManager, tmp_path: Path
    ) -> None:
        """Test returns empty list for nonexistent backup."""
        fake_path = tmp_path / "nonexistent.tar.gz"
        directories = restore_manager.get_restorable_directories(fake_path)

        assert directories == []

    def test_get_restorable_directories_invalid_archive(
        self, restore_manager: RestoreManager, tmp_path: Path
    ) -> None:
        """Test returns empty list for invalid archive."""
        invalid_path = tmp_path / "invalid.tar.gz"
        invalid_path.write_text("not a tar file")

        directories = restore_manager.get_restorable_directories(invalid_path)

        assert directories == []


class TestBackupTimestamp:
    """Tests for _get_backup_timestamp method."""

    def test_get_backup_timestamp_from_metadata(
        self,
        restore_manager: RestoreManager,
        backup_manager: BackupManager,
        mock_adapter: Mock,
        tmp_path: Path,
    ) -> None:
        """Test getting timestamp from backup metadata."""
        # Create a backup to generate metadata
        config_dir = mock_adapter.info.config_dir

        def mock_backup_method(dest_dir: Path) -> Path:
            backup_path = dest_dir / "test_backup.tar.gz"
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(config_dir, arcname="claude")
            return backup_path

        mock_adapter.backup = Mock(side_effect=mock_backup_method)
        result = backup_manager.backup_vendor(mock_adapter)

        assert result.success is True
        assert result.metadata is not None

        # Get timestamp should find it in metadata
        timestamp = restore_manager._get_backup_timestamp(result.metadata.backup_path)
        assert timestamp is not None

    def test_get_backup_timestamp_fallback_to_mtime(
        self, restore_manager: RestoreManager, sample_backup: Path
    ) -> None:
        """Test fallback to file mtime when metadata not found."""
        # sample_backup has no metadata in backup manager
        timestamp = restore_manager._get_backup_timestamp(sample_backup)

        assert timestamp is not None
        assert isinstance(timestamp, datetime)


class TestCountFilesInArchive:
    """Tests for _count_files_in_archive method."""

    def test_count_files_in_archive(
        self, restore_manager: RestoreManager, sample_backup: Path
    ) -> None:
        """Test counting files in archive."""
        count = restore_manager._count_files_in_archive(sample_backup)

        # sample_backup has settings.json, agents/test_agent.md, skills/test_skill.md
        assert count == 3

    def test_count_files_invalid_archive(
        self, restore_manager: RestoreManager, tmp_path: Path
    ) -> None:
        """Test returns 0 for invalid archive."""
        invalid_path = tmp_path / "invalid.tar.gz"
        invalid_path.write_text("not a tar file")

        count = restore_manager._count_files_in_archive(invalid_path)

        assert count == 0


class TestRestoreEdgeCases:
    """Additional edge case tests for RestoreManager."""

    def test_preview_restore_tar_error(
        self, restore_manager: RestoreManager, mock_adapter: Mock, tmp_path: Path
    ) -> None:
        """Test preview handles TarError gracefully."""
        # Create a file that looks like tar.gz but is corrupted
        corrupt_archive = tmp_path / "corrupt.tar.gz"
        corrupt_archive.write_bytes(b"\x1f\x8b\x08\x00" + b"corrupted data")

        preview = restore_manager.preview_restore(corrupt_archive, mock_adapter)

        # Should return None for corrupted archive
        assert preview is None

    def test_restore_selective_empty_archive(
        self, restore_manager: RestoreManager, mock_adapter: Mock, tmp_path: Path
    ) -> None:
        """Test selective restore handles empty archive."""
        # Create empty archive
        empty_archive = tmp_path / "empty.tar.gz"
        with tarfile.open(empty_archive, "w:gz"):
            pass

        result = restore_manager.restore_selective(
            empty_archive, mock_adapter, directories=["agents"]
        )

        assert result.success is False
        assert "empty" in result.error.lower()

    def test_restore_selective_exception_handling(
        self, restore_manager: RestoreManager, mock_adapter: Mock, tmp_path: Path
    ) -> None:
        """Test restore_selective handles exceptions."""
        fake_path = tmp_path / "nonexistent.tar.gz"

        result = restore_manager.restore_selective(fake_path, mock_adapter, directories=["agents"])

        assert result.success is False

    def test_get_restorable_directories_empty_archive(
        self, restore_manager: RestoreManager, tmp_path: Path
    ) -> None:
        """Test get_restorable_directories with empty archive."""
        empty_archive = tmp_path / "empty.tar.gz"
        with tarfile.open(empty_archive, "w:gz"):
            pass

        directories = restore_manager.get_restorable_directories(empty_archive)

        assert directories == []
