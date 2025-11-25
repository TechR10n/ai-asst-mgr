"""Database schema definitions for vendor-agnostic session tracking.

This module defines the SQLite schema for storing session data, events,
analytics, and vendor-specific configurations across Claude, Gemini, and OpenAI.
"""

from __future__ import annotations

import sqlite3
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from pathlib import Path

SCHEMA_VERSION = "1.0.0"

# Schema metadata table
SCHEMA_METADATA_SQL = """
CREATE TABLE IF NOT EXISTS schema_metadata (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL,
    updated_at TEXT DEFAULT (datetime('now'))
);
"""

# Vendor profiles table
VENDOR_PROFILES_SQL = """
CREATE TABLE IF NOT EXISTS vendor_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id TEXT NOT NULL UNIQUE,
    display_name TEXT NOT NULL,
    config_dir TEXT NOT NULL,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
"""

# Sessions table (vendor-agnostic)
SESSIONS_SQL = """
CREATE TABLE IF NOT EXISTS sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL UNIQUE,
    vendor_id TEXT NOT NULL,
    project_path TEXT,
    start_time TEXT NOT NULL,
    end_time TEXT,
    duration_seconds INTEGER,
    tool_calls_count INTEGER DEFAULT 0,
    messages_count INTEGER DEFAULT 0,
    errors_count INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (vendor_id) REFERENCES vendor_profiles(vendor_id)
);
"""

# Events table (vendor-agnostic)
EVENTS_SQL = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    vendor_id TEXT NOT NULL,
    event_type TEXT NOT NULL,
    event_name TEXT,
    event_data TEXT,
    timestamp TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (session_id) REFERENCES sessions(session_id),
    FOREIGN KEY (vendor_id) REFERENCES vendor_profiles(vendor_id)
);
"""

# Claude-specific: agent profiles
CLAUDE_AGENT_PROFILES_SQL = """
CREATE TABLE IF NOT EXISTS claude_agent_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    agent_name TEXT NOT NULL UNIQUE,
    description TEXT,
    model TEXT,
    tools TEXT,
    version TEXT,
    file_path TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
"""

# Claude-specific: skill profiles
CLAUDE_SKILL_PROFILES_SQL = """
CREATE TABLE IF NOT EXISTS claude_skill_profiles (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT NOT NULL UNIQUE,
    description TEXT,
    file_path TEXT,
    content_hash TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now'))
);
"""

# Weekly reviews table
WEEKLY_REVIEWS_SQL = """
CREATE TABLE IF NOT EXISTS weekly_reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id TEXT,
    week_start TEXT NOT NULL,
    week_end TEXT NOT NULL,
    total_sessions INTEGER DEFAULT 0,
    total_tool_calls INTEGER DEFAULT 0,
    total_messages INTEGER DEFAULT 0,
    total_errors INTEGER DEFAULT 0,
    average_session_duration INTEGER DEFAULT 0,
    top_tools TEXT,
    insights TEXT,
    recommendations TEXT,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (vendor_id) REFERENCES vendor_profiles(vendor_id)
);
"""

# Weekly aggregates table
WEEKLY_AGGREGATES_SQL = """
CREATE TABLE IF NOT EXISTS weekly_aggregates (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id TEXT NOT NULL,
    week_start TEXT NOT NULL,
    metric_name TEXT NOT NULL,
    metric_value REAL NOT NULL,
    created_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (vendor_id) REFERENCES vendor_profiles(vendor_id),
    UNIQUE(vendor_id, week_start, metric_name)
);
"""

# Coaching insights table
COACHING_INSIGHTS_SQL = """
CREATE TABLE IF NOT EXISTS coaching_insights (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id TEXT NOT NULL,
    insight_type TEXT NOT NULL,
    priority TEXT NOT NULL,
    title TEXT NOT NULL,
    description TEXT NOT NULL,
    action_items TEXT,
    is_resolved INTEGER DEFAULT 0,
    created_at TEXT DEFAULT (datetime('now')),
    resolved_at TEXT,
    FOREIGN KEY (vendor_id) REFERENCES vendor_profiles(vendor_id)
);
"""

# Capabilities table (vendor-agnostic)
CAPABILITIES_SQL = """
CREATE TABLE IF NOT EXISTS capabilities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    vendor_id TEXT NOT NULL,
    capability_type TEXT NOT NULL,
    capability_name TEXT NOT NULL,
    description TEXT,
    metadata TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TEXT DEFAULT (datetime('now')),
    updated_at TEXT DEFAULT (datetime('now')),
    FOREIGN KEY (vendor_id) REFERENCES vendor_profiles(vendor_id),
    UNIQUE(vendor_id, capability_type, capability_name)
);
"""

# Indexes
INDEXES_SQL = """
CREATE INDEX IF NOT EXISTS idx_sessions_vendor ON sessions(vendor_id);
CREATE INDEX IF NOT EXISTS idx_sessions_start_time ON sessions(start_time);
CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_vendor ON events(vendor_id);
CREATE INDEX IF NOT EXISTS idx_events_type ON events(event_type);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_weekly_reviews_vendor ON weekly_reviews(vendor_id);
CREATE INDEX IF NOT EXISTS idx_weekly_reviews_week ON weekly_reviews(week_start);
CREATE INDEX IF NOT EXISTS idx_weekly_agg_vendor_week ON weekly_aggregates(vendor_id, week_start);
CREATE INDEX IF NOT EXISTS idx_coaching_insights_vendor ON coaching_insights(vendor_id);
CREATE INDEX IF NOT EXISTS idx_capabilities_vendor ON capabilities(vendor_id);
CREATE INDEX IF NOT EXISTS idx_capabilities_type ON capabilities(capability_type);
"""

# Views
DAILY_USAGE_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_daily_usage AS
SELECT
    date(start_time) as usage_date,
    vendor_id,
    COUNT(*) as session_count,
    SUM(tool_calls_count) as total_tool_calls,
    SUM(messages_count) as total_messages,
    SUM(errors_count) as total_errors,
    AVG(duration_seconds) as avg_duration_seconds
FROM sessions
GROUP BY date(start_time), vendor_id;
"""

VENDOR_STATS_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_vendor_stats AS
SELECT
    vendor_id,
    COUNT(*) as total_sessions,
    SUM(tool_calls_count) as total_tool_calls,
    SUM(messages_count) as total_messages,
    SUM(errors_count) as total_errors,
    AVG(duration_seconds) as avg_duration_seconds,
    MIN(start_time) as first_session,
    MAX(start_time) as last_session
FROM sessions
GROUP BY vendor_id;
"""

TOOL_USAGE_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_tool_usage AS
SELECT
    vendor_id,
    event_name as tool_name,
    COUNT(*) as usage_count,
    date(MIN(timestamp)) as first_used,
    date(MAX(timestamp)) as last_used
FROM events
WHERE event_type = 'tool_call'
GROUP BY vendor_id, event_name;
"""

WEEKLY_SUMMARY_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_weekly_summary AS
SELECT
    vendor_id,
    strftime('%Y-W%W', start_time) as week,
    COUNT(*) as session_count,
    SUM(tool_calls_count) as total_tool_calls,
    SUM(messages_count) as total_messages,
    SUM(errors_count) as total_errors,
    AVG(duration_seconds) as avg_duration_seconds
FROM sessions
GROUP BY vendor_id, strftime('%Y-W%W', start_time);
"""

ERROR_SUMMARY_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_error_summary AS
SELECT
    vendor_id,
    event_name as error_type,
    COUNT(*) as error_count,
    date(MIN(timestamp)) as first_occurrence,
    date(MAX(timestamp)) as last_occurrence
FROM events
WHERE event_type = 'error'
GROUP BY vendor_id, event_name;
"""

SESSION_DETAILS_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_session_details AS
SELECT
    s.session_id,
    s.vendor_id,
    v.display_name as vendor_name,
    s.project_path,
    s.start_time,
    s.end_time,
    s.duration_seconds,
    s.tool_calls_count,
    s.messages_count,
    s.errors_count
FROM sessions s
LEFT JOIN vendor_profiles v ON s.vendor_id = v.vendor_id;
"""

CAPABILITY_SUMMARY_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_capability_summary AS
SELECT
    vendor_id,
    capability_type,
    COUNT(*) as count,
    SUM(CASE WHEN is_active = 1 THEN 1 ELSE 0 END) as active_count
FROM capabilities
GROUP BY vendor_id, capability_type;
"""

COACHING_STATUS_VIEW_SQL = """
CREATE VIEW IF NOT EXISTS v_coaching_status AS
SELECT
    vendor_id,
    priority,
    COUNT(*) as total_insights,
    SUM(CASE WHEN is_resolved = 0 THEN 1 ELSE 0 END) as pending_count,
    SUM(CASE WHEN is_resolved = 1 THEN 1 ELSE 0 END) as resolved_count
FROM coaching_insights
GROUP BY vendor_id, priority;
"""

# Default vendor profiles
DEFAULT_VENDORS_SQL = """
INSERT OR IGNORE INTO vendor_profiles (vendor_id, display_name, config_dir)
VALUES
    ('claude', 'Claude Code', '~/.claude'),
    ('gemini', 'Gemini CLI', '~/.gemini'),
    ('openai', 'OpenAI Codex', '~/.codex');
"""


def create_schema_sql() -> str:
    """Return the complete SQL for creating the database schema.

    Returns:
        Complete SQL string for schema creation.
    """
    return "\n".join(
        [
            SCHEMA_METADATA_SQL,
            VENDOR_PROFILES_SQL,
            SESSIONS_SQL,
            EVENTS_SQL,
            CLAUDE_AGENT_PROFILES_SQL,
            CLAUDE_SKILL_PROFILES_SQL,
            WEEKLY_REVIEWS_SQL,
            WEEKLY_AGGREGATES_SQL,
            COACHING_INSIGHTS_SQL,
            CAPABILITIES_SQL,
            INDEXES_SQL,
            DAILY_USAGE_VIEW_SQL,
            VENDOR_STATS_VIEW_SQL,
            TOOL_USAGE_VIEW_SQL,
            WEEKLY_SUMMARY_VIEW_SQL,
            ERROR_SUMMARY_VIEW_SQL,
            SESSION_DETAILS_VIEW_SQL,
            CAPABILITY_SUMMARY_VIEW_SQL,
            COACHING_STATUS_VIEW_SQL,
            DEFAULT_VENDORS_SQL,
        ]
    )


class SchemaManager:
    """Manages database schema creation and versioning.

    This class handles schema initialization, version tracking, and
    validation for the vendor-agnostic session database.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize the schema manager.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path

    def initialize(self) -> None:
        """Create the database schema if it doesn't exist."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            conn.executescript(create_schema_sql())
            conn.execute(
                "INSERT OR REPLACE INTO schema_metadata (key, value) VALUES (?, ?)",
                ("schema_version", SCHEMA_VERSION),
            )
            conn.commit()

    def get_version(self) -> str | None:
        """Get the current schema version.

        Returns:
            Schema version string, or None if not initialized.
        """
        if not self.db_path.exists():
            return None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                "SELECT value FROM schema_metadata WHERE key = ?",
                ("schema_version",),
            )
            row = cursor.fetchone()
            return row[0] if row else None

    def is_current(self) -> bool:
        """Check if the schema is at the current version.

        Returns:
            True if schema is current, False otherwise.
        """
        version = self.get_version()
        return version == SCHEMA_VERSION

    def needs_migration(self) -> bool:
        """Check if the database needs migration.

        Returns:
            True if migration is needed, False otherwise.
        """
        version = self.get_version()
        return version is not None and version != SCHEMA_VERSION

    def get_tables(self) -> list[str]:
        """Get list of tables in the database.

        Returns:
            List of table names.
        """
        if not self.db_path.exists():
            return []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
            return [row[0] for row in cursor.fetchall()]

    def get_views(self) -> list[str]:
        """Get list of views in the database.

        Returns:
            List of view names.
        """
        if not self.db_path.exists():
            return []

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT name FROM sqlite_master WHERE type='view' ORDER BY name")
            return [row[0] for row in cursor.fetchall()]

    def validate(self) -> list[str]:
        """Validate the database schema.

        Returns:
            List of validation errors (empty if valid).
        """
        errors: list[str] = []

        if not self.db_path.exists():
            errors.append("Database file does not exist")
            return errors

        expected_tables = {
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
        }

        expected_views = {
            "v_daily_usage",
            "v_vendor_stats",
            "v_tool_usage",
            "v_weekly_summary",
            "v_error_summary",
            "v_session_details",
            "v_capability_summary",
            "v_coaching_status",
        }

        actual_tables = set(self.get_tables())
        actual_views = set(self.get_views())

        missing_tables = expected_tables - actual_tables
        missing_views = expected_views - actual_views

        for table in missing_tables:
            errors.append(f"Missing table: {table}")

        for view in missing_views:
            errors.append(f"Missing view: {view}")

        version = self.get_version()
        if version is None:
            errors.append("Schema version not set")
        elif version != SCHEMA_VERSION:
            errors.append(f"Schema version mismatch: {version} != {SCHEMA_VERSION}")

        return errors
