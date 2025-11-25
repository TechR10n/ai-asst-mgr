"""Tests for the database sync module."""

from __future__ import annotations

import json
import tempfile
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

from ai_asst_mgr.database.sync import (
    DEFAULT_DB_PATH,
    DEFAULT_HISTORY_PATH,
    SYNC_STATE_FILE,
    HistoryEntry,
    SyncResult,
    get_last_synced_timestamp,
    get_sync_status,
    group_by_session,
    parse_history_file,
    save_last_synced_timestamp,
    sync_history_to_db,
)


class TestSyncResult:
    """Tests for SyncResult dataclass."""

    def test_create_sync_result(self) -> None:
        """Test creating a SyncResult."""
        result = SyncResult(
            sessions_imported=5,
            messages_imported=100,
            sessions_skipped=2,
            errors=["error1"],
        )
        assert result.sessions_imported == 5
        assert result.messages_imported == 100
        assert result.sessions_skipped == 2
        assert result.errors == ["error1"]

    def test_sync_result_empty_errors(self) -> None:
        """Test SyncResult with empty errors list."""
        result = SyncResult(
            sessions_imported=0,
            messages_imported=0,
            sessions_skipped=0,
            errors=[],
        )
        assert result.errors == []


class TestHistoryEntry:
    """Tests for HistoryEntry dataclass."""

    def test_create_history_entry(self) -> None:
        """Test creating a HistoryEntry."""
        entry = HistoryEntry(
            display="test message",
            timestamp=1700000000000,
            project="/path/to/project",
            session_id="session-123",
            pasted_contents={},
        )
        assert entry.display == "test message"
        assert entry.timestamp == 1700000000000
        assert entry.project == "/path/to/project"
        assert entry.session_id == "session-123"
        assert entry.pasted_contents == {}

    def test_history_entry_datetime_property(self) -> None:
        """Test HistoryEntry datetime property."""
        entry = HistoryEntry(
            display="test",
            timestamp=1700000000000,  # 2023-11-14 22:13:20 UTC
            project="/path",
            session_id="session-123",
            pasted_contents={},
        )
        dt = entry.datetime
        assert isinstance(dt, datetime)
        assert dt.tzinfo == UTC

    def test_history_entry_iso_timestamp_property(self) -> None:
        """Test HistoryEntry iso_timestamp property."""
        entry = HistoryEntry(
            display="test",
            timestamp=1700000000000,
            project="/path",
            session_id="session-123",
            pasted_contents={},
        )
        iso = entry.iso_timestamp
        assert isinstance(iso, str)
        assert "2023-11-14" in iso


class TestParseHistoryFile:
    """Tests for parse_history_file function."""

    def test_parse_nonexistent_file(self) -> None:
        """Test parsing a file that doesn't exist."""
        path = Path("/nonexistent/file.jsonl")
        entries = parse_history_file(path)
        assert entries == []

    def test_parse_empty_file(self) -> None:
        """Test parsing an empty file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            entries = parse_history_file(temp_path)
            assert entries == []
        finally:
            temp_path.unlink()

    def test_parse_valid_entries(self) -> None:
        """Test parsing valid JSONL entries."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            entry1 = {
                "display": "message 1",
                "timestamp": 1700000000000,
                "project": "/project1",
                "sessionId": "session-1",
                "pastedContents": {},
            }
            entry2 = {
                "display": "message 2",
                "timestamp": 1700000001000,
                "project": "/project1",
                "sessionId": "session-1",
                "pastedContents": {"file.txt": "content"},
            }
            f.write(json.dumps(entry1) + "\n")
            f.write(json.dumps(entry2) + "\n")
            temp_path = Path(f.name)

        try:
            entries = parse_history_file(temp_path)
            assert len(entries) == 2
            assert entries[0].display == "message 1"
            assert entries[0].session_id == "session-1"
            assert entries[1].pasted_contents == {"file.txt": "content"}
        finally:
            temp_path.unlink()

    def test_parse_skips_blank_lines(self) -> None:
        """Test that blank lines are skipped."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            entry = {
                "display": "msg",
                "timestamp": 1700000000000,
                "project": "/p",
                "sessionId": "s1",
            }
            f.write("\n")
            f.write(json.dumps(entry) + "\n")
            f.write("   \n")
            temp_path = Path(f.name)

        try:
            entries = parse_history_file(temp_path)
            assert len(entries) == 1
        finally:
            temp_path.unlink()

    def test_parse_handles_invalid_json(self) -> None:
        """Test that invalid JSON lines are skipped with warning."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("not valid json\n")
            valid = {
                "display": "valid",
                "timestamp": 1700000000000,
                "project": "/p",
                "sessionId": "s1",
            }
            f.write(json.dumps(valid) + "\n")
            temp_path = Path(f.name)

        try:
            entries = parse_history_file(temp_path)
            assert len(entries) == 1
            assert entries[0].display == "valid"
        finally:
            temp_path.unlink()

    def test_parse_handles_missing_fields(self) -> None:
        """Test that missing fields get default values."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            entry: dict[str, object] = {}  # All fields missing
            f.write(json.dumps(entry) + "\n")
            temp_path = Path(f.name)

        try:
            entries = parse_history_file(temp_path)
            assert len(entries) == 1
            assert entries[0].display == ""
            assert entries[0].timestamp == 0
            assert entries[0].project == ""
            assert entries[0].session_id == ""
            assert entries[0].pasted_contents == {}
        finally:
            temp_path.unlink()


class TestGroupBySession:
    """Tests for group_by_session function."""

    def test_group_empty_list(self) -> None:
        """Test grouping empty list."""
        result = group_by_session([])
        assert result == {}

    def test_group_single_session(self) -> None:
        """Test grouping entries from single session."""
        entries = [
            HistoryEntry("msg1", 1000, "/p", "session-1", {}),
            HistoryEntry("msg2", 2000, "/p", "session-1", {}),
        ]
        result = group_by_session(entries)
        assert len(result) == 1
        assert "session-1" in result
        assert len(result["session-1"]) == 2

    def test_group_multiple_sessions(self) -> None:
        """Test grouping entries from multiple sessions."""
        entries = [
            HistoryEntry("msg1", 1000, "/p1", "session-1", {}),
            HistoryEntry("msg2", 2000, "/p2", "session-2", {}),
            HistoryEntry("msg3", 3000, "/p1", "session-1", {}),
        ]
        result = group_by_session(entries)
        assert len(result) == 2
        assert len(result["session-1"]) == 2
        assert len(result["session-2"]) == 1

    def test_group_sorts_by_timestamp(self) -> None:
        """Test that entries are sorted by timestamp within session."""
        entries = [
            HistoryEntry("msg2", 2000, "/p", "session-1", {}),
            HistoryEntry("msg1", 1000, "/p", "session-1", {}),
            HistoryEntry("msg3", 3000, "/p", "session-1", {}),
        ]
        result = group_by_session(entries)
        session_entries = result["session-1"]
        assert session_entries[0].timestamp == 1000
        assert session_entries[1].timestamp == 2000
        assert session_entries[2].timestamp == 3000

    def test_group_skips_empty_session_id(self) -> None:
        """Test that entries without session_id are skipped."""
        entries = [
            HistoryEntry("msg1", 1000, "/p", "session-1", {}),
            HistoryEntry("msg2", 2000, "/p", "", {}),  # Empty session_id
        ]
        result = group_by_session(entries)
        assert len(result) == 1
        assert "session-1" in result


class TestSyncStateTimestamp:
    """Tests for sync state timestamp functions."""

    def test_get_last_synced_timestamp_no_file(self) -> None:
        """Test getting timestamp when file doesn't exist."""
        with patch("ai_asst_mgr.database.sync.SYNC_STATE_FILE") as mock_file:
            mock_file.exists.return_value = False
            result = get_last_synced_timestamp()
            assert result == 0

    def test_get_last_synced_timestamp_valid(self) -> None:
        """Test getting valid timestamp from file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("1700000000000")
            temp_path = Path(f.name)

        try:
            with patch("ai_asst_mgr.database.sync.SYNC_STATE_FILE", temp_path):
                result = get_last_synced_timestamp()
                assert result == 1700000000000
        finally:
            temp_path.unlink()

    def test_get_last_synced_timestamp_invalid(self) -> None:
        """Test getting timestamp when file contains invalid data."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            f.write("not a number")
            temp_path = Path(f.name)

        try:
            with patch("ai_asst_mgr.database.sync.SYNC_STATE_FILE", temp_path):
                result = get_last_synced_timestamp()
                assert result == 0
        finally:
            temp_path.unlink()

    def test_save_last_synced_timestamp(self) -> None:
        """Test saving timestamp to file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            temp_path = Path(temp_dir) / "subdir" / ".sync_state"
            with patch("ai_asst_mgr.database.sync.SYNC_STATE_FILE", temp_path):
                save_last_synced_timestamp(1700000000000)
                assert temp_path.exists()
                assert temp_path.read_text() == "1700000000000"


class TestSyncHistoryToDb:
    """Tests for sync_history_to_db function."""

    def test_sync_nonexistent_history(self) -> None:
        """Test sync with nonexistent history file."""
        mock_db = MagicMock()
        with tempfile.TemporaryDirectory() as temp_dir:
            nonexistent_path = Path(temp_dir) / "nonexistent.jsonl"
            result = sync_history_to_db(mock_db, nonexistent_path, full_sync=True)
            assert result.sessions_imported == 0
            assert result.messages_imported == 0
            assert result.sessions_skipped == 0
            assert result.errors == []

    def test_sync_empty_history(self) -> None:
        """Test sync with empty history file."""
        mock_db = MagicMock()
        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            f.write("")
            temp_path = Path(f.name)

        try:
            result = sync_history_to_db(mock_db, temp_path, full_sync=True)
            assert result.sessions_imported == 0
        finally:
            temp_path.unlink()

    def test_sync_imports_new_sessions(self) -> None:
        """Test that sync imports new sessions."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []  # No existing sessions
        mock_conn.execute.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db._connection.return_value = mock_conn

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            entry = {
                "display": "test message",
                "timestamp": 1700000000000,
                "project": "/test/project",
                "sessionId": "new-session",
                "pastedContents": {},
            }
            f.write(json.dumps(entry) + "\n")
            temp_path = Path(f.name)

        try:
            with (
                patch(
                    "ai_asst_mgr.database.sync.get_last_synced_timestamp",
                    return_value=0,
                ),
                patch("ai_asst_mgr.database.sync.save_last_synced_timestamp"),
            ):
                result = sync_history_to_db(mock_db, temp_path, full_sync=True)
                assert result.sessions_imported == 1
                assert result.messages_imported == 1
                mock_db.record_session.assert_called_once()
                mock_db.record_event.assert_called_once()
        finally:
            temp_path.unlink()

    def test_sync_skips_existing_sessions(self) -> None:
        """Test that sync skips already imported sessions."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = [("existing-session",)]
        mock_conn.execute.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db._connection.return_value = mock_conn

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            entry = {
                "display": "test message",
                "timestamp": 1700000000000,
                "project": "/test/project",
                "sessionId": "existing-session",
                "pastedContents": {},
            }
            f.write(json.dumps(entry) + "\n")
            temp_path = Path(f.name)

        try:
            with (
                patch(
                    "ai_asst_mgr.database.sync.get_last_synced_timestamp",
                    return_value=0,
                ),
                patch("ai_asst_mgr.database.sync.save_last_synced_timestamp"),
            ):
                result = sync_history_to_db(mock_db, temp_path, full_sync=True)
                assert result.sessions_imported == 0
                assert result.sessions_skipped == 1
                mock_db.record_session.assert_not_called()
        finally:
            temp_path.unlink()

    def test_sync_incremental_filters_by_timestamp(self) -> None:
        """Test that incremental sync filters by timestamp."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchall.return_value = []
        mock_conn.execute.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db._connection.return_value = mock_conn

        with tempfile.NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False) as f:
            old = {"display": "old", "timestamp": 1000, "project": "/p", "sessionId": "s1"}
            new = {"display": "new", "timestamp": 2000, "project": "/p", "sessionId": "s2"}
            f.write(json.dumps(old) + "\n")
            f.write(json.dumps(new) + "\n")
            temp_path = Path(f.name)

        try:
            with (
                patch(
                    "ai_asst_mgr.database.sync.get_last_synced_timestamp",
                    return_value=1500,
                ),
                patch("ai_asst_mgr.database.sync.save_last_synced_timestamp"),
            ):
                result = sync_history_to_db(mock_db, temp_path, full_sync=False)
                # Only the new entry (timestamp 2000 > 1500) should be imported
                assert result.sessions_imported == 1
        finally:
            temp_path.unlink()


class TestGetSyncStatus:
    """Tests for get_sync_status function."""

    def test_get_sync_status(self) -> None:
        """Test getting sync status."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        # First call for sessions count, second for events count
        mock_cursor.fetchone.side_effect = [(10,), (50,)]
        mock_conn.execute.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db._connection.return_value = mock_conn

        with (
            patch(
                "ai_asst_mgr.database.sync.get_last_synced_timestamp",
                return_value=1700000000000,
            ),
            patch("ai_asst_mgr.database.sync.DEFAULT_HISTORY_PATH") as mock_path,
        ):
            mock_path.exists.return_value = False
            status = get_sync_status(mock_db)

            assert status["database_sessions"] == 10
            assert status["database_events"] == 50
            assert status["last_synced_timestamp"] == 1700000000000
            assert status["last_synced_datetime"] is not None

    def test_get_sync_status_never_synced(self) -> None:
        """Test sync status when never synced."""
        mock_db = MagicMock()
        mock_conn = MagicMock()
        mock_cursor = MagicMock()
        mock_cursor.fetchone.side_effect = [(0,), (0,)]
        mock_conn.execute.return_value = mock_cursor
        mock_conn.__enter__ = MagicMock(return_value=mock_conn)
        mock_conn.__exit__ = MagicMock(return_value=False)
        mock_db._connection.return_value = mock_conn

        with (
            patch(
                "ai_asst_mgr.database.sync.get_last_synced_timestamp",
                return_value=0,
            ),
            patch("ai_asst_mgr.database.sync.DEFAULT_HISTORY_PATH") as mock_path,
        ):
            mock_path.exists.return_value = False
            status = get_sync_status(mock_db)

            assert status["last_synced_timestamp"] == 0
            assert status["last_synced_datetime"] is None


class TestDefaultPaths:
    """Tests for default path constants."""

    def test_default_history_path(self) -> None:
        """Test default history path is set correctly."""
        assert Path.home() / ".claude" / "history.jsonl" == DEFAULT_HISTORY_PATH

    def test_default_db_path(self) -> None:
        """Test default database path is set correctly."""
        assert Path.home() / "Data" / "claude-sessions" / "sessions.db" == DEFAULT_DB_PATH

    def test_sync_state_file(self) -> None:
        """Test sync state file path is set correctly."""
        assert Path.home() / "Data" / "claude-sessions" / ".sync_state" == SYNC_STATE_FILE
