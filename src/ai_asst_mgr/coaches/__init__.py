"""Coaching system for AI assistant usage optimization.

This module provides coaching functionality to analyze usage patterns
and generate recommendations for optimizing AI assistant workflows.
"""

from __future__ import annotations

from ai_asst_mgr.coaches.base import (
    CoachBase,
    Insight,
    Priority,
    Recommendation,
    UsageReport,
)
from ai_asst_mgr.coaches.claude import ClaudeCoach
from ai_asst_mgr.coaches.gemini import GeminiCoach
from ai_asst_mgr.coaches.openai import CodexCoach

__all__ = [
    "ClaudeCoach",
    "CoachBase",
    "CodexCoach",
    "GeminiCoach",
    "Insight",
    "Priority",
    "Recommendation",
    "UsageReport",
]
