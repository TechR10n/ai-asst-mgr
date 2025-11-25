"""Sync Claude Code history to the database.

This module provides functionality to import session data from Claude Code's
history.jsonl file into the ai-asst-mgr database.
"""

from __future__ import annotations

import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from ai_asst_mgr.database.manager import DatabaseManager

_logger = logging.getLogger(__name__)

# Default paths
DEFAULT_HISTORY_PATH = Path.home() / ".claude" / "history.jsonl"
DEFAULT_DB_PATH = Path.home() / "Data" / "claude-sessions" / "sessions.db"
SYNC_STATE_FILE = Path.home() / "Data" / "claude-sessions" / ".sync_state"


@dataclass
class SyncResult:
    """Result of a sync operation."""

    sessions_imported: int
    messages_imported: int
    sessions_skipped: int
    errors: list[str]


@dataclass
class HistoryEntry:
    """A single entry from history.jsonl."""

    display: str
    timestamp: int  # Unix timestamp in milliseconds
    project: str
    session_id: str
    pasted_contents: dict[str, Any]

    @property
    def datetime(self) -> datetime:
        """Convert timestamp to datetime."""
        return datetime.fromtimestamp(self.timestamp / 1000, tz=UTC)

    @property
    def iso_timestamp(self) -> str:
        """Get ISO format timestamp."""
        return self.datetime.isoformat()


def parse_history_file(history_path: Path) -> list[HistoryEntry]:
    """Parse the history.jsonl file.

    Args:
        history_path: Path to the history.jsonl file.

    Returns:
        List of HistoryEntry objects.
    """
    entries: list[HistoryEntry] = []

    if not history_path.exists():
        _logger.warning("History file not found: %s", history_path)
        return entries

    with history_path.open() as f:
        for line_num, raw_line in enumerate(f, 1):
            line = raw_line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                entry = HistoryEntry(
                    display=data.get("display", ""),
                    timestamp=data.get("timestamp", 0),
                    project=data.get("project", ""),
                    session_id=data.get("sessionId", ""),
                    pasted_contents=data.get("pastedContents", {}),
                )
                entries.append(entry)
            except json.JSONDecodeError as e:
                _logger.warning("Failed to parse line %d: %s", line_num, e)

    return entries


def group_by_session(entries: list[HistoryEntry]) -> dict[str, list[HistoryEntry]]:
    """Group entries by session ID.

    Args:
        entries: List of history entries.

    Returns:
        Dictionary mapping session_id to list of entries.
    """
    sessions: dict[str, list[HistoryEntry]] = defaultdict(list)
    for entry in entries:
        if entry.session_id:
            sessions[entry.session_id].append(entry)

    # Sort entries within each session by timestamp
    for _session_id, session_entries in sessions.items():
        session_entries.sort(key=lambda e: e.timestamp)

    return dict(sessions)


def get_last_synced_timestamp() -> int:
    """Get the timestamp of the last synced entry.

    Returns:
        Unix timestamp in milliseconds, or 0 if never synced.
    """
    if SYNC_STATE_FILE.exists():
        try:
            return int(SYNC_STATE_FILE.read_text().strip())
        except (ValueError, OSError):
            pass
    return 0


def save_last_synced_timestamp(timestamp: int) -> None:
    """Save the timestamp of the last synced entry.

    Args:
        timestamp: Unix timestamp in milliseconds.
    """
    SYNC_STATE_FILE.parent.mkdir(parents=True, exist_ok=True)
    SYNC_STATE_FILE.write_text(str(timestamp))


def sync_history_to_db(
    db: DatabaseManager,
    history_path: Path | None = None,
    *,
    full_sync: bool = False,
) -> SyncResult:
    """Sync history.jsonl to the database.

    Args:
        db: DatabaseManager instance.
        history_path: Path to history.jsonl (default: ~/.claude/history.jsonl).
        full_sync: If True, ignore last sync state and import all entries.

    Returns:
        SyncResult with import statistics.
    """
    history_path = history_path or DEFAULT_HISTORY_PATH
    result = SyncResult(
        sessions_imported=0,
        messages_imported=0,
        sessions_skipped=0,
        errors=[],
    )

    # Parse history file
    entries = parse_history_file(history_path)
    if not entries:
        _logger.info("No entries found in history file")
        return result

    # Filter to only new entries if not full sync
    last_synced = 0 if full_sync else get_last_synced_timestamp()
    if last_synced > 0:
        entries = [e for e in entries if e.timestamp > last_synced]
        _logger.info("Filtering to %d entries after timestamp %d", len(entries), last_synced)

    if not entries:
        _logger.info("No new entries to sync")
        return result

    # Group by session
    sessions = group_by_session(entries)
    _logger.info("Found %d sessions with %d total entries", len(sessions), len(entries))

    # Get existing sessions to avoid duplicates
    existing_sessions = _get_existing_sessions(db)

    # Track max timestamp for sync state
    max_timestamp = last_synced

    # Import each session
    for session_id, session_entries in sessions.items():
        if session_id in existing_sessions:
            result.sessions_skipped += 1
            # Still update max timestamp
            for entry in session_entries:
                max_timestamp = max(max_timestamp, entry.timestamp)
            continue

        try:
            _import_session(db, session_id, session_entries)
            result.sessions_imported += 1
            result.messages_imported += len(session_entries)

            for entry in session_entries:
                max_timestamp = max(max_timestamp, entry.timestamp)

        except Exception:
            error_msg = f"Failed to import session {session_id}"
            _logger.exception(error_msg)
            result.errors.append(error_msg)

    # Save sync state
    if max_timestamp > last_synced:
        save_last_synced_timestamp(max_timestamp)

    return result


def _get_existing_sessions(db: DatabaseManager) -> set[str]:
    """Get set of existing session IDs from the database."""
    with db._connection() as conn:
        cursor = conn.execute("SELECT session_id FROM sessions WHERE vendor_id = 'claude'")
        return {row[0] for row in cursor.fetchall()}


def _import_session(
    db: DatabaseManager,
    session_id: str,
    entries: list[HistoryEntry],
) -> None:
    """Import a single session and its messages.

    Args:
        db: DatabaseManager instance.
        session_id: Session ID.
        entries: List of entries for this session.
    """
    if not entries:
        return

    # Get session metadata from first and last entries
    first_entry = entries[0]
    last_entry = entries[-1]

    # Record the session
    db.record_session(
        session_id=session_id,
        vendor_id="claude",
        project_path=first_entry.project,
        start_time=first_entry.iso_timestamp,
    )

    # Record each message as an event
    for entry in entries:
        db.record_event(
            session_id=session_id,
            vendor_id="claude",
            event_type="message",
            event_name="user",
            event_data={
                "content_length": len(entry.display),
                "has_pasted": bool(entry.pasted_contents),
                "timestamp": entry.iso_timestamp,
            },
        )

    # End the session
    # Calculate duration in seconds
    duration = (last_entry.timestamp - first_entry.timestamp) / 1000

    # Update session with end time and counts
    with db._connection() as conn:
        conn.execute(
            """
            UPDATE sessions
            SET end_time = ?,
                duration_seconds = ?,
                messages_count = ?
            WHERE session_id = ?
            """,
            (last_entry.iso_timestamp, duration, len(entries), session_id),
        )
        conn.commit()


def get_sync_status(db: DatabaseManager) -> dict[str, Any]:
    """Get current sync status.

    Args:
        db: DatabaseManager instance.

    Returns:
        Dictionary with sync status information.
    """
    last_synced = get_last_synced_timestamp()
    last_synced_dt = (
        datetime.fromtimestamp(last_synced / 1000, tz=UTC).isoformat() if last_synced > 0 else None
    )

    # Count sessions in database
    with db._connection() as conn:
        cursor = conn.execute("SELECT COUNT(*) FROM sessions WHERE vendor_id = 'claude'")
        session_count = cursor.fetchone()[0]

        cursor = conn.execute("SELECT COUNT(*) FROM events WHERE vendor_id = 'claude'")
        event_count = cursor.fetchone()[0]

    # Count entries in history file
    history_path = DEFAULT_HISTORY_PATH
    history_count = 0
    if history_path.exists():
        with history_path.open() as f:
            history_count = sum(1 for _ in f)

    return {
        "last_synced_timestamp": last_synced,
        "last_synced_datetime": last_synced_dt,
        "database_sessions": session_count,
        "database_events": event_count,
        "history_file_entries": history_count,
        "history_file_path": str(history_path),
    }
