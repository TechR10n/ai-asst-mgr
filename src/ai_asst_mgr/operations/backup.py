"""Backup operations for AI assistant configurations.

This module provides high-level backup functionality including retention policies,
integrity verification, and progress reporting across all vendor configurations.
"""

from __future__ import annotations

import hashlib
import json
import tarfile
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Callable

    from ai_asst_mgr.adapters.base import VendorAdapter


@dataclass
class BackupMetadata:
    """Metadata for a backup archive.

    Attributes:
        vendor_id: Identifier of the vendor that was backed up.
        timestamp: When the backup was created.
        backup_path: Path to the backup archive.
        size_bytes: Size of the backup in bytes.
        checksum: SHA256 checksum of the backup file.
        file_count: Number of files in the backup.
        config_dir: Original config directory that was backed up.
    """

    vendor_id: str
    timestamp: datetime
    backup_path: Path
    size_bytes: int
    checksum: str
    file_count: int
    config_dir: str


@dataclass
class BackupResult:
    """Result of a backup operation.

    Attributes:
        success: Whether the backup succeeded.
        metadata: Backup metadata if successful.
        error: Error message if failed.
        duration_seconds: How long the backup took.
    """

    success: bool
    metadata: BackupMetadata | None = None
    error: str | None = None
    duration_seconds: float = 0.0


@dataclass
class BackupSummary:
    """Summary of a multi-vendor backup operation.

    Attributes:
        total_vendors: Number of vendors attempted.
        successful: Number of successful backups.
        failed: Number of failed backups.
        results: Individual results per vendor.
        total_size_bytes: Combined size of all backups.
        duration_seconds: Total duration of backup operation.
    """

    total_vendors: int
    successful: int
    failed: int
    results: dict[str, BackupResult] = field(default_factory=dict)
    total_size_bytes: int = 0
    duration_seconds: float = 0.0


class BackupManager:
    """Manages backup operations for AI assistant configurations.

    The BackupManager provides high-level backup functionality including:
    - Single and multi-vendor backups
    - Retention policy enforcement
    - Backup verification and integrity checks
    - Progress reporting via callbacks
    - Backup listing and metadata retrieval

    Example:
        >>> from ai_asst_mgr.vendors import VendorRegistry
        >>> registry = VendorRegistry()
        >>> manager = BackupManager(Path("~/.aim/backups"))
        >>> result = manager.backup_vendor(registry.get_vendor("claude"))
        >>> if result.success:
        ...     print(f"Backup created: {result.metadata.backup_path}")
    """

    DEFAULT_RETENTION_COUNT = 5
    METADATA_FILENAME = "backup_manifest.json"

    def __init__(
        self,
        backup_dir: Path,
        retention_count: int = DEFAULT_RETENTION_COUNT,
    ) -> None:
        """Initialize the backup manager.

        Args:
            backup_dir: Directory where backups will be stored.
            retention_count: Number of backups to keep per vendor.
        """
        self._backup_dir = Path(backup_dir).expanduser()
        self._retention_count = retention_count

    @property
    def backup_dir(self) -> Path:
        """Get the backup directory path."""
        return self._backup_dir

    @property
    def retention_count(self) -> int:
        """Get the retention count setting."""
        return self._retention_count

    def backup_vendor(
        self,
        adapter: VendorAdapter,
        progress_callback: Callable[[str], None] | None = None,
    ) -> BackupResult:
        """Create a backup of a single vendor's configuration.

        Args:
            adapter: The vendor adapter to backup.
            progress_callback: Optional callback for progress updates.

        Returns:
            BackupResult with success status and metadata or error.
        """
        start_time = datetime.now(tz=UTC)
        vendor_id = adapter.info.vendor_id

        def report(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        try:
            report(f"Starting backup for {adapter.info.name}...")

            # Ensure backup directory exists
            vendor_backup_dir = self._backup_dir / vendor_id
            vendor_backup_dir.mkdir(parents=True, exist_ok=True)

            # Check if vendor is installed
            if not adapter.is_installed():
                return BackupResult(
                    success=False,
                    error=f"{adapter.info.name} is not installed",
                    duration_seconds=self._calc_duration(start_time),
                )

            report("Creating backup archive...")

            # Use adapter's backup method
            backup_path = adapter.backup(vendor_backup_dir)

            report("Calculating checksum...")

            # Calculate metadata
            checksum = self._calculate_checksum(backup_path)
            size_bytes = backup_path.stat().st_size
            file_count = self._count_files_in_archive(backup_path)

            metadata = BackupMetadata(
                vendor_id=vendor_id,
                timestamp=start_time,
                backup_path=backup_path,
                size_bytes=size_bytes,
                checksum=checksum,
                file_count=file_count,
                config_dir=str(adapter.info.config_dir),
            )

            # Save metadata
            self._save_metadata(metadata)

            report("Applying retention policy...")

            # Apply retention policy
            self._apply_retention_policy(vendor_id)

            duration = self._calc_duration(start_time)
            report(f"Backup complete in {duration:.1f}s")

            return BackupResult(
                success=True,
                metadata=metadata,
                duration_seconds=duration,
            )

        except Exception as e:
            return BackupResult(
                success=False,
                error=str(e),
                duration_seconds=self._calc_duration(start_time),
            )

    def backup_all_vendors(
        self,
        adapters: dict[str, VendorAdapter],
        progress_callback: Callable[[str], None] | None = None,
    ) -> BackupSummary:
        """Create backups of all vendor configurations.

        Args:
            adapters: Dictionary of vendor_id to adapter instances.
            progress_callback: Optional callback for progress updates.

        Returns:
            BackupSummary with overall results and per-vendor details.
        """
        start_time = datetime.now(tz=UTC)
        results: dict[str, BackupResult] = {}
        total_size = 0
        successful = 0

        def report(msg: str) -> None:
            if progress_callback:
                progress_callback(msg)

        report(f"Starting backup of {len(adapters)} vendor(s)...")

        for vendor_id, adapter in adapters.items():
            report(f"\n[{vendor_id}] Backing up {adapter.info.name}...")
            result = self.backup_vendor(adapter, progress_callback)
            results[vendor_id] = result

            if result.success and result.metadata:
                successful += 1
                total_size += result.metadata.size_bytes

        duration = self._calc_duration(start_time)
        report(f"\nBackup complete: {successful}/{len(adapters)} succeeded")

        return BackupSummary(
            total_vendors=len(adapters),
            successful=successful,
            failed=len(adapters) - successful,
            results=results,
            total_size_bytes=total_size,
            duration_seconds=duration,
        )

    def list_backups(self, vendor_id: str | None = None) -> list[BackupMetadata]:
        """List available backups.

        Args:
            vendor_id: Optional vendor ID to filter by. If None, lists all.

        Returns:
            List of BackupMetadata objects sorted by timestamp (newest first).
        """
        backups: list[BackupMetadata] = []

        if vendor_id:
            vendor_dirs = [self._backup_dir / vendor_id]
        else:
            vendor_dirs = (
                [d for d in self._backup_dir.iterdir() if d.is_dir()]
                if self._backup_dir.exists()
                else []
            )

        for vendor_dir in vendor_dirs:
            if not vendor_dir.exists():
                continue

            manifest_path = vendor_dir / self.METADATA_FILENAME
            if manifest_path.exists():
                try:
                    manifest = self._load_manifest(manifest_path)
                    for entry in manifest.get("backups", []):
                        backup_path = Path(entry["backup_path"])
                        if backup_path.exists():
                            backups.append(
                                BackupMetadata(
                                    vendor_id=entry["vendor_id"],
                                    timestamp=datetime.fromisoformat(entry["timestamp"]),
                                    backup_path=backup_path,
                                    size_bytes=entry["size_bytes"],
                                    checksum=entry["checksum"],
                                    file_count=entry["file_count"],
                                    config_dir=entry["config_dir"],
                                )
                            )
                except (json.JSONDecodeError, KeyError, OSError):
                    continue

        # Sort by timestamp, newest first
        backups.sort(key=lambda b: b.timestamp, reverse=True)
        return backups

    def get_latest_backup(self, vendor_id: str) -> BackupMetadata | None:
        """Get the most recent backup for a vendor.

        Args:
            vendor_id: The vendor ID to get backup for.

        Returns:
            BackupMetadata for the latest backup, or None if no backups exist.
        """
        backups = self.list_backups(vendor_id)
        return backups[0] if backups else None

    def verify_backup(self, backup_path: Path) -> tuple[bool, str]:
        """Verify the integrity of a backup archive.

        Args:
            backup_path: Path to the backup archive.

        Returns:
            Tuple of (is_valid, message).
        """
        if not backup_path.exists():
            return False, f"Backup file not found: {backup_path}"

        # Check if it's a valid tar.gz
        if not tarfile.is_tarfile(backup_path):
            return False, "Invalid archive format (not a tar file)"

        try:
            # Try to read the archive
            with tarfile.open(backup_path, "r:gz") as tar:
                members = tar.getmembers()
                if not members:
                    return False, "Archive is empty"

            # Verify checksum if we have metadata
            stored_checksum = self._get_stored_checksum(backup_path)
            if stored_checksum:
                actual_checksum = self._calculate_checksum(backup_path)
                if stored_checksum != actual_checksum:
                    return False, "Checksum mismatch - backup may be corrupted"

            return True, f"Backup valid ({len(members)} files)"

        except tarfile.TarError as e:
            return False, f"Archive error: {e}"

    def delete_backup(self, backup_path: Path) -> bool:
        """Delete a backup archive.

        Args:
            backup_path: Path to the backup to delete.

        Returns:
            True if deleted, False if not found.
        """
        if not backup_path.exists():
            return False

        backup_path.unlink()

        # Update manifest
        vendor_id = backup_path.parent.name
        self._remove_from_manifest(vendor_id, backup_path)

        return True

    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with file_path.open("rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()

    def _count_files_in_archive(self, archive_path: Path) -> int:
        """Count the number of files in a tar archive."""
        try:
            with tarfile.open(archive_path, "r:gz") as tar:
                return len([m for m in tar.getmembers() if m.isfile()])
        except tarfile.TarError:
            return 0

    def _save_metadata(self, metadata: BackupMetadata) -> None:
        """Save backup metadata to manifest file."""
        manifest_path = self._backup_dir / metadata.vendor_id / self.METADATA_FILENAME

        manifest = (
            self._load_manifest(manifest_path)
            if manifest_path.exists()
            else {
                "vendor_id": metadata.vendor_id,
                "backups": [],
            }
        )

        manifest["backups"].append(
            {
                "vendor_id": metadata.vendor_id,
                "timestamp": metadata.timestamp.isoformat(),
                "backup_path": str(metadata.backup_path),
                "size_bytes": metadata.size_bytes,
                "checksum": metadata.checksum,
                "file_count": metadata.file_count,
                "config_dir": metadata.config_dir,
            }
        )

        with manifest_path.open("w") as f:
            json.dump(manifest, f, indent=2)

    def _load_manifest(self, manifest_path: Path) -> dict[str, Any]:
        """Load manifest file."""
        with manifest_path.open() as f:
            result = json.load(f)
            if isinstance(result, dict):
                return result
            return {"backups": []}

    def _apply_retention_policy(self, vendor_id: str) -> None:
        """Apply retention policy to vendor backups."""
        backups = self.list_backups(vendor_id)

        if len(backups) <= self._retention_count:
            return

        # Delete oldest backups beyond retention count
        for backup in backups[self._retention_count :]:
            self.delete_backup(backup.backup_path)

    def _get_stored_checksum(self, backup_path: Path) -> str | None:
        """Get stored checksum for a backup from manifest."""
        vendor_id = backup_path.parent.name
        manifest_path = self._backup_dir / vendor_id / self.METADATA_FILENAME

        if not manifest_path.exists():
            return None

        try:
            manifest = self._load_manifest(manifest_path)
            for entry in manifest.get("backups", []):
                if Path(entry["backup_path"]) == backup_path:
                    checksum = entry.get("checksum")
                    return str(checksum) if checksum is not None else None
        except (json.JSONDecodeError, KeyError, OSError):
            pass

        return None

    def _remove_from_manifest(self, vendor_id: str, backup_path: Path) -> None:
        """Remove a backup entry from the manifest."""
        manifest_path = self._backup_dir / vendor_id / self.METADATA_FILENAME

        if not manifest_path.exists():
            return

        try:
            manifest = self._load_manifest(manifest_path)
            manifest["backups"] = [
                entry
                for entry in manifest.get("backups", [])
                if Path(entry["backup_path"]) != backup_path
            ]
            with manifest_path.open("w") as f:
                json.dump(manifest, f, indent=2)
        except (json.JSONDecodeError, OSError):
            pass

    def _calc_duration(self, start_time: datetime) -> float:
        """Calculate duration in seconds from start time."""
        return (datetime.now(tz=UTC) - start_time).total_seconds()
