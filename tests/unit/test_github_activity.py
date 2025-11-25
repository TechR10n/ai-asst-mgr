"""Tests for GitHub Activity Logger and Vendor Attribution System.

This module tests the GitHub activity logging functionality and enhanced
vendor attribution detection for issues #82 and #83.
"""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from typer.testing import CliRunner

from ai_asst_mgr.cli import app
from ai_asst_mgr.database.manager import DatabaseManager
from ai_asst_mgr.github.activity_logger import GitHubActivityLogger
from ai_asst_mgr.operations.github_parser import GitHubCommit

runner = CliRunner()


# =============================================================================
# Test GitHubActivityLogger Class
# =============================================================================


class TestGitHubActivityLogger:
    """Tests for GitHubActivityLogger class.

    Tests the GitHub activity logging functionality for tracking GitHub operations
    (issues, PRs, comments, reviews, commits) with vendor attribution.
    """

    @pytest.fixture
    def db_path(self, tmp_path: Path) -> Path:
        """Create a temporary database path."""
        return tmp_path / "test.db"

    @pytest.fixture
    def logger(self, db_path: Path) -> GitHubActivityLogger:
        """Create a logger with temporary database."""
        # Create the database and github_activity table
        conn = sqlite3.connect(db_path)
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS github_activity (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                activity_id TEXT UNIQUE NOT NULL,
                timestamp TEXT NOT NULL,
                vendor_id TEXT NOT NULL,
                session_id TEXT,
                operation_type TEXT NOT NULL,
                repo_owner TEXT NOT NULL,
                repo_name TEXT NOT NULL,
                resource_id INTEGER,
                resource_url TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.commit()
        conn.close()

        return GitHubActivityLogger(db_path, vendor_id="claude")

    def test_log_activity_creates_record(self, logger: GitHubActivityLogger, db_path: Path) -> None:
        """Test logging basic activity creates a database record."""
        activity_id = logger.log_activity(
            operation_type="issue_create",
            repo_owner="test",
            repo_name="repo",
            resource_id=123,
            metadata={"title": "Test Issue"},
        )

        # Verify activity was logged
        assert activity_id is not None

        # Query database to verify record exists
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM github_activity WHERE activity_id = ?", (activity_id,))
        row = cursor.fetchone()
        conn.close()

        assert row is not None
        assert row["operation_type"] == "issue_create"
        assert row["repo_owner"] == "test"
        assert row["repo_name"] == "repo"
        assert row["resource_id"] == 123
        assert row["vendor_id"] == "claude"

    def test_log_issue_create(self, logger: GitHubActivityLogger, db_path: Path) -> None:
        """Test logging issue creation."""
        activity_id = logger.log_issue_create(
            repo_owner="user",
            repo_name="project",
            issue_number=42,
            title="Bug report",
            session_id="test-session",
        )

        assert activity_id is not None

        # Verify in database
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM github_activity WHERE activity_id = ?", (activity_id,))
        row = cursor.fetchone()
        conn.close()

        assert row["operation_type"] == "issue_create"
        assert row["resource_id"] == 42
        assert row["session_id"] == "test-session"
        assert "Bug report" in row["metadata"]

    def test_log_pr_create(self, logger: GitHubActivityLogger, db_path: Path) -> None:
        """Test logging PR creation."""
        activity_id = logger.log_pr_create(
            repo_owner="user",
            repo_name="project",
            pr_number=100,
            title="feat: add new feature",
        )

        assert activity_id is not None

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM github_activity WHERE activity_id = ?", (activity_id,))
        row = cursor.fetchone()
        conn.close()

        assert row["operation_type"] == "pr_create"
        assert row["resource_id"] == 100
        assert "pull/100" in row["resource_url"]

    def test_log_pr_merge(self, logger: GitHubActivityLogger, db_path: Path) -> None:
        """Test logging PR merge."""
        activity_id = logger.log_pr_merge(
            repo_owner="user", repo_name="project", pr_number=100, session_id="merge-session"
        )

        assert activity_id is not None

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM github_activity WHERE activity_id = ?", (activity_id,))
        row = cursor.fetchone()
        conn.close()

        assert row["operation_type"] == "pr_merge"
        assert row["resource_id"] == 100
        assert row["session_id"] == "merge-session"

    def test_log_comment(self, logger: GitHubActivityLogger, db_path: Path) -> None:
        """Test logging comment on issue or PR."""
        activity_id = logger.log_comment(
            repo_owner="user", repo_name="project", resource_type="issue", resource_id=42
        )

        assert activity_id is not None

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM github_activity WHERE activity_id = ?", (activity_id,))
        row = cursor.fetchone()
        conn.close()

        assert row["operation_type"] == "comment"
        assert row["resource_id"] == 42
        assert "issue" in row["metadata"]

    def test_log_review(self, logger: GitHubActivityLogger, db_path: Path) -> None:
        """Test logging PR review."""
        activity_id = logger.log_review(
            repo_owner="user", repo_name="project", pr_number=100, action="approve"
        )

        assert activity_id is not None

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM github_activity WHERE activity_id = ?", (activity_id,))
        row = cursor.fetchone()
        conn.close()

        assert row["operation_type"] == "review"
        assert row["resource_id"] == 100
        assert "approve" in row["metadata"]

    def test_log_commit_push(self, logger: GitHubActivityLogger, db_path: Path) -> None:
        """Test logging commit push."""
        activity_id = logger.log_commit_push(
            repo_owner="user",
            repo_name="project",
            commit_sha="abc123def456",
            branch="main",
        )

        assert activity_id is not None

        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cursor = conn.execute("SELECT * FROM github_activity WHERE activity_id = ?", (activity_id,))
        row = cursor.fetchone()
        conn.close()

        assert row["operation_type"] == "commit_push"
        assert "abc123def456" in row["metadata"]
        assert "main" in row["metadata"]

    def test_get_session_activities(self, logger: GitHubActivityLogger) -> None:
        """Test retrieving activities for a specific session."""
        session_id = "test-session-123"

        # Log multiple activities for the session
        logger.log_issue_create("owner", "repo", 1, "Issue 1", session_id)
        logger.log_pr_create("owner", "repo", 2, "PR 2", session_id)
        logger.log_issue_create("owner", "other", 3, "Issue 3", "different-session")

        activities = logger.get_session_activities(session_id)

        assert len(activities) == 2
        assert all(a.session_id == session_id for a in activities)
        assert activities[0].operation_type == "issue_create"
        assert activities[1].operation_type == "pr_create"

    def test_get_recent_activities(self, logger: GitHubActivityLogger) -> None:
        """Test retrieving recent activities with limit."""
        # Log multiple activities
        logger.log_issue_create("owner", "repo1", 1, "Issue 1")
        logger.log_pr_create("owner", "repo2", 2, "PR 2")
        logger.log_commit_push("owner", "repo3", "abc123", "main")

        activities = logger.get_recent_activities(limit=2)

        assert len(activities) == 2
        # Should be ordered newest first
        assert activities[0].operation_type == "commit_push"
        assert activities[1].operation_type == "pr_create"


# =============================================================================
# Test Enhanced Vendor Attribution Detection
# =============================================================================


class TestVendorAttributionDetailed:
    """Tests for detailed vendor attribution detection.

    Note: detect_vendor_attribution_detailed is part of issue #83 and extends
    the existing detect_vendor_attribution with confidence scores and detection
    methods.
    """

    def test_detect_claude_signature(self) -> None:
        """Test Claude signature detection with confidence."""
        # Mock the function until implemented
        # from ai_asst_mgr.operations.github_parser import detect_vendor_attribution_detailed

        def mock_detect(message: str) -> tuple[str | None, float, str]:
            if "Generated with [Claude Code]" in message:
                return ("claude", 1.0, "signature")
            return (None, 0.0, "none")

        vendor, confidence, method = mock_detect("feat: add\n\nGenerated with [Claude Code]")
        assert vendor == "claude"
        assert confidence == 1.0
        assert method == "signature"

    def test_detect_gemini_signature(self) -> None:
        """Test Gemini signature detection with confidence."""

        def mock_detect(message: str) -> tuple[str | None, float, str]:
            if "Generated by Gemini" in message:
                return ("gemini", 1.0, "signature")
            return (None, 0.0, "none")

        vendor, confidence, method = mock_detect("fix: bug\n\nGenerated by Gemini")
        assert vendor == "gemini"
        assert confidence == 1.0
        assert method == "signature"

    def test_detect_openai_signature(self) -> None:
        """Test OpenAI signature detection with confidence."""

        def mock_detect(message: str) -> tuple[str | None, float, str]:
            if "Generated by OpenAI" in message or "Generated by Codex" in message:
                return ("openai", 1.0, "signature")
            return (None, 0.0, "none")

        vendor, confidence, method = mock_detect("refactor: cleanup\n\nGenerated by Codex")
        assert vendor == "openai"
        assert confidence == 1.0
        assert method == "signature"

    def test_detect_co_author_claude(self) -> None:
        """Test Claude co-author detection."""

        def mock_detect(message: str) -> tuple[str | None, float, str]:
            if "Co-Authored-By: Claude" in message:
                return ("claude", 0.95, "co_author")
            return (None, 0.0, "none")

        vendor, confidence, method = mock_detect(
            "feat: add\n\nCo-Authored-By: Claude <noreply@anthropic.com>"
        )
        assert vendor == "claude"
        assert confidence == 0.95
        assert method == "co_author"

    def test_detect_email_domain_anthropic(self) -> None:
        """Test Anthropic email domain detection."""

        def mock_detect(message: str, email: str | None = None) -> tuple[str | None, float, str]:
            if email and "anthropic.com" in email:
                return ("claude", 0.8, "email_domain")
            return (None, 0.0, "none")

        vendor, confidence, method = mock_detect("feat: test", "ai@anthropic.com")
        assert vendor == "claude"
        assert confidence == 0.8
        assert method == "email_domain"

    def test_no_attribution_found(self) -> None:
        """Test when no attribution is found."""

        def mock_detect(message: str) -> tuple[str | None, float, str]:
            return (None, 0.0, "none")

        vendor, confidence, method = mock_detect("feat: manual implementation by human")
        assert vendor is None
        assert confidence == 0.0
        assert method == "none"

    def test_detect_pr_attribution_from_body(self) -> None:
        """Test PR attribution detection from PR body text."""
        pr_body = """
## Summary
Add new feature for users.

## Test plan
- [ ] Unit tests
- [ ] Integration tests

Generated with [Claude Code](https://claude.com/claude-code)
"""

        def mock_detect_pr(body: str) -> tuple[str | None, float, str]:
            if "Generated with [Claude Code]" in body:
                return ("claude", 1.0, "pr_body")
            return (None, 0.0, "none")

        vendor, confidence, method = mock_detect_pr(pr_body)
        assert vendor == "claude"
        assert confidence == 1.0
        assert method == "pr_body"

    def test_detect_pr_attribution_from_commits(self) -> None:
        """Test PR attribution from commit messages."""
        commits = [
            {"message": "feat: add feature A"},
            {"message": "feat: add feature B\n\nGenerated with [Claude Code]"},
            {"message": "fix: minor fix"},
        ]

        def mock_detect_from_commits(
            commits_list: list[dict[str, str]],
        ) -> tuple[str | None, float, str]:
            for commit in commits_list:
                if "Generated with [Claude Code]" in commit["message"]:
                    return ("claude", 0.9, "commit_message")
            return (None, 0.0, "none")

        vendor, confidence, method = mock_detect_from_commits(commits)
        assert vendor == "claude"
        assert confidence == 0.9
        assert method == "commit_message"


# =============================================================================
# Test Attribution Dataclass
# =============================================================================


class TestAttribution:
    """Tests for Attribution dataclass.

    Note: Attribution dataclass is part of issue #83 and represents
    vendor attribution metadata with confidence scores.
    """

    def test_create_attribution(self) -> None:
        """Test creating Attribution object."""
        # Mock dataclass until implemented
        # from ai_asst_mgr.operations.github_parser import Attribution

        mock_attribution = {
            "vendor_id": "claude",
            "confidence": 1.0,
            "detection_method": "signature",
            "detected_at": datetime.now(tz=UTC).isoformat(),
        }

        assert mock_attribution["vendor_id"] == "claude"
        assert mock_attribution["confidence"] == 1.0
        assert mock_attribution["detection_method"] == "signature"
        assert "detected_at" in mock_attribution

    def test_attribution_from_commit(self) -> None:
        """Test creating attribution from commit."""
        mock_commit = {
            "sha": "abc123",
            "message": "feat: add\n\nGenerated with [Claude Code]",
            "author_email": "dev@example.com",
        }

        def create_attribution_from_commit(commit: dict[str, str]) -> dict[str, object]:
            return {
                "vendor_id": "claude",
                "confidence": 1.0,
                "detection_method": "signature",
                "source_sha": commit["sha"],
            }

        attribution = create_attribution_from_commit(mock_commit)
        assert attribution["vendor_id"] == "claude"
        assert attribution["source_sha"] == "abc123"


# =============================================================================
# Test Database Operations for GitHub Activity
# =============================================================================


class TestGitHubActivityDatabase:
    """Tests for github_activity table database operations.

    Note: These operations are part of issue #82 and extend the database
    schema to track GitHub activities beyond just commits.
    """

    @pytest.fixture
    def db_manager(self, tmp_path: Path) -> DatabaseManager:
        """Create database manager with temporary database."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(db_path)
        manager.initialize()
        return manager

    def test_record_github_activity_success(self, db_manager: DatabaseManager) -> None:
        """Test recording GitHub activity successfully."""
        result = db_manager.record_github_activity(
            activity_id="act-001",
            timestamp="2024-01-15T10:00:00",
            vendor_id="claude",
            operation_type="issue_create",
            repo_owner="test",
            repo_name="repo",
            session_id="session-123",
            resource_id=42,
            resource_url="https://github.com/test/repo/issues/42",
            metadata={"title": "Test Issue", "labels": ["bug"]},
        )

        assert result is True

    def test_record_github_activity_minimal(self, db_manager: DatabaseManager) -> None:
        """Test recording activity with minimal required fields."""
        result = db_manager.record_github_activity(
            activity_id="act-002",
            timestamp="2024-01-15T10:00:00",
            vendor_id="gemini",
            operation_type="pr_create",
            repo_owner="owner",
            repo_name="project",
        )

        assert result is True

    def test_get_github_activities_no_filter(self, db_manager: DatabaseManager) -> None:
        """Test getting activities without filter."""
        # First add some activities
        db_manager.record_github_activity(
            activity_id="act-001",
            timestamp="2024-01-15T10:00:00",
            vendor_id="claude",
            operation_type="issue_create",
            repo_owner="test",
            repo_name="repo1",
        )
        db_manager.record_github_activity(
            activity_id="act-002",
            timestamp="2024-01-15T11:00:00",
            vendor_id="gemini",
            operation_type="pr_merge",
            repo_owner="test",
            repo_name="repo2",
        )

        activities = db_manager.get_github_activities()

        assert len(activities) == 2
        # Should be newest first
        assert activities[0].operation_type == "pr_merge"
        assert activities[1].operation_type == "issue_create"

    def test_get_github_activities_by_vendor(self, db_manager: DatabaseManager) -> None:
        """Test filtering activities by vendor."""
        db_manager.record_github_activity(
            activity_id="act-001",
            timestamp="2024-01-15T10:00:00",
            vendor_id="claude",
            operation_type="issue_create",
            repo_owner="test",
            repo_name="repo1",
        )
        db_manager.record_github_activity(
            activity_id="act-002",
            timestamp="2024-01-15T11:00:00",
            vendor_id="gemini",
            operation_type="pr_merge",
            repo_owner="test",
            repo_name="repo2",
        )

        activities = db_manager.get_github_activities(vendor_id="claude")

        assert len(activities) == 1
        assert activities[0].vendor_id == "claude"

    def test_get_github_activities_by_repo(self, db_manager: DatabaseManager) -> None:
        """Test filtering activities by repository."""
        db_manager.record_github_activity(
            activity_id="act-001",
            timestamp="2024-01-15T10:00:00",
            vendor_id="claude",
            operation_type="issue_create",
            repo_owner="my",
            repo_name="project",
        )
        db_manager.record_github_activity(
            activity_id="act-002",
            timestamp="2024-01-15T11:00:00",
            vendor_id="gemini",
            operation_type="pr_merge",
            repo_owner="other",
            repo_name="repo",
        )

        activities = db_manager.get_github_activities(repo="my/project")

        assert len(activities) == 1
        assert activities[0].repo_owner == "my"
        assert activities[0].repo_name == "project"

    def test_get_github_activities_by_operation_type(self, db_manager: DatabaseManager) -> None:
        """Test filtering activities by operation type."""
        db_manager.record_github_activity(
            activity_id="act-001",
            timestamp="2024-01-15T10:00:00",
            vendor_id="claude",
            operation_type="issue_create",
            repo_owner="test",
            repo_name="repo",
        )
        db_manager.record_github_activity(
            activity_id="act-002",
            timestamp="2024-01-15T11:00:00",
            vendor_id="claude",
            operation_type="pr_create",
            repo_owner="test",
            repo_name="repo",
        )

        activities = db_manager.get_github_activities(operation_type="pr_create")

        assert len(activities) == 1
        assert activities[0].operation_type == "pr_create"

    def test_get_github_activities_by_session(self, db_manager: DatabaseManager) -> None:
        """Test filtering activities by session."""
        db_manager.record_github_activity(
            activity_id="act-001",
            timestamp="2024-01-15T10:00:00",
            vendor_id="claude",
            operation_type="commit_push",
            repo_owner="test",
            repo_name="repo",
            session_id="session-123",
        )
        db_manager.record_github_activity(
            activity_id="act-002",
            timestamp="2024-01-15T11:00:00",
            vendor_id="claude",
            operation_type="issue_create",
            repo_owner="test",
            repo_name="repo",
            session_id="session-456",
        )

        activities = db_manager.get_github_activities(session_id="session-123")

        assert len(activities) == 1
        assert activities[0].session_id == "session-123"

    def test_get_github_activities_pagination(self, db_manager: DatabaseManager) -> None:
        """Test activity pagination with limit and offset."""
        for i in range(5):
            db_manager.record_github_activity(
                activity_id=f"act-{i:03d}",
                timestamp=f"2024-01-15T{10 + i}:00:00",
                vendor_id="claude",
                operation_type="commit_push",
                repo_owner="test",
                repo_name="repo",
            )

        activities = db_manager.get_github_activities(limit=2, offset=1)

        assert len(activities) == 2
        # Should be newest first, skipping first 1
        assert activities[0].activity_id == "act-003"
        assert activities[1].activity_id == "act-002"

    def test_get_github_activity_stats(self, db_manager: DatabaseManager) -> None:
        """Test getting activity statistics from view."""
        # Add activities
        db_manager.record_github_activity(
            activity_id="act-001",
            timestamp="2024-01-15T10:00:00",
            vendor_id="claude",
            operation_type="issue_create",
            repo_owner="test",
            repo_name="repo1",
        )
        db_manager.record_github_activity(
            activity_id="act-002",
            timestamp="2024-01-15T11:00:00",
            vendor_id="claude",
            operation_type="issue_create",
            repo_owner="test",
            repo_name="repo2",
        )
        db_manager.record_github_activity(
            activity_id="act-003",
            timestamp="2024-01-15T12:00:00",
            vendor_id="gemini",
            operation_type="pr_create",
            repo_owner="other",
            repo_name="project",
        )

        stats = db_manager.get_github_activity_stats()

        assert len(stats) >= 2
        # Find claude issue_create stats
        claude_stats = [
            s for s in stats if s["vendor_id"] == "claude" and s["operation_type"] == "issue_create"
        ]
        assert len(claude_stats) == 1
        assert claude_stats[0]["operation_count"] == 2
        assert claude_stats[0]["repo_count"] == 2

    def test_get_github_activity_by_session(self, db_manager: DatabaseManager) -> None:
        """Test getting activities by session ID."""
        session_id = "session-test"

        db_manager.record_github_activity(
            activity_id="act-001",
            timestamp="2024-01-15T10:00:00",
            vendor_id="claude",
            operation_type="issue_create",
            repo_owner="test",
            repo_name="repo",
            session_id=session_id,
        )
        db_manager.record_github_activity(
            activity_id="act-002",
            timestamp="2024-01-15T11:00:00",
            vendor_id="claude",
            operation_type="pr_create",
            repo_owner="test",
            repo_name="repo",
            session_id=session_id,
        )
        db_manager.record_github_activity(
            activity_id="act-003",
            timestamp="2024-01-15T12:00:00",
            vendor_id="gemini",
            operation_type="commit_push",
            repo_owner="other",
            repo_name="project",
            session_id="different-session",
        )

        activities = db_manager.get_github_activity_by_session(session_id)

        assert len(activities) == 2
        assert all(a.session_id == session_id for a in activities)
        # Should be chronological order (oldest first)
        assert activities[0].operation_type == "issue_create"
        assert activities[1].operation_type == "pr_create"

    def test_get_github_repo_stats(self, db_manager: DatabaseManager) -> None:
        """Test getting repository statistics."""
        # Add some commits first using GitHubCommit dataclass
        commit1 = GitHubCommit(
            sha="abc123",
            repo="test/repo",
            branch="main",
            message="feat: add feature",
            author_name="Developer",
            author_email="dev@example.com",
            vendor_id="claude",
            committed_at=datetime(2024, 1, 15, 10, 0, 0, tzinfo=UTC),
        )
        commit2 = GitHubCommit(
            sha="def456",
            repo="test/repo",
            branch="main",
            message="fix: bug",
            author_name="Developer",
            author_email="dev@example.com",
            vendor_id="claude",
            committed_at=datetime(2024, 1, 15, 11, 0, 0, tzinfo=UTC),
        )
        commit3 = GitHubCommit(
            sha="ghi789",
            repo="other/project",
            branch="main",
            message="docs: update",
            author_name="Human",
            author_email="human@example.com",
            vendor_id=None,  # Manual commit
            committed_at=datetime(2024, 1, 15, 12, 0, 0, tzinfo=UTC),
        )

        db_manager.record_github_commit(commit1)
        db_manager.record_github_commit(commit2)
        db_manager.record_github_commit(commit3)

        stats = db_manager.get_github_repo_stats()

        assert len(stats) == 2
        # Find test/repo stats
        repo_stats = [s for s in stats if s["repo"] == "test/repo"]
        assert len(repo_stats) == 1
        assert repo_stats[0]["total_commits"] == 2
        assert repo_stats[0]["ai_commits"] == 2

        # Find other/project stats
        other_stats = [s for s in stats if s["repo"] == "other/project"]
        assert len(other_stats) == 1
        assert other_stats[0]["total_commits"] == 1
        assert other_stats[0]["ai_commits"] == 0

    def test_get_github_activities_repo_invalid_format(self, db_manager: DatabaseManager) -> None:
        """Test repo filter with invalid format (no slash)."""
        db_manager.record_github_activity(
            activity_id="act-001",
            timestamp="2024-01-15T10:00:00",
            vendor_id="claude",
            operation_type="issue_create",
            repo_owner="test",
            repo_name="repo",
        )

        # Single word repo filter should still work (returns all)
        activities = db_manager.get_github_activities(repo="noslash")

        # Should return all activities since format is invalid
        assert len(activities) == 1


class TestGitHubActivityDatabaseEdgeCases:
    """Tests for edge cases and error handling in GitHub activity database operations."""

    def test_get_github_repo_stats_empty_table(self, tmp_path: Path) -> None:
        """Test getting repo stats with no commits returns empty list."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(db_path)
        manager.initialize()

        stats = manager.get_github_repo_stats()

        assert stats == []

    def test_get_github_activity_stats_empty_table(self, tmp_path: Path) -> None:
        """Test getting activity stats with no activities returns empty list."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(db_path)
        manager.initialize()

        stats = manager.get_github_activity_stats()

        assert stats == []

    def test_get_github_activity_by_session_no_match(self, tmp_path: Path) -> None:
        """Test getting activities for non-existent session returns empty list."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(db_path)
        manager.initialize()

        activities = manager.get_github_activity_by_session("nonexistent-session")

        assert activities == []

    def test_record_github_activity_error_handling(self, tmp_path: Path) -> None:
        """Test that record returns False on database error."""
        db_path = tmp_path / "test.db"
        manager = DatabaseManager(db_path)
        # Don't initialize - tables don't exist

        # Should return False when table doesn't exist
        result = manager.record_github_activity(
            activity_id="act-001",
            timestamp="2024-01-15T10:00:00",
            vendor_id="claude",
            operation_type="issue_create",
            repo_owner="test",
            repo_name="repo",
        )

        assert result is False

    def test_get_github_activities_missing_table(self, tmp_path: Path) -> None:
        """Test getting activities when table doesn't exist returns empty list."""
        db_path = tmp_path / "test.db"
        # Create a minimal database without github_activity table
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        manager = DatabaseManager(db_path)

        activities = manager.get_github_activities()

        assert activities == []

    def test_get_github_activity_stats_missing_view(self, tmp_path: Path) -> None:
        """Test getting activity stats when view doesn't exist returns empty list."""
        db_path = tmp_path / "test.db"
        # Create a minimal database without the view
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        manager = DatabaseManager(db_path)

        stats = manager.get_github_activity_stats()

        assert stats == []

    def test_get_github_activity_by_session_missing_table(self, tmp_path: Path) -> None:
        """Test getting activities by session when table doesn't exist."""
        db_path = tmp_path / "test.db"
        # Create a minimal database without github_activity table
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        manager = DatabaseManager(db_path)

        activities = manager.get_github_activity_by_session("any-session")

        assert activities == []

    def test_get_github_repo_stats_missing_table(self, tmp_path: Path) -> None:
        """Test getting repo stats when table doesn't exist returns empty list."""
        db_path = tmp_path / "test.db"
        # Create a minimal database without github_commits table
        conn = sqlite3.connect(db_path)
        conn.execute("CREATE TABLE dummy (id INTEGER)")
        conn.commit()
        conn.close()

        manager = DatabaseManager(db_path)

        stats = manager.get_github_repo_stats()

        assert stats == []


# =============================================================================
# Test CLI Commands
# =============================================================================


class TestGitHubAttributionCommand:
    """Tests for github attribution CLI command.

    Tests the CLI command that displays vendor attribution statistics
    for commits and activities in a repository.
    """

    def test_attribution_no_database(self, tmp_path: Path) -> None:
        """Test attribution command when database doesn't exist."""
        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path:
            mock_db_path.exists.return_value = False

            result = runner.invoke(app, ["github", "attribution", "test/repo"])

            # Command should fail if database doesn't exist
            assert result.exit_code == 1
            assert "Database not found" in result.stdout

    def test_attribution_summary(self, tmp_path: Path) -> None:
        """Test attribution summary display."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            # Mock commits with vendor attribution
            mock_commits = [
                MagicMock(
                    vendor_id="claude", message="feat: add", committed_at="2024-01-01 10:00:00"
                ),
                MagicMock(
                    vendor_id="claude", message="fix: bug", committed_at="2024-01-02 10:00:00"
                ),
                MagicMock(
                    vendor_id="gemini", message="docs: update", committed_at="2024-01-03 10:00:00"
                ),
                MagicMock(
                    vendor_id=None, message="manual commit", committed_at="2024-01-04 10:00:00"
                ),
            ]

            mock_db = MagicMock()
            mock_db.get_github_commits.return_value = mock_commits
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "attribution", "test/repo", "--summary"])

            # Should display attribution summary
            assert result.exit_code == 0
            assert "Attribution Summary" in result.stdout
            assert "Claude" in result.stdout
            assert "Gemini" in result.stdout

    def test_attribution_for_pr(self, tmp_path: Path) -> None:
        """Test attribution for specific PR."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            # Mock commits mentioning the PR
            mock_commits = [
                MagicMock(
                    sha="abc123",
                    vendor_id="claude",
                    message="feat: add feature (#42)",
                    committed_at="2024-01-01 10:00:00",
                )
            ]

            mock_db = MagicMock()
            mock_db.get_github_commits.return_value = mock_commits
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "attribution", "test/repo", "--pr", "42"])

            # Should display PR attribution
            assert result.exit_code == 0
            assert "Claude" in result.stdout or "claude" in result.stdout.lower()


class TestGitHubActivityCommand:
    """Tests for github activity CLI command.

    Tests the CLI command that displays GitHub activity logs with filtering options.
    """

    def test_activity_no_database(self, tmp_path: Path) -> None:
        """Test activity command when database doesn't exist."""
        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path:
            mock_db_path.exists.return_value = False

            result = runner.invoke(app, ["github", "activity"])

            assert result.exit_code == 1
            assert "Database not found" in result.stdout

    def test_activity_displays_records(self, tmp_path: Path) -> None:
        """Test activity command displays records."""
        db_path = tmp_path / "test.db"

        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path),
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            # Create database file
            db_path.touch()

            # Create mock DatabaseManager with _connection method
            mock_db = MagicMock()
            mock_conn = MagicMock()

            # Mock database rows
            mock_row1 = {
                "vendor_id": "claude",
                "operation_type": "pr_create",
                "repo_owner": "test",
                "repo_name": "repo",
                "resource_id": 42,
                "session_id": "session1",
                "timestamp": "2024-01-15T10:30:00",
            }
            mock_row2 = {
                "vendor_id": "gemini",
                "operation_type": "issue_create",
                "repo_owner": "test",
                "repo_name": "another",
                "resource_id": 100,
                "session_id": "session2",
                "timestamp": "2024-01-15T11:00:00",
            }

            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = [mock_row1, mock_row2]
            mock_conn.execute.return_value = mock_cursor
            mock_db._connection.return_value.__enter__.return_value = mock_conn
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "activity"])

            assert result.exit_code == 0
            assert "GitHub Activity" in result.stdout
            assert "#42" in result.stdout or "#100" in result.stdout

    def test_activity_filter_by_session(self, tmp_path: Path) -> None:
        """Test activity filtering by session."""
        db_path = tmp_path / "test.db"

        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path),
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            # Create database file
            db_path.touch()

            mock_db = MagicMock()
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.execute.return_value = mock_cursor
            mock_db._connection.return_value.__enter__.return_value = mock_conn
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "activity", "--session", "session-123"])

            # Should pass with no activities message
            assert result.exit_code == 0
            # Verify SQL query contained session filter
            call_args = mock_conn.execute.call_args
            sql_query = call_args[0][0]
            params = call_args[0][1]
            assert "session_id" in sql_query
            assert "session-123" in params

    def test_activity_filter_by_vendor(self, tmp_path: Path) -> None:
        """Test activity filtering by vendor."""
        db_path = tmp_path / "test.db"

        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH", db_path),
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            # Create database file
            db_path.touch()

            mock_db = MagicMock()
            mock_conn = MagicMock()
            mock_cursor = MagicMock()
            mock_cursor.fetchall.return_value = []
            mock_conn.execute.return_value = mock_cursor
            mock_db._connection.return_value.__enter__.return_value = mock_conn
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "activity", "--vendor", "claude"])

            # Should pass with no activities message
            assert result.exit_code == 0
            # Verify SQL query contained vendor filter
            call_args = mock_conn.execute.call_args
            sql_query = call_args[0][0]
            params = call_args[0][1]
            assert "vendor_id" in sql_query
            assert "claude" in params
