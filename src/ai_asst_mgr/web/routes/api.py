"""JSON API routes for the web dashboard.

This module provides RESTful API endpoints for retrieving
statistics, vendor information, coaching insights, and agent data.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from ai_asst_mgr.web.services import (
    get_agents_data,
    get_coaching_data,
    get_stats_data,
    get_vendors_data,
)

router = APIRouter(tags=["api"])


@router.get("/stats")  # type: ignore[misc]
async def get_stats() -> dict[str, Any]:
    """Get overall statistics.

    Returns:
        Dictionary containing overall statistics.
    """
    return get_stats_data()


@router.get("/vendors")  # type: ignore[misc]
async def get_vendors() -> dict[str, Any]:
    """Get vendor list with status.

    Returns:
        Dictionary containing vendor information.
    """
    return get_vendors_data()


@router.get("/coaching")  # type: ignore[misc]
async def get_coaching() -> dict[str, Any]:
    """Get coaching insights.

    Returns:
        Dictionary containing coaching data.
    """
    return get_coaching_data()


@router.get("/agents")  # type: ignore[misc]
async def get_agents() -> dict[str, Any]:
    """Get agent list.

    Returns:
        Dictionary containing agent data.
    """
    return get_agents_data()
