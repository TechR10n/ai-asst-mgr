"""Tests for tracking module."""

from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from ai_asst_mgr.tracking.session_tracker import (
    CREDENTIAL_PATTERNS,
    VendorSessionTracker,
)


class TestVendorSessionTracker:
    """Tests for VendorSessionTracker class."""

    @pytest.fixture
    def tracker(self) -> VendorSessionTracker:
        """Create a tracker with temporary database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            yield VendorSessionTracker(db_path, vendor_id="claude")

    def test_init_creates_database(self) -> None:
        """Verify constructor initializes database."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            tracker = VendorSessionTracker(db_path)
            assert db_path.exists()
            assert tracker.vendor_id == "claude"

    def test_init_with_custom_vendor(self) -> None:
        """Verify constructor accepts custom vendor."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            tracker = VendorSessionTracker(db_path, vendor_id="gemini")
            assert tracker.vendor_id == "gemini"

    def test_init_without_auto_initialize(self) -> None:
        """Verify auto_initialize=False skips database setup."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            tracker = VendorSessionTracker(db_path, auto_initialize=False)
            assert not db_path.exists()
            assert tracker.db_path == db_path

    def test_start_session_returns_id(self, tracker: VendorSessionTracker) -> None:
        """Verify start_session returns session ID."""
        session_id = tracker.start_session()
        assert session_id is not None
        assert len(session_id) > 0

    def test_start_session_with_custom_id(self, tracker: VendorSessionTracker) -> None:
        """Verify start_session accepts custom session ID."""
        session_id = tracker.start_session(session_id="custom-123")
        assert session_id == "custom-123"

    def test_start_session_with_vendor(self, tracker: VendorSessionTracker) -> None:
        """Verify start_session accepts vendor override."""
        session_id = tracker.start_session(vendor_id="gemini")
        stats = tracker.get_session_stats(session_id)
        assert stats is not None
        assert stats["vendor_id"] == "gemini"

    def test_start_session_with_project_path(self, tracker: VendorSessionTracker) -> None:
        """Verify start_session records project path."""
        session_id = tracker.start_session(project_path="/path/to/project")
        stats = tracker.get_session_stats(session_id)
        assert stats is not None
        assert stats["project_path"] == "/path/to/project"

    def test_end_session_returns_summary(self, tracker: VendorSessionTracker) -> None:
        """Verify end_session returns session summary."""
        session_id = tracker.start_session()
        summary = tracker.end_session(session_id)
        assert summary["session_id"] == session_id
        assert "duration_seconds" in summary

    def test_end_session_removes_from_active(self, tracker: VendorSessionTracker) -> None:
        """Verify end_session removes session from active list."""
        session_id = tracker.start_session()
        assert session_id in tracker.get_active_sessions()
        tracker.end_session(session_id)
        assert session_id not in tracker.get_active_sessions()

    def test_end_session_unknown_session(self, tracker: VendorSessionTracker) -> None:
        """Verify end_session handles unknown session gracefully."""
        summary = tracker.end_session("nonexistent")
        assert summary["session_id"] == "nonexistent"

    def test_log_tool_call(self, tracker: VendorSessionTracker) -> None:
        """Verify log_tool_call records tool usage."""
        session_id = tracker.start_session()
        tracker.log_tool_call(session_id, "Read")
        tracker.log_tool_call(session_id, "Write")

        stats = tracker.get_session_stats(session_id)
        assert stats is not None
        assert stats["tool_calls"] == 2

    def test_log_tool_call_with_input(self, tracker: VendorSessionTracker) -> None:
        """Verify log_tool_call accepts input parameters."""
        session_id = tracker.start_session()
        tracker.log_tool_call(session_id, "Read", tool_input={"file": "test.py"})

        stats = tracker.get_session_stats(session_id)
        assert stats is not None
        assert stats["tool_calls"] == 1

    def test_log_message(self, tracker: VendorSessionTracker) -> None:
        """Verify log_message records message."""
        session_id = tracker.start_session()
        tracker.log_message(session_id, "user")
        tracker.log_message(session_id, "assistant")

        stats = tracker.get_session_stats(session_id)
        assert stats is not None
        assert stats["messages"] == 2

    def test_log_message_with_content_length(self, tracker: VendorSessionTracker) -> None:
        """Verify log_message records content length."""
        session_id = tracker.start_session()
        tracker.log_message(session_id, "user", content_length=100)

        stats = tracker.get_session_stats(session_id)
        assert stats is not None
        assert stats["messages"] == 1

    def test_log_error(self, tracker: VendorSessionTracker) -> None:
        """Verify log_error records error."""
        session_id = tracker.start_session()
        tracker.log_error(session_id, "ValidationError")

        stats = tracker.get_session_stats(session_id)
        assert stats is not None
        assert stats["errors"] == 1

    def test_log_error_with_message(self, tracker: VendorSessionTracker) -> None:
        """Verify log_error records error message."""
        session_id = tracker.start_session()
        tracker.log_error(session_id, "AuthError", error_message="Invalid API key")

        stats = tracker.get_session_stats(session_id)
        assert stats is not None
        assert stats["errors"] == 1

    def test_get_active_sessions(self, tracker: VendorSessionTracker) -> None:
        """Verify get_active_sessions returns all active sessions."""
        s1 = tracker.start_session()
        s2 = tracker.start_session()

        active = tracker.get_active_sessions()
        assert s1 in active
        assert s2 in active
        assert len(active) == 2

    def test_get_session_stats_returns_none_for_unknown(
        self, tracker: VendorSessionTracker
    ) -> None:
        """Verify get_session_stats returns None for unknown session."""
        stats = tracker.get_session_stats("nonexistent")
        assert stats is None

    def test_get_session_stats_returns_stats(self, tracker: VendorSessionTracker) -> None:
        """Verify get_session_stats returns correct statistics."""
        session_id = tracker.start_session(project_path="/project")
        tracker.log_tool_call(session_id, "Read")
        tracker.log_message(session_id, "user")
        tracker.log_error(session_id, "TestError")

        stats = tracker.get_session_stats(session_id)
        assert stats is not None
        assert stats["session_id"] == session_id
        assert stats["vendor_id"] == "claude"
        assert stats["project_path"] == "/project"
        assert stats["tool_calls"] == 1
        assert stats["messages"] == 1
        assert stats["errors"] == 1

    def test_get_vendor_stats(self, tracker: VendorSessionTracker) -> None:
        """Verify get_vendor_stats returns statistics."""
        session_id = tracker.start_session()
        tracker.end_session(session_id)

        stats = tracker.get_vendor_stats()
        assert stats is not None


class TestCredentialRedaction:
    """Tests for credential redaction functionality."""

    @pytest.fixture
    def tracker(self) -> VendorSessionTracker:
        """Create a tracker for testing redaction."""
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = Path(temp_dir) / "test.db"
            yield VendorSessionTracker(db_path)

    def test_redact_api_key(self, tracker: VendorSessionTracker) -> None:
        """Verify API keys are redacted."""
        text = "api_key=sk-12345678901234567890"
        result = tracker._redact_text(text)
        assert "sk-12345678901234567890" not in result
        assert "REDACTED" in result

    def test_redact_bearer_token(self, tracker: VendorSessionTracker) -> None:
        """Verify bearer tokens are redacted."""
        text = "Authorization: Bearer abcdefghijklmnopqrstuvwxyz123456"
        result = tracker._redact_text(text)
        assert "abcdefghijklmnopqrstuvwxyz123456" not in result
        assert "REDACTED" in result

    def test_redact_password(self, tracker: VendorSessionTracker) -> None:
        """Verify passwords are redacted."""
        text = "password=secret123"
        result = tracker._redact_text(text)
        assert "secret123" not in result
        assert "REDACTED" in result

    def test_redact_openai_key(self, tracker: VendorSessionTracker) -> None:
        """Verify OpenAI API keys are redacted."""
        text = "Using key: sk-abc123def456ghi789jkl012mno345pqr678"
        result = tracker._redact_text(text)
        assert "sk-abc123def456ghi789jkl012mno345pqr678" not in result
        assert "REDACTED_API_KEY" in result

    def test_redact_google_key(self, tracker: VendorSessionTracker) -> None:
        """Verify Google API keys are redacted."""
        text = "API: AIzaSyAxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx"
        result = tracker._redact_text(text)
        assert "AIzaSyA" not in result
        assert "REDACTED_API_KEY" in result

    def test_redact_credentials_dict(self, tracker: VendorSessionTracker) -> None:
        """Verify credentials in dicts are redacted."""
        data = {
            "api_key": "sk-12345678901234567890abcd",
            "nested": {
                "token": "my-secret-token-value-here",
            },
            "safe": "normal value",
        }
        result = tracker._redact_credentials(data)
        assert "REDACTED" in result["api_key"]
        assert result["safe"] == "normal value"

    def test_hash_content(self, tracker: VendorSessionTracker) -> None:
        """Verify content hashing works correctly."""
        content = "This is some test content"
        hash1 = tracker._hash_content(content)
        hash2 = tracker._hash_content(content)

        assert len(hash1) == 16
        assert hash1 == hash2

        different_hash = tracker._hash_content("Different content")
        assert different_hash != hash1


class TestCredentialPatterns:
    """Tests for credential pattern matching."""

    def test_patterns_exist(self) -> None:
        """Verify credential patterns are defined."""
        assert len(CREDENTIAL_PATTERNS) > 0

    def test_all_patterns_are_tuples(self) -> None:
        """Verify all patterns are (regex, replacement) tuples."""
        for pattern, replacement in CREDENTIAL_PATTERNS:
            assert hasattr(pattern, "sub")
            assert isinstance(replacement, str)
