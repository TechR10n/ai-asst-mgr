"""Unit tests for git utilities."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from git.exc import GitCommandError, InvalidGitRepositoryError

from ai_asst_mgr.utils.git import (
    GitError,
    GitNotFoundError,
    GitValidationError,
    find_git_executable,
    git_clone,
    is_command_available,
    is_git_installed,
    validate_git_branch,
    validate_git_url,
)


class TestValidateGitUrl:
    """Tests for validate_git_url function."""

    def test_validate_https_url(self) -> None:
        """Test validation of HTTPS URLs."""
        assert validate_git_url("https://github.com/user/repo.git") is True
        assert validate_git_url("https://github.com/user/repo") is True
        assert validate_git_url("http://gitlab.com/user/repo.git") is True

    def test_validate_ssh_url(self) -> None:
        """Test validation of SSH URLs."""
        assert validate_git_url("git@github.com:user/repo.git") is True
        assert validate_git_url("git@gitlab.com:user/repo") is True
        assert validate_git_url("ssh://git@github.com/user/repo.git") is True

    def test_validate_file_url(self) -> None:
        """Test validation of file:// URLs."""
        assert validate_git_url("file:///path/to/repo") is True
        assert validate_git_url("file:///home/user/repo.git") is True

    def test_reject_empty_url(self) -> None:
        """Test rejection of empty URLs."""
        assert validate_git_url("") is False

    def test_reject_none_url(self) -> None:
        """Test rejection of None URL."""
        assert validate_git_url(None) is False  # type: ignore[arg-type]

    def test_reject_non_string_url(self) -> None:
        """Test rejection of non-string URLs."""
        assert validate_git_url(123) is False  # type: ignore[arg-type]
        assert validate_git_url([]) is False  # type: ignore[arg-type]

    def test_reject_url_with_shell_metacharacters(self) -> None:
        """Test rejection of URLs with dangerous characters."""
        assert validate_git_url("https://github.com/user/repo;ls") is False
        assert validate_git_url("https://github.com/user/repo|cat") is False
        assert validate_git_url("https://github.com/user/repo&whoami") is False
        assert validate_git_url("https://github.com/user/repo$(echo)") is False
        assert validate_git_url("https://github.com/user/repo`ls`") is False
        assert validate_git_url("https://github.com/user/repo()") is False
        assert validate_git_url("https://github.com/user/repo{}") is False
        assert validate_git_url("https://github.com/user/repo<>") is False
        assert validate_git_url("https://github.com/user/repo\n") is False
        assert validate_git_url("https://github.com/user/repo\r") is False

    def test_reject_url_too_long(self) -> None:
        """Test rejection of URLs exceeding max length."""
        # Create URL that exceeds 2048 characters
        long_url = "https://github.com/" + "a" * 2050
        assert validate_git_url(long_url) is False

    def test_reject_invalid_url_format(self) -> None:
        """Test rejection of invalid URL formats."""
        assert validate_git_url("not-a-valid-url") is False
        assert validate_git_url("ftp://github.com/user/repo") is False
        assert validate_git_url("/local/path/to/repo") is False


class TestValidateGitBranch:
    """Tests for validate_git_branch function."""

    def test_validate_simple_branch_name(self) -> None:
        """Test validation of simple branch names."""
        assert validate_git_branch("main") is True
        assert validate_git_branch("develop") is True
        assert validate_git_branch("feature") is True

    def test_validate_branch_with_hyphens(self) -> None:
        """Test validation of branch names with hyphens."""
        assert validate_git_branch("feature-branch") is True
        assert validate_git_branch("bug-fix-123") is True

    def test_validate_branch_with_underscores(self) -> None:
        """Test validation of branch names with underscores."""
        assert validate_git_branch("feature_branch") is True
        assert validate_git_branch("bug_fix_123") is True

    def test_validate_branch_with_slashes(self) -> None:
        """Test validation of branch names with slashes."""
        assert validate_git_branch("feature/new-feature") is True
        assert validate_git_branch("bugfix/issue-123") is True

    def test_validate_branch_with_dots(self) -> None:
        """Test validation of branch names with dots."""
        assert validate_git_branch("release.1.0") is True
        assert validate_git_branch("v1.2.3") is True

    def test_reject_empty_branch(self) -> None:
        """Test rejection of empty branch names."""
        assert validate_git_branch("") is False

    def test_reject_none_branch(self) -> None:
        """Test rejection of None branch name."""
        assert validate_git_branch(None) is False  # type: ignore[arg-type]

    def test_reject_non_string_branch(self) -> None:
        """Test rejection of non-string branch names."""
        assert validate_git_branch(123) is False  # type: ignore[arg-type]
        assert validate_git_branch([]) is False  # type: ignore[arg-type]

    def test_reject_branch_starting_with_hyphen(self) -> None:
        """Test rejection of branch names starting with hyphen."""
        assert validate_git_branch("-main") is False
        assert validate_git_branch("-feature") is False

    def test_reject_branch_with_double_dots(self) -> None:
        """Test rejection of branch names with double dots."""
        assert validate_git_branch("feature..branch") is False
        assert validate_git_branch("..main") is False

    def test_reject_branch_ending_with_lock(self) -> None:
        """Test rejection of branch names ending with .lock."""
        assert validate_git_branch("main.lock") is False
        assert validate_git_branch("feature.lock") is False

    def test_reject_branch_too_long(self) -> None:
        """Test rejection of branch names exceeding max length."""
        long_branch = "a" * 256
        assert validate_git_branch(long_branch) is False


class TestFindGitExecutable:
    """Tests for find_git_executable function."""

    @patch("ai_asst_mgr.utils.git.shutil.which")
    def test_find_git_executable_found(self, mock_which: Mock) -> None:
        """Test finding git executable when it exists."""
        mock_which.return_value = "/usr/bin/git"

        result = find_git_executable()

        assert result is not None
        assert result == Path("/usr/bin/git")
        mock_which.assert_called_once_with("git")

    @patch("ai_asst_mgr.utils.git.shutil.which")
    def test_find_git_executable_not_found(self, mock_which: Mock) -> None:
        """Test finding git executable when it doesn't exist."""
        mock_which.return_value = None

        result = find_git_executable()

        assert result is None
        mock_which.assert_called_once_with("git")


class TestGitClone:
    """Tests for git_clone function."""

    @patch("ai_asst_mgr.utils.git.is_git_installed")
    @patch("ai_asst_mgr.utils.git.git.Repo.clone_from")
    def test_git_clone_success(
        self, mock_clone_from: Mock, mock_is_installed: Mock, tmp_path: Path
    ) -> None:
        """Test successful git clone."""
        mock_is_installed.return_value = True
        mock_clone_from.return_value = Mock()

        dest_dir = tmp_path / "repo"
        result = git_clone("https://github.com/user/repo.git", dest_dir)

        assert result is True
        mock_clone_from.assert_called_once_with(
            "https://github.com/user/repo.git",
            str(dest_dir),
            branch="main",
            depth=1,
        )

    @patch("ai_asst_mgr.utils.git.is_git_installed")
    def test_git_clone_invalid_url(self, mock_is_installed: Mock, tmp_path: Path) -> None:
        """Test git clone with invalid URL raises GitValidationError."""
        mock_is_installed.return_value = True

        dest_dir = tmp_path / "repo"

        with pytest.raises(GitValidationError, match="Invalid Git URL"):
            git_clone("invalid-url", dest_dir)

    @patch("ai_asst_mgr.utils.git.is_git_installed")
    def test_git_clone_invalid_branch(self, mock_is_installed: Mock, tmp_path: Path) -> None:
        """Test git clone with invalid branch raises GitValidationError."""
        mock_is_installed.return_value = True

        dest_dir = tmp_path / "repo"

        with pytest.raises(GitValidationError, match="Invalid Git branch"):
            git_clone("https://github.com/user/repo.git", dest_dir, branch="-invalid")

    @patch("ai_asst_mgr.utils.git.is_git_installed")
    def test_git_clone_git_not_found(self, mock_is_installed: Mock, tmp_path: Path) -> None:
        """Test git clone when git is not installed raises GitNotFoundError."""
        mock_is_installed.return_value = False

        dest_dir = tmp_path / "repo"

        with pytest.raises(GitNotFoundError, match="Git executable not found"):
            git_clone("https://github.com/user/repo.git", dest_dir)

    @patch("ai_asst_mgr.utils.git.is_git_installed")
    @patch("ai_asst_mgr.utils.git.git.Repo.clone_from")
    def test_git_clone_command_error(
        self, mock_clone_from: Mock, mock_is_installed: Mock, tmp_path: Path
    ) -> None:
        """Test git clone handles GitCommandError."""
        mock_is_installed.return_value = True
        mock_clone_from.side_effect = GitCommandError("clone", "error")

        dest_dir = tmp_path / "repo"
        result = git_clone("https://github.com/user/repo.git", dest_dir)

        assert result is False

    @patch("ai_asst_mgr.utils.git.is_git_installed")
    @patch("ai_asst_mgr.utils.git.git.Repo.clone_from")
    def test_git_clone_invalid_repo_error(
        self, mock_clone_from: Mock, mock_is_installed: Mock, tmp_path: Path
    ) -> None:
        """Test git clone handles InvalidGitRepositoryError."""
        mock_is_installed.return_value = True
        mock_clone_from.side_effect = InvalidGitRepositoryError("/invalid/path")

        dest_dir = tmp_path / "repo"
        result = git_clone("https://github.com/user/repo.git", dest_dir)

        assert result is False

    @patch("ai_asst_mgr.utils.git.is_git_installed")
    @patch("ai_asst_mgr.utils.git.git.Repo.clone_from")
    def test_git_clone_with_custom_depth(
        self, mock_clone_from: Mock, mock_is_installed: Mock, tmp_path: Path
    ) -> None:
        """Test git clone with custom depth."""
        mock_is_installed.return_value = True
        mock_clone_from.return_value = Mock()

        dest_dir = tmp_path / "repo"
        result = git_clone("https://github.com/user/repo.git", dest_dir, depth=5)

        assert result is True
        mock_clone_from.assert_called_once_with(
            "https://github.com/user/repo.git",
            str(dest_dir),
            branch="main",
            depth=5,
        )

    @patch("ai_asst_mgr.utils.git.is_git_installed")
    @patch("ai_asst_mgr.utils.git.git.Repo.clone_from")
    def test_git_clone_with_invalid_depth(
        self, mock_clone_from: Mock, mock_is_installed: Mock, tmp_path: Path
    ) -> None:
        """Test git clone with invalid depth defaults to 1."""
        mock_is_installed.return_value = True
        mock_clone_from.return_value = Mock()

        dest_dir = tmp_path / "repo"
        result = git_clone("https://github.com/user/repo.git", dest_dir, depth=-1)

        assert result is True
        # Should default to 1
        mock_clone_from.assert_called_once_with(
            "https://github.com/user/repo.git",
            str(dest_dir),
            branch="main",
            depth=1,
        )

    @patch("ai_asst_mgr.utils.git.is_git_installed")
    @patch("ai_asst_mgr.utils.git.git.Repo.clone_from")
    def test_git_clone_with_custom_branch(
        self, mock_clone_from: Mock, mock_is_installed: Mock, tmp_path: Path
    ) -> None:
        """Test git clone with custom branch."""
        mock_is_installed.return_value = True
        mock_clone_from.return_value = Mock()

        dest_dir = tmp_path / "repo"
        result = git_clone("https://github.com/user/repo.git", dest_dir, branch="develop")

        assert result is True
        mock_clone_from.assert_called_once_with(
            "https://github.com/user/repo.git",
            str(dest_dir),
            branch="develop",
            depth=1,
        )


class TestIsGitInstalled:
    """Tests for is_git_installed function."""

    @patch("ai_asst_mgr.utils.git.find_git_executable")
    def test_is_git_installed_true(self, mock_find_git: Mock) -> None:
        """Test is_git_installed returns True when git is found."""
        mock_find_git.return_value = Path("/usr/bin/git")

        result = is_git_installed()

        assert result is True

    @patch("ai_asst_mgr.utils.git.find_git_executable")
    def test_is_git_installed_false(self, mock_find_git: Mock) -> None:
        """Test is_git_installed returns False when git is not found."""
        mock_find_git.return_value = None

        result = is_git_installed()

        assert result is False


class TestIsCommandAvailable:
    """Tests for is_command_available function."""

    @patch("ai_asst_mgr.utils.git.shutil.which")
    def test_is_command_available_true(self, mock_which: Mock) -> None:
        """Test is_command_available returns True when command exists."""
        mock_which.return_value = "/usr/bin/python"

        result = is_command_available("python")

        assert result is True
        mock_which.assert_called_once_with("python")

    @patch("ai_asst_mgr.utils.git.shutil.which")
    def test_is_command_available_false(self, mock_which: Mock) -> None:
        """Test is_command_available returns False when command doesn't exist."""
        mock_which.return_value = None

        result = is_command_available("nonexistent-command")

        assert result is False
        mock_which.assert_called_once_with("nonexistent-command")


class TestGitExceptions:
    """Tests for Git exception classes."""

    def test_git_error_base_exception(self) -> None:
        """Test GitError can be raised and caught."""
        msg = "test error"
        with pytest.raises(GitError, match="test error"):
            raise GitError(msg)

    def test_git_validation_error_inheritance(self) -> None:
        """Test GitValidationError inherits from GitError."""
        assert issubclass(GitValidationError, GitError)
        msg = "validation failed"
        with pytest.raises(GitError, match="validation failed"):
            raise GitValidationError(msg)

    def test_git_not_found_error_inheritance(self) -> None:
        """Test GitNotFoundError inherits from GitError."""
        assert issubclass(GitNotFoundError, GitError)
        msg = "git not found"
        with pytest.raises(GitError, match="git not found"):
            raise GitNotFoundError(msg)


class TestGitEdgeCases:
    """Additional edge case tests for git utilities."""

    def test_validate_git_url_with_port_number(self) -> None:
        """Test validation of URLs with port numbers."""
        assert validate_git_url("https://github.com:443/user/repo.git") is False
        # Port numbers aren't explicitly supported in our regex

    def test_validate_git_url_with_spaces(self) -> None:
        """Test rejection of URLs with spaces."""
        assert validate_git_url("https://github.com/user name/repo.git") is False

    def test_validate_git_branch_numeric_only(self) -> None:
        """Test validation of numeric branch names."""
        # Must start with alphanumeric
        assert validate_git_branch("123") is True
        assert validate_git_branch("v1") is True

    def test_validate_git_branch_with_special_chars(self) -> None:
        """Test rejection of branch names with special characters."""
        assert validate_git_branch("feature@123") is False
        assert validate_git_branch("feature#123") is False
        assert validate_git_branch("feature$123") is False

    @patch("ai_asst_mgr.utils.git.is_git_installed")
    @patch("ai_asst_mgr.utils.git.git.Repo.clone_from")
    def test_git_clone_with_zero_depth(
        self, mock_clone_from: Mock, mock_is_installed: Mock, tmp_path: Path
    ) -> None:
        """Test git clone with zero depth defaults to 1."""
        mock_is_installed.return_value = True
        mock_clone_from.return_value = Mock()

        dest_dir = tmp_path / "repo"
        result = git_clone("https://github.com/user/repo.git", dest_dir, depth=0)

        assert result is True
        mock_clone_from.assert_called_once_with(
            "https://github.com/user/repo.git",
            str(dest_dir),
            branch="main",
            depth=1,
        )

    @patch("ai_asst_mgr.utils.git.is_git_installed")
    @patch("ai_asst_mgr.utils.git.git.Repo.clone_from")
    def test_git_clone_with_string_depth(
        self, mock_clone_from: Mock, mock_is_installed: Mock, tmp_path: Path
    ) -> None:
        """Test git clone with string depth defaults to 1."""
        mock_is_installed.return_value = True
        mock_clone_from.return_value = Mock()

        dest_dir = tmp_path / "repo"
        # Pass invalid type for depth
        result = git_clone(
            "https://github.com/user/repo.git",
            dest_dir,
            depth="invalid",  # type: ignore[arg-type]
        )

        assert result is True
        mock_clone_from.assert_called_once_with(
            "https://github.com/user/repo.git",
            str(dest_dir),
            branch="main",
            depth=1,
        )
