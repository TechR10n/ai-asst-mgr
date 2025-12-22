"""Unit tests for Gemini database synchronization."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_asst_mgr.database.manager import DatabaseManager
from ai_asst_mgr.database.sync_gemini import (
    find_session_files,
    sync_gemini_history_to_db,
)


@pytest.fixture
def mock_db() -> MagicMock:
    """Create a mock DatabaseManager."""
    return MagicMock(spec=DatabaseManager)


@pytest.fixture
def temp_gemini_logs(tmp_path: Path) -> Path:
    """Create a temporary Gemini log directory structure."""
    logs_dir = tmp_path / "gemini_logs"
    chats_dir = logs_dir / "project1" / "chats"
    chats_dir.mkdir(parents=True)
    
    session_data = {
        "sessionId": "sess123",
        "projectHash": "hash123",
        "startTime": "2025-12-22T10:00:00Z",
        "messages": [
            {
                "type": "user",
                "content": "Hello",
                "timestamp": "2025-12-22T10:00:01Z",
                "thoughts": [{"subject": "greeting", "description": "User said hello", "timestamp": "2025-12-22T10:00:01Z"}]
            },
            {
                "type": "gemini",
                "content": "Hi there!",
                "timestamp": "2025-12-22T10:00:02Z",
                "toolCalls": [
                    {
                        "name": "read_file",
                        "args": {"path": "test.txt"},
                        "status": "success",
                        "result": "content",
                        "timestamp": "2025-12-22T10:00:03Z"
                    }
                ]
            }
        ]
    }
    
    session_file = chats_dir / "session-sess123.json"
    session_file.write_text(json.dumps(session_data))
    
    return logs_dir


def test_find_session_files(temp_gemini_logs: Path) -> None:
    """Test finding Gemini session files."""
    files = find_session_files(temp_gemini_logs)
    assert len(files) == 1
    assert files[0].name == "session-sess123.json"


def test_find_session_files_nonexistent() -> None:
    """Test finding session files in a non-existent directory."""
    files = find_session_files(Path("/nonexistent/path"))
    assert files == []


def test_sync_gemini_history_to_db_success(mock_db: MagicMock, temp_gemini_logs: Path) -> None:
    """Test successful sync of Gemini history."""
    # Setup mock DB connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    # 1st call (sync_gemini_history_to_db): existing sessions check
    # 2nd call (_import_gemini_session): session existence check
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = None 
    
    mock_conn.execute.return_value = mock_cursor
    mock_db._connection.return_value.__enter__.return_value = mock_conn
    
    result = sync_gemini_history_to_db(mock_db, temp_gemini_logs)
    
    assert result.sessions_imported == 1
    assert result.messages_imported == 2
    assert result.thoughts_imported == 1
    assert result.tools_imported == 1
    assert result.errors == []
    
    # Verify DB calls
    mock_db.record_session.assert_called_once()
    assert mock_db.record_event.call_count == 4 # user msg, thought, gemini msg, tool call
    mock_db.end_session.assert_called_once()


def test_sync_gemini_history_to_db_full_sync(mock_db: MagicMock, temp_gemini_logs: Path) -> None:
    """Test full sync of Gemini history."""
    # Setup mock DB connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchone.return_value = None 
    mock_conn.execute.return_value = mock_cursor
    mock_db._connection.return_value.__enter__.return_value = mock_conn

    result = sync_gemini_history_to_db(mock_db, temp_gemini_logs, full_sync=True)
    
    assert result.sessions_imported == 1
    mock_db.record_session.assert_called_once()


def test_sync_gemini_history_to_db_session_exists(mock_db: MagicMock, temp_gemini_logs: Path) -> None:
    """Test sync when session already exists (should still update events)."""
    # Setup mock DB connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    
    # 1st call: existing sessions
    mock_cursor.fetchall.return_value = [("sess123",)]
    # 2nd call: session existence check in _import
    mock_cursor.fetchone.return_value = (1,)
    
    mock_conn.execute.return_value = mock_cursor
    mock_db._connection.return_value.__enter__.return_value = mock_conn
    
    result = sync_gemini_history_to_db(mock_db, temp_gemini_logs)
    
    assert result.sessions_imported == 1
    # record_session should NOT be called
    assert mock_db.record_session.call_count == 0
    # events should still be recorded (after deletion)
    assert mock_db.record_event.call_count == 4
    mock_db.end_session.assert_called_once()


def test_sync_gemini_history_to_db_with_errors(mock_db: MagicMock, temp_gemini_logs: Path) -> None:
    """Test sync with a corrupted session file."""
    # Corrupt the file
    files = find_session_files(temp_gemini_logs)
    files[0].write_text("{corrupted json")
    
    # Setup mock DB connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_conn.execute.return_value = mock_cursor
    mock_db._connection.return_value.__enter__.return_value = mock_conn
    
    result = sync_gemini_history_to_db(mock_db, temp_gemini_logs)
    
    assert result.sessions_imported == 0
    assert len(result.errors) == 1
    assert "Failed to import" in result.errors[0]


def test_sync_gemini_history_to_db_edge_cases(mock_db: MagicMock, temp_gemini_logs: Path) -> None:
    """Test sync with edge cases (missing sessionId, invalid date, info/error types)."""
    chats_dir = temp_gemini_logs / "project1" / "chats"
    
    # Remove original file to have predictable order or just use one file
    for f in chats_dir.glob("*.json"):
        f.unlink()

    # 1. Missing sessionId
    file1 = chats_dir / "session-missing.json"
    file1.write_text(json.dumps({"messages": []}))
    
    # 2. Missing startTime (should hit line 137)
    file3 = chats_dir / "session-no-start.json"
    file3.write_text(json.dumps({
        "sessionId": "sess_no_start",
        "messages": []
    }))
    
    # 3. Invalid date format and unknown message type
    file2 = chats_dir / "session-edge.json"
    file2.write_text(json.dumps({
        "sessionId": "sess_edge",
        "startTime": "not-a-date",
        "messages": [
            {"type": "info", "content": "system info", "timestamp": "2025-12-22T10:00:00Z"},
            {"type": "error", "content": "error msg", "timestamp": "2025-12-22T10:00:01Z"},
            {"type": "unknown_type", "content": "ignored"}
        ]
    }))
    
    # Setup mock DB connection
    mock_conn = MagicMock()
    mock_cursor = MagicMock()
    mock_cursor.fetchall.return_value = []
    mock_cursor.fetchone.return_value = None
    mock_conn.execute.return_value = mock_cursor
    mock_db._connection.return_value.__enter__.return_value = mock_conn
    
    result = sync_gemini_history_to_db(mock_db, temp_gemini_logs)
    
    # Should have imported 3 sessions (original sess123 and sess_no_start, sess_edge)
    # session-missing.json skipped because no sessionId
    assert result.sessions_imported == 2 # wait, original is removed in this test! 
    # Ah, I added `for f in chats_dir.glob("*.json"): f.unlink()`
    # so sess123 is GONE.
    # so we have sess_no_start and sess_edge.
    assert result.sessions_imported == 2
    assert result.messages_imported == 2
    
    assert mock_db.end_session.call_count == 2


def test_sync_gemini_history_to_db_no_dir(mock_db: MagicMock, tmp_path: Path) -> None:
    """Test sync with non-existent directory."""
    result = sync_gemini_history_to_db(mock_db, tmp_path / "nonexistent")
    assert result.sessions_imported == 0
    assert result.errors == []
