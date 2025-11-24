"""Vendor adapter implementations.

This package contains adapter classes for different AI assistant platforms,
providing a unified interface for vendor-specific operations.
"""

from ai_asst_mgr.adapters.base import VendorAdapter, VendorInfo, VendorStatus

__all__ = ["VendorAdapter", "VendorInfo", "VendorStatus"]
