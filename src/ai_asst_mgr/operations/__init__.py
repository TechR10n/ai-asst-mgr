"""Core operations for AI assistant management.

This package provides high-level operations such as backup, restore,
sync, audit, and coaching functionality.
"""

from ai_asst_mgr.operations.backup import (
    BackupManager,
    BackupMetadata,
    BackupResult,
    BackupSummary,
)
from ai_asst_mgr.operations.restore import (
    RestoreManager,
    RestorePreview,
    RestoreResult,
)
from ai_asst_mgr.operations.sync import (
    FileChange,
    MergeStrategy,
    SyncManager,
    SyncPreview,
    SyncResult,
)

__all__ = [
    "BackupManager",
    "BackupMetadata",
    "BackupResult",
    "BackupSummary",
    "FileChange",
    "MergeStrategy",
    "RestoreManager",
    "RestorePreview",
    "RestoreResult",
    "SyncManager",
    "SyncPreview",
    "SyncResult",
]
