"""Database migration framework for ai-asst-mgr.

This module provides a simple migration framework for managing database
schema changes. It handles migration execution, rollback, and version tracking.
"""

from __future__ import annotations

import re
import shutil
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Callable

# Constants for validation
MIGRATION_VERSION_LENGTH = 3
MIGRATION_FILENAME_PARTS = 2


class MigrationError(Exception):
    """Raised when a migration operation fails."""


class Migration:
    """Represents a single database migration.

    Attributes:
        version: Migration version number (e.g., '001').
        name: Migration name (e.g., 'vendor_agnostic').
        sql_file: Path to SQL migration file.
        applied_at: Timestamp when migration was applied (None if not applied).
    """

    def __init__(self, version: str, name: str, sql_file: Path) -> None:
        """Initialize migration.

        Args:
            version: Migration version (must be 3 digits).
            name: Migration name.
            sql_file: Path to SQL file containing migration.

        Raises:
            ValueError: If version format is invalid.
        """
        if not version.isdigit() or len(version) != MIGRATION_VERSION_LENGTH:
            msg = (
                f"Invalid version format: {version}. "
                f"Must be {MIGRATION_VERSION_LENGTH} digits (e.g., '001')"
            )
            raise ValueError(msg)

        self.version = version
        self.name = name
        self.sql_file = sql_file
        self.applied_at: datetime | None = None

    def __repr__(self) -> str:
        """Return string representation."""
        status = f"applied {self.applied_at}" if self.applied_at else "pending"
        return f"Migration({self.version}_{self.name}, {status})"


class MigrationManager:
    """Manages database migrations.

    The MigrationManager handles applying migrations, tracking migration
    history, creating backups, and validating database schema.

    Example:
        >>> manager = MigrationManager(db_path="~/Data/claude-sessions/sessions.db")
        >>> manager.upgrade()  # Apply all pending migrations
    """

    def __init__(self, db_path: str | Path, migrations_dir: str | Path | None = None) -> None:
        """Initialize migration manager.

        Args:
            db_path: Path to SQLite database file.
            migrations_dir: Directory containing migration SQL files.
                Defaults to src/ai_asst_mgr/database/migrations.
        """
        self.db_path = Path(db_path).expanduser()

        if migrations_dir is None:
            # Default to migrations directory relative to this file
            migrations_dir = Path(__file__).parent / "migrations"

        self.migrations_dir = Path(migrations_dir)
        self._migrations: list[Migration] = []
        self._discover_migrations()

    def _discover_migrations(self) -> None:
        """Discover all migration files in migrations directory.

        Migration files must follow naming convention: NNN_name.sql
        where NNN is a 3-digit version number.
        """
        if not self.migrations_dir.exists():
            return

        for sql_file in sorted(self.migrations_dir.glob("*.sql")):
            # Parse filename: 001_vendor_agnostic.sql
            parts = sql_file.stem.split("_", 1)
            if len(parts) != MIGRATION_FILENAME_PARTS:
                continue

            version, name = parts
            try:
                migration = Migration(version, name, sql_file)
                self._migrations.append(migration)
            except ValueError:
                # Skip files with invalid version format
                continue

    def get_current_version(self) -> str | None:
        """Get current database schema version.

        Returns:
            Current version string (e.g., '2.0.0'), or None if not set.
        """
        if not self.db_path.exists():
            return None

        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT value FROM schema_metadata WHERE key = 'version'")
                result = cursor.fetchone()
                return result[0] if result else None
        except sqlite3.OperationalError:
            # Table doesn't exist yet
            return None

    def get_applied_migrations(self) -> list[str]:
        """Get list of applied migration versions.

        Returns:
            List of migration versions that have been applied (e.g., ['001']).
        """
        if not self.db_path.exists():
            return []

        try:
            with sqlite3.connect(self.db_path) as conn:
                # Check if migrations table exists
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'"
                )
                if not cursor.fetchone():
                    return []

                cursor = conn.execute("SELECT version FROM _migrations ORDER BY version")
                return [row[0] for row in cursor.fetchall()]
        except sqlite3.OperationalError:
            return []

    def get_pending_migrations(self) -> list[Migration]:
        """Get list of migrations that haven't been applied yet.

        Returns:
            List of pending Migration objects.
        """
        applied = set(self.get_applied_migrations())
        return [m for m in self._migrations if m.version not in applied]

    def create_backup(self) -> Path:
        """Create backup of database before migration.

        Returns:
            Path to backup file.

        Raises:
            MigrationError: If backup creation fails.
        """
        if not self.db_path.exists():
            msg = f"Database does not exist: {self.db_path}"
            raise MigrationError(msg)

        timestamp = datetime.now(UTC).strftime("%Y%m%d_%H%M%S")
        backup_path = self.db_path.parent / f"{self.db_path.stem}_backup_{timestamp}.db"

        try:
            shutil.copy2(self.db_path, backup_path)
        except OSError as e:
            msg = f"Failed to create backup: {e}"
            raise MigrationError(msg) from e
        else:
            return backup_path

    def _ensure_migrations_table(self, conn: sqlite3.Connection) -> None:
        """Ensure migrations tracking table exists.

        Args:
            conn: Database connection.
        """
        conn.execute("""
            CREATE TABLE IF NOT EXISTS _migrations (
                version TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()

    def apply_migration(self, migration: Migration, *, dry_run: bool = False) -> None:
        """Apply a single migration.

        Args:
            migration: Migration to apply.
            dry_run: If True, validate SQL but don't execute.

        Raises:
            MigrationError: If migration fails.
        """
        if not migration.sql_file.exists():
            msg = f"Migration file not found: {migration.sql_file}"
            raise MigrationError(msg)

        # Read migration SQL
        sql = migration.sql_file.read_text()

        if dry_run:
            # For dry-run, just validate SQL syntax (not execution)
            # Note: We can't fully validate ALTER TABLE statements without existing schema
            # So we just check for basic SQL syntax errors
            # Check for common SQL syntax patterns
            if not re.search(r"(CREATE|ALTER|INSERT|UPDATE|DELETE|SELECT)", sql, re.IGNORECASE):
                msg = f"Migration {migration.version} contains no SQL statements"
                raise MigrationError(msg)
            return

        # Apply migration to actual database
        try:
            with sqlite3.connect(self.db_path) as conn:
                self._ensure_migrations_table(conn)

                # Execute migration SQL
                conn.executescript(sql)

                # Record migration in tracking table
                conn.execute(
                    "INSERT INTO _migrations (version, name) VALUES (?, ?)",
                    (migration.version, migration.name),
                )
                conn.commit()

                migration.applied_at = datetime.now(UTC)
        except sqlite3.Error as e:
            msg = f"Failed to apply migration {migration.version}: {e}"
            raise MigrationError(msg) from e

    def upgrade(
        self,
        *,
        target_version: str | None = None,
        dry_run: bool = False,
        backup: bool = True,
    ) -> list[Migration]:
        """Apply all pending migrations up to target version.

        Args:
            target_version: Apply migrations up to this version (inclusive).
                If None, apply all pending migrations.
            dry_run: If True, validate migrations but don't execute.
            backup: If True, create backup before applying migrations.

        Returns:
            List of migrations that were applied.

        Raises:
            MigrationError: If any migration fails.
        """
        pending = self.get_pending_migrations()

        if target_version:
            pending = [m for m in pending if m.version <= target_version]

        if not pending:
            return []

        # Create backup before applying migrations (unless dry_run)
        if backup and not dry_run and self.db_path.exists():
            backup_path = self.create_backup()
            print(f"Created backup: {backup_path}")

        applied: list[Migration] = []
        for migration in pending:
            try:
                self.apply_migration(migration, dry_run=dry_run)
                applied.append(migration)

                if dry_run:
                    print(f"[DRY RUN] Would apply: {migration.version}_{migration.name}")
                else:
                    print(f"Applied: {migration.version}_{migration.name}")
            except MigrationError:
                if applied and not dry_run:
                    print(f"Migration failed. {len(applied)} migrations were applied.")
                    print(f"Restore from backup: {backup_path}")
                raise

        return applied

    def validate_schema(self, expected_version: str) -> bool:
        """Validate database schema matches expected version.

        Args:
            expected_version: Expected schema version (e.g., '2.0.0').

        Returns:
            True if schema version matches expected version.
        """
        current = self.get_current_version()
        return current == expected_version

    def get_migration_status(self) -> dict[str, str | list[str]]:
        """Get current migration status.

        Returns:
            Dictionary with current version, applied migrations, and pending migrations.
        """
        return {
            "current_version": self.get_current_version() or "unknown",
            "applied_migrations": self.get_applied_migrations(),
            "pending_migrations": [f"{m.version}_{m.name}" for m in self.get_pending_migrations()],
        }


def migrate_database(
    db_path: str | Path,
    *,
    target_version: str | None = None,
    dry_run: bool = False,
    backup: bool = True,
    on_progress: Callable[[str], None] | None = None,
) -> None:
    """Convenience function to migrate database to target version.

    Args:
        db_path: Path to SQLite database.
        target_version: Target migration version (None = all pending).
        dry_run: If True, validate but don't execute.
        backup: If True, create backup before migrating.
        on_progress: Optional callback for progress updates.

    Raises:
        MigrationError: If migration fails.
    """
    manager = MigrationManager(db_path)

    if on_progress:
        status = manager.get_migration_status()
        on_progress(f"Current version: {status['current_version']}")
        on_progress(f"Pending migrations: {len(status['pending_migrations'])}")

    applied = manager.upgrade(
        target_version=target_version,
        dry_run=dry_run,
        backup=backup,
    )

    if on_progress:
        if dry_run:
            on_progress(f"Validated {len(applied)} migrations")
        else:
            on_progress(f"Applied {len(applied)} migrations")
            new_version = manager.get_current_version()
            on_progress(f"New version: {new_version}")


__all__ = ["Migration", "MigrationError", "MigrationManager", "migrate_database"]
