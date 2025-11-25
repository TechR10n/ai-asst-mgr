"""Web dashboard module for ai-asst-mgr.

This module provides a FastAPI-based web interface for viewing
AI assistant statistics, coaching insights, and agent management.
"""

from ai_asst_mgr.web.app import create_app

__all__ = ["create_app"]
