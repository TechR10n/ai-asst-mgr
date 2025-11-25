"""GitHub activity logger for tracking GitHub operations during AI sessions.

This module provides the GitHubActivityLogger class for logging GitHub operations
such as issue creation, PR creation, merges, comments, reviews, and commit pushes.
"""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Iterator
    from pathlib import Path


@dataclass
class GitHubActivity:
    """Represents a GitHub activity performed during a session.

    Attributes:
        activity_id: Unique identifier for the activity.
        timestamp: When the activity occurred.
        vendor_id: AI vendor identifier (claude, gemini, openai).
        session_id: Associated session ID (optional).
        operation_type: Type of operation (issue_create, pr_create, pr_merge, etc).
        repo_owner: GitHub repository owner/organization.
        repo_name: GitHub repository name.
        resource_id: Issue/PR number or other resource identifier (optional).
        resource_url: Full URL to the GitHub resource (optional).
        metadata: Additional operation-specific data (optional).
    """

    activity_id: str
    timestamp: datetime
    vendor_id: str
    session_id: str | None
    operation_type: str
    repo_owner: str
    repo_name: str
    resource_id: int | None
    resource_url: str | None
    metadata: dict[str, Any] | None


class GitHubActivityLogger:
    """Logger for GitHub operations performed during AI sessions.

    This class provides methods to log various GitHub activities such as
    creating issues, pull requests, merging PRs, adding comments, and pushing commits.
    All activities are stored in the unified session database for tracking and analysis.

    Example:
        >>> logger = GitHubActivityLogger(db_path, vendor_id="claude")
        >>> activity_id = logger.log_pr_create(
        ...     "TechR10n", "ai-asst-mgr", 90, "Add feature", session_id="abc123"
        ... )
    """

    def __init__(self, db_path: Path, vendor_id: str = "claude") -> None:
        """Initialize the GitHub activity logger.

        Args:
            db_path: Path to the SQLite database file.
            vendor_id: Default vendor identifier (defaults to "claude").
        """
        self.db_path = db_path
        self.vendor_id = vendor_id

    @contextmanager
    def _connection(self) -> Iterator[sqlite3.Connection]:
        """Create a database connection context manager.

        Yields:
            SQLite connection with row factory enabled.
        """
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def log_activity(
        self,
        operation_type: str,
        repo_owner: str,
        repo_name: str,
        session_id: str | None = None,
        resource_id: int | None = None,
        resource_url: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> str:
        """Log a GitHub activity to the database.

        Args:
            operation_type: Type of operation (issue_create, pr_create, pr_merge, etc).
            repo_owner: GitHub repository owner/organization.
            repo_name: GitHub repository name.
            session_id: Associated session ID (optional).
            resource_id: Issue/PR number or other resource identifier (optional).
            resource_url: Full URL to the GitHub resource (optional).
            metadata: Additional operation-specific data (optional).

        Returns:
            The generated activity_id.
        """
        activity_id = str(uuid.uuid4())
        timestamp = datetime.now(tz=UTC).isoformat()

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO github_activity (
                    activity_id, timestamp, vendor_id, session_id,
                    operation_type, repo_owner, repo_name,
                    resource_id, resource_url, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    activity_id,
                    timestamp,
                    self.vendor_id,
                    session_id,
                    operation_type,
                    repo_owner,
                    repo_name,
                    resource_id,
                    resource_url,
                    json.dumps(metadata) if metadata else None,
                ),
            )
            conn.commit()

        return activity_id

    def log_issue_create(
        self,
        repo_owner: str,
        repo_name: str,
        issue_number: int,
        title: str,
        session_id: str | None = None,
    ) -> str:
        """Log an issue creation activity.

        Args:
            repo_owner: GitHub repository owner/organization.
            repo_name: GitHub repository name.
            issue_number: The created issue number.
            title: The issue title.
            session_id: Associated session ID (optional).

        Returns:
            The generated activity_id.
        """
        return self.log_activity(
            operation_type="issue_create",
            repo_owner=repo_owner,
            repo_name=repo_name,
            session_id=session_id,
            resource_id=issue_number,
            resource_url=f"https://github.com/{repo_owner}/{repo_name}/issues/{issue_number}",
            metadata={"title": title},
        )

    def log_pr_create(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        title: str,
        session_id: str | None = None,
    ) -> str:
        """Log a pull request creation activity.

        Args:
            repo_owner: GitHub repository owner/organization.
            repo_name: GitHub repository name.
            pr_number: The created pull request number.
            title: The pull request title.
            session_id: Associated session ID (optional).

        Returns:
            The generated activity_id.
        """
        return self.log_activity(
            operation_type="pr_create",
            repo_owner=repo_owner,
            repo_name=repo_name,
            session_id=session_id,
            resource_id=pr_number,
            resource_url=f"https://github.com/{repo_owner}/{repo_name}/pull/{pr_number}",
            metadata={"title": title},
        )

    def log_pr_merge(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        session_id: str | None = None,
    ) -> str:
        """Log a pull request merge activity.

        Args:
            repo_owner: GitHub repository owner/organization.
            repo_name: GitHub repository name.
            pr_number: The merged pull request number.
            session_id: Associated session ID (optional).

        Returns:
            The generated activity_id.
        """
        return self.log_activity(
            operation_type="pr_merge",
            repo_owner=repo_owner,
            repo_name=repo_name,
            session_id=session_id,
            resource_id=pr_number,
            resource_url=f"https://github.com/{repo_owner}/{repo_name}/pull/{pr_number}",
        )

    def log_comment(
        self,
        repo_owner: str,
        repo_name: str,
        resource_type: str,
        resource_id: int,
        session_id: str | None = None,
    ) -> str:
        """Log a comment activity on an issue or pull request.

        Args:
            repo_owner: GitHub repository owner/organization.
            repo_name: GitHub repository name.
            resource_type: Type of resource ("issue" or "pr").
            resource_id: Issue or PR number.
            session_id: Associated session ID (optional).

        Returns:
            The generated activity_id.
        """
        url_path = "issues" if resource_type == "issue" else "pull"
        return self.log_activity(
            operation_type="comment",
            repo_owner=repo_owner,
            repo_name=repo_name,
            session_id=session_id,
            resource_id=resource_id,
            resource_url=f"https://github.com/{repo_owner}/{repo_name}/{url_path}/{resource_id}",
            metadata={"resource_type": resource_type},
        )

    def log_review(
        self,
        repo_owner: str,
        repo_name: str,
        pr_number: int,
        action: str,
        session_id: str | None = None,
    ) -> str:
        """Log a pull request review activity.

        Args:
            repo_owner: GitHub repository owner/organization.
            repo_name: GitHub repository name.
            pr_number: The pull request number being reviewed.
            action: Review action (approve, request_changes, comment).
            session_id: Associated session ID (optional).

        Returns:
            The generated activity_id.
        """
        return self.log_activity(
            operation_type="review",
            repo_owner=repo_owner,
            repo_name=repo_name,
            session_id=session_id,
            resource_id=pr_number,
            resource_url=f"https://github.com/{repo_owner}/{repo_name}/pull/{pr_number}",
            metadata={"action": action},
        )

    def log_commit_push(
        self,
        repo_owner: str,
        repo_name: str,
        commit_sha: str,
        branch: str,
        session_id: str | None = None,
    ) -> str:
        """Log a commit push activity.

        Args:
            repo_owner: GitHub repository owner/organization.
            repo_name: GitHub repository name.
            commit_sha: The commit SHA hash.
            branch: The branch name the commit was pushed to.
            session_id: Associated session ID (optional).

        Returns:
            The generated activity_id.
        """
        return self.log_activity(
            operation_type="commit_push",
            repo_owner=repo_owner,
            repo_name=repo_name,
            session_id=session_id,
            resource_url=f"https://github.com/{repo_owner}/{repo_name}/commit/{commit_sha}",
            metadata={"commit_sha": commit_sha, "branch": branch},
        )

    def get_session_activities(self, session_id: str) -> list[GitHubActivity]:
        """Get all GitHub activities for a specific session.

        Args:
            session_id: The session ID to query activities for.

        Returns:
            List of GitHubActivity objects for the session, ordered by timestamp.
        """
        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    activity_id, timestamp, vendor_id, session_id,
                    operation_type, repo_owner, repo_name,
                    resource_id, resource_url, metadata
                FROM github_activity
                WHERE session_id = ?
                ORDER BY timestamp ASC
                """,
                (session_id,),
            )
            rows = cursor.fetchall()

        return [self._row_to_activity(row) for row in rows]

    def get_recent_activities(self, limit: int = 50) -> list[GitHubActivity]:
        """Get recent GitHub activities across all sessions.

        Args:
            limit: Maximum number of activities to return (default: 50).

        Returns:
            List of GitHubActivity objects, ordered by timestamp descending (newest first).
        """
        with self._connection() as conn:
            cursor = conn.execute(
                """
                SELECT
                    activity_id, timestamp, vendor_id, session_id,
                    operation_type, repo_owner, repo_name,
                    resource_id, resource_url, metadata
                FROM github_activity
                ORDER BY timestamp DESC
                LIMIT ?
                """,
                (limit,),
            )
            rows = cursor.fetchall()

        return [self._row_to_activity(row) for row in rows]

    def _row_to_activity(self, row: sqlite3.Row) -> GitHubActivity:
        """Convert a database row to a GitHubActivity object.

        Args:
            row: SQLite row from the github_activity table.

        Returns:
            GitHubActivity object.
        """
        return GitHubActivity(
            activity_id=row["activity_id"],
            timestamp=datetime.fromisoformat(row["timestamp"]),
            vendor_id=row["vendor_id"],
            session_id=row["session_id"],
            operation_type=row["operation_type"],
            repo_owner=row["repo_owner"],
            repo_name=row["repo_name"],
            resource_id=row["resource_id"],
            resource_url=row["resource_url"],
            metadata=json.loads(row["metadata"]) if row["metadata"] else None,
        )
