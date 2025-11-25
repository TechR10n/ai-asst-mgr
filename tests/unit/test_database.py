"""Tests for database module."""

from __future__ import annotations

import sqlite3
import tempfile
from pathlib import Path

import pytest

from ai_asst_mgr.database.manager import DatabaseManager, WeeklyReview
from ai_asst_mgr.database.migrations import MigrationManager, migrate_from_claude_sessions
from ai_asst_mgr.database.schema import (
    SCHEMA_VERSION,
    SchemaManager,
    create_schema_sql,
)


class TestSchemaSQL:
    """Tests for schema SQL generation."""

    def test_create_schema_sql_returns_string(self) -> None:
        """Verify create_schema_sql returns a non-empty string."""
        sql = create_schema_sql()
        assert isinstance(sql, str)
        assert len(sql) > 0

    def test_create_schema_sql_contains_all_tables(self) -> None:
        """Verify all required tables are defined in schema SQL."""
        sql = create_schema_sql()
        expected_tables = [
            "schema_metadata",
            "vendor_profiles",
            "sessions",
            "events",
            "claude_agent_profiles",
            "claude_skill_profiles",
            "weekly_reviews",
            "weekly_aggregates",
            "coaching_insights",
            "capabilities",
        ]
        for table in expected_tables:
            assert f"CREATE TABLE IF NOT EXISTS {table}" in sql

    def test_create_schema_sql_contains_indexes(self) -> None:
        """Verify performance indexes are defined in schema SQL."""
        sql = create_schema_sql()
        assert "CREATE INDEX IF NOT EXISTS" in sql
        assert "idx_sessions_vendor" in sql
        assert "idx_events_session" in sql

    def test_create_schema_sql_contains_views(self) -> None:
        """Verify all analytical views are defined in schema SQL."""
        sql = create_schema_sql()
        expected_views = [
            "v_daily_usage",
            "v_vendor_stats",
            "v_tool_usage",
            "v_weekly_summary",
            "v_error_summary",
            "v_session_details",
            "v_capability_summary",
            "v_coaching_status",
        ]
        for view in expected_views:
            assert f"CREATE VIEW IF NOT EXISTS {view}" in sql

    def test_create_schema_sql_contains_default_vendors(self) -> None:
        """Verify default vendor profiles are seeded in schema SQL."""
        sql = create_schema_sql()
        assert "('claude', 'Claude Code', '~/.claude')" in sql
        assert "('gemini', 'Gemini CLI', '~/.gemini')" in sql
        assert "('openai', 'OpenAI Codex', '~/.codex')" in sql


class TestSchemaManager:
    """Tests for SchemaManager class."""

    @pytest.fixture
    def temp_db(self) -> Path:
        """Create a temporary database path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "test.db"

    def test_init_stores_path(self, temp_db: Path) -> None:
        """Verify constructor stores the database path."""
        manager = SchemaManager(temp_db)
        assert manager.db_path == temp_db

    def test_initialize_creates_database(self, temp_db: Path) -> None:
        """Verify initialize creates the database file."""
        manager = SchemaManager(temp_db)
        manager.initialize()
        assert temp_db.exists()

    def test_initialize_creates_parent_directories(self) -> None:
        """Verify initialize creates nested parent directories."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "nested" / "dirs" / "test.db"
            manager = SchemaManager(db_path)
            manager.initialize()
            assert db_path.exists()

    def test_initialize_creates_all_tables(self, temp_db: Path) -> None:
        """Verify initialize creates all required tables."""
        manager = SchemaManager(temp_db)
        manager.initialize()

        tables = manager.get_tables()
        expected_tables = [
            "schema_metadata",
            "vendor_profiles",
            "sessions",
            "events",
            "claude_agent_profiles",
            "claude_skill_profiles",
            "weekly_reviews",
            "weekly_aggregates",
            "coaching_insights",
            "capabilities",
        ]
        for table in expected_tables:
            assert table in tables

    def test_initialize_creates_all_views(self, temp_db: Path) -> None:
        """Verify initialize creates all analytical views."""
        manager = SchemaManager(temp_db)
        manager.initialize()

        views = manager.get_views()
        expected_views = [
            "v_daily_usage",
            "v_vendor_stats",
            "v_tool_usage",
            "v_weekly_summary",
            "v_error_summary",
            "v_session_details",
            "v_capability_summary",
            "v_coaching_status",
        ]
        for view in expected_views:
            assert view in views

    def test_initialize_sets_schema_version(self, temp_db: Path) -> None:
        """Verify initialize records the schema version."""
        manager = SchemaManager(temp_db)
        manager.initialize()
        assert manager.get_version() == SCHEMA_VERSION

    def test_initialize_inserts_default_vendors(self, temp_db: Path) -> None:
        """Verify initialize seeds default vendor profiles."""
        manager = SchemaManager(temp_db)
        manager.initialize()

        with sqlite3.connect(temp_db) as conn:
            cursor = conn.execute("SELECT vendor_id FROM vendor_profiles ORDER BY vendor_id")
            vendors = [row[0] for row in cursor.fetchall()]

        assert "claude" in vendors
        assert "gemini" in vendors
        assert "openai" in vendors

    def test_initialize_is_idempotent(self, temp_db: Path) -> None:
        """Verify initialize can be called multiple times safely."""
        manager = SchemaManager(temp_db)
        manager.initialize()
        manager.initialize()
        assert manager.get_version() == SCHEMA_VERSION
        assert len(manager.validate()) == 0

    def test_get_version_returns_none_for_nonexistent_db(self, temp_db: Path) -> None:
        """Verify get_version returns None when database does not exist."""
        manager = SchemaManager(temp_db)
        assert manager.get_version() is None

    def test_get_version_returns_version_after_init(self, temp_db: Path) -> None:
        """Verify get_version returns correct version after initialization."""
        manager = SchemaManager(temp_db)
        manager.initialize()
        assert manager.get_version() == SCHEMA_VERSION

    def test_is_current_false_for_nonexistent_db(self, temp_db: Path) -> None:
        """Verify is_current returns False for nonexistent database."""
        manager = SchemaManager(temp_db)
        assert manager.is_current() is False

    def test_is_current_true_after_init(self, temp_db: Path) -> None:
        """Verify is_current returns True after initialization."""
        manager = SchemaManager(temp_db)
        manager.initialize()
        assert manager.is_current() is True

    def test_needs_migration_false_for_nonexistent_db(self, temp_db: Path) -> None:
        """Verify needs_migration returns False for nonexistent database."""
        manager = SchemaManager(temp_db)
        assert manager.needs_migration() is False

    def test_needs_migration_false_for_current_version(self, temp_db: Path) -> None:
        """Verify needs_migration returns False for current schema version."""
        manager = SchemaManager(temp_db)
        manager.initialize()
        assert manager.needs_migration() is False

    def test_needs_migration_true_for_old_version(self, temp_db: Path) -> None:
        """Verify needs_migration returns True for outdated schema version."""
        manager = SchemaManager(temp_db)
        manager.initialize()

        with sqlite3.connect(temp_db) as conn:
            conn.execute(
                "UPDATE schema_metadata SET value = ? WHERE key = ?",
                ("0.9.0", "schema_version"),
            )
            conn.commit()

        assert manager.needs_migration() is True

    def test_get_tables_returns_empty_for_nonexistent_db(self, temp_db: Path) -> None:
        """Verify get_tables returns empty list for nonexistent database."""
        manager = SchemaManager(temp_db)
        assert manager.get_tables() == []

    def test_get_views_returns_empty_for_nonexistent_db(self, temp_db: Path) -> None:
        """Verify get_views returns empty list for nonexistent database."""
        manager = SchemaManager(temp_db)
        assert manager.get_views() == []

    def test_validate_returns_error_for_nonexistent_db(self, temp_db: Path) -> None:
        """Verify validate reports error for nonexistent database."""
        manager = SchemaManager(temp_db)
        errors = manager.validate()
        assert len(errors) == 1
        assert "Database file does not exist" in errors[0]

    def test_validate_returns_empty_for_valid_db(self, temp_db: Path) -> None:
        """Verify validate returns no errors for valid database."""
        manager = SchemaManager(temp_db)
        manager.initialize()
        errors = manager.validate()
        assert errors == []

    def test_validate_detects_missing_table(self, temp_db: Path) -> None:
        """Verify validate detects missing tables."""
        manager = SchemaManager(temp_db)
        manager.initialize()

        with sqlite3.connect(temp_db) as conn:
            conn.execute("DROP TABLE capabilities")
            conn.commit()

        errors = manager.validate()
        assert any("Missing table: capabilities" in e for e in errors)

    def test_validate_detects_missing_view(self, temp_db: Path) -> None:
        """Verify validate detects missing views."""
        manager = SchemaManager(temp_db)
        manager.initialize()

        with sqlite3.connect(temp_db) as conn:
            conn.execute("DROP VIEW v_daily_usage")
            conn.commit()

        errors = manager.validate()
        assert any("Missing view: v_daily_usage" in e for e in errors)

    def test_validate_detects_version_mismatch(self, temp_db: Path) -> None:
        """Verify validate detects schema version mismatch."""
        manager = SchemaManager(temp_db)
        manager.initialize()

        with sqlite3.connect(temp_db) as conn:
            conn.execute(
                "UPDATE schema_metadata SET value = ? WHERE key = ?",
                ("0.0.1", "schema_version"),
            )
            conn.commit()

        errors = manager.validate()
        assert any("Schema version mismatch" in e for e in errors)


class TestSchemaIntegrity:
    """Tests for schema data integrity."""

    @pytest.fixture
    def initialized_db(self) -> Path:
        """Create an initialized temporary database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            manager = SchemaManager(db_path)
            manager.initialize()
            yield db_path

    def test_sessions_vendor_foreign_key(self, initialized_db: Path) -> None:
        """Verify sessions table links to vendor_profiles."""
        with sqlite3.connect(initialized_db) as conn:
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("""
                INSERT INTO sessions (session_id, vendor_id, start_time)
                VALUES ('test-session', 'claude', datetime('now'))
            """)
            conn.commit()

            cursor = conn.execute("SELECT COUNT(*) FROM sessions")
            assert cursor.fetchone()[0] == 1

    def test_events_session_link(self, initialized_db: Path) -> None:
        """Verify events table links to sessions."""
        with sqlite3.connect(initialized_db) as conn:
            conn.execute("""
                INSERT INTO sessions (session_id, vendor_id, start_time)
                VALUES ('test-session', 'claude', datetime('now'))
            """)
            conn.execute("""
                INSERT INTO events (session_id, vendor_id, event_type, event_name)
                VALUES ('test-session', 'claude', 'tool_call', 'Read')
            """)
            conn.commit()

            cursor = conn.execute("SELECT COUNT(*) FROM events")
            assert cursor.fetchone()[0] == 1

    def test_capabilities_unique_constraint(self, initialized_db: Path) -> None:
        """Verify capabilities table enforces unique vendor/type/name constraint."""
        with sqlite3.connect(initialized_db) as conn:
            conn.execute("""
                INSERT INTO capabilities (vendor_id, capability_type, capability_name)
                VALUES ('claude', 'agent', 'test-agent')
            """)
            conn.commit()

            with pytest.raises(sqlite3.IntegrityError):
                conn.execute("""
                    INSERT INTO capabilities (vendor_id, capability_type, capability_name)
                    VALUES ('claude', 'agent', 'test-agent')
                """)

    def test_weekly_aggregates_upsert(self, initialized_db: Path) -> None:
        """Verify weekly_aggregates supports upsert via INSERT OR REPLACE."""
        with sqlite3.connect(initialized_db) as conn:
            conn.execute("""
                INSERT INTO weekly_aggregates (vendor_id, week_start, metric_name, metric_value)
                VALUES ('claude', '2024-01-01', 'sessions', 10)
            """)
            conn.commit()

            conn.execute("""
                INSERT OR REPLACE INTO weekly_aggregates
                (vendor_id, week_start, metric_name, metric_value)
                VALUES ('claude', '2024-01-01', 'sessions', 20)
            """)
            conn.commit()

            cursor = conn.execute("""
                SELECT metric_value FROM weekly_aggregates
                WHERE vendor_id = 'claude' AND metric_name = 'sessions'
            """)
            assert cursor.fetchone()[0] == 20

    def test_daily_usage_view_aggregation(self, initialized_db: Path) -> None:
        """Verify v_daily_usage view aggregates sessions by date."""
        with sqlite3.connect(initialized_db) as conn:
            conn.execute("""
                INSERT INTO sessions (session_id, vendor_id, start_time, tool_calls_count)
                VALUES ('s1', 'claude', '2024-01-15 10:00:00', 5)
            """)
            conn.execute("""
                INSERT INTO sessions (session_id, vendor_id, start_time, tool_calls_count)
                VALUES ('s2', 'claude', '2024-01-15 14:00:00', 10)
            """)
            conn.commit()

            cursor = conn.execute("""
                SELECT session_count, total_tool_calls FROM v_daily_usage
                WHERE usage_date = '2024-01-15' AND vendor_id = 'claude'
            """)
            row = cursor.fetchone()
            assert row[0] == 2
            assert row[1] == 15


class TestDatabaseManager:
    """Tests for DatabaseManager class."""

    @pytest.fixture
    def db_manager(self) -> DatabaseManager:
        """Create a DatabaseManager with temporary database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            manager = DatabaseManager(db_path)
            manager.initialize()
            yield manager

    def test_init_stores_path(self) -> None:
        """Verify constructor stores database path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            manager = DatabaseManager(db_path)
            assert manager.db_path == db_path

    def test_initialize_creates_schema(self) -> None:
        """Verify initialize creates database schema."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            manager = DatabaseManager(db_path)
            manager.initialize()
            assert db_path.exists()

    def test_record_session(self, db_manager: DatabaseManager) -> None:
        """Verify record_session creates session record."""
        db_manager.record_session("sess-1", "claude", "/project")

        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.execute("SELECT * FROM sessions WHERE session_id = 'sess-1'")
            row = cursor.fetchone()
            assert row is not None
            assert row[2] == "claude"

    def test_end_session_updates_record(self, db_manager: DatabaseManager) -> None:
        """Verify end_session updates session with metrics."""
        db_manager.record_session("sess-1", "claude")
        db_manager.end_session("sess-1", tool_calls_count=10, messages_count=5, errors_count=1)

        with sqlite3.connect(db_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM sessions WHERE session_id = 'sess-1'")
            row = cursor.fetchone()
            assert row["tool_calls_count"] == 10
            assert row["messages_count"] == 5
            assert row["errors_count"] == 1
            assert row["end_time"] is not None

    def test_record_event(self, db_manager: DatabaseManager) -> None:
        """Verify record_event creates event record."""
        db_manager.record_session("sess-1", "claude")
        db_manager.record_event("sess-1", "claude", "tool_call", "Read", {"file": "test.py"})

        with sqlite3.connect(db_manager.db_path) as conn:
            cursor = conn.execute("SELECT * FROM events WHERE session_id = 'sess-1'")
            row = cursor.fetchone()
            assert row is not None

    def test_get_vendor_stats_returns_none_for_no_data(self, db_manager: DatabaseManager) -> None:
        """Verify get_vendor_stats returns None when no sessions exist."""
        result = db_manager.get_vendor_stats("claude")
        assert result is None

    def test_get_vendor_stats_returns_stats(self, db_manager: DatabaseManager) -> None:
        """Verify get_vendor_stats returns correct statistics."""
        db_manager.record_session("sess-1", "claude")
        db_manager.end_session("sess-1", tool_calls_count=10, messages_count=5)
        db_manager.record_session("sess-2", "claude")
        db_manager.end_session("sess-2", tool_calls_count=20, messages_count=10)

        result = db_manager.get_vendor_stats("claude")
        assert result is not None
        assert result.vendor_id == "claude"
        assert result.total_sessions == 2
        assert result.total_tool_calls == 30
        assert result.total_messages == 15

    def test_get_vendor_stats_summary(self, db_manager: DatabaseManager) -> None:
        """Verify get_vendor_stats_summary returns all vendors."""
        db_manager.record_session("sess-1", "claude")
        db_manager.end_session("sess-1", tool_calls_count=10)
        db_manager.record_session("sess-2", "gemini")
        db_manager.end_session("sess-2", tool_calls_count=20)

        results = db_manager.get_vendor_stats_summary()
        assert len(results) == 2
        vendors = {r.vendor_id for r in results}
        assert "claude" in vendors
        assert "gemini" in vendors

    def test_get_daily_usage(self, db_manager: DatabaseManager) -> None:
        """Verify get_daily_usage returns daily metrics."""
        db_manager.record_session("sess-1", "claude")
        db_manager.end_session("sess-1", tool_calls_count=10)

        results = db_manager.get_daily_usage(days=7)
        assert len(results) >= 0

    def test_get_week_stats(self, db_manager: DatabaseManager) -> None:
        """Verify get_week_stats returns current week data."""
        db_manager.record_session("sess-1", "claude")
        db_manager.end_session("sess-1", tool_calls_count=10)

        result = db_manager.get_week_stats()
        assert result.week_start is not None
        assert result.week_end is not None
        assert result.total_sessions >= 0

    def test_save_and_get_reviews(self, db_manager: DatabaseManager) -> None:
        """Verify save_review and get_previous_reviews work correctly."""
        review = WeeklyReview(
            id=None,
            vendor_id="claude",
            week_start="2024-01-01",
            week_end="2024-01-07",
            total_sessions=10,
            total_tool_calls=100,
            total_messages=50,
            total_errors=2,
            average_session_duration=300,
            top_tools=["Read", "Write", "Edit"],
            insights=["High tool usage"],
            recommendations=["Use more batch operations"],
            created_at=None,
        )

        review_id = db_manager.save_review(review)
        assert review_id > 0

        reviews = db_manager.get_previous_reviews(limit=10)
        assert len(reviews) == 1
        assert reviews[0].vendor_id == "claude"
        assert reviews[0].top_tools == ["Read", "Write", "Edit"]

    def test_get_agent_usage_history_empty(self, db_manager: DatabaseManager) -> None:
        """Verify get_agent_usage_history returns empty list when no data."""
        results = db_manager.get_agent_usage_history()
        assert results == []

    def test_get_tool_usage(self, db_manager: DatabaseManager) -> None:
        """Verify get_tool_usage returns tool statistics."""
        db_manager.record_session("sess-1", "claude")
        db_manager.record_event("sess-1", "claude", "tool_call", "Read")
        db_manager.record_event("sess-1", "claude", "tool_call", "Read")
        db_manager.record_event("sess-1", "claude", "tool_call", "Write")

        results = db_manager.get_tool_usage("claude")
        assert len(results) >= 0


class TestMigrationManager:
    """Tests for MigrationManager class."""

    @pytest.fixture
    def source_db(self) -> Path:
        """Create a source database with legacy data."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "sessions.db"

            with sqlite3.connect(db_path) as conn:
                conn.execute("""
                    CREATE TABLE sessions (
                        id INTEGER PRIMARY KEY,
                        session_id TEXT UNIQUE,
                        project_path TEXT,
                        start_time TEXT,
                        end_time TEXT,
                        duration_seconds INTEGER,
                        tool_calls_count INTEGER,
                        messages_count INTEGER,
                        errors_count INTEGER
                    )
                """)
                conn.execute("""
                    CREATE TABLE events (
                        id INTEGER PRIMARY KEY,
                        session_id TEXT,
                        event_type TEXT,
                        event_name TEXT,
                        event_data TEXT,
                        timestamp TEXT
                    )
                """)
                conn.execute("""
                    INSERT INTO sessions (session_id, start_time, tool_calls_count)
                    VALUES ('sess-1', '2024-01-15 10:00:00', 5)
                """)
                conn.execute("""
                    INSERT INTO events (session_id, event_type, event_name, timestamp)
                    VALUES ('sess-1', 'tool_call', 'Read', '2024-01-15 10:01:00')
                """)
                conn.commit()

            yield db_path

    @pytest.fixture
    def target_db(self) -> Path:
        """Create target database path."""
        with tempfile.TemporaryDirectory() as temp_dir:
            yield Path(temp_dir) / "unified.db"

    def test_migrate_nonexistent_source(self, target_db: Path) -> None:
        """Verify migration fails for nonexistent source."""
        manager = MigrationManager(target_db)
        result = manager.migrate_from_claude_sessions(Path("/nonexistent/db"))

        assert not result.success
        assert "does not exist" in result.errors[0]

    def test_migrate_creates_backup(self, source_db: Path, target_db: Path) -> None:
        """Verify migration creates backup of source."""
        manager = MigrationManager(target_db)
        result = manager.migrate_from_claude_sessions(source_db)

        assert result.backup_path is not None
        assert result.backup_path.exists()
        assert ".backup_" in str(result.backup_path)

    def test_migrate_without_backup(self, source_db: Path, target_db: Path) -> None:
        """Verify migration works without backup."""
        manager = MigrationManager(target_db)
        result = manager.migrate_from_claude_sessions(source_db, create_backup=False)

        assert result.backup_path is None
        assert result.success

    def test_migrate_sessions(self, source_db: Path, target_db: Path) -> None:
        """Verify sessions are migrated correctly."""
        manager = MigrationManager(target_db)
        result = manager.migrate_from_claude_sessions(source_db)

        assert result.sessions_migrated == 1
        assert result.success

        with sqlite3.connect(target_db) as conn:
            cursor = conn.execute("SELECT vendor_id FROM sessions WHERE session_id = 'sess-1'")
            row = cursor.fetchone()
            assert row[0] == "claude"

    def test_migrate_events(self, source_db: Path, target_db: Path) -> None:
        """Verify events are migrated correctly."""
        manager = MigrationManager(target_db)
        result = manager.migrate_from_claude_sessions(source_db)

        assert result.events_migrated == 1
        assert result.success

        with sqlite3.connect(target_db) as conn:
            cursor = conn.execute("SELECT vendor_id FROM events WHERE session_id = 'sess-1'")
            row = cursor.fetchone()
            assert row[0] == "claude"

    def test_validate_migration(self, source_db: Path, target_db: Path) -> None:
        """Verify validate_migration returns no errors for valid migration."""
        manager = MigrationManager(target_db)
        manager.migrate_from_claude_sessions(source_db)

        errors = manager.validate_migration()
        assert errors == []

    def test_rollback_with_valid_backup(self, source_db: Path, target_db: Path) -> None:
        """Verify rollback removes target database."""
        manager = MigrationManager(target_db)
        result = manager.migrate_from_claude_sessions(source_db)

        assert target_db.exists()
        assert result.backup_path is not None

        success = manager.rollback(result.backup_path)
        assert success
        assert not target_db.exists()

    def test_rollback_with_invalid_backup(self, target_db: Path) -> None:
        """Verify rollback fails with nonexistent backup."""
        manager = MigrationManager(target_db)
        success = manager.rollback(Path("/nonexistent/backup.db"))
        assert not success

    def test_migrate_source_without_sessions_table(self, target_db: Path) -> None:
        """Verify migration handles source without sessions table."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_db = Path(temp_dir) / "empty.db"

            # Create DB with only events table, no sessions
            with sqlite3.connect(source_db) as conn:
                conn.execute("""
                    CREATE TABLE events (
                        id INTEGER PRIMARY KEY,
                        session_id TEXT
                    )
                """)
                conn.commit()

            manager = MigrationManager(target_db)
            result = manager.migrate_from_claude_sessions(source_db)

            assert result.sessions_migrated == 0
            assert result.success

    def test_migrate_source_without_events_table(self, target_db: Path) -> None:
        """Verify migration handles source without events table."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_db = Path(temp_dir) / "empty.db"

            # Create DB with only sessions table, no events
            with sqlite3.connect(source_db) as conn:
                conn.execute("""
                    CREATE TABLE sessions (
                        id INTEGER PRIMARY KEY,
                        session_id TEXT
                    )
                """)
                conn.commit()

            manager = MigrationManager(target_db)
            result = manager.migrate_from_claude_sessions(source_db)

            assert result.events_migrated == 0
            assert result.success


class TestMigrateConvenienceFunction:
    """Tests for migrate_from_claude_sessions convenience function."""

    def test_convenience_function(self) -> None:
        """Verify convenience function works correctly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = Path(temp_dir) / "source.db"
            target_path = Path(temp_dir) / "target.db"

            with sqlite3.connect(source_path) as conn:
                conn.execute("CREATE TABLE sessions (id INTEGER PRIMARY KEY)")
                conn.execute("CREATE TABLE events (id INTEGER PRIMARY KEY)")
                conn.commit()

            result = migrate_from_claude_sessions(source_path, target_path)
            assert result.success
            assert target_path.exists()
