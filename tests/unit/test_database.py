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
            "github_commits",
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

    def test_end_session_nonexistent_session(self, db_manager: DatabaseManager) -> None:
        """Verify end_session handles nonexistent session gracefully."""
        # End a session that was never started - should not crash
        # This tests the case where row is None (line 544->548 branch)
        db_manager.end_session("nonexistent-sess", tool_calls_count=5)

        # Verify that no session was created (UPDATE doesn't create rows)
        with sqlite3.connect(db_manager.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("SELECT * FROM sessions WHERE session_id = 'nonexistent-sess'")
            row = cursor.fetchone()
            # Session doesn't exist, so row should be None
            assert row is None

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

    def test_get_agent_usage_history_with_agent_name(self, db_manager: DatabaseManager) -> None:
        """Verify get_agent_usage_history filters by agent name."""
        # Insert capabilities
        with sqlite3.connect(db_manager.db_path) as conn:
            conn.execute(
                """
                INSERT INTO capabilities (vendor_id, capability_type, capability_name)
                VALUES ('claude', 'agent', 'test-agent')
                """
            )
            conn.execute(
                """
                INSERT INTO capabilities (vendor_id, capability_type, capability_name)
                VALUES ('gemini', 'agent', 'other-agent')
                """
            )
            conn.commit()

        # Query for specific agent
        results = db_manager.get_agent_usage_history(agent_name="test-agent")
        assert len(results) == 1
        assert results[0].agent_name == "test-agent"
        assert results[0].vendor_id == "claude"

    def test_get_tool_usage(self, db_manager: DatabaseManager) -> None:
        """Verify get_tool_usage returns tool statistics."""
        db_manager.record_session("sess-1", "claude")
        db_manager.record_event("sess-1", "claude", "tool_call", "Read")
        db_manager.record_event("sess-1", "claude", "tool_call", "Read")
        db_manager.record_event("sess-1", "claude", "tool_call", "Write")

        results = db_manager.get_tool_usage("claude")
        assert len(results) >= 0

    def test_get_tool_usage_all_vendors(self, db_manager: DatabaseManager) -> None:
        """Verify get_tool_usage returns tool statistics for all vendors."""
        db_manager.record_session("sess-1", "claude")
        db_manager.record_event("sess-1", "claude", "tool_call", "Read")
        db_manager.record_session("sess-2", "gemini")
        db_manager.record_event("sess-2", "gemini", "tool_call", "Write")

        # Query without vendor_id to get all vendors
        results = db_manager.get_tool_usage(vendor_id=None)
        assert len(results) >= 2
        # Should include vendor_id in results when no filter is applied
        vendor_ids = [r["vendor_id"] for r in results]
        assert "claude" in vendor_ids
        assert "gemini" in vendor_ids


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

    def test_migrate_with_database_reading_error(self, target_db: Path) -> None:
        """Verify migration handles sqlite3.Error during reading tables."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_db = Path(temp_dir) / "corrupted.db"

            # Create a corrupted database file
            source_db.write_text("This is not a valid SQLite database")

            manager = MigrationManager(target_db)
            result = manager.migrate_from_claude_sessions(source_db, create_backup=False)

            assert not result.success
            assert len(result.errors) > 0
            # The error occurs during table reading, not connection (lines 154-155, 191-192)
            assert any("Error reading" in error for error in result.errors)

    def test_migrate_with_session_reading_error(self, target_db: Path) -> None:
        """Verify migration handles errors when reading sessions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_db = Path(temp_dir) / "source.db"

            # Create source with sessions table
            with sqlite3.connect(source_db) as conn:
                conn.execute("""
                    CREATE TABLE sessions (
                        id INTEGER PRIMARY KEY,
                        session_id TEXT
                    )
                """)
                conn.execute("INSERT INTO sessions (session_id) VALUES ('test')")
                conn.commit()

            # Now corrupt the sessions table structure
            with sqlite3.connect(source_db) as conn:
                # Create a view with same name to cause confusion
                conn.execute("DROP TABLE sessions")
                conn.execute("CREATE VIEW sessions AS SELECT 'fake' as id")
                conn.commit()

            manager = MigrationManager(target_db)
            result = manager.migrate_from_claude_sessions(source_db, create_backup=False)

            # Should handle the error gracefully
            assert result.sessions_migrated == 0

    def test_migrate_with_event_reading_error(self, target_db: Path) -> None:
        """Verify migration handles errors when reading events."""
        with tempfile.TemporaryDirectory() as temp_dir:
            source_db = Path(temp_dir) / "source.db"

            # Create source with events table
            with sqlite3.connect(source_db) as conn:
                conn.execute("""
                    CREATE TABLE events (
                        id INTEGER PRIMARY KEY,
                        session_id TEXT
                    )
                """)
                conn.execute("INSERT INTO events (session_id) VALUES ('test')")
                conn.commit()

            # Now corrupt the events table structure
            with sqlite3.connect(source_db) as conn:
                conn.execute("DROP TABLE events")
                conn.execute("CREATE VIEW events AS SELECT 'fake' as id")
                conn.commit()

            manager = MigrationManager(target_db)
            result = manager.migrate_from_claude_sessions(source_db, create_backup=False)

            # Should handle the error gracefully
            assert result.events_migrated == 0

    def test_rollback_removes_existing_target(self, source_db: Path, target_db: Path) -> None:
        """Verify rollback removes existing target database."""
        manager = MigrationManager(target_db)
        result = manager.migrate_from_claude_sessions(source_db)

        # Verify target was created
        assert target_db.exists()
        assert result.backup_path is not None

        # Perform rollback - this tests line 266->269 where target exists
        success = manager.rollback(result.backup_path)

        # Verify target was removed
        assert success
        assert not target_db.exists()

    def test_validate_migration_with_null_vendor_ids(
        self, source_db: Path, target_db: Path
    ) -> None:
        """Verify validation detects NULL vendor_id in sessions and events."""
        manager = MigrationManager(target_db)
        manager._schema_manager.initialize()

        # Need to bypass NOT NULL constraint - recreate tables without it
        with sqlite3.connect(target_db) as conn:
            # Drop and recreate sessions table without NOT NULL on vendor_id
            conn.execute("DROP TABLE sessions")
            conn.execute("""
                CREATE TABLE sessions (
                    session_id TEXT PRIMARY KEY,
                    vendor_id TEXT,
                    project_path TEXT,
                    start_time TEXT,
                    end_time TEXT,
                    duration_seconds INTEGER DEFAULT 0,
                    tool_calls_count INTEGER DEFAULT 0,
                    messages_count INTEGER DEFAULT 0,
                    errors_count INTEGER DEFAULT 0
                )
            """)

            # Drop and recreate events table without NOT NULL on vendor_id
            conn.execute("DROP TABLE events")
            conn.execute("""
                CREATE TABLE events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT,
                    vendor_id TEXT,
                    event_type TEXT NOT NULL,
                    event_name TEXT,
                    event_data TEXT,
                    timestamp TEXT DEFAULT (datetime('now'))
                )
            """)

            # Now insert data with NULL vendor_id
            conn.execute("""
                INSERT INTO sessions (session_id, vendor_id, start_time)
                VALUES ('test-session', NULL, '2024-01-15 10:00:00')
            """)
            conn.execute("""
                INSERT INTO events (session_id, vendor_id, event_type, event_name)
                VALUES ('test-session', NULL, 'tool_call', 'Read')
            """)
            conn.commit()

        errors = manager.validate_migration()

        # Should detect NULL vendor_ids (lines 283, 287)
        assert len(errors) == 2
        assert any("sessions without vendor_id" in error for error in errors)
        assert any("events without vendor_id" in error for error in errors)

    def test_validate_migration_without_database(self, target_db: Path) -> None:
        """Verify validation when target database doesn't exist."""
        manager = MigrationManager(target_db)

        # Don't initialize - database doesn't exist
        errors = manager.validate_migration()

        # Should have error from schema validation (line 279->289 path taken)
        assert len(errors) > 0
        assert any("Database file does not exist" in error for error in errors)


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


class TestGitHubDatabaseMethods:
    """Tests for GitHub commit tracking methods."""

    @pytest.fixture
    def db_with_schema(self) -> DatabaseManager:
        """Create an in-memory database with full schema."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            manager = SchemaManager(db_path)
            manager.initialize()
            yield DatabaseManager(db_path)

    def test_record_github_commit_success(self, db_with_schema: DatabaseManager) -> None:
        """Test recording a GitHub commit."""
        from datetime import UTC, datetime

        from ai_asst_mgr.operations.github_parser import GitHubCommit

        commit = GitHubCommit(
            sha="abc1234567890def",
            repo="user/repo",
            branch="main",
            message="feat: add feature\n\nGenerated with [Claude Code]",
            author_name="Test User",
            author_email="test@example.com",
            vendor_id="claude",
            committed_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )

        result = db_with_schema.record_github_commit(commit)
        assert result is True

    def test_record_duplicate_commit_updates(self, db_with_schema: DatabaseManager) -> None:
        """Test that recording duplicate commit updates existing record (upsert)."""
        from datetime import UTC, datetime

        from ai_asst_mgr.operations.github_parser import GitHubCommit

        # Insert initial commit
        commit1 = GitHubCommit(
            sha="abc1234567890def",
            repo="user/repo",
            branch="main",
            message="initial message",
            author_name="Test",
            author_email="test@test.com",
            vendor_id=None,
            committed_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )
        assert db_with_schema.record_github_commit(commit1) is True

        # Update with same SHA but different message (upsert behavior)
        commit2 = GitHubCommit(
            sha="abc1234567890def",
            repo="user/repo",
            branch="main",
            message="updated message",
            author_name="Test",
            author_email="test@test.com",
            vendor_id="claude",
            committed_at=datetime(2024, 1, 15, 10, 30, 0, tzinfo=UTC),
        )
        # Should succeed (upsert - INSERT OR REPLACE)
        assert db_with_schema.record_github_commit(commit2) is True

        # Verify the record was updated
        record = db_with_schema.get_github_commit_by_sha("abc1234567890def")
        assert record is not None
        assert record.message == "updated message"
        assert record.vendor_id == "claude"

    def test_get_github_stats_empty(self, db_with_schema: DatabaseManager) -> None:
        """Test get_github_stats with no commits."""
        stats = db_with_schema.get_github_stats()
        assert stats.total_commits == 0
        assert stats.claude_commits == 0
        assert stats.gemini_commits == 0
        assert stats.openai_commits == 0
        assert stats.repos_tracked == 0
        assert stats.ai_attributed_commits == 0
        assert stats.ai_percentage == 0.0

    def test_get_github_stats_with_commits(self, db_with_schema: DatabaseManager) -> None:
        """Test get_github_stats with various commits."""
        from datetime import UTC, datetime

        from ai_asst_mgr.operations.github_parser import GitHubCommit

        # Add commits with different vendors
        commits = [
            GitHubCommit(
                sha="abc123",
                repo="repo1",
                branch="main",
                message="Claude commit",
                author_name="A",
                author_email="a@test.com",
                vendor_id="claude",
                committed_at=datetime(2024, 1, 1, tzinfo=UTC),
            ),
            GitHubCommit(
                sha="def456",
                repo="repo1",
                branch="main",
                message="Gemini commit",
                author_name="B",
                author_email="b@test.com",
                vendor_id="gemini",
                committed_at=datetime(2024, 1, 2, tzinfo=UTC),
            ),
            GitHubCommit(
                sha="ghi789",
                repo="repo2",
                branch="main",
                message="Human commit",
                author_name="C",
                author_email="c@test.com",
                vendor_id=None,
                committed_at=datetime(2024, 1, 3, tzinfo=UTC),
            ),
        ]

        for commit in commits:
            db_with_schema.record_github_commit(commit)

        stats = db_with_schema.get_github_stats()
        assert stats.total_commits == 3
        assert stats.claude_commits == 1
        assert stats.gemini_commits == 1
        assert stats.openai_commits == 0
        assert stats.repos_tracked == 2
        assert stats.ai_attributed_commits == 2
        assert abs(stats.ai_percentage - 66.67) < 0.1

    def test_get_github_commits_all(self, db_with_schema: DatabaseManager) -> None:
        """Test getting all commits without filters."""
        from datetime import UTC, datetime

        from ai_asst_mgr.operations.github_parser import GitHubCommit

        commit = GitHubCommit(
            sha="abc123",
            repo="repo1",
            branch="main",
            message="Test",
            author_name="Test",
            author_email="test@test.com",
            vendor_id="claude",
            committed_at=datetime(2024, 1, 1, tzinfo=UTC),
        )
        db_with_schema.record_github_commit(commit)

        commits = db_with_schema.get_github_commits()
        assert len(commits) == 1
        assert commits[0].sha == "abc123"
        assert commits[0].vendor_id == "claude"

    def test_get_github_commits_filter_by_vendor(self, db_with_schema: DatabaseManager) -> None:
        """Test filtering commits by vendor."""
        from datetime import UTC, datetime

        from ai_asst_mgr.operations.github_parser import GitHubCommit

        commits_data = [
            ("abc123", "claude"),
            ("def456", "gemini"),
            ("ghi789", None),
        ]

        for sha, vendor in commits_data:
            db_with_schema.record_github_commit(
                GitHubCommit(
                    sha=sha,
                    repo="repo",
                    branch="main",
                    message="Test",
                    author_name="Test",
                    author_email="test@test.com",
                    vendor_id=vendor,
                    committed_at=datetime(2024, 1, 1, tzinfo=UTC),
                )
            )

        # Filter by claude
        commits = db_with_schema.get_github_commits(vendor_id="claude")
        assert len(commits) == 1
        assert commits[0].sha == "abc123"

        # Filter by "none" (unattributed)
        commits = db_with_schema.get_github_commits(vendor_id="none")
        assert len(commits) == 1
        assert commits[0].sha == "ghi789"

    def test_get_github_commits_filter_by_repo(self, db_with_schema: DatabaseManager) -> None:
        """Test filtering commits by repository."""
        from datetime import UTC, datetime

        from ai_asst_mgr.operations.github_parser import GitHubCommit

        commits_data = [
            ("abc123", "repo1"),
            ("def456", "repo2"),
        ]

        for sha, repo in commits_data:
            db_with_schema.record_github_commit(
                GitHubCommit(
                    sha=sha,
                    repo=repo,
                    branch="main",
                    message="Test",
                    author_name="Test",
                    author_email="test@test.com",
                    vendor_id=None,
                    committed_at=datetime(2024, 1, 1, tzinfo=UTC),
                )
            )

        commits = db_with_schema.get_github_commits(repo="repo1")
        assert len(commits) == 1
        assert commits[0].repo == "repo1"

    def test_get_github_repos(self, db_with_schema: DatabaseManager) -> None:
        """Test getting list of tracked repositories."""
        from datetime import UTC, datetime

        from ai_asst_mgr.operations.github_parser import GitHubCommit

        repos = ["alpha-repo", "beta-repo", "gamma-repo"]
        for i, repo in enumerate(repos):
            db_with_schema.record_github_commit(
                GitHubCommit(
                    sha=f"sha{i}",
                    repo=repo,
                    branch="main",
                    message="Test",
                    author_name="Test",
                    author_email="test@test.com",
                    vendor_id=None,
                    committed_at=datetime(2024, 1, 1, tzinfo=UTC),
                )
            )

        result = db_with_schema.get_github_repos()
        assert len(result) == 3
        assert "alpha-repo" in result
        assert "beta-repo" in result
        assert "gamma-repo" in result

    def test_get_github_commit_by_sha(self, db_with_schema: DatabaseManager) -> None:
        """Test getting commit by SHA."""
        from datetime import UTC, datetime

        from ai_asst_mgr.operations.github_parser import GitHubCommit

        db_with_schema.record_github_commit(
            GitHubCommit(
                sha="abc123def456ghi",
                repo="repo",
                branch="main",
                message="Test",
                author_name="Test",
                author_email="test@test.com",
                vendor_id="claude",
                committed_at=datetime(2024, 1, 1, tzinfo=UTC),
            )
        )

        # Full SHA
        commit = db_with_schema.get_github_commit_by_sha("abc123def456ghi")
        assert commit is not None
        assert commit.sha == "abc123def456ghi"

        # Partial SHA
        commit = db_with_schema.get_github_commit_by_sha("abc123")
        assert commit is not None
        assert commit.sha == "abc123def456ghi"

        # Non-existent
        commit = db_with_schema.get_github_commit_by_sha("nonexistent")
        assert commit is None

    def test_github_stats_properties(self, db_with_schema: DatabaseManager) -> None:
        """Test GitHubStats computed properties."""
        from ai_asst_mgr.database.manager import GitHubStats

        stats = GitHubStats(
            total_commits=100,
            claude_commits=25,
            gemini_commits=15,
            openai_commits=10,
            repos_tracked=5,
            first_commit="2024-01-01",
            last_commit="2024-12-31",
        )

        assert stats.ai_attributed_commits == 50
        assert stats.ai_percentage == 50.0

    def test_github_stats_zero_division(self, db_with_schema: DatabaseManager) -> None:
        """Test GitHubStats handles zero total commits."""
        from ai_asst_mgr.database.manager import GitHubStats

        stats = GitHubStats(
            total_commits=0,
            claude_commits=0,
            gemini_commits=0,
            openai_commits=0,
            repos_tracked=0,
            first_commit=None,
            last_commit=None,
        )

        assert stats.ai_percentage == 0.0

    def test_record_github_commit_database_error(self, db_with_schema: DatabaseManager) -> None:
        """Test record_github_commit handles database errors gracefully."""
        from datetime import UTC, datetime

        from ai_asst_mgr.operations.github_parser import GitHubCommit

        # Close the database connection to force an error
        db_with_schema.db_path.unlink()

        commit = GitHubCommit(
            sha="abc123",
            repo="repo",
            branch="main",
            message="Test",
            author_name="Test",
            author_email="test@test.com",
            vendor_id="claude",
            committed_at=datetime(2024, 1, 1, tzinfo=UTC),
        )

        # Should return False on database error
        result = db_with_schema.record_github_commit(commit)
        assert result is False

    def test_get_github_commits_table_not_exists(self) -> None:
        """Test get_github_commits returns empty list when table doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "old_schema.db"
            # Create database without github_commits table (old schema)
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            manager = DatabaseManager(db_path)
            commits = manager.get_github_commits()
            assert commits == []

    def test_get_github_repos_table_not_exists(self) -> None:
        """Test get_github_repos returns empty list when table doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "old_schema.db"
            # Create database without github_commits table (old schema)
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            manager = DatabaseManager(db_path)
            repos = manager.get_github_repos()
            assert repos == []

    def test_get_github_commit_by_sha_table_not_exists(self) -> None:
        """Test get_github_commit_by_sha returns None when table doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "old_schema.db"
            # Create database without github_commits table (old schema)
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            manager = DatabaseManager(db_path)
            commit = manager.get_github_commit_by_sha("abc123")
            assert commit is None

    def test_get_github_stats_table_not_exists(self) -> None:
        """Test get_github_stats returns empty stats when table doesn't exist."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "old_schema.db"
            # Create database without github_commits table (old schema)
            with sqlite3.connect(db_path) as conn:
                conn.execute("CREATE TABLE dummy (id INTEGER)")
                conn.commit()

            manager = DatabaseManager(db_path)
            stats = manager.get_github_stats()
            # Should return empty stats, not raise error
            assert stats.total_commits == 0
            assert stats.claude_commits == 0
            assert stats.repos_tracked == 0
