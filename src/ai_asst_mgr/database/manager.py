"""Database manager for vendor-agnostic session tracking.

This module provides the DatabaseManager class for all database operations
including querying, inserting, and aggregating session and event data.
"""

from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

from ai_asst_mgr.database.schema import SchemaManager

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@dataclass
class VendorStats:
    """Statistics for a single vendor."""

    vendor_id: str
    total_sessions: int
    total_tool_calls: int
    total_messages: int
    total_errors: int
    avg_duration_seconds: float
    first_session: str | None
    last_session: str | None


@dataclass
class DailyUsage:
    """Daily usage metrics."""

    date: str
    vendor_id: str
    session_count: int
    total_tool_calls: int
    total_messages: int
    total_errors: int
    avg_duration_seconds: float


@dataclass
class WeekStats:
    """Current week statistics."""

    week_start: str
    week_end: str
    total_sessions: int
    total_tool_calls: int
    total_messages: int
    total_errors: int
    sessions_by_vendor: dict[str, int]


@dataclass
class WeeklyReview:
    """Weekly review data."""

    id: int | None
    vendor_id: str | None
    week_start: str
    week_end: str
    total_sessions: int
    total_tool_calls: int
    total_messages: int
    total_errors: int
    average_session_duration: int
    top_tools: list[str]
    insights: list[str]
    recommendations: list[str]
    created_at: str | None


@dataclass
class AgentUsage:
    """Agent usage history."""

    agent_name: str
    vendor_id: str
    usage_count: int
    first_used: str
    last_used: str


class DatabaseManager:
    """Manages database operations for session tracking.

    This class provides methods for querying, inserting, and aggregating
    session and event data across all supported vendors.
    """

    def __init__(self, db_path: Path) -> None:
        """Initialize the database manager.

        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._schema_manager = SchemaManager(db_path)

    def initialize(self) -> None:
        """Initialize the database schema."""
        self._schema_manager.initialize()

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Create a database connection context manager.

        Yields:
            SQLite connection with row factory enabled.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def get_vendor_stats(self, vendor_id: str, days: int = 30) -> VendorStats | None:
        """Get usage statistics for a specific vendor.

        Args:
            vendor_id: The vendor identifier (claude, gemini, openai).
            days: Number of days to include in statistics.

        Returns:
            VendorStats object or None if no data found.
        """
        cutoff = (datetime.now(tz=UTC) - timedelta(days=days)).isoformat()

        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    vendor_id,
                    COUNT(*) as total_sessions,
                    COALESCE(SUM(tool_calls_count), 0) as total_tool_calls,
                    COALESCE(SUM(messages_count), 0) as total_messages,
                    COALESCE(SUM(errors_count), 0) as total_errors,
                    COALESCE(AVG(duration_seconds), 0) as avg_duration_seconds,
                    MIN(start_time) as first_session,
                    MAX(start_time) as last_session
                FROM sessions
                WHERE vendor_id = ? AND start_time >= ?
                GROUP BY vendor_id
                """,
                (vendor_id, cutoff),
            )
            row = cursor.fetchone()

        if row is None:
            return None

        return VendorStats(
            vendor_id=row["vendor_id"],
            total_sessions=row["total_sessions"],
            total_tool_calls=row["total_tool_calls"],
            total_messages=row["total_messages"],
            total_errors=row["total_errors"],
            avg_duration_seconds=float(row["avg_duration_seconds"]),
            first_session=row["first_session"],
            last_session=row["last_session"],
        )

    def get_vendor_stats_summary(self, days: int = 30) -> list[VendorStats]:
        """Get usage statistics for all vendors.

        Args:
            days: Number of days to include in statistics.

        Returns:
            List of VendorStats objects for each vendor with data.
        """
        cutoff = (datetime.now(tz=UTC) - timedelta(days=days)).isoformat()

        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    vendor_id,
                    COUNT(*) as total_sessions,
                    COALESCE(SUM(tool_calls_count), 0) as total_tool_calls,
                    COALESCE(SUM(messages_count), 0) as total_messages,
                    COALESCE(SUM(errors_count), 0) as total_errors,
                    COALESCE(AVG(duration_seconds), 0) as avg_duration_seconds,
                    MIN(start_time) as first_session,
                    MAX(start_time) as last_session
                FROM sessions
                WHERE start_time >= ?
                GROUP BY vendor_id
                ORDER BY total_sessions DESC
                """,
                (cutoff,),
            )
            rows = cursor.fetchall()

        return [
            VendorStats(
                vendor_id=row["vendor_id"],
                total_sessions=row["total_sessions"],
                total_tool_calls=row["total_tool_calls"],
                total_messages=row["total_messages"],
                total_errors=row["total_errors"],
                avg_duration_seconds=float(row["avg_duration_seconds"]),
                first_session=row["first_session"],
                last_session=row["last_session"],
            )
            for row in rows
        ]

    def get_daily_usage(self, days: int = 7) -> list[DailyUsage]:
        """Get daily usage metrics for charting.

        Args:
            days: Number of days to include.

        Returns:
            List of DailyUsage objects ordered by date.
        """
        cutoff = (datetime.now(tz=UTC) - timedelta(days=days)).strftime("%Y-%m-%d")

        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    usage_date as date,
                    vendor_id,
                    session_count,
                    COALESCE(total_tool_calls, 0) as total_tool_calls,
                    COALESCE(total_messages, 0) as total_messages,
                    COALESCE(total_errors, 0) as total_errors,
                    COALESCE(avg_duration_seconds, 0) as avg_duration_seconds
                FROM v_daily_usage
                WHERE usage_date >= ?
                ORDER BY usage_date ASC, vendor_id
                """,
                (cutoff,),
            )
            rows = cursor.fetchall()

        return [
            DailyUsage(
                date=row["date"],
                vendor_id=row["vendor_id"],
                session_count=row["session_count"],
                total_tool_calls=row["total_tool_calls"],
                total_messages=row["total_messages"],
                total_errors=row["total_errors"],
                avg_duration_seconds=float(row["avg_duration_seconds"]),
            )
            for row in rows
        ]

    def get_week_stats(self) -> WeekStats:
        """Get statistics for the current week.

        Returns:
            WeekStats object with current week data.
        """
        today = datetime.now(tz=UTC)
        week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")
        week_end = (today + timedelta(days=6 - today.weekday())).strftime("%Y-%m-%d")

        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    COUNT(*) as total_sessions,
                    COALESCE(SUM(tool_calls_count), 0) as total_tool_calls,
                    COALESCE(SUM(messages_count), 0) as total_messages,
                    COALESCE(SUM(errors_count), 0) as total_errors
                FROM sessions
                WHERE date(start_time) >= ? AND date(start_time) <= ?
                """,
                (week_start, week_end),
            )
            totals = cursor.fetchone()

            cursor = conn.execute(
                """
                SELECT vendor_id, COUNT(*) as count
                FROM sessions
                WHERE date(start_time) >= ? AND date(start_time) <= ?
                GROUP BY vendor_id
                """,
                (week_start, week_end),
            )
            vendor_rows = cursor.fetchall()

        sessions_by_vendor = {row["vendor_id"]: row["count"] for row in vendor_rows}

        return WeekStats(
            week_start=week_start,
            week_end=week_end,
            total_sessions=totals["total_sessions"] if totals else 0,
            total_tool_calls=totals["total_tool_calls"] if totals else 0,
            total_messages=totals["total_messages"] if totals else 0,
            total_errors=totals["total_errors"] if totals else 0,
            sessions_by_vendor=sessions_by_vendor,
        )

    def get_previous_reviews(self, limit: int = 10) -> list[WeeklyReview]:
        """Get previous weekly reviews.

        Args:
            limit: Maximum number of reviews to return.

        Returns:
            List of WeeklyReview objects ordered by date descending.
        """
        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT *
                FROM weekly_reviews
                ORDER BY week_start DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        return [
            WeeklyReview(
                id=row["id"],
                vendor_id=row["vendor_id"],
                week_start=row["week_start"],
                week_end=row["week_end"],
                total_sessions=row["total_sessions"],
                total_tool_calls=row["total_tool_calls"],
                total_messages=row["total_messages"],
                total_errors=row["total_errors"],
                average_session_duration=row["average_session_duration"],
                top_tools=json.loads(row["top_tools"]) if row["top_tools"] else [],
                insights=json.loads(row["insights"]) if row["insights"] else [],
                recommendations=(
                    json.loads(row["recommendations"]) if row["recommendations"] else []
                ),
                created_at=row["created_at"],
            )
            for row in rows
        ]

    def save_review(self, review: WeeklyReview) -> int:
        """Save a weekly review.

        Args:
            review: WeeklyReview object to save.

        Returns:
            The ID of the saved review.
        """
        with self._connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO weekly_reviews (
                    vendor_id, week_start, week_end, total_sessions,
                    total_tool_calls, total_messages, total_errors,
                    average_session_duration, top_tools, insights, recommendations
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    review.vendor_id,
                    review.week_start,
                    review.week_end,
                    review.total_sessions,
                    review.total_tool_calls,
                    review.total_messages,
                    review.total_errors,
                    review.average_session_duration,
                    json.dumps(review.top_tools),
                    json.dumps(review.insights),
                    json.dumps(review.recommendations),
                ),
            )
            conn.commit()
            return cursor.lastrowid or 0

    def get_agent_usage_history(
        self, agent_name: str | None = None, days: int = 30
    ) -> list[AgentUsage]:
        """Get agent usage history.

        Args:
            agent_name: Optional agent name to filter by.
            days: Number of days to include.

        Returns:
            List of AgentUsage objects.
        """
        cutoff = (datetime.now(tz=UTC) - timedelta(days=days)).isoformat()

        with self._connection() as conn:
            if agent_name:
                cursor = conn.execute(
                    """
                    SELECT
                        capability_name as agent_name,
                        vendor_id,
                        COUNT(*) as usage_count,
                        MIN(created_at) as first_used,
                        MAX(updated_at) as last_used
                    FROM capabilities
                    WHERE capability_type = 'agent'
                        AND capability_name = ?
                        AND created_at >= ?
                    GROUP BY capability_name, vendor_id
                    ORDER BY usage_count DESC
                    """,
                    (agent_name, cutoff),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT
                        capability_name as agent_name,
                        vendor_id,
                        COUNT(*) as usage_count,
                        MIN(created_at) as first_used,
                        MAX(updated_at) as last_used
                    FROM capabilities
                    WHERE capability_type = 'agent' AND created_at >= ?
                    GROUP BY capability_name, vendor_id
                    ORDER BY usage_count DESC
                    """,
                    (cutoff,),
                )
            rows = cursor.fetchall()

        return [
            AgentUsage(
                agent_name=row["agent_name"],
                vendor_id=row["vendor_id"],
                usage_count=row["usage_count"],
                first_used=row["first_used"],
                last_used=row["last_used"],
            )
            for row in rows
        ]

    def record_session(
        self,
        session_id: str,
        vendor_id: str,
        project_path: str | None = None,
        start_time: str | None = None,
    ) -> None:
        """Record a new session.

        Args:
            session_id: Unique session identifier.
            vendor_id: Vendor identifier.
            project_path: Optional project path.
            start_time: Optional start time (defaults to now).
        """
        start = start_time or datetime.now(tz=UTC).isoformat()

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (session_id, vendor_id, project_path, start_time)
                VALUES (?, ?, ?, ?)
                """,
                (session_id, vendor_id, project_path, start),
            )
            conn.commit()

    def end_session(
        self,
        session_id: str,
        tool_calls_count: int = 0,
        messages_count: int = 0,
        errors_count: int = 0,
    ) -> None:
        """End an existing session.

        Args:
            session_id: Session identifier to end.
            tool_calls_count: Total tool calls in session.
            messages_count: Total messages in session.
            errors_count: Total errors in session.
        """
        end_time = datetime.now(tz=UTC).isoformat()

        with self._connection() as conn:
            cursor = conn.execute(
                "SELECT start_time FROM sessions WHERE session_id = ?",
                (session_id,),
            )
            row = cursor.fetchone()

            duration = 0
            if row:
                start = datetime.fromisoformat(row["start_time"])
                duration = int((datetime.now(tz=UTC) - start).total_seconds())

            conn.execute(
                """
                UPDATE sessions SET
                    end_time = ?,
                    duration_seconds = ?,
                    tool_calls_count = ?,
                    messages_count = ?,
                    errors_count = ?
                WHERE session_id = ?
                """,
                (
                    end_time,
                    duration,
                    tool_calls_count,
                    messages_count,
                    errors_count,
                    session_id,
                ),
            )
            conn.commit()

    def record_event(
        self,
        session_id: str,
        vendor_id: str,
        event_type: str,
        event_name: str | None = None,
        event_data: dict[str, Any] | None = None,
    ) -> None:
        """Record an event within a session.

        Args:
            session_id: Session identifier.
            vendor_id: Vendor identifier.
            event_type: Type of event (tool_call, message, error).
            event_name: Optional event name.
            event_data: Optional event data dictionary.
        """
        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO events (session_id, vendor_id, event_type, event_name, event_data)
                VALUES (?, ?, ?, ?, ?)
                """,
                (
                    session_id,
                    vendor_id,
                    event_type,
                    event_name,
                    json.dumps(event_data) if event_data else None,
                ),
            )
            conn.commit()

    def get_tool_usage(self, vendor_id: str | None = None, days: int = 30) -> list[dict[str, Any]]:
        """Get tool usage statistics.

        Args:
            vendor_id: Optional vendor to filter by.
            days: Number of days to include.

        Returns:
            List of tool usage dictionaries.
        """
        cutoff = (datetime.now(tz=UTC) - timedelta(days=days)).isoformat()

        with self._connection() as conn:
            if vendor_id:
                cursor = conn.execute(
                    """
                    SELECT
                        event_name as tool_name,
                        COUNT(*) as usage_count,
                        MIN(timestamp) as first_used,
                        MAX(timestamp) as last_used
                    FROM events
                    WHERE event_type = 'tool_call'
                        AND vendor_id = ?
                        AND timestamp >= ?
                    GROUP BY event_name
                    ORDER BY usage_count DESC
                    """,
                    (vendor_id, cutoff),
                )
            else:
                cursor = conn.execute(
                    """
                    SELECT
                        vendor_id,
                        event_name as tool_name,
                        COUNT(*) as usage_count,
                        MIN(timestamp) as first_used,
                        MAX(timestamp) as last_used
                    FROM events
                    WHERE event_type = 'tool_call' AND timestamp >= ?
                    GROUP BY vendor_id, event_name
                    ORDER BY usage_count DESC
                    """,
                    (cutoff,),
                )
            rows = cursor.fetchall()

        return [dict(row) for row in rows]
