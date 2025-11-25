"""Utility functions and helpers.

This package provides common utility functions used across the application.
"""

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
from ai_asst_mgr.utils.tarfile_safe import (
    TarfileSecurityError,
    get_safe_members,
    is_member_safe,
    is_path_safe,
    unpack_members_securely,
    unpack_tar_securely,
)

__all__ = [
    "GitError",
    "GitNotFoundError",
    "GitValidationError",
    "TarfileSecurityError",
    "find_git_executable",
    "get_safe_members",
    "git_clone",
    "is_command_available",
    "is_git_installed",
    "is_member_safe",
    "is_path_safe",
    "unpack_members_securely",
    "unpack_tar_securely",
    "validate_git_branch",
    "validate_git_url",
]
