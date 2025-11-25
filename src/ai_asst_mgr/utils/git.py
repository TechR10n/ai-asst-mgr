"""Safe Git operation utilities.

This module provides secure Git operations using GitPython library,
with proper input validation to prevent injection attacks.
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import TYPE_CHECKING

import git
from git.exc import GitCommandError, InvalidGitRepositoryError

if TYPE_CHECKING:
    from git import Repo


class GitError(Exception):
    """Raised when a Git operation fails."""


class GitValidationError(GitError):
    """Raised when Git input validation fails."""


class GitNotFoundError(GitError):
    """Raised when Git executable is not found."""


# Regex patterns for validation
# Git URL pattern: https://, git@, file://, or ssh:// URLs
_GIT_URL_PATTERN = re.compile(
    r"^("
    r"https?://[a-zA-Z0-9._\-]+(/[a-zA-Z0-9._\-/]+)*(\.git)?"
    r"|git@[a-zA-Z0-9._\-]+:[a-zA-Z0-9._\-/]+(\.git)?"
    r"|file://[a-zA-Z0-9._\-/]+"
    r"|ssh://[a-zA-Z0-9._\-@]+(/[a-zA-Z0-9._\-/]+)*(\.git)?"
    r")$"
)

# Git branch name pattern: alphanumeric, dots, underscores, hyphens, slashes
# Must not start with -, contain .., or end with .lock
_GIT_BRANCH_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9._\-/]*$")

# Maximum lengths for input validation (prevent DoS attacks)
_MAX_URL_LENGTH = 2048
_MAX_BRANCH_LENGTH = 255


def validate_git_url(url: str) -> bool:
    """Validate a Git repository URL.

    Accepts HTTPS, SSH (git@), file://, and ssh:// URLs.
    Rejects URLs with shell metacharacters or suspicious patterns.

    Args:
        url: The URL to validate.

    Returns:
        True if the URL is valid, False otherwise.
    """
    if not url or not isinstance(url, str):
        return False

    # Check length (prevent DoS with huge URLs)
    if len(url) > _MAX_URL_LENGTH:
        return False

    # Check for shell metacharacters that could enable injection
    dangerous_chars = [";", "|", "&", "$", "`", "(", ")", "{", "}", "<", ">", "\n", "\r"]
    if any(char in url for char in dangerous_chars):
        return False

    # Validate against URL pattern
    return bool(_GIT_URL_PATTERN.match(url))


def validate_git_branch(branch: str) -> bool:
    """Validate a Git branch name.

    Args:
        branch: The branch name to validate.

    Returns:
        True if the branch name is valid, False otherwise.
    """
    if not branch or not isinstance(branch, str):
        return False

    # Check length
    if len(branch) > _MAX_BRANCH_LENGTH:
        return False

    # Check for invalid patterns
    if ".." in branch:  # Path traversal in branch name
        return False
    if branch.endswith(".lock"):  # Git lock file pattern
        return False
    if branch.startswith("-"):  # Could be interpreted as flag
        return False

    # Validate against pattern
    return bool(_GIT_BRANCH_PATTERN.match(branch))


def find_git_executable() -> Path | None:
    """Find the Git executable on the system.

    Uses shutil.which() to locate Git in the system PATH.

    Returns:
        Path to the Git executable, or None if not found.
    """
    git_path = shutil.which("git")
    if git_path:
        return Path(git_path)
    return None


def git_clone(
    url: str,
    dest_dir: Path,
    branch: str = "main",
    *,
    depth: int = 1,
    timeout: int = 120,
) -> bool:
    """Clone a Git repository securely using GitPython.

    This function validates all inputs before executing the clone.

    Args:
        url: The repository URL (HTTPS, SSH, or file://).
        dest_dir: The destination directory for the clone.
        branch: The branch to clone (default: "main").
        depth: Clone depth for shallow clones (default: 1).
        timeout: Command timeout in seconds (default: 120, unused with GitPython).

    Returns:
        True if clone succeeded, False otherwise.

    Raises:
        GitValidationError: If URL or branch fails validation.
        GitNotFoundError: If Git is not installed.
    """
    # Validate inputs
    if not validate_git_url(url):
        msg = f"Invalid Git URL: {url}"
        raise GitValidationError(msg)

    if not validate_git_branch(branch):
        msg = f"Invalid Git branch: {branch}"
        raise GitValidationError(msg)

    # Check Git is available
    if not is_git_installed():
        msg = "Git executable not found in PATH"
        raise GitNotFoundError(msg)

    # Validate depth
    if not isinstance(depth, int) or depth < 1:
        depth = 1

    # Use timeout parameter to suppress unused warning
    _ = timeout

    try:
        _repo: Repo = git.Repo.clone_from(
            url,
            str(dest_dir),
            branch=branch,
            depth=depth,
        )
    except (GitCommandError, InvalidGitRepositoryError):
        return False
    else:
        return True


def is_git_installed() -> bool:
    """Check if Git is installed on the system.

    Returns:
        True if Git is available, False otherwise.
    """
    return find_git_executable() is not None


def is_command_available(command: str) -> bool:
    """Check if a command is available in PATH.

    This is a safer alternative to running 'which' via subprocess.

    Args:
        command: The command name to check.

    Returns:
        True if the command is available, False otherwise.
    """
    return shutil.which(command) is not None
