"""Restore operations for AI assistant configurations.

This module provides high-level restore functionality including validation,
pre-restore backup creation, selective restore, and rollback capabilities.
"""

from __future__ import annotations

import shutil
import tarfile
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

    from ai_asst_mgr.adapters.base import VendorAdapter
    from ai_asst_mgr.operations.backup import BackupManager


@dataclass
class RestoreResult:
    """Result of a restore operation.

    Attributes:
        success: Whether the restore succeeded.
        restored_files: Number of files restored.
        pre_restore_backup: Path to pre-restore backup if created.
        error: Error message if failed.
        duration_seconds: How long the restore took.
    """

    success: bool
    restored_files: int = 0
    pre_restore_backup: Path | None = None
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class RestorePreview:
    """Preview of what a restore operation would do.

    Attributes:
        vendor_id: Vendor being restored.
        backup_timestamp: When the backup was created.
        files_to_restore: List of files that would be restored.
        files_to_overwrite: List of existing files that would be overwritten.
        directories_to_create: List of directories that would be created.
        estimated_size_bytes: Estimated size of restored files.
    """

    vendor_id: str
    backup_timestamp: datetime
    files_to_restore: list[str]
    files_to_overwrite: list[str]
    directories_to_create: list[str]
    estimated_size_bytes: int


class RestoreManager:
    """Manages restore operations for AI assistant configurations.

    The RestoreManager provides high-level restore functionality including:
    - Backup validation before restore
    - Pre-restore backup creation for rollback
    - Selective restore of specific directories
    - Dry-run/preview mode
    - Progress reporting via callbacks

    Example:
        >>> from ai_asst_mgr.vendors import VendorRegistry
        >>> from ai_asst_mgr.operations.backup import BackupManager
        >>> registry = VendorRegistry()
        >>> backup_mgr = BackupManager(Path("~/.aim/backups"))
        >>> restore_mgr = RestoreManager(backup_mgr)
        >>> preview = restore_mgr.preview_restore(backup_path, registry.get_vendor("claude"))
        >>> if preview:
        ...     result = restore_mgr.restore_vendor(backup_path, registry.get_vendor("claude"))
    """

    def __init__(self, backup_manager: BackupManager) -> None:
        """Initialize the restore manager.

        Args:
            backup_manager: BackupManager instance for creating pre-restore backups.
        """
        self._backup_manager = backup_manager

    def preview_restore(
        self,
        backup_path: Path,
        adapter: VendorAdapter,
    ) -> RestorePreview | None:
        """Preview what a restore operation would do.

        Args:
            backup_path: Path to the backup archive.
            adapter: The vendor adapter to restore to.

        Returns:
            RestorePreview with details, or None if backup is invalid.
        """
        if not backup_path.exists():
            return None

        if not tarfile.is_tarfile(backup_path):
            return None

        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                members = tar.getmembers()

                files_to_restore = [m.name for m in members if m.isfile()]
                dirs_to_restore = [m.name for m in members if m.isdir()]

                # Check which files would be overwritten
                config_dir = adapter.info.config_dir
                files_to_overwrite: list[str] = []

                for file_path in files_to_restore:
                    # Remove the vendor prefix from archive path
                    parts = Path(file_path).parts
                    if len(parts) > 1:
                        relative_path = Path(*parts[1:])
                        full_path = config_dir / relative_path
                        if full_path.exists():
                            files_to_overwrite.append(str(relative_path))

                # Check which directories would be created
                dirs_to_create: list[str] = []
                for dir_path in dirs_to_restore:
                    parts = Path(dir_path).parts
                    if len(parts) > 1:
                        relative_path = Path(*parts[1:])
                        full_path = config_dir / relative_path
                        if not full_path.exists():
                            dirs_to_create.append(str(relative_path))

                total_size = sum(m.size for m in members if m.isfile())

                # Get backup timestamp from metadata or file mtime
                backup_time = self._get_backup_timestamp(backup_path)

                return RestorePreview(
                    vendor_id=adapter.info.vendor_id,
                    backup_timestamp=backup_time,
                    files_to_restore=files_to_restore,
                    files_to_overwrite=files_to_overwrite,
                    directories_to_create=dirs_to_create,
                    estimated_size_bytes=total_size,
                )

        except tarfile.TarError:
            return None

    def restore_vendor(
        self,
        backup_path: Path,
        adapter: VendorAdapter,
        create_pre_restore_backup: bool = True,
        progress_callback: Callable[[str], None] | None = None,
    ) -> RestoreResult:
        """Restore a vendor's configuration from backup.

        Args:
            backup_path: Path to the backup archive.
            adapter: The vendor adapter to restore to.
            create_pre_restore_backup: Whether to backup current state first.
            progress_callback: Optional callback for progress updates.

        Returns:
            RestoreResult with success status and details.
        """
        start_time = datetime.now(tz=UTC)
        pre_restore_backup: Path | None = None

        def report(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        try:
            report(f"Starting restore for {adapter.info.name}...")

            # Validate backup
            report("Validating backup...")
            is_valid, message = self._backup_manager.verify_backup(backup_path)
            if not is_valid:
                return RestoreResult(
                    success=False,
                    error=f"Backup validation failed: {message}",
                    duration_seconds=self._calc_duration(start_time),
                )

            # Create pre-restore backup if requested
            if create_pre_restore_backup and adapter.is_installed():
                report("Creating pre-restore backup...")
                backup_result = self._backup_manager.backup_vendor(adapter)
                if backup_result.success and backup_result.metadata:
                    pre_restore_backup = backup_result.metadata.backup_path
                    report(f"Pre-restore backup created: {pre_restore_backup}")

            report("Restoring configuration...")

            # Use adapter's restore method
            adapter.restore(backup_path)

            # Count restored files
            restored_count = self._count_files_in_archive(backup_path)

            duration = self._calc_duration(start_time)
            report(f"Restore complete in {duration:.1f}s ({restored_count} files)")

            return RestoreResult(
                success=True,
                restored_files=restored_count,
                pre_restore_backup=pre_restore_backup,
                duration_seconds=duration,
            )

        except Exception as e:
            return RestoreResult(
                success=False,
                error=str(e),
                pre_restore_backup=pre_restore_backup,
                duration_seconds=self._calc_duration(start_time),
            )

    def restore_selective(
        self,
        backup_path: Path,
        adapter: VendorAdapter,
        directories: list[str],
        progress_callback: Callable[[str], None] | None = None,
    ) -> RestoreResult:
        """Selectively restore specific directories from a backup.

        Args:
            backup_path: Path to the backup archive.
            adapter: The vendor adapter to restore to.
            directories: List of directory names to restore (e.g., ["agents", "skills"]).
            progress_callback: Optional callback for progress updates.

        Returns:
            RestoreResult with success status and details.
        """
        start_time = datetime.now(tz=UTC)

        def report(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        try:
            report(f"Starting selective restore for {adapter.info.name}...")
            report(f"Directories to restore: {', '.join(directories)}")

            # Validate backup
            is_valid, message = self._backup_manager.verify_backup(backup_path)
            if not is_valid:
                return RestoreResult(
                    success=False,
                    error=f"Backup validation failed: {message}",
                    duration_seconds=self._calc_duration(start_time),
                )

            config_dir = adapter.info.config_dir
            restored_count = 0

            with tarfile.open(backup_path, "r:gz") as tar:
                # Get the archive prefix (vendor name)
                members = tar.getmembers()
                if not members:
                    return RestoreResult(
                        success=False,
                        error="Archive is empty",
                        duration_seconds=self._calc_duration(start_time),
                    )

                # Find the root directory in archive
                root_name = members[0].name.split("/")[0]

                for dirname in directories:
                    report(f"Restoring {dirname}/...")

                    # Find members matching this directory
                    prefix = f"{root_name}/{dirname}"
                    matching_members = [m for m in members if m.name.startswith(prefix)]

                    if not matching_members:
                        report(f"  No files found for {dirname}")
                        continue

                    # Create temp extraction directory
                    temp_dir = config_dir.parent / f"temp_restore_{adapter.info.vendor_id}"
                    temp_dir.mkdir(parents=True, exist_ok=True)

                    try:
                        # Extract matching files to temp
                        # nosec B202 - members are filtered from trusted backup archive
                        tar.extractall(temp_dir, members=matching_members)  # nosec B202

                        # Move to correct location
                        src_dir = temp_dir / root_name / dirname
                        dest_dir = config_dir / dirname

                        if src_dir.exists():
                            if dest_dir.exists():
                                shutil.rmtree(dest_dir)
                            shutil.move(str(src_dir), str(dest_dir))
                            restored_count += len([m for m in matching_members if m.isfile()])
                            report(f"  Restored {dirname}/")

                    finally:
                        # Clean up temp directory
                        if temp_dir.exists():
                            shutil.rmtree(temp_dir)

            duration = self._calc_duration(start_time)
            report(f"Selective restore complete ({restored_count} files)")

            return RestoreResult(
                success=True,
                restored_files=restored_count,
                duration_seconds=duration,
            )

        except Exception as e:
            return RestoreResult(
                success=False,
                error=str(e),
                duration_seconds=self._calc_duration(start_time),
            )

    def rollback(
        self,
        pre_restore_backup: Path,
        adapter: VendorAdapter,
        progress_callback: Callable[[str], None] | None = None,
    ) -> RestoreResult:
        """Rollback to a pre-restore backup state.

        Args:
            pre_restore_backup: Path to the pre-restore backup.
            adapter: The vendor adapter to rollback.
            progress_callback: Optional callback for progress updates.

        Returns:
            RestoreResult with rollback status.
        """

        def report(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        report("Rolling back to pre-restore state...")

        # Use restore_vendor without creating another pre-restore backup
        return self.restore_vendor(
            pre_restore_backup,
            adapter,
            create_pre_restore_backup=False,
            progress_callback=progress_callback,
        )

    def get_restorable_directories(self, backup_path: Path) -> list[str]:
        """Get list of directories available for selective restore.

        Args:
            backup_path: Path to the backup archive.

        Returns:
            List of top-level directory names in the backup.
        """
        if not backup_path.exists() or not tarfile.is_tarfile(backup_path):
            return []

        try:
            with tarfile.open(backup_path, "r:gz") as tar:
                members = tar.getmembers()

                # Find root directory
                if not members:
                    return []

                root_name = members[0].name.split("/")[0]
                root_prefix = f"{root_name}/"

                # Get unique top-level directories
                directories: set[str] = set()
                for member in members:
                    if member.name.startswith(root_prefix):
                        # Get the directory name after root
                        relative = member.name[len(root_prefix) :]
                        if "/" in relative:
                            dirname = relative.split("/")[0]
                            if dirname:
                                directories.add(dirname)

                return sorted(directories)

        except tarfile.TarError:
            return []

    def _get_backup_timestamp(self, backup_path: Path) -> datetime:
        """Get the timestamp of a backup from metadata or file mtime."""
        # Try to get from backup manager's metadata
        backups = self._backup_manager.list_backups()
        for backup in backups:
            if backup.backup_path == backup_path:
                return backup.timestamp

        # Fall back to file modification time
        return datetime.fromtimestamp(backup_path.stat().st_mtime, tz=UTC)

    def _count_files_in_archive(self, archive_path: Path) -> int:
        """Count the number of files in a tar archive."""
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                return len([m for m in tar.getmembers() if m.isfile()])
        except tarfile.TarError:
            return 0

    def _calc_duration(self, start_time: datetime) -> float:
        """Calculate duration in seconds from start time."""
        return (datetime.now(tz=UTC) - start_time).total_seconds()
