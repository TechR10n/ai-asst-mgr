"""FastAPI application factory for the web dashboard.

This module creates and configures the FastAPI application with
templates, static files, and route handlers.
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from ai_asst_mgr.web.routes.api import router as api_router
from ai_asst_mgr.web.routes.pages import router as pages_router

# Module paths
WEB_DIR = Path(__file__).parent
TEMPLATES_DIR = WEB_DIR / "templates"
STATIC_DIR = WEB_DIR / "static"


class AppState:
    """Application state container for shared resources."""

    def __init__(self) -> None:
        """Initialize application state."""
        self.templates: Jinja2Templates = Jinja2Templates(directory=str(TEMPLATES_DIR))


def create_app() -> FastAPI:
    """Create and configure the FastAPI application.

    Returns:
        Configured FastAPI application instance.
    """
    app = FastAPI(
        title="AI Assistant Manager",
        description="Web dashboard for managing AI assistant configurations",
        version="0.1.0",
    )

    # Initialize application state with templates
    app.state.app_state = AppState()

    # Mount static files
    if STATIC_DIR.exists():
        app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

    # Register error handlers
    _register_error_handlers(app)

    # Register routes
    app.include_router(pages_router)
    app.include_router(api_router, prefix="/api")

    return app


def _register_error_handlers(app: FastAPI) -> None:
    """Register custom error handlers.

    Args:
        app: The FastAPI application instance.
    """

    @app.exception_handler(404)  # type: ignore[misc]
    async def not_found_handler(request: Request, _exc: Exception) -> HTMLResponse | JSONResponse:
        """Handle 404 Not Found errors."""
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=404,
                content={"error": "Not found", "path": str(request.url.path)},
            )
        templates = request.app.state.app_state.templates
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"error_code": 404, "error_message": "Page not found"},
            status_code=404,
        )

    @app.exception_handler(500)  # type: ignore[misc]
    async def server_error_handler(
        request: Request, _exc: Exception
    ) -> HTMLResponse | JSONResponse:
        """Handle 500 Internal Server errors."""
        if request.url.path.startswith("/api/"):
            return JSONResponse(
                status_code=500,
                content={"error": "Internal server error"},
            )
        templates = request.app.state.app_state.templates
        return templates.TemplateResponse(
            request=request,
            name="error.html",
            context={"error_code": 500, "error_message": "Internal server error"},
            status_code=500,
        )
