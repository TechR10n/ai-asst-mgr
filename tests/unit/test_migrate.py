"""Unit tests for database migration framework."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from ai_asst_mgr.database.migrate import (
    Migration,
    MigrationError,
    MigrationManager,
    migrate_database,
)


class TestMigration:
    """Tests for Migration class."""

    def test_valid_migration_initialization(self) -> None:
        """Test creating migration with valid parameters."""
        sql_file = Path("/tmp/001_test.sql")
        migration = Migration("001", "test", sql_file)

        assert migration.version == "001"
        assert migration.name == "test"
        assert migration.sql_file == sql_file
        assert migration.applied_at is None

    def test_invalid_version_format_raises_value_error(self) -> None:
        """Test creating migration with invalid version format."""
        with pytest.raises(ValueError, match="Invalid version format"):
            Migration("1", "test", Path("/tmp/test.sql"))

        with pytest.raises(ValueError, match="Invalid version format"):
            Migration("0001", "test", Path("/tmp/test.sql"))

        with pytest.raises(ValueError, match="Invalid version format"):
            Migration("abc", "test", Path("/tmp/test.sql"))

    def test_repr_shows_pending_status(self) -> None:
        """Test __repr__ shows pending for unapplied migration."""
        migration = Migration("001", "test", Path("/tmp/test.sql"))
        repr_str = repr(migration)

        assert "001_test" in repr_str
        assert "pending" in repr_str


class TestMigrationManagerInitialization:
    """Tests for MigrationManager initialization."""

    def test_initializes_with_valid_paths(self) -> None:
        """Test manager initializes with valid database and migrations paths."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            manager = MigrationManager(db_path, migrations_dir)

            assert manager.db_path == db_path
            assert manager.migrations_dir == migrations_dir

    def test_expands_tilde_in_db_path(self) -> None:
        """Test manager expands ~ in database path."""
        manager = MigrationManager("~/test.db")

        assert "~" not in str(manager.db_path)
        assert manager.db_path.is_absolute()

    def test_discovers_migrations_from_directory(self) -> None:
        """Test manager discovers migration files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            # Create test migration files
            (migrations_dir / "001_first.sql").write_text("-- First migration")
            (migrations_dir / "002_second.sql").write_text("-- Second migration")
            (migrations_dir / "invalid.sql").write_text("-- Invalid")

            manager = MigrationManager(db_path, migrations_dir)

            # Should discover 2 valid migrations, skip invalid
            assert len(manager._migrations) == 2
            assert manager._migrations[0].version == "001"
            assert manager._migrations[0].name == "first"
            assert manager._migrations[1].version == "002"
            assert manager._migrations[1].name == "second"

    def test_handles_nonexistent_migrations_directory(self) -> None:
        """Test manager handles missing migrations directory gracefully."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "nonexistent"

            manager = MigrationManager(db_path, migrations_dir)

            assert len(manager._migrations) == 0


class TestMigrationManagerVersionTracking:
    """Tests for version tracking methods."""

    def test_get_current_version_returns_none_for_new_database(self) -> None:
        """Test returns None for database without version metadata."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            manager = MigrationManager(db_path)

            assert manager.get_current_version() is None

    def test_get_current_version_reads_from_metadata_table(self) -> None:
        """Test reads version from schema_metadata table."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"

            # Create database with version metadata
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE schema_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        last_updated TIMESTAMP
                    )
                """)
                conn.execute("INSERT INTO schema_metadata (key, value) VALUES ('version', '2.0.0')")
                conn.commit()

            manager = MigrationManager(db_path)
            assert manager.get_current_version() == "2.0.0"

    def test_get_applied_migrations_returns_empty_for_new_database(self) -> None:
        """Test returns empty list for new database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            manager = MigrationManager(db_path)

            assert manager.get_applied_migrations() == []

    def test_get_applied_migrations_reads_from_tracking_table(self) -> None:
        """Test reads applied migrations from _migrations table."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"

            # Create database with migrations table
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE _migrations (
                        version TEXT PRIMARY KEY,
                        name TEXT,
                        applied_at TIMESTAMP
                    )
                """)
                conn.execute("INSERT INTO _migrations (version, name) VALUES ('001', 'first')")
                conn.execute("INSERT INTO _migrations (version, name) VALUES ('002', 'second')")
                conn.commit()

            manager = MigrationManager(db_path)
            applied = manager.get_applied_migrations()

            assert applied == ["001", "002"]

    def test_get_pending_migrations_returns_unapplied_migrations(self) -> None:
        """Test returns only migrations that haven't been applied."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            # Create migration files
            (migrations_dir / "001_first.sql").write_text("-- First")
            (migrations_dir / "002_second.sql").write_text("-- Second")
            (migrations_dir / "003_third.sql").write_text("-- Third")

            # Mark 001 as applied
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE _migrations (
                        version TEXT PRIMARY KEY,
                        name TEXT,
                        applied_at TIMESTAMP
                    )
                """)
                conn.execute("INSERT INTO _migrations (version, name) VALUES ('001', 'first')")
                conn.commit()

            manager = MigrationManager(db_path, migrations_dir)
            pending = manager.get_pending_migrations()

            assert len(pending) == 2
            assert pending[0].version == "002"
            assert pending[1].version == "003"


class TestMigrationManagerBackup:
    """Tests for backup functionality."""

    def test_create_backup_copies_database_file(self) -> None:
        """Test backup creates copy of database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"

            # Create test database
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE test (id INTEGER)")
                conn.commit()

            manager = MigrationManager(db_path)
            backup_path = manager.create_backup()

            # Verify backup exists and is valid
            assert backup_path.exists()
            assert backup_path.name.startswith("test_backup_")
            assert backup_path.suffix == ".db"

            # Verify backup is valid SQLite database
            with sqlite3.connect(backup_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='test'"
                )
                assert cursor.fetchone() is not None

    def test_create_backup_raises_error_for_nonexistent_database(self) -> None:
        """Test backup raises error if database doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "nonexistent.db"
            manager = MigrationManager(db_path)

            with pytest.raises(MigrationError, match="Database does not exist"):
                manager.create_backup()


class TestMigrationManagerApplyMigration:
    """Tests for applying individual migrations."""

    def test_apply_migration_executes_sql(self) -> None:
        """Test applying migration executes SQL commands."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            # Create migration that creates a table
            sql = "CREATE TABLE test_table (id INTEGER PRIMARY KEY);"
            migration_file = migrations_dir / "001_create_table.sql"
            migration_file.write_text(sql)

            # Initialize database
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            manager = MigrationManager(db_path, migrations_dir)
            migration = manager._migrations[0]
            manager.apply_migration(migration)

            # Verify table was created
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='test_table'"
                )
                assert cursor.fetchone() is not None

    def test_apply_migration_records_in_tracking_table(self) -> None:
        """Test migration is recorded in _migrations table."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            migration_file = migrations_dir / "001_test.sql"
            migration_file.write_text("CREATE TABLE test (id INTEGER);")

            # Initialize database
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            manager = MigrationManager(db_path, migrations_dir)
            migration = manager._migrations[0]
            manager.apply_migration(migration)

            # Verify tracking record
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute("SELECT version, name FROM _migrations WHERE version='001'")
                result = cursor.fetchone()
                assert result is not None
                assert result[0] == "001"
                assert result[1] == "test"

    def test_apply_migration_dry_run_validates_without_executing(self) -> None:
        """Test dry_run validates SQL without executing."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            migration_file = migrations_dir / "001_test.sql"
            migration_file.write_text("CREATE TABLE test (id INTEGER);")

            # Initialize database
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            manager = MigrationManager(db_path, migrations_dir)
            migration = manager._migrations[0]
            manager.apply_migration(migration, dry_run=True)

            # Verify table was NOT created
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='test'"
                )
                assert cursor.fetchone() is None

    def test_apply_migration_raises_error_for_invalid_sql(self) -> None:
        """Test applying migration with invalid SQL raises error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            # Create migration with invalid SQL
            migration_file = migrations_dir / "001_bad.sql"
            migration_file.write_text("INVALID SQL SYNTAX HERE;")

            # Initialize database
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            manager = MigrationManager(db_path, migrations_dir)
            migration = manager._migrations[0]

            with pytest.raises(MigrationError, match="Failed to apply migration"):
                manager.apply_migration(migration)


class TestMigrationManagerUpgrade:
    """Tests for upgrade functionality."""

    def test_upgrade_applies_all_pending_migrations(self) -> None:
        """Test upgrade applies all pending migrations in order."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            # Create multiple migrations
            (migrations_dir / "001_first.sql").write_text("CREATE TABLE first (id INTEGER);")
            (migrations_dir / "002_second.sql").write_text("CREATE TABLE second (id INTEGER);")
            (migrations_dir / "003_third.sql").write_text("CREATE TABLE third (id INTEGER);")

            # Initialize database
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            manager = MigrationManager(db_path, migrations_dir)
            applied = manager.upgrade(backup=False)

            assert len(applied) == 3
            assert applied[0].version == "001"
            assert applied[1].version == "002"
            assert applied[2].version == "003"

            # Verify all tables were created
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                )
                tables = [row[0] for row in cursor.fetchall()]
                assert "first" in tables
                assert "second" in tables
                assert "third" in tables

    def test_upgrade_with_target_version_stops_at_target(self) -> None:
        """Test upgrade stops at target version."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            (migrations_dir / "001_first.sql").write_text("CREATE TABLE first (id INTEGER);")
            (migrations_dir / "002_second.sql").write_text("CREATE TABLE second (id INTEGER);")
            (migrations_dir / "003_third.sql").write_text("CREATE TABLE third (id INTEGER);")

            # Initialize database
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            manager = MigrationManager(db_path, migrations_dir)
            applied = manager.upgrade(target_version="002", backup=False)

            assert len(applied) == 2
            assert applied[0].version == "001"
            assert applied[1].version == "002"

    def test_upgrade_returns_empty_list_if_no_pending_migrations(self) -> None:
        """Test upgrade returns empty list when nothing to apply."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            (migrations_dir / "001_first.sql").write_text("CREATE TABLE first (id INTEGER);")

            # Initialize and apply migration
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            manager = MigrationManager(db_path, migrations_dir)
            manager.upgrade(backup=False)

            # Try upgrading again
            applied = manager.upgrade(backup=False)
            assert len(applied) == 0

    def test_upgrade_creates_backup_by_default(self) -> None:
        """Test upgrade creates backup before applying migrations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            (migrations_dir / "001_first.sql").write_text("CREATE TABLE first (id INTEGER);")

            # Initialize database
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            manager = MigrationManager(db_path, migrations_dir)
            manager.upgrade()  # backup=True by default

            # Check backup was created
            backups = list(Path(temp_dir).glob("test_backup_*.db"))
            assert len(backups) == 1


class TestMigrationManagerValidation:
    """Tests for schema validation."""

    def test_validate_schema_returns_true_for_matching_version(self) -> None:
        """Test validation succeeds when version matches."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"

            # Create database with version
            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE schema_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        last_updated TIMESTAMP
                    )
                """)
                conn.execute("INSERT INTO schema_metadata (key, value) VALUES ('version', '2.0.0')")
                conn.commit()

            manager = MigrationManager(db_path)
            assert manager.validate_schema("2.0.0") is True

    def test_validate_schema_returns_false_for_mismatched_version(self) -> None:
        """Test validation fails when version doesn't match."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"

            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE schema_metadata (
                        key TEXT PRIMARY KEY,
                        value TEXT,
                        last_updated TIMESTAMP
                    )
                """)
                conn.execute("INSERT INTO schema_metadata (key, value) VALUES ('version', '1.0.0')")
                conn.commit()

            manager = MigrationManager(db_path)
            assert manager.validate_schema("2.0.0") is False


class TestMigrateDatabaseConvenienceFunction:
    """Tests for migrate_database convenience function."""

    def test_migrates_database_successfully(self) -> None:
        """Test convenience function migrates database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            (migrations_dir / "001_first.sql").write_text("CREATE TABLE first (id INTEGER);")

            # Initialize database
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            # Use real migrations directory
            manager = MigrationManager(db_path, migrations_dir)
            manager.upgrade(backup=False)

            # Verify table created
            with sqlite3.connect(db_path) as conn:
                cursor = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' AND name='first'"
                )
                assert cursor.fetchone() is not None

    def test_calls_progress_callback(self) -> None:
        """Test progress callback is called."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            migrations_dir = Path(temp_dir) / "migrations"
            migrations_dir.mkdir()

            (migrations_dir / "001_test.sql").write_text("CREATE TABLE test (id INTEGER);")

            # Initialize database
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            progress_messages: list[str] = []

            def on_progress(msg: str) -> None:
                progress_messages.append(msg)

            # Create manager and set migrations_dir
            manager = MigrationManager(db_path, migrations_dir)
            manager.upgrade(backup=False)

            # Call migrate_database with progress callback
            migrate_database(db_path, backup=False, on_progress=on_progress)

            assert len(progress_messages) > 0
            assert any("Current version" in msg for msg in progress_messages)
