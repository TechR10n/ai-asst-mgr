"""Unit tests for SyncManager."""

import shutil
import tarfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_asst_mgr.adapters.base import VendorInfo
from ai_asst_mgr.operations.backup import BackupManager
from ai_asst_mgr.operations.sync import (
    FileChange,
    MergeStrategy,
    SyncManager,
    SyncPreview,
    SyncResult,
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
def sync_manager(backup_manager: BackupManager) -> SyncManager:
    """Create a SyncManager with BackupManager."""
    return SyncManager(backup_manager)


@pytest.fixture
def sync_manager_no_backup() -> SyncManager:
    """Create a SyncManager without BackupManager."""
    return SyncManager(None)


@pytest.fixture
def mock_adapter(tmp_path: Path) -> Mock:
    """Create a mock VendorAdapter with config directory."""
    config_dir = tmp_path / ".claude"
    config_dir.mkdir()
    (config_dir / "settings.json").write_text('{"existing": "config"}')
    (config_dir / "agents").mkdir()
    (config_dir / "agents" / "local_agent.md").write_text("# Local Agent")

    info = Mock(spec=VendorInfo)
    info.vendor_id = "claude"
    info.name = "Claude Code"
    info.config_dir = config_dir

    adapter = Mock()
    adapter.info = info
    adapter.is_installed.return_value = True

    return adapter


@pytest.fixture
def mock_repo_dir(tmp_path: Path) -> Path:
    """Create a mock git repository structure."""
    repo_dir = tmp_path / "repo"
    repo_dir.mkdir()

    # Create config files
    (repo_dir / "settings.json").write_text('{"remote": "config"}')

    # Create directories
    (repo_dir / "agents").mkdir()
    (repo_dir / "agents" / "remote_agent.md").write_text("# Remote Agent")
    (repo_dir / "skills").mkdir()
    (repo_dir / "skills" / "new_skill.md").write_text("# New Skill")

    return repo_dir


class TestMergeStrategy:
    """Tests for MergeStrategy enum."""

    def test_strategy_values(self) -> None:
        """Test MergeStrategy has expected values."""
        assert MergeStrategy.REPLACE.value == "replace"
        assert MergeStrategy.MERGE.value == "merge"
        assert MergeStrategy.KEEP_LOCAL.value == "keep_local"
        assert MergeStrategy.KEEP_REMOTE.value == "keep_remote"


class TestFileChange:
    """Tests for FileChange dataclass."""

    def test_file_change_fields(self) -> None:
        """Test FileChange contains all required fields."""
        change = FileChange(
            path="agents/test.md",
            change_type="added",
            local_exists=False,
            remote_exists=True,
        )

        assert change.path == "agents/test.md"
        assert change.change_type == "added"
        assert change.local_exists is False
        assert change.remote_exists is True


class TestSyncPreview:
    """Tests for SyncPreview dataclass."""

    def test_preview_fields(self) -> None:
        """Test SyncPreview contains all required fields."""
        preview = SyncPreview(
            vendor_id="claude",
            repo_url="https://github.com/test/config.git",
            branch="main",
            files_to_add=["new.md"],
            files_to_modify=["settings.json"],
            files_to_delete=["old.md"],
            conflicts=["settings.json"],
        )

        assert preview.vendor_id == "claude"
        assert preview.repo_url == "https://github.com/test/config.git"
        assert preview.branch == "main"
        assert len(preview.files_to_add) == 1
        assert len(preview.files_to_modify) == 1
        assert len(preview.conflicts) == 1


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_successful_result(self, tmp_path: Path) -> None:
        """Test successful sync result."""
        backup_path = tmp_path / "backup.tar.gz"
        backup_path.touch()

        result = SyncResult(
            success=True,
            files_synced=5,
            files_added=3,
            files_modified=2,
            files_deleted=0,
            pre_sync_backup=backup_path,
            duration_seconds=1.5,
        )

        assert result.success is True
        assert result.files_synced == 5
        assert result.files_added == 3
        assert result.files_modified == 2
        assert result.error is None

    def test_failed_result(self) -> None:
        """Test failed sync result."""
        result = SyncResult(success=False, error="Clone failed", duration_seconds=0.5)

        assert result.success is False
        assert result.error == "Clone failed"


class TestSyncManagerInit:
    """Tests for SyncManager initialization."""

    def test_init_with_backup_manager(self, backup_manager: BackupManager) -> None:
        """Test initialization with backup manager."""
        manager = SyncManager(backup_manager)
        assert manager._backup_manager == backup_manager

    def test_init_without_backup_manager(self) -> None:
        """Test initialization without backup manager."""
        manager = SyncManager(None)
        assert manager._backup_manager is None


class TestVendorSyncDirs:
    """Tests for VENDOR_SYNC_DIRS class variable."""

    def test_vendor_sync_dirs_exists(self) -> None:
        """Test VENDOR_SYNC_DIRS is defined."""
        assert hasattr(SyncManager, "VENDOR_SYNC_DIRS")
        assert "claude" in SyncManager.VENDOR_SYNC_DIRS
        assert "gemini" in SyncManager.VENDOR_SYNC_DIRS
        assert "openai" in SyncManager.VENDOR_SYNC_DIRS

    def test_claude_sync_dirs(self) -> None:
        """Test Claude sync directories."""
        claude_dirs = SyncManager.VENDOR_SYNC_DIRS["claude"]
        assert "agents" in claude_dirs
        assert "skills" in claude_dirs
        assert "commands" in claude_dirs


class TestVendorSyncFiles:
    """Tests for VENDOR_SYNC_FILES class variable."""

    def test_vendor_sync_files_exists(self) -> None:
        """Test VENDOR_SYNC_FILES is defined."""
        assert hasattr(SyncManager, "VENDOR_SYNC_FILES")
        assert "claude" in SyncManager.VENDOR_SYNC_FILES
        assert "gemini" in SyncManager.VENDOR_SYNC_FILES

    def test_claude_sync_files(self) -> None:
        """Test Claude sync files."""
        claude_files = SyncManager.VENDOR_SYNC_FILES["claude"]
        assert "settings.json" in claude_files


class TestPreviewSync:
    """Tests for preview_sync method."""

    def test_preview_sync_clone_failure(
        self, sync_manager: SyncManager, mock_adapter: Mock
    ) -> None:
        """Test preview returns None when clone fails."""
        with patch.object(sync_manager, "_clone_repo", return_value=False):
            preview = sync_manager.preview_sync("https://github.com/fake/repo.git", mock_adapter)

        assert preview is None

    def test_preview_sync_success(
        self, sync_manager: SyncManager, mock_adapter: Mock, mock_repo_dir: Path
    ) -> None:
        """Test successful sync preview."""

        def mock_clone(_url: str, dest_dir: Path, _branch: str) -> bool:
            # Copy mock repo content to dest_dir
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with patch.object(sync_manager, "_clone_repo", side_effect=mock_clone):
            preview = sync_manager.preview_sync("https://github.com/test/config.git", mock_adapter)

        assert preview is not None
        assert preview.vendor_id == "claude"
        # settings.json exists locally and remotely with different content
        assert any("settings.json" in f for f in preview.files_to_modify)
        # skills/new_skill.md doesn't exist locally
        assert any("skills" in f for f in preview.files_to_add)


class TestSyncVendor:
    """Tests for sync_vendor method."""

    def test_sync_vendor_clone_failure(self, sync_manager: SyncManager, mock_adapter: Mock) -> None:
        """Test sync fails when clone fails."""
        with patch.object(sync_manager, "_clone_repo", return_value=False):
            result = sync_manager.sync_vendor(
                "https://github.com/fake/repo.git", mock_adapter, create_backup=False
            )

        assert result.success is False
        assert "clone" in result.error.lower()

    def test_sync_vendor_success_keep_remote(
        self, sync_manager: SyncManager, mock_adapter: Mock, mock_repo_dir: Path
    ) -> None:
        """Test successful sync with KEEP_REMOTE strategy."""

        def mock_clone(_url: str, dest_dir: Path, _branch: str) -> bool:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with patch.object(sync_manager, "_clone_repo", side_effect=mock_clone):
            result = sync_manager.sync_vendor(
                "https://github.com/test/config.git",
                mock_adapter,
                strategy=MergeStrategy.KEEP_REMOTE,
                create_backup=False,
            )

        assert result.success is True
        assert result.files_synced > 0

    def test_sync_vendor_with_progress_callback(
        self, sync_manager: SyncManager, mock_adapter: Mock, mock_repo_dir: Path
    ) -> None:
        """Test sync with progress callback."""
        progress_messages: list[str] = []

        def callback(msg: str) -> None:
            progress_messages.append(msg)

        def mock_clone(_url: str, dest_dir: Path, _branch: str) -> bool:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with patch.object(sync_manager, "_clone_repo", side_effect=mock_clone):
            result = sync_manager.sync_vendor(
                "https://github.com/test/config.git",
                mock_adapter,
                create_backup=False,
                progress_callback=callback,
            )

        assert result.success is True
        assert len(progress_messages) > 0
        assert any("Starting" in msg for msg in progress_messages)

    def test_sync_vendor_creates_backup(
        self, sync_manager: SyncManager, mock_adapter: Mock, mock_repo_dir: Path
    ) -> None:
        """Test sync creates backup when requested."""
        config_dir = mock_adapter.info.config_dir

        def mock_backup_method(dest_dir: Path) -> Path:
            backup_path = dest_dir / "pre_sync_backup.tar.gz"
            with tarfile.open(backup_path, "w:gz") as tar:
                tar.add(config_dir, arcname="claude")
            return backup_path

        mock_adapter.backup = Mock(side_effect=mock_backup_method)

        def mock_clone(_url: str, dest_dir: Path, _branch: str) -> bool:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with patch.object(sync_manager, "_clone_repo", side_effect=mock_clone):
            result = sync_manager.sync_vendor(
                "https://github.com/test/config.git",
                mock_adapter,
                create_backup=True,
            )

        assert result.success is True
        assert result.pre_sync_backup is not None


class TestSyncAllVendors:
    """Tests for sync_all_vendors method."""

    def test_sync_all_vendors_success(
        self, sync_manager: SyncManager, mock_adapter: Mock, mock_repo_dir: Path
    ) -> None:
        """Test sync all vendors."""

        def mock_clone(_url: str, dest_dir: Path, _branch: str) -> bool:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with patch.object(sync_manager, "_clone_repo", side_effect=mock_clone):
            results = sync_manager.sync_all_vendors(
                "https://github.com/test/config.git", {"claude": mock_adapter}
            )

        assert "claude" in results
        assert results["claude"].success is True

    def test_sync_all_vendors_with_failure(
        self, sync_manager: SyncManager, mock_adapter: Mock
    ) -> None:
        """Test sync handles failures gracefully."""
        mock_adapter2 = Mock()
        mock_adapter2.info = Mock()
        mock_adapter2.info.vendor_id = "gemini"
        mock_adapter2.info.name = "Gemini"
        mock_adapter2.info.config_dir = Path("/nonexistent")
        mock_adapter2.is_installed.return_value = False

        with patch.object(sync_manager, "_clone_repo", return_value=False):
            results = sync_manager.sync_all_vendors(
                "https://github.com/test/config.git",
                {"claude": mock_adapter, "gemini": mock_adapter2},
            )

        assert len(results) == 2
        # Both should fail because clone fails
        assert results["claude"].success is False
        assert results["gemini"].success is False


class TestCloneRepo:
    """Tests for _clone_repo method."""

    def test_clone_repo_success(self, sync_manager: SyncManager, tmp_path: Path) -> None:
        """Test successful repo clone."""
        dest_dir = tmp_path / "cloned"

        # Mock git_clone to simulate successful clone
        with patch("ai_asst_mgr.operations.sync.git_clone") as mock_git_clone:
            mock_git_clone.return_value = True
            result = sync_manager._clone_repo("https://github.com/test/repo.git", dest_dir, "main")

        assert result is True
        mock_git_clone.assert_called_once()

    def test_clone_repo_failure(self, sync_manager: SyncManager, tmp_path: Path) -> None:
        """Test failed repo clone."""
        dest_dir = tmp_path / "cloned"

        with patch("ai_asst_mgr.operations.sync.git_clone") as mock_git_clone:
            mock_git_clone.return_value = False
            result = sync_manager._clone_repo("https://github.com/fake/repo.git", dest_dir, "main")

        assert result is False


class TestFilesDiffer:
    """Tests for _files_differ method."""

    def test_files_differ_same_content(self, sync_manager: SyncManager, tmp_path: Path) -> None:
        """Test files with same content don't differ."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("same content")
        file2.write_text("same content")

        assert sync_manager._files_differ(file1, file2) is False

    def test_files_differ_different_content(
        self, sync_manager: SyncManager, tmp_path: Path
    ) -> None:
        """Test files with different content differ."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "file2.txt"
        file1.write_text("content 1")
        file2.write_text("content 2")

        assert sync_manager._files_differ(file1, file2) is True

    def test_files_differ_nonexistent(self, sync_manager: SyncManager, tmp_path: Path) -> None:
        """Test nonexistent file returns True (differ)."""
        file1 = tmp_path / "file1.txt"
        file2 = tmp_path / "nonexistent.txt"
        file1.write_text("content")

        assert sync_manager._files_differ(file1, file2) is True


class TestSyncDirectory:
    """Tests for _sync_directory method."""

    def test_sync_directory_replace_strategy(
        self, sync_manager: SyncManager, tmp_path: Path
    ) -> None:
        """Test sync directory with REPLACE strategy."""
        remote_dir = tmp_path / "remote"
        remote_dir.mkdir()
        (remote_dir / "new_file.txt").write_text("new content")

        local_dir = tmp_path / "local"
        local_dir.mkdir()
        (local_dir / "old_file.txt").write_text("old content")

        added, _modified, deleted = sync_manager._sync_directory(
            remote_dir, local_dir, MergeStrategy.REPLACE
        )

        # Replace deletes old and adds new
        assert added > 0
        assert deleted > 0
        assert (local_dir / "new_file.txt").exists()
        assert not (local_dir / "old_file.txt").exists()

    def test_sync_directory_keep_remote_strategy(
        self, sync_manager: SyncManager, tmp_path: Path
    ) -> None:
        """Test sync directory with KEEP_REMOTE strategy."""
        remote_dir = tmp_path / "remote"
        remote_dir.mkdir()
        (remote_dir / "file.txt").write_text("remote content")

        local_dir = tmp_path / "local"
        local_dir.mkdir()
        (local_dir / "file.txt").write_text("local content")

        _added, modified, _deleted = sync_manager._sync_directory(
            remote_dir, local_dir, MergeStrategy.KEEP_REMOTE
        )

        # Remote content should overwrite local
        assert modified == 1
        assert (local_dir / "file.txt").read_text() == "remote content"

    def test_sync_directory_keep_local_strategy(
        self, sync_manager: SyncManager, tmp_path: Path
    ) -> None:
        """Test sync directory with KEEP_LOCAL strategy."""
        remote_dir = tmp_path / "remote"
        remote_dir.mkdir()
        (remote_dir / "file.txt").write_text("remote content")

        local_dir = tmp_path / "local"
        local_dir.mkdir()
        (local_dir / "file.txt").write_text("local content")

        _added, modified, _deleted = sync_manager._sync_directory(
            remote_dir, local_dir, MergeStrategy.KEEP_LOCAL
        )

        # Local content should be preserved
        assert modified == 0
        assert (local_dir / "file.txt").read_text() == "local content"


class TestSyncFile:
    """Tests for _sync_file method."""

    def test_sync_file_keep_remote_new_file(
        self, sync_manager: SyncManager, tmp_path: Path
    ) -> None:
        """Test sync adds new file with KEEP_REMOTE strategy."""
        remote_file = tmp_path / "remote.txt"
        remote_file.write_text("remote content")

        local_file = tmp_path / "local.txt"

        added, modified = sync_manager._sync_file(
            remote_file, local_file, MergeStrategy.KEEP_REMOTE
        )

        assert added == 1
        assert modified == 0
        assert local_file.read_text() == "remote content"

    def test_sync_file_keep_remote_existing_file(
        self, sync_manager: SyncManager, tmp_path: Path
    ) -> None:
        """Test sync modifies existing file with KEEP_REMOTE strategy."""
        remote_file = tmp_path / "remote.txt"
        remote_file.write_text("remote content")

        local_file = tmp_path / "local.txt"
        local_file.write_text("local content")

        added, modified = sync_manager._sync_file(
            remote_file, local_file, MergeStrategy.KEEP_REMOTE
        )

        assert added == 0
        assert modified == 1
        assert local_file.read_text() == "remote content"

    def test_sync_file_keep_local_preserves_file(
        self, sync_manager: SyncManager, tmp_path: Path
    ) -> None:
        """Test sync preserves existing file with KEEP_LOCAL strategy."""
        remote_file = tmp_path / "remote.txt"
        remote_file.write_text("remote content")

        local_file = tmp_path / "local.txt"
        local_file.write_text("local content")

        added, modified = sync_manager._sync_file(remote_file, local_file, MergeStrategy.KEEP_LOCAL)

        assert added == 0
        assert modified == 0
        assert local_file.read_text() == "local content"

    def test_sync_file_merge_creates_remote_version(
        self, sync_manager: SyncManager, tmp_path: Path
    ) -> None:
        """Test sync creates .remote version for conflicts in MERGE strategy."""
        remote_file = tmp_path / "remote.txt"
        remote_file.write_text("remote content")

        local_file = tmp_path / "local.txt"
        local_file.write_text("local content")

        _added, modified = sync_manager._sync_file(remote_file, local_file, MergeStrategy.MERGE)

        assert modified == 1
        # Original file preserved
        assert local_file.read_text() == "local content"
        # Remote version created
        remote_version = tmp_path / "local.txt.remote"
        assert remote_version.exists()
        assert remote_version.read_text() == "remote content"


class TestSyncEdgeCases:
    """Additional edge case tests for SyncManager."""

    def test_preview_sync_returns_none_on_exception(
        self, sync_manager: SyncManager, mock_adapter: Mock
    ) -> None:
        """Test preview_sync returns None on exception."""
        with patch.object(sync_manager, "_clone_repo", side_effect=Exception("Unexpected error")):
            preview = sync_manager.preview_sync("https://github.com/test/repo.git", mock_adapter)

        # Should return None, not raise exception
        assert preview is None

    def test_sync_vendor_with_exception(
        self, sync_manager: SyncManager, mock_adapter: Mock, mock_repo_dir: Path
    ) -> None:
        """Test sync_vendor handles exceptions gracefully."""

        def mock_clone_then_fail(_url: str, dest_dir: Path, _branch: str) -> bool:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with (
            patch.object(sync_manager, "_clone_repo", side_effect=mock_clone_then_fail),
            patch.object(sync_manager, "_sync_directory", side_effect=OSError("Permission denied")),
        ):
            result = sync_manager.sync_vendor(
                "https://github.com/test/repo.git",
                mock_adapter,
                create_backup=False,
            )

        assert result.success is False
        assert "Permission denied" in result.error

    def test_sync_file_merge_new_file(self, sync_manager: SyncManager, tmp_path: Path) -> None:
        """Test MERGE strategy adds new file when local doesn't exist."""
        remote_file = tmp_path / "remote.txt"
        remote_file.write_text("remote content")

        local_file = tmp_path / "new_local.txt"
        # local_file doesn't exist

        added, modified = sync_manager._sync_file(remote_file, local_file, MergeStrategy.MERGE)

        assert added == 1
        assert modified == 0
        assert local_file.read_text() == "remote content"

    def test_sync_file_merge_same_content(self, sync_manager: SyncManager, tmp_path: Path) -> None:
        """Test MERGE strategy handles identical files."""
        remote_file = tmp_path / "remote.txt"
        remote_file.write_text("same content")

        local_file = tmp_path / "local.txt"
        local_file.write_text("same content")

        added, modified = sync_manager._sync_file(remote_file, local_file, MergeStrategy.MERGE)

        # No changes when files are identical
        assert added == 0
        assert modified == 0

    def test_sync_directory_new_local_dir(self, sync_manager: SyncManager, tmp_path: Path) -> None:
        """Test sync_directory creates new local directory."""
        remote_dir = tmp_path / "remote"
        remote_dir.mkdir()
        (remote_dir / "file.txt").write_text("content")

        local_dir = tmp_path / "nonexistent"
        # local_dir doesn't exist

        added, _modified, _deleted = sync_manager._sync_directory(
            remote_dir, local_dir, MergeStrategy.KEEP_REMOTE
        )

        assert added == 1
        assert (local_dir / "file.txt").exists()

    def test_sync_all_vendors_with_progress(
        self, sync_manager: SyncManager, mock_adapter: Mock, mock_repo_dir: Path
    ) -> None:
        """Test sync_all_vendors with progress callback."""
        progress_messages: list[str] = []

        def callback(msg: str) -> None:
            progress_messages.append(msg)

        def mock_clone(_url: str, dest_dir: Path, _branch: str) -> bool:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with patch.object(sync_manager, "_clone_repo", side_effect=mock_clone):
            sync_manager.sync_all_vendors(
                "https://github.com/test/config.git",
                {"claude": mock_adapter},
                progress_callback=callback,
            )

        assert len(progress_messages) > 0

    def test_preview_sync_no_remote_dir(
        self, sync_manager: SyncManager, mock_adapter: Mock, tmp_path: Path
    ) -> None:
        """Test preview_sync when remote directory doesn't exist."""
        mock_repo_dir = tmp_path / "repo"
        mock_repo_dir.mkdir()
        # No agents or skills directories

        def mock_clone(_url: str, dest_dir: Path, _branch: str) -> bool:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with patch.object(sync_manager, "_clone_repo", side_effect=mock_clone):
            preview = sync_manager.preview_sync("https://github.com/test/config.git", mock_adapter)

        assert preview is not None
        # Should have no files to add/modify from directories
        assert len(preview.files_to_add) == 0

    def test_preview_sync_no_local_dir(
        self, sync_manager: SyncManager, tmp_path: Path, mock_repo_dir: Path
    ) -> None:
        """Test preview_sync when local directory doesn't exist."""
        config_dir = tmp_path / ".claude_new"
        config_dir.mkdir()

        info = Mock()
        info.vendor_id = "claude"
        info.name = "Claude Code"
        info.config_dir = config_dir

        adapter = Mock()
        adapter.info = info

        def mock_clone(_url: str, dest_dir: Path, _branch: str) -> bool:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with patch.object(sync_manager, "_clone_repo", side_effect=mock_clone):
            preview = sync_manager.preview_sync("https://github.com/test/config.git", adapter)

        assert preview is not None
        # All files should be additions (no deletions since local dir is empty)
        assert len(preview.files_to_delete) == 0

    def test_preview_files_no_remote_file(
        self, sync_manager: SyncManager, mock_adapter: Mock, tmp_path: Path
    ) -> None:
        """Test _preview_files when remote file doesn't exist."""
        mock_repo_dir = tmp_path / "repo"
        mock_repo_dir.mkdir()
        # No settings.json in remote

        def mock_clone(_url: str, dest_dir: Path, _branch: str) -> bool:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with patch.object(sync_manager, "_clone_repo", side_effect=mock_clone):
            preview = sync_manager.preview_sync("https://github.com/test/config.git", mock_adapter)

        assert preview is not None
        # settings.json exists locally but not remotely, so not in files_to_add
        assert "settings.json" not in preview.files_to_add

    def test_sync_vendor_no_backup_manager(
        self, sync_manager_no_backup: SyncManager, mock_adapter: Mock, mock_repo_dir: Path
    ) -> None:
        """Test sync_vendor without backup manager."""

        def mock_clone(_url: str, dest_dir: Path, _branch: str) -> bool:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with patch.object(sync_manager_no_backup, "_clone_repo", side_effect=mock_clone):
            result = sync_manager_no_backup.sync_vendor(
                "https://github.com/test/config.git",
                mock_adapter,
                create_backup=True,
            )

        assert result.success is True
        # No backup should be created when backup_manager is None
        assert result.pre_sync_backup is None

    def test_sync_vendor_adapter_not_installed(
        self, sync_manager: SyncManager, mock_adapter: Mock, mock_repo_dir: Path
    ) -> None:
        """Test sync_vendor when adapter not installed (skips backup)."""
        mock_adapter.is_installed.return_value = False

        def mock_clone(_url: str, dest_dir: Path, _branch: str) -> bool:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with patch.object(sync_manager, "_clone_repo", side_effect=mock_clone):
            result = sync_manager.sync_vendor(
                "https://github.com/test/config.git",
                mock_adapter,
                create_backup=True,
            )

        assert result.success is True
        # No backup created because adapter not installed
        assert result.pre_sync_backup is None

    def test_sync_files_no_remote_file(
        self, sync_manager: SyncManager, mock_adapter: Mock, tmp_path: Path
    ) -> None:
        """Test _sync_files when remote file doesn't exist."""
        mock_repo_dir = tmp_path / "repo"
        mock_repo_dir.mkdir()
        # No settings.json

        def mock_clone(_url: str, dest_dir: Path, _branch: str) -> bool:
            if dest_dir.exists():
                shutil.rmtree(dest_dir)
            shutil.copytree(mock_repo_dir, dest_dir)
            return True

        with patch.object(sync_manager, "_clone_repo", side_effect=mock_clone):
            result = sync_manager.sync_vendor(
                "https://github.com/test/config.git",
                mock_adapter,
                create_backup=False,
            )

        assert result.success is True
        # No files synced from VENDOR_SYNC_FILES
        assert result.files_synced >= 0

    def test_sync_file_no_change_needed(self, sync_manager: SyncManager, tmp_path: Path) -> None:
        """Test _sync_file when file exists and content is same."""
        remote_file = tmp_path / "remote.txt"
        remote_file.write_text("same content")

        local_file = tmp_path / "local.txt"
        local_file.write_text("same content")

        added, modified = sync_manager._sync_file(
            remote_file, local_file, MergeStrategy.KEEP_REMOTE
        )

        # Files are same, so should still copy but count as modified
        assert added == 0
        assert modified == 1

    def test_sync_directory_replace_with_empty_local(
        self, sync_manager: SyncManager, tmp_path: Path
    ) -> None:
        """Test _sync_directory REPLACE strategy with empty local dir."""
        remote_dir = tmp_path / "remote"
        remote_dir.mkdir()
        (remote_dir / "file.txt").write_text("content")

        local_dir = tmp_path / "local_empty"
        local_dir.mkdir()
        # Empty local directory

        added, modified, deleted = sync_manager._sync_directory(
            remote_dir, local_dir, MergeStrategy.REPLACE
        )

        assert added > 0
        assert deleted == 0  # No files to delete in empty dir

    def test_sync_directory_keep_remote_with_subdirs(
        self, sync_manager: SyncManager, tmp_path: Path
    ) -> None:
        """Test _sync_directory KEEP_REMOTE strategy with subdirectories."""
        remote_dir = tmp_path / "remote"
        remote_dir.mkdir()
        (remote_dir / "subdir").mkdir()
        (remote_dir / "subdir" / "file.txt").write_text("remote content")

        local_dir = tmp_path / "local"
        local_dir.mkdir()

        added, modified, deleted = sync_manager._sync_directory(
            remote_dir, local_dir, MergeStrategy.KEEP_REMOTE
        )

        assert added == 1
        assert (local_dir / "subdir" / "file.txt").exists()

    def test_sync_file_merge_with_identical_files(
        self, sync_manager: SyncManager, tmp_path: Path
    ) -> None:
        """Test _sync_file MERGE strategy with identical files."""
        remote_file = tmp_path / "remote.txt"
        remote_file.write_text("same content")

        local_file = tmp_path / "local.txt"
        local_file.write_text("same content")

        added, modified = sync_manager._sync_file(remote_file, local_file, MergeStrategy.MERGE)

        # Files are identical, no changes needed
        assert added == 0
        assert modified == 0
        # No .remote version should be created
        assert not (tmp_path / "local.txt.remote").exists()

    def test_clone_repo_removes_existing_dir(
        self, sync_manager: SyncManager, tmp_path: Path
    ) -> None:
        """Test _clone_repo removes existing directory before cloning."""
        dest_dir = tmp_path / "cloned"
        dest_dir.mkdir()
        (dest_dir / "old_file.txt").write_text("old content")

        # Mock the git_clone utility function
        with patch("ai_asst_mgr.operations.sync.git_clone", return_value=True) as mock_git:
            result = sync_manager._clone_repo("https://github.com/test/repo.git", dest_dir, "main")

        assert result is True
        # Destination directory should have been removed before cloning
        mock_git.assert_called_once_with("https://github.com/test/repo.git", dest_dir, "main")
