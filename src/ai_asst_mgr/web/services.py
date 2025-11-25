"""Service functions for the web dashboard.

This module provides data retrieval functions that integrate with
the existing ai-asst-mgr adapters, coaches, and audit systems.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from ai_asst_mgr.coaches import ClaudeCoach, CoachBase, CodexCoach, GeminiCoach
from ai_asst_mgr.database import DatabaseManager
from ai_asst_mgr.database.sync import DEFAULT_DB_PATH, get_sync_status
from ai_asst_mgr.vendors import VendorRegistry

_logger = logging.getLogger(__name__)

# Mapping of vendor IDs to coach classes
_COACH_REGISTRY: dict[str, type[CoachBase]] = {
    "claude": ClaudeCoach,
    "gemini": GeminiCoach,
    "openai": CodexCoach,
}


def get_coach(vendor_id: str) -> CoachBase | None:
    """Get coach instance for a vendor.

    Args:
        vendor_id: The vendor identifier.

    Returns:
        The coach instance, or None if not found.
    """
    coach_class = _COACH_REGISTRY.get(vendor_id)
    if coach_class:
        return coach_class()
    return None


def get_installed_vendors() -> list[str]:
    """Get list of installed vendor IDs.

    Returns:
        List of vendor IDs that are installed.
    """
    registry = VendorRegistry()
    return list(registry.get_installed_vendors().keys())


def get_vendor_adapter(vendor_id: str) -> Any:  # noqa: ANN401
    """Get vendor adapter by ID.

    Args:
        vendor_id: The vendor identifier.

    Returns:
        The vendor adapter, or None if not found.

    Note:
        Returns Any because concrete adapters have additional methods
        beyond the VendorAdapter base class (e.g., list_agents).
    """
    registry = VendorRegistry()
    return registry.get_vendor(vendor_id)


def get_dashboard_data() -> dict[str, Any]:
    """Get data for the dashboard page.

    Returns:
        Dictionary containing dashboard statistics and summaries.
    """
    vendors = get_installed_vendors()
    vendor_stats = []

    for vendor_id in vendors:
        adapter = get_vendor_adapter(vendor_id)
        if adapter:
            config_dir = adapter.info.config_dir
            vendor_stats.append(
                {
                    "id": vendor_id,
                    "name": adapter.info.name,
                    "installed": adapter.is_installed(),
                    "config_exists": config_dir.exists() if config_dir else False,
                }
            )

    return {
        "title": "Dashboard",
        "vendors": vendor_stats,
        "total_vendors": len(vendors),
        "installed_count": sum(1 for v in vendor_stats if v["installed"]),
        "last_updated": datetime.now(tz=UTC).isoformat(),
    }


def get_agents_data() -> dict[str, Any]:
    """Get data for the agents browser page.

    Returns:
        Dictionary containing agent information by vendor.
    """
    vendors = get_installed_vendors()
    agents_by_vendor: dict[str, list[dict[str, Any]]] = {}

    for vendor_id in vendors:
        adapter = get_vendor_adapter(vendor_id)
        if adapter and adapter.is_installed():
            try:
                agents = adapter.list_agents()
                agents_by_vendor[vendor_id] = [
                    {"name": agent, "vendor": vendor_id} for agent in agents
                ]
            except (AttributeError, NotImplementedError):
                _logger.debug("Adapter %s does not support list_agents", vendor_id)
                agents_by_vendor[vendor_id] = []

    total_agents = sum(len(agents) for agents in agents_by_vendor.values())

    return {
        "title": "Agents",
        "agents_by_vendor": agents_by_vendor,
        "total_agents": total_agents,
        "last_updated": datetime.now(tz=UTC).isoformat(),
    }


def get_weekly_review_data() -> dict[str, Any]:
    """Get data for the weekly review page.

    Returns:
        Dictionary containing weekly activity summary.
    """
    vendors = get_installed_vendors()
    vendor_summaries = []

    for vendor_id in vendors:
        adapter = get_vendor_adapter(vendor_id)
        if adapter and adapter.is_installed():
            vendor_summaries.append(
                {
                    "id": vendor_id,
                    "name": adapter.info.name,
                    "status": "active",
                }
            )

    return {
        "title": "Weekly Review",
        "vendors": vendor_summaries,
        "period": "This Week",
        "last_updated": datetime.now(tz=UTC).isoformat(),
    }


def get_stats_data() -> dict[str, Any]:
    """Get overall statistics for the API.

    Returns:
        Dictionary containing overall statistics.
    """
    vendors = get_installed_vendors()
    installed_count = 0
    total_agents = 0

    for vendor_id in vendors:
        adapter = get_vendor_adapter(vendor_id)
        if adapter and adapter.is_installed():
            installed_count += 1
            try:
                agents = adapter.list_agents()
                total_agents += len(agents)
            except (AttributeError, NotImplementedError):
                _logger.debug("Adapter %s does not support list_agents", vendor_id)

    return {
        "total_vendors": len(vendors),
        "installed_vendors": installed_count,
        "total_agents": total_agents,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }


def get_vendors_data() -> dict[str, Any]:
    """Get vendor list with status for the API.

    Returns:
        Dictionary containing vendor information.
    """
    vendors = get_installed_vendors()
    vendor_list = []

    for vendor_id in vendors:
        adapter = get_vendor_adapter(vendor_id)
        if adapter:
            config_dir = adapter.info.config_dir
            vendor_list.append(
                {
                    "id": vendor_id,
                    "name": adapter.info.name,
                    "installed": adapter.is_installed(),
                    "config_path": str(config_dir) if config_dir else None,
                    "config_exists": config_dir.exists() if config_dir else False,
                }
            )

    return {
        "vendors": vendor_list,
        "count": len(vendor_list),
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }


def get_coaching_data() -> dict[str, Any]:
    """Get coaching insights for the API.

    Returns:
        Dictionary containing coaching data.
    """
    vendors = get_installed_vendors()
    coaching_insights = []

    for vendor_id in vendors:
        coach = get_coach(vendor_id)
        if coach:
            try:
                insights = coach.get_insights()
                coaching_insights.append(
                    {
                        "vendor": vendor_id,
                        "insights": insights,
                    }
                )
            except (AttributeError, NotImplementedError) as e:
                _logger.debug("Failed to get coaching insights for %s: %s", vendor_id, e)
                coaching_insights.append(
                    {
                        "vendor": vendor_id,
                        "insights": [],
                        "error": "Failed to get insights",
                    }
                )

    return {
        "coaching": coaching_insights,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }


def _get_db() -> DatabaseManager | None:
    """Get database manager if database exists.

    Returns:
        DatabaseManager instance or None if not initialized.
    """
    if DEFAULT_DB_PATH.exists():
        return DatabaseManager(DEFAULT_DB_PATH)
    return None


def get_sessions_data(
    limit: int = 50,
    offset: int = 0,
    project_filter: str | None = None,
) -> dict[str, Any]:
    """Get session history data for the sessions page.

    Args:
        limit: Maximum number of sessions to return.
        offset: Number of sessions to skip.
        project_filter: Optional project path filter.

    Returns:
        Dictionary containing session history.
    """
    db = _get_db()
    if not db:
        return {
            "title": "Sessions",
            "sessions": [],
            "total_sessions": 0,
            "total_messages": 0,
            "projects": [],
            "sync_status": None,
            "db_initialized": False,
            "last_updated": datetime.now(tz=UTC).isoformat(),
        }

    # Get sync status
    sync_status = get_sync_status(db)

    # Query sessions
    with db._connection() as conn:
        # Get distinct projects for filter dropdown
        cursor = conn.execute(
            "SELECT DISTINCT project_path FROM sessions "
            "WHERE vendor_id = 'claude' ORDER BY project_path"
        )
        projects = [row[0] for row in cursor.fetchall() if row[0]]

        # Build query with optional filter
        query = """
            SELECT session_id, project_path, start_time, end_time,
                   duration_seconds, messages_count
            FROM sessions
            WHERE vendor_id = 'claude'
        """
        params: list[Any] = []

        if project_filter:
            query += " AND project_path = ?"
            params.append(project_filter)

        query += " ORDER BY start_time DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])

        cursor = conn.execute(query, params)
        sessions = []
        for row in cursor.fetchall():
            sessions.append(
                {
                    "session_id": row[0],
                    "project": row[1] or "Unknown",
                    "start_time": row[2],
                    "end_time": row[3],
                    "duration_seconds": row[4] or 0,
                    "messages_count": row[5] or 0,
                }
            )

        # Get total count
        count_query = "SELECT COUNT(*) FROM sessions WHERE vendor_id = 'claude'"
        count_params: list[Any] = []
        if project_filter:
            count_query += " AND project_path = ?"
            count_params.append(project_filter)
        cursor = conn.execute(count_query, count_params)
        total_sessions = cursor.fetchone()[0]

    return {
        "title": "Sessions",
        "sessions": sessions,
        "total_sessions": total_sessions,
        "total_messages": sync_status.get("database_events", 0),
        "projects": projects,
        "current_filter": project_filter,
        "sync_status": sync_status,
        "db_initialized": True,
        "last_updated": datetime.now(tz=UTC).isoformat(),
    }


def get_session_detail(session_id: str) -> dict[str, Any]:
    """Get detailed information for a specific session.

    Args:
        session_id: The session ID to look up.

    Returns:
        Dictionary containing session detail.
    """
    db = _get_db()
    if not db:
        return {"error": "Database not initialized", "session": None}

    with db._connection() as conn:
        # Get session info
        cursor = conn.execute(
            """
            SELECT session_id, project_path, start_time, end_time,
                   duration_seconds, messages_count
            FROM sessions
            WHERE session_id = ? AND vendor_id = 'claude'
            """,
            (session_id,),
        )
        row = cursor.fetchone()

        if not row:
            return {"error": "Session not found", "session": None}

        session = {
            "session_id": row[0],
            "project": row[1] or "Unknown",
            "start_time": row[2],
            "end_time": row[3],
            "duration_seconds": row[4] or 0,
            "messages_count": row[5] or 0,
        }

        # Get events for this session
        cursor = conn.execute(
            """
            SELECT event_type, event_name, event_data, timestamp
            FROM events
            WHERE session_id = ? AND vendor_id = 'claude'
            ORDER BY timestamp
            """,
            (session_id,),
        )
        events = []
        for event_row in cursor.fetchall():
            events.append(
                {
                    "event_type": event_row[0],
                    "event_name": event_row[1],
                    "event_data": event_row[2],
                    "timestamp": event_row[3],
                }
            )

    return {
        "session": session,
        "events": events,
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }


def get_sessions_stats() -> dict[str, Any]:
    """Get session statistics for the API.

    Returns:
        Dictionary containing session statistics.
    """
    db = _get_db()
    if not db:
        return {
            "db_initialized": False,
            "total_sessions": 0,
            "total_messages": 0,
            "projects_count": 0,
            "last_synced": None,
            "timestamp": datetime.now(tz=UTC).isoformat(),
        }

    sync_status = get_sync_status(db)

    with db._connection() as conn:
        # Get project count
        cursor = conn.execute(
            "SELECT COUNT(DISTINCT project_path) FROM sessions WHERE vendor_id = 'claude'"
        )
        projects_count = cursor.fetchone()[0]

    return {
        "db_initialized": True,
        "total_sessions": sync_status.get("database_sessions", 0),
        "total_messages": sync_status.get("database_events", 0),
        "projects_count": projects_count,
        "last_synced": sync_status.get("last_synced_datetime"),
        "timestamp": datetime.now(tz=UTC).isoformat(),
    }
