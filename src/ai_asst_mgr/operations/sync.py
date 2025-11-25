"""Git sync operations for AI assistant configurations.

This module provides functionality to synchronize AI assistant configurations
from Git repositories, including diff preview, merge strategies, and dry-run mode.
"""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING, ClassVar

from ai_asst_mgr.utils import git_clone

if TYPE_CHECKING:
    from collections.abc import Callable

    from ai_asst_mgr.adapters.base import VendorAdapter
    from ai_asst_mgr.operations.backup import BackupManager


class MergeStrategy(Enum):
    """Strategy for merging configurations.

    Attributes:
        REPLACE: Replace all existing files with synced content.
        MERGE: Merge files, keeping both local and remote versions.
        KEEP_LOCAL: Keep local files if they exist.
        KEEP_REMOTE: Always use remote files.
    """

    REPLACE = "replace"
    MERGE = "merge"
    KEEP_LOCAL = "keep_local"
    KEEP_REMOTE = "keep_remote"


@dataclass
class FileChange:
    """Represents a file change during sync.

    Attributes:
        path: Relative path of the file.
        change_type: Type of change (added, modified, deleted).
        local_exists: Whether file exists locally.
        remote_exists: Whether file exists in remote.
    """

    path: str
    change_type: str  # "added", "modified", "deleted", "unchanged"
    local_exists: bool
    remote_exists: bool


@dataclass
class SyncPreview:
    """Preview of what a sync operation would do.

    Attributes:
        vendor_id: Vendor being synced.
        repo_url: Git repository URL.
        branch: Git branch being synced from.
        files_to_add: Files that would be added.
        files_to_modify: Files that would be modified.
        files_to_delete: Files that would be deleted (in REPLACE mode).
        conflicts: Files with potential conflicts.
    """

    vendor_id: str
    repo_url: str
    branch: str
    files_to_add: list[str] = field(default_factory=list)
    files_to_modify: list[str] = field(default_factory=list)
    files_to_delete: list[str] = field(default_factory=list)
    conflicts: list[str] = field(default_factory=list)


@dataclass
class SyncConfig:
    """Configuration parameters for a sync operation.

    Attributes:
        repo_url: URL of the Git repository.
        adapter: The vendor adapter to sync to.
        branch: Git branch to sync from.
        strategy: Merge strategy to use.
        create_backup: Whether to create a backup before syncing.
        progress_callback: Optional callback for progress updates.
    """

    repo_url: str
    adapter: VendorAdapter
    branch: str = "main"
    strategy: MergeStrategy = MergeStrategy.KEEP_REMOTE
    create_backup: bool = True
    progress_callback: Callable[[str], None] | None = None


@dataclass
class _PreviewContext:
    """Internal context for preview operations.

    Attributes:
        vendor_id: Vendor identifier.
        temp_dir: Temporary directory with remote files.
        config_dir: Local configuration directory.
        files_to_add: List of files to be added.
        files_to_modify: List of files to be modified.
        files_to_delete: List of files to be deleted.
        conflicts: List of conflicting files.
    """

    vendor_id: str
    temp_dir: Path
    config_dir: Path
    files_to_add: list[str]
    files_to_modify: list[str]
    files_to_delete: list[str]
    conflicts: list[str]


@dataclass
class SyncResult:
    """Result of a sync operation.

    Attributes:
        success: Whether the sync succeeded.
        files_synced: Number of files synced.
        files_added: Number of new files added.
        files_modified: Number of files modified.
        files_deleted: Number of files deleted.
        pre_sync_backup: Path to pre-sync backup if created.
        error: Error message if failed.
        duration_seconds: How long the sync took.
    """

    success: bool
    files_synced: int = 0
    files_added: int = 0
    files_modified: int = 0
    files_deleted: int = 0
    pre_sync_backup: Path | None = None
    error: str | None = None
    duration_seconds: float = 0.0


class SyncManager:
    """Manages Git sync operations for AI assistant configurations.

    The SyncManager provides functionality to synchronize configurations from
    Git repositories with features including:
    - Clone and extract vendor-specific directories
    - Multiple merge strategies
    - Dry-run preview mode
    - Conflict detection
    - Pre-sync backup creation
    - Progress reporting

    Example:
        >>> from ai_asst_mgr.vendors import VendorRegistry
        >>> from ai_asst_mgr.operations.backup import BackupManager
        >>> registry = VendorRegistry()
        >>> backup_mgr = BackupManager(Path("~/.aim/backups"))
        >>> sync_mgr = SyncManager(backup_mgr)
        >>> preview = sync_mgr.preview_sync(
        ...     "https://github.com/user/config.git",
        ...     registry.get_vendor("claude"),
        ... )
    """

    # Directories to sync per vendor
    VENDOR_SYNC_DIRS: ClassVar[dict[str, list[str]]] = {
        "claude": ["agents", "skills", "commands", "hooks", "templates"],
        "gemini": ["mcp_servers"],
        "openai": ["profiles", "mcp_servers"],
    }

    # Files to sync per vendor
    VENDOR_SYNC_FILES: ClassVar[dict[str, list[str]]] = {
        "claude": ["settings.json"],
        "gemini": ["GEMINI.md", "settings.json"],
        "openai": ["AGENTS.md", "config.toml"],
    }

    def __init__(self, backup_manager: BackupManager | None = None) -> None:
        """Initialize the sync manager.

        Args:
            backup_manager: Optional BackupManager for creating pre-sync backups.
        """
        self._backup_manager = backup_manager

    def preview_sync(
        self,
        repo_url: str,
        adapter: VendorAdapter,
        branch: str = "main",
    ) -> SyncPreview | None:
        """Preview what a sync operation would do.

        Args:
            repo_url: URL of the Git repository.
            adapter: The vendor adapter to sync to.
            branch: Git branch to sync from.

        Returns:
            SyncPreview with details, or None if preview fails.
        """
        vendor_id = adapter.info.vendor_id
        config_dir = adapter.info.config_dir
        temp_dir = config_dir.parent / f"temp_sync_preview_{vendor_id}"

        try:
            # Clone repository
            if not self._clone_repo(repo_url, temp_dir, branch):
                return None

            # Create preview context
            ctx = _PreviewContext(
                vendor_id=vendor_id,
                temp_dir=temp_dir,
                config_dir=config_dir,
                files_to_add=[],
                files_to_modify=[],
                files_to_delete=[],
                conflicts=[],
            )

            # Check directories and files
            self._preview_directories(ctx)
            self._preview_files(ctx)

            return SyncPreview(
                vendor_id=vendor_id,
                repo_url=repo_url,
                branch=branch,
                files_to_add=ctx.files_to_add,
                files_to_modify=ctx.files_to_modify,
                files_to_delete=ctx.files_to_delete,
                conflicts=ctx.conflicts,
            )

        except Exception:
            return None

        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def _preview_directories(self, ctx: _PreviewContext) -> None:
        """Preview directory changes for sync operation.

        Args:
            ctx: Preview context with paths and result lists.
        """
        sync_dirs = self.VENDOR_SYNC_DIRS.get(ctx.vendor_id, [])
        for dirname in sync_dirs:
            remote_dir = ctx.temp_dir / dirname
            local_dir = ctx.config_dir / dirname

            if remote_dir.exists():
                self._preview_remote_files(remote_dir, ctx)

            # Check for files that would be deleted in REPLACE mode
            if local_dir.exists():
                self._preview_local_deletions(local_dir, ctx)

    def _preview_remote_files(self, remote_dir: Path, ctx: _PreviewContext) -> None:
        """Preview changes for remote files in a directory.

        Args:
            remote_dir: Remote directory to check.
            ctx: Preview context with paths and result lists.
        """
        for remote_file in remote_dir.rglob("*"):
            if remote_file.is_file():
                rel_path = remote_file.relative_to(ctx.temp_dir)
                local_file = ctx.config_dir / rel_path

                if local_file.exists():
                    # Check if content differs
                    if self._files_differ(local_file, remote_file):
                        ctx.files_to_modify.append(str(rel_path))
                        ctx.conflicts.append(str(rel_path))
                else:
                    ctx.files_to_add.append(str(rel_path))

    def _preview_local_deletions(self, local_dir: Path, ctx: _PreviewContext) -> None:
        """Preview local files that would be deleted in REPLACE mode.

        Args:
            local_dir: Local directory to check.
            ctx: Preview context with paths and result lists.
        """
        for local_file in local_dir.rglob("*"):
            if local_file.is_file():
                rel_path = local_file.relative_to(ctx.config_dir)
                remote_file = ctx.temp_dir / rel_path
                if not remote_file.exists():
                    ctx.files_to_delete.append(str(rel_path))

    def _preview_files(self, ctx: _PreviewContext) -> None:
        """Preview individual file changes for sync operation.

        Args:
            ctx: Preview context with paths and result lists.
        """
        sync_files = self.VENDOR_SYNC_FILES.get(ctx.vendor_id, [])
        for filename in sync_files:
            remote_file = ctx.temp_dir / filename
            local_file = ctx.config_dir / filename

            if remote_file.exists():
                if local_file.exists():
                    if self._files_differ(local_file, remote_file):
                        ctx.files_to_modify.append(filename)
                        ctx.conflicts.append(filename)
                else:
                    ctx.files_to_add.append(filename)

    def sync_vendor(
        self,
        repo_url: str,
        adapter: VendorAdapter,
        branch: str = "main",
        strategy: MergeStrategy = MergeStrategy.KEEP_REMOTE,
        create_backup: bool = True,
        progress_callback: Callable[[str], None] | None = None,
    ) -> SyncResult:
        """Sync a vendor's configuration from a Git repository.

        Args:
            repo_url: URL of the Git repository.
            adapter: The vendor adapter to sync to.
            branch: Git branch to sync from.
            strategy: Merge strategy to use.
            create_backup: Whether to create a backup before syncing.
            progress_callback: Optional callback for progress updates.

        Returns:
            SyncResult with success status and details.
        """
        config = SyncConfig(
            repo_url=repo_url,
            adapter=adapter,
            branch=branch,
            strategy=strategy,
            create_backup=create_backup,
            progress_callback=progress_callback,
        )
        return self._execute_sync(config)

    def _execute_sync(self, config: SyncConfig) -> SyncResult:
        """Execute sync operation with given configuration.

        Args:
            config: Sync configuration parameters.

        Returns:
            SyncResult with success status and details.
        """
        start_time = datetime.now(tz=UTC)
        vendor_id = config.adapter.info.vendor_id
        config_dir = config.adapter.info.config_dir
        temp_dir = config_dir.parent / f"temp_sync_{vendor_id}"

        def report(msg: str) -> None:
            if config.progress_callback:
                config.progress_callback(msg)

        try:
            report(f"Starting sync for {config.adapter.info.name}...")
            report(f"Repository: {config.repo_url}")
            report(f"Branch: {config.branch}")
            report(f"Strategy: {config.strategy.value}")

            # Create pre-sync backup if requested
            pre_sync_backup = self._create_backup_if_needed(config, report)

            # Clone repository
            report("Cloning repository...")
            if not self._clone_repo(config.repo_url, temp_dir, config.branch):
                return SyncResult(
                    success=False,
                    error="Failed to clone repository",
                    pre_sync_backup=pre_sync_backup,
                    duration_seconds=self._calc_duration(start_time),
                )

            # Ensure config directory exists
            config_dir.mkdir(parents=True, exist_ok=True)

            # Perform sync
            files_added, files_modified, files_deleted = self._perform_sync(
                vendor_id, temp_dir, config_dir, config.strategy, report
            )

            duration = self._calc_duration(start_time)
            total_synced = files_added + files_modified

            report(f"Sync complete: {total_synced} files synced in {duration:.1f}s")

            return SyncResult(
                success=True,
                files_synced=total_synced,
                files_added=files_added,
                files_modified=files_modified,
                files_deleted=files_deleted,
                pre_sync_backup=pre_sync_backup,
                duration_seconds=duration,
            )

        except Exception as e:
            return SyncResult(
                success=False,
                error=str(e),
                pre_sync_backup=None,
                duration_seconds=self._calc_duration(start_time),
            )

        finally:
            # Clean up temp directory
            if temp_dir.exists():
                shutil.rmtree(temp_dir)

    def _create_backup_if_needed(
        self, config: SyncConfig, report: Callable[[str], None]
    ) -> Path | None:
        """Create pre-sync backup if requested.

        Args:
            config: Sync configuration parameters.
            report: Progress reporting callback.

        Returns:
            Path to backup file if created, None otherwise.
        """
        if not config.create_backup:
            return None

        if not self._backup_manager:
            return None

        if not config.adapter.is_installed():
            return None

        report("Creating pre-sync backup...")
        backup_result = self._backup_manager.backup_vendor(config.adapter)
        if backup_result.success and backup_result.metadata:
            backup_path = backup_result.metadata.backup_path
            report(f"Backup created: {backup_path}")
            return backup_path

        return None

    def _perform_sync(
        self,
        vendor_id: str,
        temp_dir: Path,
        config_dir: Path,
        strategy: MergeStrategy,
        report: Callable[[str], None],
    ) -> tuple[int, int, int]:
        """Perform the actual file synchronization.

        Args:
            vendor_id: Vendor identifier.
            temp_dir: Temporary directory with remote files.
            config_dir: Local configuration directory.
            strategy: Merge strategy to use.
            report: Progress reporting callback.

        Returns:
            Tuple of (files_added, files_modified, files_deleted).
        """
        files_added = 0
        files_modified = 0
        files_deleted = 0

        # Sync directories
        report("Syncing directories...")
        added, modified, deleted = self._sync_directories(
            vendor_id, temp_dir, config_dir, strategy, report
        )
        files_added += added
        files_modified += modified
        files_deleted += deleted

        # Sync files
        report("Syncing files...")
        added, modified = self._sync_files(vendor_id, temp_dir, config_dir, strategy, report)
        files_added += added
        files_modified += modified

        return files_added, files_modified, files_deleted

    def _sync_directories(
        self,
        vendor_id: str,
        temp_dir: Path,
        config_dir: Path,
        strategy: MergeStrategy,
        report: Callable[[str], None],
    ) -> tuple[int, int, int]:
        """Sync all directories for a vendor.

        Args:
            vendor_id: Vendor identifier.
            temp_dir: Temporary directory with remote files.
            config_dir: Local configuration directory.
            strategy: Merge strategy to use.
            report: Progress reporting callback.

        Returns:
            Tuple of (files_added, files_modified, files_deleted).
        """
        files_added = 0
        files_modified = 0
        files_deleted = 0

        sync_dirs = self.VENDOR_SYNC_DIRS.get(vendor_id, [])
        for dirname in sync_dirs:
            remote_dir = temp_dir / dirname
            local_dir = config_dir / dirname

            if remote_dir.exists():
                added, modified, deleted = self._sync_directory(remote_dir, local_dir, strategy)
                files_added += added
                files_modified += modified
                files_deleted += deleted
                report(f"  {dirname}/: +{added} ~{modified} -{deleted}")

        return files_added, files_modified, files_deleted

    def _sync_files(
        self,
        vendor_id: str,
        temp_dir: Path,
        config_dir: Path,
        strategy: MergeStrategy,
        report: Callable[[str], None],
    ) -> tuple[int, int]:
        """Sync individual files for a vendor.

        Args:
            vendor_id: Vendor identifier.
            temp_dir: Temporary directory with remote files.
            config_dir: Local configuration directory.
            strategy: Merge strategy to use.
            report: Progress reporting callback.

        Returns:
            Tuple of (files_added, files_modified).
        """
        files_added = 0
        files_modified = 0

        sync_files = self.VENDOR_SYNC_FILES.get(vendor_id, [])
        for filename in sync_files:
            remote_file = temp_dir / filename
            local_file = config_dir / filename

            if remote_file.exists():
                added, modified = self._sync_file(remote_file, local_file, strategy)
                files_added += added
                files_modified += modified
                if added or modified:
                    report(f"  {filename}: {'added' if added else 'modified'}")

        return files_added, files_modified

    def sync_all_vendors(
        self,
        repo_url: str,
        adapters: dict[str, VendorAdapter],
        branch: str = "main",
        strategy: MergeStrategy = MergeStrategy.KEEP_REMOTE,
        progress_callback: Callable[[str], None] | None = None,
        *,
        create_backup: bool = True,
    ) -> dict[str, SyncResult]:
        """Sync all vendors from a Git repository.

        Args:
            repo_url: URL of the Git repository.
            adapters: Dictionary of vendor_id to adapter instances.
            branch: Git branch to sync from.
            strategy: Merge strategy to use.
            progress_callback: Optional callback for progress updates.
            create_backup: Whether to create a pre-sync backup.

        Returns:
            Dictionary mapping vendor_id to SyncResult.
        """
        results: dict[str, SyncResult] = {}

        def report(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        report(f"Starting sync of {len(adapters)} vendor(s)...")

        for vendor_id, adapter in adapters.items():
            report(f"\n[{vendor_id}] Syncing {adapter.info.name}...")
            result = self.sync_vendor(
                repo_url,
                adapter,
                branch,
                strategy,
                create_backup=create_backup,
                progress_callback=progress_callback,
            )
            results[vendor_id] = result

        successful = sum(1 for r in results.values() if r.success)
        report(f"\nSync complete: {successful}/{len(adapters)} succeeded")

        return results

    def _clone_repo(self, repo_url: str, dest_dir: Path, branch: str) -> bool:
        """Clone a Git repository securely.

        Uses the git_clone utility which validates inputs to prevent
        command injection and uses absolute paths to the git executable.
        """
        # Remove existing temp directory
        if dest_dir.exists():
            shutil.rmtree(dest_dir)

        return git_clone(repo_url, dest_dir, branch)

    def _files_differ(self, file1: Path, file2: Path) -> bool:
        """Check if two files have different content."""
        try:
            return file1.read_bytes() != file2.read_bytes()
        except OSError:
            return True

    def _sync_directory(
        self,
        remote_dir: Path,
        local_dir: Path,
        strategy: MergeStrategy,
    ) -> tuple[int, int, int]:
        """Sync a directory using the specified strategy.

        Returns:
            Tuple of (files_added, files_modified, files_deleted).
        """
        added = 0
        modified = 0
        deleted = 0

        if strategy == MergeStrategy.REPLACE:
            # Remove local directory and replace with remote
            if local_dir.exists():
                old_files = list(local_dir.rglob("*"))
                deleted = len([f for f in old_files if f.is_file()])
                shutil.rmtree(local_dir)

            shutil.copytree(remote_dir, local_dir)
            added = len(list(local_dir.rglob("*")))
            return added, 0, deleted

        # For other strategies, sync file by file
        local_dir.mkdir(parents=True, exist_ok=True)

        for remote_file in remote_dir.rglob("*"):
            if remote_file.is_file():
                rel_path = remote_file.relative_to(remote_dir)
                local_file = local_dir / rel_path

                local_file.parent.mkdir(parents=True, exist_ok=True)
                a, m = self._sync_file(remote_file, local_file, strategy)
                added += a
                modified += m

        return added, modified, deleted

    def _sync_file(
        self,
        remote_file: Path,
        local_file: Path,
        strategy: MergeStrategy,
    ) -> tuple[int, int]:
        """Sync a single file using the specified strategy.

        Returns:
            Tuple of (added, modified) counts (0 or 1 each).
        """
        file_exists = local_file.exists()

        if strategy == MergeStrategy.KEEP_LOCAL and file_exists:
            return 0, 0

        if strategy in (MergeStrategy.KEEP_REMOTE, MergeStrategy.REPLACE):
            local_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(remote_file, local_file)
            return (0, 1) if file_exists else (1, 0)

        if strategy == MergeStrategy.MERGE:
            if not file_exists:
                local_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(remote_file, local_file)
                return 1, 0
            if self._files_differ(local_file, remote_file):
                # Create .remote version for manual merge
                remote_version = local_file.with_suffix(local_file.suffix + ".remote")
                shutil.copy2(remote_file, remote_version)
                return 0, 1

        return 0, 0

    def _calc_duration(self, start_time: datetime) -> float:
        """Calculate duration in seconds from start time."""
        return (datetime.now(tz=UTC) - start_time).total_seconds()
