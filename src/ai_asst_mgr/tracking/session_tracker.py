"""Vendor-agnostic session tracker for AI assistant usage monitoring.

This module provides the VendorSessionTracker class for tracking sessions,
tool calls, messages, and errors across all supported AI assistant vendors.
"""

from __future__ import annotations

import hashlib
import re
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

from ai_asst_mgr.database.manager import DatabaseManager, VendorStats

if TYPE_CHECKING:
    from pathlib import Path


# Patterns for credential redaction
CREDENTIAL_PATTERNS = [
    (re.compile(r"(api[_-]?key\s*[=:]\s*)['\"]?[\w-]{20,}['\"]?", re.I), r"\1[REDACTED]"),
    (re.compile(r"(token\s*[=:]\s*)['\"]?[\w-]{20,}['\"]?", re.I), r"\1[REDACTED]"),
    (re.compile(r"(password\s*[=:]\s*)['\"]?[^\s'\"]+['\"]?", re.I), r"\1[REDACTED]"),
    (re.compile(r"(secret\s*[=:]\s*)['\"]?[\w-]{10,}['\"]?", re.I), r"\1[REDACTED]"),
    (re.compile(r"(bearer\s+)[\w-]{20,}", re.I), r"\1[REDACTED]"),
    (re.compile(r"(sk-[a-zA-Z0-9]{20,})"), "[REDACTED_API_KEY]"),
    (re.compile(r"(AIza[a-zA-Z0-9_-]{35})"), "[REDACTED_API_KEY]"),
]


@dataclass
class SessionContext:
    """Context for an active session."""

    session_id: str
    vendor_id: str
    project_path: str | None
    start_time: datetime
    tool_calls: int = 0
    messages: int = 0
    errors: int = 0
    events: list[dict[str, Any]] = field(default_factory=list)


class VendorSessionTracker:
    """Tracks AI assistant sessions across vendors.

    This class provides methods for starting and ending sessions,
    logging tool calls and messages, and tracking errors with
    automatic credential redaction.

    Attributes:
        db_path: Path to the SQLite database.
        vendor_id: Default vendor identifier for sessions.
    """

    def __init__(
        self,
        db_path: Path,
        vendor_id: str = "claude",
        *,
        auto_initialize: bool = True,
    ) -> None:
        """Initialize the session tracker.

        Args:
            db_path: Path to the SQLite database file.
            vendor_id: Default vendor identifier (claude, gemini, openai).
            auto_initialize: Whether to auto-initialize database schema.
        """
        self.db_path = db_path
        self.vendor_id = vendor_id
        self._db = DatabaseManager(db_path)
        self._active_sessions: dict[str, SessionContext] = {}

        if auto_initialize:
            self._db.initialize()

    def start_session(
        self,
        vendor_id: str | None = None,
        project_path: str | None = None,
        session_id: str | None = None,
    ) -> str:
        """Start a new tracking session.

        Args:
            vendor_id: Vendor identifier (defaults to instance default).
            project_path: Optional project path being worked on.
            session_id: Optional session ID (auto-generated if not provided).

        Returns:
            The session ID for the new session.
        """
        session_id = session_id or str(uuid.uuid4())
        vendor = vendor_id or self.vendor_id
        now = datetime.now(tz=UTC)

        context = SessionContext(
            session_id=session_id,
            vendor_id=vendor,
            project_path=project_path,
            start_time=now,
        )
        self._active_sessions[session_id] = context

        self._db.record_session(
            session_id=session_id,
            vendor_id=vendor,
            project_path=project_path,
            start_time=now.isoformat(),
        )

        return session_id

    def end_session(self, session_id: str) -> dict[str, Any]:
        """End an active session.

        Args:
            session_id: The session ID to end.

        Returns:
            Summary of the session including duration and counts.
        """
        context = self._active_sessions.pop(session_id, None)

        if context:
            self._db.end_session(
                session_id=session_id,
                tool_calls_count=context.tool_calls,
                messages_count=context.messages,
                errors_count=context.errors,
            )

            duration = (datetime.now(tz=UTC) - context.start_time).total_seconds()

            return {
                "session_id": session_id,
                "vendor_id": context.vendor_id,
                "duration_seconds": int(duration),
                "tool_calls": context.tool_calls,
                "messages": context.messages,
                "errors": context.errors,
            }

        self._db.end_session(session_id=session_id)
        return {"session_id": session_id}

    def log_tool_call(
        self,
        session_id: str,
        tool_name: str,
        vendor_id: str | None = None,
        *,
        tool_input: dict[str, Any] | None = None,
        tool_output: str | None = None,
        success: bool = True,
    ) -> None:
        """Log a tool call within a session.

        Args:
            session_id: The session ID.
            tool_name: Name of the tool called.
            vendor_id: Vendor ID (uses session vendor if not provided).
            tool_input: Optional tool input parameters.
            tool_output: Optional tool output (will be redacted).
            success: Whether the tool call succeeded.
        """
        context = self._active_sessions.get(session_id)
        vendor = vendor_id or (context.vendor_id if context else self.vendor_id)

        if context:
            context.tool_calls += 1

        event_data = {
            "tool_name": tool_name,
            "success": success,
        }

        if tool_input:
            event_data["input"] = self._redact_credentials(tool_input)

        if tool_output:
            event_data["output_hash"] = self._hash_content(tool_output)

        self._db.record_event(
            session_id=session_id,
            vendor_id=vendor,
            event_type="tool_call",
            event_name=tool_name,
            event_data=event_data,
        )

    def log_message(
        self,
        session_id: str,
        role: str,
        vendor_id: str | None = None,
        *,
        content_length: int | None = None,
    ) -> None:
        """Log a message within a session.

        Args:
            session_id: The session ID.
            role: Message role (user, assistant, system).
            vendor_id: Vendor ID (uses session vendor if not provided).
            content_length: Optional message content length.
        """
        context = self._active_sessions.get(session_id)
        vendor = vendor_id or (context.vendor_id if context else self.vendor_id)

        if context:
            context.messages += 1

        event_data: dict[str, Any] = {"role": role}
        if content_length is not None:
            event_data["content_length"] = content_length

        self._db.record_event(
            session_id=session_id,
            vendor_id=vendor,
            event_type="message",
            event_name=role,
            event_data=event_data,
        )

    def log_error(
        self,
        session_id: str,
        error_type: str,
        vendor_id: str | None = None,
        *,
        error_message: str | None = None,
    ) -> None:
        """Log an error within a session.

        Args:
            session_id: The session ID.
            error_type: Type of error that occurred.
            vendor_id: Vendor ID (uses session vendor if not provided).
            error_message: Optional error message (will be redacted).
        """
        context = self._active_sessions.get(session_id)
        vendor = vendor_id or (context.vendor_id if context else self.vendor_id)

        if context:
            context.errors += 1

        event_data: dict[str, Any] = {"error_type": error_type}
        if error_message:
            event_data["message"] = self._redact_text(error_message)

        self._db.record_event(
            session_id=session_id,
            vendor_id=vendor,
            event_type="error",
            event_name=error_type,
            event_data=event_data,
        )

    def get_active_sessions(self) -> list[str]:
        """Get list of active session IDs.

        Returns:
            List of currently active session IDs.
        """
        return list(self._active_sessions.keys())

    def get_session_stats(self, session_id: str) -> dict[str, Any] | None:
        """Get current statistics for an active session.

        Args:
            session_id: The session ID to get stats for.

        Returns:
            Session statistics or None if not found.
        """
        context = self._active_sessions.get(session_id)
        if not context:
            return None

        duration = (datetime.now(tz=UTC) - context.start_time).total_seconds()

        return {
            "session_id": session_id,
            "vendor_id": context.vendor_id,
            "project_path": context.project_path,
            "duration_seconds": int(duration),
            "tool_calls": context.tool_calls,
            "messages": context.messages,
            "errors": context.errors,
        }

    def get_vendor_stats(self, vendor_id: str | None = None, days: int = 30) -> VendorStats | None:
        """Get usage statistics for a vendor.

        Args:
            vendor_id: Vendor to get stats for (defaults to instance vendor).
            days: Number of days to include.

        Returns:
            VendorStats object or None.
        """
        vendor = vendor_id or self.vendor_id
        return self._db.get_vendor_stats(vendor, days)

    def _redact_credentials(self, data: dict[str, Any]) -> dict[str, Any]:
        """Redact credentials from a dictionary.

        Args:
            data: Dictionary to redact.

        Returns:
            Dictionary with sensitive values redacted.
        """
        result: dict[str, Any] = {}
        for key, value in data.items():
            if isinstance(value, str):
                result[key] = self._redact_text(value)
            elif isinstance(value, dict):
                result[key] = self._redact_credentials(value)
            else:
                result[key] = value
        return result

    def _redact_text(self, text: str) -> str:
        """Redact credentials from text.

        Args:
            text: Text to redact.

        Returns:
            Text with credentials redacted.
        """
        result = text
        for pattern, replacement in CREDENTIAL_PATTERNS:
            result = pattern.sub(replacement, result)
        return result

    def _hash_content(self, content: str) -> str:
        """Create a hash of content for tracking without storing.

        Args:
            content: Content to hash.

        Returns:
            SHA-256 hash of the content.
        """
        return hashlib.sha256(content.encode()).hexdigest()[:16]
