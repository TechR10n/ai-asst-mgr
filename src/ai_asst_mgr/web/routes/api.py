"""JSON API routes for the web dashboard.

This module provides RESTful API endpoints for retrieving
statistics, vendor information, coaching insights, and agent data.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Query

from ai_asst_mgr.capabilities import UniversalAgentManager
from ai_asst_mgr.vendors import VendorRegistry
from ai_asst_mgr.web.services import (
    get_agents_data,
    get_coaching_data,
    get_session_detail,
    get_sessions_data,
    get_sessions_stats,
    get_stats_data,
    get_vendors_data,
)

router = APIRouter(tags=["api"])


@router.get("/stats")
async def get_stats() -> dict[str, Any]:
    """Get overall statistics.

    Returns:
        Dictionary containing overall statistics.
    """
    return get_stats_data()


@router.get("/vendors")
async def get_vendors() -> dict[str, Any]:
    """Get vendor list with status.

    Returns:
        Dictionary containing vendor information.
    """
    return get_vendors_data()


@router.get("/coaching")
async def get_coaching() -> dict[str, Any]:
    """Get coaching insights.

    Returns:
        Dictionary containing coaching data.
    """
    return get_coaching_data()


@router.get("/agents")
async def get_agents() -> dict[str, Any]:
    """Get agent list.

    Returns:
        Dictionary containing agent data.
    """
    return get_agents_data()


@router.get("/sessions")
async def get_sessions(
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    project: str | None = Query(default=None),
) -> dict[str, Any]:
    """Get session history.

    Args:
        limit: Maximum number of sessions to return.
        offset: Number of sessions to skip.
        project: Optional project path filter.

    Returns:
        Dictionary containing session data.
    """
    return get_sessions_data(limit=limit, offset=offset, project_filter=project)


@router.get("/sessions/stats")
async def get_session_stats() -> dict[str, Any]:
    """Get session statistics.

    Returns:
        Dictionary containing session statistics.
    """
    return get_sessions_stats()


@router.get("/sessions/{session_id}")
async def get_session(session_id: str) -> dict[str, Any]:
    """Get details for a specific session.

    Args:
        session_id: The session ID to look up.

    Returns:
        Dictionary containing session details.
    """
    return get_session_detail(session_id)


@router.get("/agents/{vendor_id}/{agent_name}")
async def get_agent_detail(vendor_id: str, agent_name: str) -> dict[str, Any]:
    """Get details for a specific agent.

    Args:
        vendor_id: The vendor ID.
        agent_name: The agent name.

    Returns:
        Dictionary containing agent details.
    """
    registry = VendorRegistry()
    vendors = registry.get_installed_vendors()
    manager = UniversalAgentManager(vendors)
    agent = manager.get_agent(agent_name, vendor_id)

    if agent:
        return {
            "agent": {
                "name": agent.name,
                "vendor": agent.vendor_id,
                "type": agent.agent_type.value,
                "description": agent.description,
                "file_path": str(agent.file_path) if agent.file_path else None,
                "content": agent.content[:500] if agent.content else None,
                "metadata": agent.metadata,
            },
            "found": True,
        }
    return {"agent": None, "found": False, "error": "Agent not found"}
