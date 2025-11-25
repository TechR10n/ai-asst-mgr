"""Database module for vendor-agnostic data persistence.

This module provides SQLite-based storage for session tracking, analytics,
and configuration persistence across all supported AI assistant vendors.
"""

from __future__ import annotations

from ai_asst_mgr.database.manager import (
    AgentUsage,
    DailyUsage,
    DatabaseManager,
    VendorStats,
    WeeklyReview,
    WeekStats,
)
from ai_asst_mgr.database.migrations import (
    MigrationManager,
    MigrationResult,
    migrate_from_claude_sessions,
)
from ai_asst_mgr.database.schema import (
    SCHEMA_VERSION,
    SchemaManager,
    create_schema_sql,
)

__all__ = [
    "SCHEMA_VERSION",
    "AgentUsage",
    "DailyUsage",
    "DatabaseManager",
    "MigrationManager",
    "MigrationResult",
    "SchemaManager",
    "VendorStats",
    "WeekStats",
    "WeeklyReview",
    "create_schema_sql",
    "migrate_from_claude_sessions",
]
