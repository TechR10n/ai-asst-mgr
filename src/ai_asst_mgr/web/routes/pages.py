"""HTML page routes for the web dashboard.

This module provides routes that render HTML templates for the
dashboard, agents browser, and weekly review pages.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse

from ai_asst_mgr.web.services import (
    get_agents_data,
    get_dashboard_data,
    get_sessions_data,
    get_weekly_review_data,
)

if TYPE_CHECKING:
    from fastapi.templating import Jinja2Templates

router = APIRouter(tags=["pages"])


def _get_templates(request: Request) -> Jinja2Templates:
    """Get the Jinja2 templates instance from app state.

    Args:
        request: The incoming request.

    Returns:
        Jinja2Templates instance.
    """
    templates: Jinja2Templates = request.app.state.app_state.templates
    return templates


@router.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Render the main dashboard page.

    Args:
        request: The incoming request.

    Returns:
        Rendered HTML dashboard page.
    """
    templates = _get_templates(request)
    data = get_dashboard_data()
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"data": data},
    )


@router.get("/agents", response_class=HTMLResponse)
async def agents(request: Request) -> HTMLResponse:
    """Render the agents browser page.

    Args:
        request: The incoming request.

    Returns:
        Rendered HTML agents page.
    """
    templates = _get_templates(request)
    data = get_agents_data()
    return templates.TemplateResponse(
        request=request,
        name="agents.html",
        context={"data": data},
    )


@router.get("/review", response_class=HTMLResponse)
async def weekly_review(request: Request) -> HTMLResponse:
    """Render the weekly review page.

    Args:
        request: The incoming request.

    Returns:
        Rendered HTML weekly review page.
    """
    templates = _get_templates(request)
    data = get_weekly_review_data()
    return templates.TemplateResponse(
        request=request,
        name="review.html",
        context={"data": data},
    )


@router.get("/sessions", response_class=HTMLResponse)
async def sessions(
    request: Request,
    project: str | None = None,
) -> HTMLResponse:
    """Render the session history page.

    Args:
        request: The incoming request.
        project: Optional project filter.

    Returns:
        Rendered HTML sessions page.
    """
    templates = _get_templates(request)
    data = get_sessions_data(project_filter=project)
    return templates.TemplateResponse(
        request=request,
        name="sessions.html",
        context={"data": data},
    )
