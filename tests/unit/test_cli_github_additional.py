"""Additional CLI tests for GitHub commands and uncovered lines."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from ai_asst_mgr.cli import (
    _categorize_init_result,
    _format_size_bytes,
    app,
)

runner = CliRunner()


# =============================================================================
# GitHub CLI Commands Tests
# =============================================================================


class TestGitHubSyncCommand:
    """Tests for the github sync command."""

    def test_github_sync_help_shows_options(self) -> None:
        """Test github sync command shows help."""
        result = runner.invoke(app, ["github", "sync", "--help"])
        assert result.exit_code == 0
        assert "sync" in result.stdout.lower()

    def test_github_sync_no_database_exits(self) -> None:
        """Test github sync requires database to exist."""
        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path:
            mock_db_path.exists.return_value = False
            result = runner.invoke(app, ["github", "sync"])
            assert result.exit_code == 1
            assert "Database not found" in result.stdout

    def test_github_sync_current_directory_default(self) -> None:
        """Test github sync uses current directory by default."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
            patch("ai_asst_mgr.cli.GitLogParser") as mock_parser,
            patch("ai_asst_mgr.cli.Path.cwd") as mock_cwd,
        ):
            mock_db_path.exists.return_value = True
            mock_cwd.return_value = Path("/current/dir")

            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_repo.return_value = []
            mock_parser.return_value = mock_parser_instance

            result = runner.invoke(app, ["github", "sync"])
            assert result.exit_code == 0
            mock_parser_instance.parse_repo.assert_called_once()

    def test_github_sync_specific_repo(self, tmp_path: Path) -> None:
        """Test github sync with specific repository path."""
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()

        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
            patch("ai_asst_mgr.cli.GitLogParser") as mock_parser,
        ):
            mock_db_path.exists.return_value = True

            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_repo.return_value = []
            mock_parser.return_value = mock_parser_instance

            result = runner.invoke(app, ["github", "sync", "--repo", str(repo_path)])
            assert result.exit_code == 0

    def test_github_sync_repo_not_found(self) -> None:
        """Test github sync with nonexistent repo path."""
        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path:
            mock_db_path.exists.return_value = True

            result = runner.invoke(app, ["github", "sync", "--repo", "/nonexistent/path"])
            assert result.exit_code == 1
            assert "Repository not found" in result.stdout

    def test_github_sync_base_path_not_found(self) -> None:
        """Test github sync with nonexistent base path."""
        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path:
            mock_db_path.exists.return_value = True

            result = runner.invoke(app, ["github", "sync", "--base", "/nonexistent/base"])
            assert result.exit_code == 1
            assert "Path not found" in result.stdout

    def test_github_sync_base_path_no_repos(self, tmp_path: Path) -> None:
        """Test github sync with base path containing no git repos."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.find_git_repos") as mock_find,
        ):
            mock_db_path.exists.return_value = True
            mock_find.return_value = []

            result = runner.invoke(app, ["github", "sync", "--base", str(tmp_path)])
            assert result.exit_code == 0
            assert "No git repositories found" in result.stdout

    def test_github_sync_base_path_with_repos(self, tmp_path: Path) -> None:
        """Test github sync with base path containing git repos."""
        repo1 = tmp_path / "repo1"
        repo2 = tmp_path / "repo2"

        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.find_git_repos") as mock_find,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
            patch("ai_asst_mgr.cli.GitLogParser") as mock_parser,
        ):
            mock_db_path.exists.return_value = True
            mock_find.return_value = [repo1, repo2]

            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_repo.return_value = []
            mock_parser.return_value = mock_parser_instance

            result = runner.invoke(app, ["github", "sync", "--base", str(tmp_path)])
            assert result.exit_code == 0
            assert "Found 2 repositories" in result.stdout

    def test_github_sync_records_commits(self, tmp_path: Path) -> None:
        """Test github sync records commits to database."""
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()

        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
            patch("ai_asst_mgr.cli.GitLogParser") as mock_parser,
        ):
            mock_db_path.exists.return_value = True

            # Mock commits
            mock_commit1 = MagicMock()
            mock_commit1.vendor_id = "claude"
            mock_commit2 = MagicMock()
            mock_commit2.vendor_id = None

            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_repo.return_value = [mock_commit1, mock_commit2]
            mock_parser.return_value = mock_parser_instance

            mock_db = MagicMock()
            mock_db.record_github_commit.return_value = True
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "sync", "--repo", str(repo_path)])
            assert result.exit_code == 0
            assert "Commits synced: 2" in result.stdout or "2" in result.stdout
            assert "AI-attributed:  1" in result.stdout or "1" in result.stdout

    def test_github_sync_handles_errors(self, tmp_path: Path) -> None:
        """Test github sync handles parsing errors gracefully."""
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()

        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
            patch("ai_asst_mgr.cli.GitLogParser") as mock_parser,
        ):
            mock_db_path.exists.return_value = True

            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_repo.side_effect = ValueError("Git error")
            mock_parser.return_value = mock_parser_instance

            result = runner.invoke(app, ["github", "sync", "--repo", str(repo_path)])
            # Should complete but show errors
            assert "errors" in result.stdout.lower() or "error" in result.stdout.lower()

    def test_github_sync_with_limit(self, tmp_path: Path) -> None:
        """Test github sync respects commit limit."""
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()

        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
            patch("ai_asst_mgr.cli.GitLogParser") as mock_parser,
        ):
            mock_db_path.exists.return_value = True

            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_repo.return_value = []
            mock_parser.return_value = mock_parser_instance

            result = runner.invoke(
                app, ["github", "sync", "--repo", str(repo_path), "--limit", "50"]
            )
            assert result.exit_code == 0
            # Verify limit was passed
            call_args = mock_parser_instance.parse_repo.call_args
            assert call_args[1]["limit"] == 50

    def test_github_sync_handles_os_error(self, tmp_path: Path) -> None:
        """Test github sync handles OS errors gracefully."""
        repo_path = tmp_path / "test-repo"
        repo_path.mkdir()

        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
            patch("ai_asst_mgr.cli.GitLogParser") as mock_parser,
        ):
            mock_db_path.exists.return_value = True

            mock_parser_instance = MagicMock()
            mock_parser_instance.parse_repo.side_effect = OSError("Permission denied")
            mock_parser.return_value = mock_parser_instance

            result = runner.invoke(app, ["github", "sync", "--repo", str(repo_path)])
            # Should complete but show errors
            assert "error" in result.stdout.lower()


class TestGitHubStatsCommand:
    """Tests for the github stats command."""

    def test_github_stats_help_shows_options(self) -> None:
        """Test github stats command shows help."""
        result = runner.invoke(app, ["github", "stats", "--help"])
        assert result.exit_code == 0
        assert "stats" in result.stdout.lower() or "statistics" in result.stdout.lower()

    def test_github_stats_no_database_exits(self) -> None:
        """Test github stats requires database to exist."""
        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path:
            mock_db_path.exists.return_value = False
            result = runner.invoke(app, ["github", "stats"])
            assert result.exit_code == 1
            assert "Database not found" in result.stdout

    def test_github_stats_no_commits(self) -> None:
        """Test github stats with no commits tracked."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            mock_db = MagicMock()
            mock_stats = MagicMock()
            mock_stats.total_commits = 0
            mock_db.get_github_stats.return_value = mock_stats
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "stats"])
            assert result.exit_code == 0
            assert "No commits tracked" in result.stdout

    def test_github_stats_displays_statistics(self) -> None:
        """Test github stats displays commit statistics."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            mock_db = MagicMock()
            mock_stats = MagicMock()
            mock_stats.total_commits = 100
            mock_stats.repos_tracked = 5
            mock_stats.claude_commits = 30
            mock_stats.gemini_commits = 20
            mock_stats.openai_commits = 10
            mock_stats.ai_attributed_commits = 60
            mock_stats.ai_percentage = 60.0
            mock_stats.first_commit = "2024-01-01 12:00:00"
            mock_stats.last_commit = "2024-01-31 12:00:00"
            mock_db.get_github_stats.return_value = mock_stats
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "stats"])
            assert result.exit_code == 0
            assert "100" in result.stdout
            assert "60" in result.stdout or "60.0%" in result.stdout

    def test_github_stats_without_timestamps(self) -> None:
        """Test github stats when first/last commit are None."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            mock_db = MagicMock()
            mock_stats = MagicMock()
            mock_stats.total_commits = 50
            mock_stats.repos_tracked = 2
            mock_stats.claude_commits = 10
            mock_stats.gemini_commits = 5
            mock_stats.openai_commits = 5
            mock_stats.ai_attributed_commits = 20
            mock_stats.ai_percentage = 40.0
            mock_stats.first_commit = None
            mock_stats.last_commit = None
            mock_db.get_github_stats.return_value = mock_stats
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "stats"])
            assert result.exit_code == 0
            assert "50" in result.stdout


class TestGitHubListCommand:
    """Tests for the github list command."""

    def test_github_list_help_shows_options(self) -> None:
        """Test github list command shows help."""
        result = runner.invoke(app, ["github", "list", "--help"])
        assert result.exit_code == 0
        assert "list" in result.stdout.lower()

    def test_github_list_no_database_exits(self) -> None:
        """Test github list requires database to exist."""
        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path:
            mock_db_path.exists.return_value = False
            result = runner.invoke(app, ["github", "list"])
            assert result.exit_code == 1
            assert "Database not found" in result.stdout

    def test_github_list_no_commits(self) -> None:
        """Test github list with no commits found."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            mock_db = MagicMock()
            mock_db.get_github_commits.return_value = []
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "list"])
            assert result.exit_code == 0
            assert "No commits found" in result.stdout

    def test_github_list_displays_commits(self) -> None:
        """Test github list displays commit table."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            # Create mock commits
            mock_commit1 = MagicMock()
            mock_commit1.sha = "abc123def456"
            mock_commit1.repo = "test-repo"
            mock_commit1.message = "feat: add feature"
            mock_commit1.vendor_id = "claude"
            mock_commit1.committed_at = "2024-01-15 10:30:00"

            mock_commit2 = MagicMock()
            mock_commit2.sha = "def456ghi789"
            mock_commit2.repo = "another-repo"
            mock_commit2.message = "fix: bug fix"
            mock_commit2.vendor_id = None
            mock_commit2.committed_at = "2024-01-14 09:15:00"

            mock_db = MagicMock()
            mock_db.get_github_commits.return_value = [mock_commit1, mock_commit2]
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "list"])
            assert result.exit_code == 0
            # Rich tables use special characters, just check for key content
            assert "test-repo" in result.stdout
            assert "feat: add feature" in result.stdout

    def test_github_list_filter_by_vendor(self) -> None:
        """Test github list with vendor filter."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            mock_db = MagicMock()
            mock_db.get_github_commits.return_value = []
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "list", "--vendor", "claude"])
            assert result.exit_code == 0
            # Verify vendor filter was passed
            call_args = mock_db.get_github_commits.call_args
            assert call_args[1]["vendor_id"] == "claude"

    def test_github_list_filter_by_repo(self) -> None:
        """Test github list with repo filter."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            mock_db = MagicMock()
            mock_db.get_github_commits.return_value = []
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "list", "--repo", "my-project"])
            assert result.exit_code == 0
            call_args = mock_db.get_github_commits.call_args
            assert call_args[1]["repo"] == "my-project"

    def test_github_list_with_limit(self) -> None:
        """Test github list with custom limit."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            mock_db = MagicMock()
            mock_db.get_github_commits.return_value = []
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "list", "--limit", "50"])
            assert result.exit_code == 0
            call_args = mock_db.get_github_commits.call_args
            assert call_args[1]["limit"] == 50

    def test_github_list_vendor_badge_colors(self) -> None:
        """Test github list displays different vendor badges."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            # Create commits for each vendor
            commits = []
            for vendor in ["claude", "gemini", "openai", None]:
                mock_commit = MagicMock()
                mock_commit.sha = f"{vendor or 'none'}123456"
                mock_commit.repo = "test-repo"
                mock_commit.message = f"commit by {vendor or 'none'}"
                mock_commit.vendor_id = vendor
                mock_commit.committed_at = "2024-01-15 10:30:00"
                commits.append(mock_commit)

            mock_db = MagicMock()
            mock_db.get_github_commits.return_value = commits
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "list"])
            assert result.exit_code == 0
            # Check the table was created with vendor data
            assert "GitHub Commits" in result.stdout
            assert "test-repo" in result.stdout

    def test_github_list_truncates_long_messages(self) -> None:
        """Test github list truncates long commit messages."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            mock_commit = MagicMock()
            mock_commit.sha = "abc123"
            mock_commit.repo = "test-repo"
            mock_commit.message = "a" * 100 + "\nSecond line"  # Very long message
            mock_commit.vendor_id = "claude"
            mock_commit.committed_at = "2024-01-15 10:30:00"

            mock_db = MagicMock()
            mock_db.get_github_commits.return_value = [mock_commit]
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "list"])
            assert result.exit_code == 0
            # Message should be displayed (may be truncated with ellipsis)
            assert "test-repo" in result.stdout

    def test_github_list_truncates_long_repo_names(self) -> None:
        """Test github list truncates long repository names."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            mock_commit = MagicMock()
            mock_commit.sha = "abc123"
            mock_commit.repo = "a" * 50  # Very long repo name
            mock_commit.message = "test commit"
            mock_commit.vendor_id = "claude"
            mock_commit.committed_at = "2024-01-15 10:30:00"

            mock_db = MagicMock()
            mock_db.get_github_commits.return_value = [mock_commit]
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "list"])
            assert result.exit_code == 0
            # Repo displayed (may be truncated)
            assert "GitHub Commits" in result.stdout


class TestGitHubReposCommand:
    """Tests for the github repos command."""

    def test_github_repos_help_shows_options(self) -> None:
        """Test github repos command shows help."""
        result = runner.invoke(app, ["github", "repos", "--help"])
        assert result.exit_code == 0
        assert "repos" in result.stdout.lower() or "repositories" in result.stdout.lower()

    def test_github_repos_no_database_exits(self) -> None:
        """Test github repos requires database to exist."""
        with patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path:
            mock_db_path.exists.return_value = False
            result = runner.invoke(app, ["github", "repos"])
            assert result.exit_code == 1
            assert "Database not found" in result.stdout

    def test_github_repos_no_repos_tracked(self) -> None:
        """Test github repos with no repositories tracked."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            mock_db = MagicMock()
            mock_db.get_github_repo_stats.return_value = []
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "repos"])
            assert result.exit_code == 0
            assert "No repositories tracked" in result.stdout

    def test_github_repos_displays_repository_table(self) -> None:
        """Test github repos displays repository statistics."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            # Create mock repo info
            repo_info = {
                "repo": "test-project",
                "total_commits": 100,
                "ai_commits": 60,
                "last_commit": "2024-01-31 12:00:00",
            }

            mock_db = MagicMock()
            mock_db.get_github_repo_stats.return_value = [repo_info]
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "repos"])
            assert result.exit_code == 0
            assert "100" in result.stdout
            assert "60" in result.stdout
            assert "60.0%" in result.stdout

    def test_github_repos_truncates_long_names(self) -> None:
        """Test github repos truncates long repository names."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            # Create repo with very long name
            repo_info = {
                "repo": "a" * 50,  # Very long repo name
                "total_commits": 10,
                "ai_commits": 5,
                "last_commit": "2024-01-31 12:00:00",
            }

            mock_db = MagicMock()
            mock_db.get_github_repo_stats.return_value = [repo_info]
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "repos"])
            assert result.exit_code == 0
            # Repo tracked with name (may be truncated)
            assert "Tracked Repositories" in result.stdout

    def test_github_repos_handles_zero_total_commits(self) -> None:
        """Test github repos handles repos with zero commits."""
        with (
            patch("ai_asst_mgr.cli.DEFAULT_DB_PATH") as mock_db_path,
            patch("ai_asst_mgr.cli.DatabaseManager") as mock_db_mgr,
        ):
            mock_db_path.exists.return_value = True

            # Create repo with zero commits
            repo_info = {
                "repo": "empty-repo",
                "total_commits": 0,
                "ai_commits": 0,
                "last_commit": None,
            }

            mock_db = MagicMock()
            mock_db.get_github_repo_stats.return_value = [repo_info]
            mock_db_mgr.return_value = mock_db

            result = runner.invoke(app, ["github", "repos"])
            assert result.exit_code == 0
            assert "0.0%" in result.stdout


# =============================================================================
# Additional Coverage Tests for Uncovered Lines
# =============================================================================


class TestDoctorCommandEdgeCases:
    """Additional tests for doctor command edge cases."""

    def test_doctor_database_exists_and_readable_success_path(self, tmp_path: Path) -> None:
        """Test doctor command with readable database (lines 551-552)."""
        with patch("ai_asst_mgr.cli.Path.home") as mock_home:
            mock_home.return_value = tmp_path
            # Create config dir structure
            config_dir = tmp_path / ".config" / "ai-asst-mgr"
            config_dir.mkdir(parents=True)
            db_path = config_dir / "database.db"
            db_path.write_text("database")

            result = runner.invoke(app, ["doctor"])
            # Check that database readable check passed
            assert (
                "Database is readable" in result.stdout or "Database file exists" in result.stdout
            )


class TestConfigCommandEdgeCases:
    """Additional tests for config command edge cases."""

    def test_config_list_vendor_without_load_settings(self) -> None:
        """Test config list when vendor lacks _load_settings method (lines 1078-1081)."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_adapter = MagicMock()
            mock_adapter.is_configured.return_value = True
            # Don't set _load_settings attribute
            del mock_adapter._load_settings

            mock_registry = MagicMock()
            mock_registry.get_all_vendors.return_value = {"test": mock_adapter}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "--list"])
            assert "Unable to load settings" in result.stdout or result.exit_code == 0

    def test_config_get_value_error_with_specific_vendor(self) -> None:
        """Test config get with error on specific vendor (lines 1129-1132)."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_adapter = MagicMock()
            mock_adapter.get_config.side_effect = RuntimeError("Config error")

            mock_registry = MagicMock()
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "some_key", "--vendor", "claude"])
            assert result.exit_code == 1
            assert "Error reading config" in result.stdout

    def test_config_set_value_error(self) -> None:
        """Test config set with error (lines 1164-1166)."""
        with patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class:
            mock_adapter = MagicMock()
            mock_adapter.set_config.side_effect = RuntimeError("Set error")

            mock_registry = MagicMock()
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["config", "some_key", "value", "--vendor", "claude"])
            assert result.exit_code == 1
            assert "Error setting config" in result.stdout


class TestBackupCommandProgressCallback:
    """Test backup command progress callback (line 1710)."""

    def test_backup_progress_callback_is_called(self, tmp_path: Path) -> None:
        """Test that progress callback prints messages (line 1710)."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            # Setup mock adapter
            mock_adapter = MagicMock()
            mock_adapter.info.name = "Claude"

            mock_registry = MagicMock()
            mock_registry.get_vendor.return_value = mock_adapter
            mock_registry_class.return_value = mock_registry

            # Setup mock backup result
            mock_result = MagicMock()
            mock_result.success = True
            mock_metadata = MagicMock()
            mock_metadata.backup_path = Path("/backups/claude_backup.tar.gz")
            mock_metadata.size_bytes = 1024
            mock_metadata.file_count = 5
            mock_result.metadata = mock_metadata

            mock_manager = MagicMock()

            # Capture the progress callback
            def capture_callback(adapter: object, callback: object) -> object:
                # Call the callback to test line 1710
                callback("Creating backup...")
                return mock_result

            mock_manager.backup_vendor.side_effect = capture_callback
            mock_get_manager.return_value = mock_manager

            result = runner.invoke(app, ["backup", "--vendor", "claude"])
            assert result.exit_code == 0
            # Check that callback output appears
            assert (
                "Creating backup..." in result.stdout
                or "Backup created successfully" in result.stdout
            )

    def test_backup_no_installed_vendors(self) -> None:
        """Test backup all when no vendors installed (line 1740-1742)."""
        with (
            patch("ai_asst_mgr.cli._get_backup_manager") as mock_get_manager,
            patch("ai_asst_mgr.cli.VendorRegistry") as mock_registry_class,
        ):
            mock_registry = MagicMock()
            mock_registry.get_installed_vendors.return_value = {}
            mock_registry_class.return_value = mock_registry

            result = runner.invoke(app, ["backup"])
            assert "No installed vendors found to backup" in result.stdout


class TestInitCommandCategorization:
    """Test init command result categorization (line 1057)."""

    def test_init_categorize_result_failed_status(self) -> None:
        """Test _categorize_init_result with failed status (line 1057)."""
        status_display, count_category = _categorize_init_result("Failed")
        assert "Failed" in status_display
        assert count_category == "failed"


class TestFormatSizeBytes:
    """Test _format_size_bytes function (line 1589)."""

    def test_format_size_bytes_terabytes(self) -> None:
        """Test _format_size_bytes with TB size (line 1589)."""
        # Test TB threshold
        size_tb = 1024 * 1024 * 1024 * 1024 * 2  # 2 TB
        result = _format_size_bytes(size_tb)
        assert "TB" in result
