"""Safe tarfile extraction utilities.

This module provides secure tarfile extraction that prevents path traversal
attacks (CWE-22) by validating all member paths before extraction.
"""

from __future__ import annotations

import tarfile
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from collections.abc import Generator


class TarfileSecurityError(Exception):
    """Raised when a tarfile member fails security validation."""


def is_path_safe(member_path: str, dest_dir: Path) -> bool:
    """Check if a tarfile member path is safe to extract.

    A path is considered safe if:
    1. It doesn't start with '/' (absolute path)
    2. It doesn't contain '..' path traversal sequences after normalization
    3. When resolved relative to dest_dir, it stays within dest_dir

    Args:
        member_path: The path from the tarfile member.
        dest_dir: The destination directory for extraction.

    Returns:
        True if the path is safe to extract, False otherwise.
    """
    # Reject absolute paths
    if member_path.startswith("/"):
        return False

    # Reject paths with null bytes (potential bypass attempt)
    if "\x00" in member_path:
        return False

    # Normalize the path and check for traversal
    try:
        # Construct the full target path
        target_path = (dest_dir / member_path).resolve()
        dest_resolved = dest_dir.resolve()

        # Ensure target is within destination directory
        # Use is_relative_to for Python 3.9+ compatibility
        return target_path == dest_resolved or str(target_path).startswith(str(dest_resolved) + "/")
    except (ValueError, OSError):
        # Path resolution failed - reject as unsafe
        return False


def is_member_safe(member: tarfile.TarInfo, dest_dir: Path) -> bool:
    """Check if a tarfile member is safe to extract.

    This validates both the member path and handles special member types
    like symlinks and hardlinks that could be used for attacks.

    Args:
        member: The TarInfo object to validate.
        dest_dir: The destination directory for extraction.

    Returns:
        True if the member is safe to extract, False otherwise.
    """
    # Check the basic path safety
    if not is_path_safe(member.name, dest_dir):
        return False

    # For symlinks, validate the link target
    if member.issym():
        link_target = member.linkname
        # Symlink targets are resolved relative to the symlink location
        symlink_dir = (dest_dir / member.name).parent
        if not is_path_safe(link_target, symlink_dir):
            return False
        # Also check that the resolved symlink stays in dest_dir
        try:
            resolved_link = (symlink_dir / link_target).resolve()
            dest_resolved = dest_dir.resolve()
            if not (
                resolved_link == dest_resolved
                or str(resolved_link).startswith(str(dest_resolved) + "/")
            ):
                return False
        except (ValueError, OSError):
            return False

    # For hardlinks, validate the link target
    return not member.islnk() or is_path_safe(member.linkname, dest_dir)


def get_safe_members(tar: tarfile.TarFile, dest_dir: Path) -> Generator[tarfile.TarInfo]:
    """Yield only safe members from a tarfile.

    This is a generator that filters tarfile members, yielding only those
    that pass security validation.

    Args:
        tar: The tarfile to read members from.
        dest_dir: The destination directory for extraction.

    Yields:
        TarInfo objects that are safe to extract.
    """
    for member in tar.getmembers():
        if is_member_safe(member, dest_dir):
            yield member


def unpack_tar_securely(tar: tarfile.TarFile, dest_dir: Path) -> list[str]:
    """Securely unpack all members from a tarfile.

    This unpacks only members that pass security validation, preventing
    path traversal attacks (CWE-22).

    Args:
        tar: The tarfile to unpack from.
        dest_dir: The destination directory for unpacking.

    Returns:
        List of unpacked file paths (relative to dest_dir).
    """
    safe_members = list(get_safe_members(tar, dest_dir))
    unpacked: list[str] = []

    for member in safe_members:
        tar.extract(member, dest_dir)
        unpacked.append(member.name)

    return unpacked


def unpack_members_securely(
    tar: tarfile.TarFile, dest_dir: Path, members: list[tarfile.TarInfo]
) -> list[str]:
    """Securely unpack specified members from a tarfile.

    This validates each member before unpacking.

    Args:
        tar: The tarfile to unpack from.
        dest_dir: The destination directory for unpacking.
        members: List of TarInfo objects to unpack.

    Returns:
        List of unpacked file paths (relative to dest_dir).

    Raises:
        TarfileSecurityError: If any member fails security validation.
    """
    unpacked: list[str] = []

    for member in members:
        if not is_member_safe(member, dest_dir):
            msg = f"Unsafe tarfile member rejected: {member.name}"
            raise TarfileSecurityError(msg)
        tar.extract(member, dest_dir)
        unpacked.append(member.name)

    return unpacked
