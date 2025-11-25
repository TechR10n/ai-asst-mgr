"""Database migration tools for legacy data.

This module provides utilities for migrating existing session data
from vendor-specific databases to the unified schema.
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from ai_asst_mgr.database.schema import SchemaManager

if TYPE_CHECKING:
    from pathlib import Path


@dataclass
class MigrationResult:
    """Result of a migration operation."""

    success: bool
    sessions_migrated: int
    events_migrated: int
    errors: list[str]
    backup_path: Path | None


class MigrationManager:
    """Manages database migrations from legacy formats.

    This class handles migrating existing session data from vendor-specific
    databases (like Claude's sessions.db) to the unified schema.
    """

    def __init__(self, target_db_path: Path) -> None:
        """Initialize the migration manager.

        Args:
            target_db_path: Path to the target unified database.
        """
        self.target_db_path = target_db_path
        self._schema_manager = SchemaManager(target_db_path)

    def migrate_from_claude_sessions(
        self,
        source_db_path: Path,
        *,
        create_backup: bool = True,
    ) -> MigrationResult:
        """Migrate sessions from Claude's sessions.db to unified schema.

        Args:
            source_db_path: Path to the Claude sessions.db file.
            create_backup: Whether to create a backup of the source.

        Returns:
            MigrationResult with migration statistics.
        """
        errors: list[str] = []
        backup_path: Path | None = None

        if not source_db_path.exists():
            return MigrationResult(
                success=False,
                sessions_migrated=0,
                events_migrated=0,
                errors=["Source database does not exist"],
                backup_path=None,
            )

        if create_backup:
            backup_path = self._create_backup(source_db_path)

        self._schema_manager.initialize()

        sessions_count = 0
        events_count = 0

        try:
            with sqlite3.connect(source_db_path) as source_conn:
                source_conn.row_factory = sqlite3.Row

                sessions_count = self._migrate_sessions(source_conn, errors)
                events_count = self._migrate_events(source_conn, errors)

        except sqlite3.Error as e:
            errors.append(f"Database error: {e}")
            return MigrationResult(
                success=False,
                sessions_migrated=sessions_count,
                events_migrated=events_count,
                errors=errors,
                backup_path=backup_path,
            )

        return MigrationResult(
            success=len(errors) == 0,
            sessions_migrated=sessions_count,
            events_migrated=events_count,
            errors=errors,
            backup_path=backup_path,
        )

    def _create_backup(self, source_path: Path) -> Path:
        """Create a backup of the source database.

        Args:
            source_path: Path to the source database.

        Returns:
            Path to the backup file.
        """
        timestamp = datetime.now(tz=UTC).strftime("%Y%m%d_%H%M%S")
        backup_path = source_path.with_suffix(f".backup_{timestamp}.db")
        shutil.copy2(source_path, backup_path)
        return backup_path

    def _migrate_sessions(self, source_conn: sqlite3.Connection, errors: list[str]) -> int:
        """Migrate sessions from source to target database.

        Args:
            source_conn: Connection to source database.
            errors: List to append errors to.

        Returns:
            Number of sessions migrated.
        """
        count = 0

        try:
            cursor = source_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'"
            )
            if not cursor.fetchone():
                return 0

            cursor = source_conn.execute("SELECT * FROM sessions")
            rows = cursor.fetchall()

            with sqlite3.connect(self.target_db_path) as target_conn:
                for row in rows:
                    try:
                        self._insert_session(target_conn, dict(row))
                        count += 1
                    except sqlite3.Error as e:
                        errors.append(f"Failed to migrate session: {e}")

                target_conn.commit()

        except sqlite3.Error as e:
            errors.append(f"Error reading sessions: {e}")

        return count

    def _migrate_events(self, source_conn: sqlite3.Connection, errors: list[str]) -> int:
        """Migrate events from source to target database.

        Args:
            source_conn: Connection to source database.
            errors: List to append errors to.

        Returns:
            Number of events migrated.
        """
        count = 0

        try:
            cursor = source_conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='events'"
            )
            if not cursor.fetchone():
                return 0

            cursor = source_conn.execute("SELECT * FROM events")
            rows = cursor.fetchall()

            with sqlite3.connect(self.target_db_path) as target_conn:
                for row in rows:
                    try:
                        self._insert_event(target_conn, dict(row))
                        count += 1
                    except sqlite3.Error as e:
                        errors.append(f"Failed to migrate event: {e}")

                target_conn.commit()

        except sqlite3.Error as e:
            errors.append(f"Error reading events: {e}")

        return count

    def _insert_session(self, conn: sqlite3.Connection, session_data: dict[str, object]) -> None:
        """Insert a session into the target database.

        Args:
            conn: Connection to target database.
            session_data: Session data dictionary.
        """
        session_id = session_data.get("session_id") or session_data.get("id")
        start_time = session_data.get("start_time") or session_data.get("created_at")

        conn.execute(
            """
            INSERT OR IGNORE INTO sessions (
                session_id, vendor_id, project_path, start_time,
                end_time, duration_seconds, tool_calls_count,
                messages_count, errors_count
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                str(session_id),
                "claude",
                session_data.get("project_path"),
                start_time,
                session_data.get("end_time"),
                session_data.get("duration_seconds", 0),
                session_data.get("tool_calls_count", 0),
                session_data.get("messages_count", 0),
                session_data.get("errors_count", 0),
            ),
        )

    def _insert_event(self, conn: sqlite3.Connection, event_data: dict[str, object]) -> None:
        """Insert an event into the target database.

        Args:
            conn: Connection to target database.
            event_data: Event data dictionary.
        """
        session_id = event_data.get("session_id")
        event_type = event_data.get("event_type") or event_data.get("type", "unknown")
        event_name = event_data.get("event_name") or event_data.get("name")

        conn.execute(
            """
            INSERT INTO events (
                session_id, vendor_id, event_type, event_name, event_data, timestamp
            ) VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                str(session_id),
                "claude",
                str(event_type),
                event_name,
                event_data.get("event_data") or event_data.get("data"),
                event_data.get("timestamp") or event_data.get("created_at"),
            ),
        )

    def rollback(self, backup_path: Path) -> bool:
        """Rollback a migration by restoring from backup.

        Args:
            backup_path: Path to the backup file.

        Returns:
            True if rollback succeeded, False otherwise.
        """
        if not backup_path.exists():
            return False

        if self.target_db_path.exists():
            self.target_db_path.unlink()

        return True

    def validate_migration(self) -> list[str]:
        """Validate the migrated database.

        Returns:
            List of validation errors (empty if valid).
        """
        errors = self._schema_manager.validate()

        if self.target_db_path.exists():
            with sqlite3.connect(self.target_db_path) as conn:
                cursor = conn.execute("SELECT COUNT(*) FROM sessions WHERE vendor_id IS NULL")
                if cursor.fetchone()[0] > 0:
                    errors.append("Found sessions without vendor_id")

                cursor = conn.execute("SELECT COUNT(*) FROM events WHERE vendor_id IS NULL")
                if cursor.fetchone()[0] > 0:
                    errors.append("Found events without vendor_id")

        return errors


def migrate_from_claude_sessions(
    source_path: Path,
    target_path: Path,
    *,
    create_backup: bool = True,
) -> MigrationResult:
    """Convenience function to migrate Claude sessions.

    Args:
        source_path: Path to Claude's sessions.db.
        target_path: Path to target unified database.
        create_backup: Whether to create a backup.

    Returns:
        MigrationResult with migration statistics.
    """
    manager = MigrationManager(target_path)
    return manager.migrate_from_claude_sessions(source_path, create_backup=create_backup)
