"""Vendor adapter implementations.

This package contains adapter classes for different AI assistant platforms,
providing a unified interface for vendor-specific operations.
"""

from ai_asst_mgr.adapters.base import VendorAdapter, VendorInfo, VendorStatus
from ai_asst_mgr.adapters.claude import ClaudeAdapter
from ai_asst_mgr.adapters.gemini import GeminiAdapter

__all__ = ["ClaudeAdapter", "GeminiAdapter", "VendorAdapter", "VendorInfo", "VendorStatus"]
