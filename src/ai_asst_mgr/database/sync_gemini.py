"""Sync Gemini CLI history to the database.

This module provides functionality to import session data from Gemini CLI's
JSON session logs into the ai-asst-mgr database.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_asst_mgr.database.manager import DatabaseManager

_logger = logging.getLogger(__name__)

# Default path for Gemini logs (based on investigation)
DEFAULT_GEMINI_TMP_DIR = Path.home() / ".gemini" / "tmp"


@dataclass
class GeminiSyncResult:
    """Result of a Gemini sync operation."""

    sessions_imported: int
    messages_imported: int
    thoughts_imported: int
    tools_imported: int
    sessions_skipped: int
    errors: list[str]


def find_session_files(base_dir: Path) -> list[Path]:
    """Find all session JSON files in the Gemini tmp directory.

    Args:
        base_dir: Base directory to search (e.g. ~/.gemini/tmp).

    Returns:
        List of paths to session JSON files.
    """
    session_files = []
    if not base_dir.exists():
        return session_files

    # Search recursively for chats/session-*.json
    for path in base_dir.rglob("chats/session-*.json"):
        session_files.append(path)
    
    return session_files


def sync_gemini_history_to_db(
    db: DatabaseManager,
    base_dir: Path | None = None,
    *,
    full_sync: bool = False,
) -> GeminiSyncResult:
    """Sync Gemini history to the database.

    Args:
        db: DatabaseManager instance.
        base_dir: Base directory for Gemini logs (default: ~/.gemini/tmp).
        full_sync: If True, re-import existing sessions (updating them).

    Returns:
        GeminiSyncResult with import statistics.
    """
    base_dir = base_dir or DEFAULT_GEMINI_TMP_DIR
    result = GeminiSyncResult(0, 0, 0, 0, 0, [])

    session_files = find_session_files(base_dir)
    _logger.info("Found %d Gemini session files", len(session_files))

    if not session_files:
        return result

    # Get existing sessions if not full sync
    existing_sessions = set()
    if not full_sync:
        with db._connection() as conn:
            cursor = conn.execute("SELECT session_id FROM sessions WHERE vendor_id = 'gemini'")
            existing_sessions = {row[0] for row in cursor.fetchall()}

    for file_path in session_files:
        try:
            with file_path.open("r", encoding="utf-8") as f:
                data = json.load(f)
            
            session_id = data.get("sessionId")
            if not session_id:
                continue

            # If not full sync and session exists, we might still want to update it
            # if it has new messages. For simplicity, we'll skip if strictly not full_sync
            # unless we implement incremental updates. 
            # A better approach for file-based logs is to check lastUpdated timestamp.
            # But for this implementation, we will upsert (replace) the session data.
            
            _import_gemini_session(db, data, result)
            result.sessions_imported += 1

        except Exception as e:
            error_msg = f"Failed to import {file_path.name}: {e}"
            _logger.error(error_msg)
            result.errors.append(error_msg)

    return result


def _import_gemini_session(
    db: DatabaseManager,
    data: dict[str, Any],
    result: GeminiSyncResult,
) -> None:
    """Import a single Gemini session.

    Args:
        db: DatabaseManager instance.
        data: Parsed JSON content of the session file.
        result: Result object to update stats.
    """
    session_id = data["sessionId"]
    project_hash = data.get("projectHash", "unknown")
    start_time_str = data.get("startTime")
    
    # Ensure start_time is valid
    try:
        if start_time_str:
            # Parse ISO format (handling potential 'Z')
            start_time = datetime.fromisoformat(start_time_str.replace('Z', '+00:00'))
        else:
            start_time = datetime.now(tz=UTC)
    except ValueError:
        start_time = datetime.now(tz=UTC)

    # 1. Upsert Session
    # We use INSERT OR REPLACE logic by first deleting (simplest for full refresh) or INSERT OR IGNORE
    # But since we want to update end_time/stats, let's use db.record_session which inserts.
    # We might need to handle the "already exists" case if record_session implies new.
    # The existing record_session uses INSERT, which fails on duplicate.
    # We should check existence first or use a custom query here.
    
    with db._connection() as conn:
        # Check if session exists
        cursor = conn.execute("SELECT 1 FROM sessions WHERE session_id = ?", (session_id,))
        exists = cursor.fetchone() is not None
        
        if not exists:
            db.record_session(
                session_id=session_id,
                vendor_id="gemini",
                project_path=f"hash:{project_hash}", # Proxy for project path
                start_time=start_time.isoformat()
            )
    
    # 2. Process Messages and Events
    messages = data.get("messages", [])
    
    # Clear existing events for this session to avoid duplicates during re-sync
    # (Since we are re-parsing the whole file)
    with db._connection() as conn:
        conn.execute(
            "DELETE FROM events WHERE session_id = ? AND vendor_id = 'gemini'",
            (session_id,)
        )
        conn.commit()

    tool_calls_count = 0
    messages_count = 0
    errors_count = 0

    for msg in messages:
        msg_type = msg.get("type", "unknown")
        timestamp = msg.get("timestamp")
        
        # User or System Message
        if msg_type in ("user", "gemini", "info", "error"):
            db.record_event(
                session_id=session_id,
                vendor_id="gemini",
                event_type="message" if msg_type in ("user", "gemini") else msg_type,
                event_name=msg_type,
                event_data={
                    "content": msg.get("content"),
                    "timestamp": timestamp
                }
            )
            messages_count += 1
            if msg_type == "error":
                errors_count += 1

        # Thoughts (Reasoning)
        thoughts = msg.get("thoughts", [])
        for thought in thoughts:
            db.record_event(
                session_id=session_id,
                vendor_id="gemini",
                event_type="thought",
                event_name="reasoning",
                event_data={
                    "subject": thought.get("subject"),
                    "description": thought.get("description"),
                    "timestamp": thought.get("timestamp")
                }
            )
            result.thoughts_imported += 1

        # Tool Calls (The Telemetry Goal!)
        tool_calls = msg.get("toolCalls", [])
        for tool in tool_calls:
            tool_name = tool.get("name")
            tool_args = tool.get("args")
            tool_status = tool.get("status")
            tool_result = tool.get("result")
            
            db.record_event(
                session_id=session_id,
                vendor_id="gemini",
                event_type="tool_call",
                event_name=tool_name,
                event_data={
                    "args": tool_args,
                    "status": tool_status,
                    "result": tool_result, # Might be large, but schema is TEXT
                    "timestamp": tool.get("timestamp")
                }
            )
            tool_calls_count += 1
            result.tools_imported += 1

    result.messages_imported += messages_count

    # 3. Update Session Statistics
    db.end_session(
        session_id=session_id,
        tool_calls_count=tool_calls_count,
        messages_count=messages_count,
        errors_count=errors_count
    )
