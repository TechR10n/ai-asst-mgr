"""Capabilities module for cross-vendor agent management.

This module provides unified access to agents and capabilities across
all supported AI assistant vendors.
"""

from ai_asst_mgr.capabilities.manager import (
    Agent,
    AgentType,
    UniversalAgentManager,
)

__all__ = [
    "Agent",
    "AgentType",
    "UniversalAgentManager",
]
