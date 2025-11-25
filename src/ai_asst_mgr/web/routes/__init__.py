"""Route handlers for the web dashboard."""

from ai_asst_mgr.web.routes.api import router as api_router
from ai_asst_mgr.web.routes.pages import router as pages_router

__all__ = ["api_router", "pages_router"]
