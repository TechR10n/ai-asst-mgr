"""Unit tests for safe tarfile utilities."""

import tarfile
from pathlib import Path
from unittest.mock import patch

import pytest

from ai_asst_mgr.utils.tarfile_safe import (
    TarfileSecurityError,
    get_safe_members,
    is_member_safe,
    is_path_safe,
    unpack_members_securely,
    unpack_tar_securely,
)


@pytest.fixture
def temp_dest_dir(tmp_path: Path) -> Path:
    """Create a temporary destination directory."""
    dest_dir = tmp_path / "extract"
    dest_dir.mkdir()
    return dest_dir


@pytest.fixture
def safe_tar_file(tmp_path: Path) -> Path:
    """Create a safe tar file for testing."""
    tar_path = tmp_path / "safe.tar.gz"
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Create some safe files
    (source_dir / "file1.txt").write_text("content1")
    (source_dir / "file2.txt").write_text("content2")
    subdir = source_dir / "subdir"
    subdir.mkdir()
    (subdir / "file3.txt").write_text("content3")

    with tarfile.open(tar_path, "w:gz") as tar:
        tar.add(source_dir / "file1.txt", arcname="file1.txt")
        tar.add(source_dir / "file2.txt", arcname="file2.txt")
        tar.add(subdir / "file3.txt", arcname="subdir/file3.txt")

    return tar_path


@pytest.fixture
def malicious_tar_file(tmp_path: Path) -> Path:
    """Create a malicious tar file with path traversal."""
    tar_path = tmp_path / "malicious.tar.gz"
    source_dir = tmp_path / "source"
    source_dir.mkdir()

    # Create files
    (source_dir / "safe.txt").write_text("safe")
    (source_dir / "evil.txt").write_text("evil")

    with tarfile.open(tar_path, "w:gz") as tar:
        # Add safe file
        tar.add(source_dir / "safe.txt", arcname="safe.txt")
        # Add file with path traversal
        tar.add(source_dir / "evil.txt", arcname="../evil.txt")

    return tar_path


class TestIsPathSafe:
    """Tests for is_path_safe function."""

    def test_is_path_safe_relative_path(self, temp_dest_dir: Path) -> None:
        """Test that relative paths within dest_dir are safe."""
        assert is_path_safe("file.txt", temp_dest_dir) is True
        assert is_path_safe("subdir/file.txt", temp_dest_dir) is True
        assert is_path_safe("a/b/c/file.txt", temp_dest_dir) is True

    def test_is_path_safe_rejects_absolute_path(self, temp_dest_dir: Path) -> None:
        """Test that absolute paths are rejected."""
        assert is_path_safe("/etc/passwd", temp_dest_dir) is False
        assert is_path_safe("/tmp/file.txt", temp_dest_dir) is False

    def test_is_path_safe_rejects_path_traversal(self, temp_dest_dir: Path) -> None:
        """Test that path traversal attempts are rejected."""
        assert is_path_safe("../file.txt", temp_dest_dir) is False
        assert is_path_safe("subdir/../../file.txt", temp_dest_dir) is False
        assert is_path_safe("./subdir/../../../file.txt", temp_dest_dir) is False

    def test_is_path_safe_rejects_null_bytes(self, temp_dest_dir: Path) -> None:
        """Test that paths with null bytes are rejected."""
        assert is_path_safe("file\x00.txt", temp_dest_dir) is False
        assert is_path_safe("subdir/\x00file.txt", temp_dest_dir) is False

    def test_is_path_safe_with_dots(self, temp_dest_dir: Path) -> None:
        """Test that single dots in paths are handled correctly."""
        assert is_path_safe("./file.txt", temp_dest_dir) is True
        assert is_path_safe("subdir/./file.txt", temp_dest_dir) is True

    def test_is_path_safe_handles_symlinks(self, temp_dest_dir: Path) -> None:
        """Test that paths are resolved correctly."""
        # Create a subdirectory in dest_dir
        subdir = temp_dest_dir / "subdir"
        subdir.mkdir()

        # Path that resolves within dest_dir
        assert is_path_safe("subdir/file.txt", temp_dest_dir) is True

    def test_is_path_safe_edge_case_empty_path(self, temp_dest_dir: Path) -> None:
        """Test that empty paths are handled."""
        # Empty path resolves to dest_dir itself
        assert is_path_safe("", temp_dest_dir) is True
        assert is_path_safe(".", temp_dest_dir) is True

    def test_is_path_safe_handles_resolution_errors(
        self, temp_dest_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that path resolution errors are caught."""
        error_msg = "Resolution failed"

        def mock_resolve(_path: Path) -> Path:
            raise ValueError(error_msg)

        # Patch Path.resolve to raise an error
        monkeypatch.setattr(Path, "resolve", mock_resolve)

        # Should return False when resolution fails
        assert is_path_safe("file.txt", temp_dest_dir) is False


class TestIsMemberSafe:
    """Tests for is_member_safe function."""

    def test_is_member_safe_regular_file(self, temp_dest_dir: Path) -> None:
        """Test that regular files are validated."""
        member = tarfile.TarInfo(name="file.txt")
        member.type = tarfile.REGTYPE

        assert is_member_safe(member, temp_dest_dir) is True

    def test_is_member_safe_directory(self, temp_dest_dir: Path) -> None:
        """Test that directories are validated."""
        member = tarfile.TarInfo(name="subdir")
        member.type = tarfile.DIRTYPE

        assert is_member_safe(member, temp_dest_dir) is True

    def test_is_member_safe_rejects_unsafe_path(self, temp_dest_dir: Path) -> None:
        """Test that unsafe paths are rejected."""
        member = tarfile.TarInfo(name="../evil.txt")
        member.type = tarfile.REGTYPE

        assert is_member_safe(member, temp_dest_dir) is False

    def test_is_member_safe_symlink_within_dest(self, temp_dest_dir: Path) -> None:
        """Test that safe symlinks are accepted."""
        # Create target file
        (temp_dest_dir / "target.txt").write_text("target")

        member = tarfile.TarInfo(name="link.txt")
        member.type = tarfile.SYMTYPE
        member.linkname = "target.txt"

        assert is_member_safe(member, temp_dest_dir) is True

    def test_is_member_safe_rejects_symlink_traversal(self, temp_dest_dir: Path) -> None:
        """Test that symlinks with path traversal are rejected."""
        member = tarfile.TarInfo(name="link.txt")
        member.type = tarfile.SYMTYPE
        member.linkname = "../../../etc/passwd"

        assert is_member_safe(member, temp_dest_dir) is False

    def test_is_member_safe_rejects_symlink_outside_dest(
        self, temp_dest_dir: Path, tmp_path: Path
    ) -> None:
        """Test that symlinks pointing outside dest_dir are rejected."""
        # Create target outside dest_dir
        outside_file = tmp_path / "outside.txt"
        outside_file.write_text("outside")

        member = tarfile.TarInfo(name="link.txt")
        member.type = tarfile.SYMTYPE
        member.linkname = str(outside_file)

        assert is_member_safe(member, temp_dest_dir) is False

    def test_is_member_safe_hardlink_within_dest(self, temp_dest_dir: Path) -> None:
        """Test that safe hardlinks are accepted."""
        member = tarfile.TarInfo(name="hardlink.txt")
        member.type = tarfile.LNKTYPE
        member.linkname = "target.txt"

        assert is_member_safe(member, temp_dest_dir) is True

    def test_is_member_safe_rejects_hardlink_traversal(self, temp_dest_dir: Path) -> None:
        """Test that hardlinks with path traversal are rejected."""
        member = tarfile.TarInfo(name="hardlink.txt")
        member.type = tarfile.LNKTYPE
        member.linkname = "../../../etc/passwd"

        assert is_member_safe(member, temp_dest_dir) is False

    def test_is_member_safe_symlink_with_subdirectory(self, temp_dest_dir: Path) -> None:
        """Test symlink validation rejects parent directory traversal."""
        # Create subdirectory structure and target file
        subdir = temp_dest_dir / "subdir"
        subdir.mkdir()
        # Create the target file that the symlink will point to
        target = temp_dest_dir / "file.txt"
        target.write_text("target")

        member = tarfile.TarInfo(name="subdir/link.txt")
        member.type = tarfile.SYMTYPE
        member.linkname = "../file.txt"  # Uses .. which is rejected for safety

        # This is rejected because symlink targets with .. are unsafe
        # even if they resolve within dest_dir
        assert is_member_safe(member, temp_dest_dir) is False

    def test_is_member_safe_symlink_same_directory(self, temp_dest_dir: Path) -> None:
        """Test symlink validation accepts links in same directory."""
        # Create subdirectory structure
        subdir = temp_dest_dir / "subdir"
        subdir.mkdir()
        # Create target files
        (subdir / "target.txt").write_text("target")

        member = tarfile.TarInfo(name="subdir/link.txt")
        member.type = tarfile.SYMTYPE
        member.linkname = "target.txt"  # Points to same directory

        assert is_member_safe(member, temp_dest_dir) is True

    def test_is_member_safe_symlink_to_directory(self, temp_dest_dir: Path) -> None:
        """Test symlink validation for link pointing to dest_dir itself."""
        member = tarfile.TarInfo(name="link")
        member.type = tarfile.SYMTYPE
        member.linkname = "."  # Points to current directory

        # This should be safe - resolves to dest_dir
        assert is_member_safe(member, temp_dest_dir) is True

    def test_is_member_safe_symlink_resolution_error(
        self, temp_dest_dir: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Test that symlink resolution errors are handled."""
        error_msg = "Resolution failed"

        def mock_resolve(_path: Path) -> Path:
            raise OSError(error_msg)

        monkeypatch.setattr(Path, "resolve", mock_resolve)

        member = tarfile.TarInfo(name="link.txt")
        member.type = tarfile.SYMTYPE
        member.linkname = "target.txt"

        assert is_member_safe(member, temp_dest_dir) is False

    def test_is_member_safe_symlink_resolves_outside_bounds(
        self, temp_dest_dir: Path, tmp_path: Path
    ) -> None:
        """Test symlink that resolves outside dest_dir is rejected (line 90)."""
        # This test covers line 90: when a symlink's target passes initial safety
        # checks but resolves to a path outside dest_dir.

        # Strategy: patch is_path_safe to return True for the first check (line 80)
        # Then let the actual resolution at lines 84-85 detect the escape

        outside_path = tmp_path / "outside" / "evil.txt"
        outside_path.parent.mkdir(exist_ok=True)

        member = tarfile.TarInfo(name="link.txt")
        member.type = tarfile.SYMTYPE
        member.linkname = "target.txt"

        # We need to patch BOTH is_path_safe AND Path.resolve in a coordinated way
        # First, make is_path_safe return True for the line 80 check
        # Then, make Path.resolve return outside_path for line 84

        from ai_asst_mgr.utils import tarfile_safe

        original_is_path_safe = tarfile_safe.is_path_safe
        original_resolve = Path.resolve
        is_path_safe_call_count = [0]
        resolve_call_count = [0]

        def mock_is_path_safe(member_path: str, dest_dir: Path) -> bool:
            is_path_safe_call_count[0] += 1
            # First call (line 72) checks member.name - let it pass
            # Second call (line 80) checks link_target - make it pass
            if is_path_safe_call_count[0] <= 2:
                return True
            # Other calls use original logic
            return original_is_path_safe(member_path, dest_dir)

        def mock_resolve(self: Path, *args, **kwargs) -> Path:
            resolve_call_count[0] += 1
            # First call is at line 84: (symlink_dir / link_target).resolve()
            if resolve_call_count[0] == 1:
                return outside_path  # Return path outside dest_dir
            # Second call is at line 85: dest_dir.resolve()
            return original_resolve(self, *args, **kwargs)

        with patch.object(tarfile_safe, "is_path_safe", mock_is_path_safe):
            with patch.object(Path, "resolve", mock_resolve):
                result = is_member_safe(member, temp_dest_dir)

        # Should return False because resolved link is outside dest_dir
        assert result is False

    def test_is_member_safe_symlink_resolution_value_error(
        self, temp_dest_dir: Path, tmp_path: Path
    ) -> None:
        """Test that ValueError during symlink resolution is caught (line 92)."""
        # Similar to the previous test, but this time raise an exception
        # during resolution instead of returning an outside path

        member = tarfile.TarInfo(name="link.txt")
        member.type = tarfile.SYMTYPE
        member.linkname = "target.txt"

        from ai_asst_mgr.utils import tarfile_safe

        original_is_path_safe = tarfile_safe.is_path_safe
        original_resolve = Path.resolve
        is_path_safe_call_count = [0]
        resolve_call_count = [0]

        def mock_is_path_safe(member_path: str, dest_dir: Path) -> bool:
            is_path_safe_call_count[0] += 1
            # First two calls should pass (line 72 and line 80)
            if is_path_safe_call_count[0] <= 2:
                return True
            return original_is_path_safe(member_path, dest_dir)

        def mock_resolve(self: Path, *args, **kwargs) -> Path:
            resolve_call_count[0] += 1
            # First call is at line 84: raise ValueError
            if resolve_call_count[0] == 1:
                raise ValueError("Simulated path resolution error")
            return original_resolve(self, *args, **kwargs)

        with patch.object(tarfile_safe, "is_path_safe", mock_is_path_safe):
            with patch.object(Path, "resolve", mock_resolve):
                result = is_member_safe(member, temp_dest_dir)

        # Should return False when resolution raises ValueError
        assert result is False


class TestGetSafeMembers:
    """Tests for get_safe_members function."""

    def test_get_safe_members_all_safe(self, safe_tar_file: Path, temp_dest_dir: Path) -> None:
        """Test that all safe members are yielded."""
        with tarfile.open(safe_tar_file, "r:gz") as tar:
            safe_members = list(get_safe_members(tar, temp_dest_dir))

        assert len(safe_members) == 3
        member_names = [m.name for m in safe_members]
        assert "file1.txt" in member_names
        assert "file2.txt" in member_names
        assert "subdir/file3.txt" in member_names

    def test_get_safe_members_filters_unsafe(
        self, malicious_tar_file: Path, temp_dest_dir: Path
    ) -> None:
        """Test that unsafe members are filtered out."""
        with tarfile.open(malicious_tar_file, "r:gz") as tar:
            safe_members = list(get_safe_members(tar, temp_dest_dir))

        # Only safe.txt should be included
        assert len(safe_members) == 1
        assert safe_members[0].name == "safe.txt"

    def test_get_safe_members_empty_archive(self, tmp_path: Path, temp_dest_dir: Path) -> None:
        """Test that empty archive yields no members."""
        empty_tar = tmp_path / "empty.tar.gz"
        with tarfile.open(empty_tar, "w:gz"):
            pass  # Create empty archive

        with tarfile.open(empty_tar, "r:gz") as tar:
            safe_members = list(get_safe_members(tar, temp_dest_dir))

        assert len(safe_members) == 0


class TestSafeExtractall:
    """Tests for unpack_tar_securely function."""

    def test_unpack_tar_securely_success(self, safe_tar_file: Path, temp_dest_dir: Path) -> None:
        """Test successful extraction of safe archive."""
        with tarfile.open(safe_tar_file, "r:gz") as tar:
            extracted = unpack_tar_securely(tar, temp_dest_dir)

        assert len(extracted) == 3
        assert "file1.txt" in extracted
        assert "file2.txt" in extracted
        assert "subdir/file3.txt" in extracted

        # Verify files were extracted
        assert (temp_dest_dir / "file1.txt").exists()
        assert (temp_dest_dir / "file2.txt").exists()
        assert (temp_dest_dir / "subdir" / "file3.txt").exists()

    def test_unpack_tar_securely_verifies_content(
        self, safe_tar_file: Path, temp_dest_dir: Path
    ) -> None:
        """Test that extracted files have correct content."""
        with tarfile.open(safe_tar_file, "r:gz") as tar:
            unpack_tar_securely(tar, temp_dest_dir)

        assert (temp_dest_dir / "file1.txt").read_text() == "content1"
        assert (temp_dest_dir / "file2.txt").read_text() == "content2"
        assert (temp_dest_dir / "subdir" / "file3.txt").read_text() == "content3"

    def test_unpack_tar_securely_filters_unsafe(
        self, malicious_tar_file: Path, temp_dest_dir: Path, tmp_path: Path
    ) -> None:
        """Test that unsafe members are not extracted."""
        with tarfile.open(malicious_tar_file, "r:gz") as tar:
            extracted = unpack_tar_securely(tar, temp_dest_dir)

        # Only safe file should be extracted
        assert len(extracted) == 1
        assert extracted[0] == "safe.txt"
        assert (temp_dest_dir / "safe.txt").exists()

        # Evil file should not be extracted outside dest_dir
        assert not (tmp_path / "evil.txt").exists()

    def test_unpack_tar_securely_empty_archive(self, tmp_path: Path, temp_dest_dir: Path) -> None:
        """Test extraction of empty archive."""
        empty_tar = tmp_path / "empty.tar.gz"
        with tarfile.open(empty_tar, "w:gz"):
            pass

        with tarfile.open(empty_tar, "r:gz") as tar:
            extracted = unpack_tar_securely(tar, temp_dest_dir)

        assert len(extracted) == 0

    def test_unpack_tar_securely_preserves_directory_structure(
        self, tmp_path: Path, temp_dest_dir: Path
    ) -> None:
        """Test that directory structure is preserved."""
        tar_path = tmp_path / "nested.tar.gz"
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create nested structure
        (source_dir / "a").mkdir()
        (source_dir / "a" / "b").mkdir()
        (source_dir / "a" / "b" / "c").mkdir()
        (source_dir / "a" / "b" / "c" / "file.txt").write_text("deep")

        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(source_dir / "a" / "b" / "c" / "file.txt", arcname="a/b/c/file.txt")

        with tarfile.open(tar_path, "r:gz") as tar:
            extracted = unpack_tar_securely(tar, temp_dest_dir)

        assert "a/b/c/file.txt" in extracted
        assert (temp_dest_dir / "a" / "b" / "c" / "file.txt").exists()


class TestSafeExtractMembers:
    """Tests for unpack_members_securely function."""

    def test_unpack_members_securely_success(
        self, safe_tar_file: Path, temp_dest_dir: Path
    ) -> None:
        """Test successful extraction of specified members."""
        with tarfile.open(safe_tar_file, "r:gz") as tar:
            members = tar.getmembers()
            # Extract only first two members
            extracted = unpack_members_securely(tar, temp_dest_dir, members[:2])

        assert len(extracted) == 2
        assert (temp_dest_dir / "file1.txt").exists()
        assert (temp_dest_dir / "file2.txt").exists()
        # Third file should not exist
        assert not (temp_dest_dir / "subdir" / "file3.txt").exists()

    def test_unpack_members_securely_raises_on_unsafe(
        self, malicious_tar_file: Path, temp_dest_dir: Path
    ) -> None:
        """Test that extraction raises error for unsafe members."""
        with tarfile.open(malicious_tar_file, "r:gz") as tar:
            members = tar.getmembers()
            # Find the unsafe member (../evil.txt)
            unsafe_member = next(m for m in members if ".." in m.name)

            with pytest.raises(TarfileSecurityError) as exc_info:
                unpack_members_securely(tar, temp_dest_dir, [unsafe_member])

            assert "Unsafe tarfile member rejected" in str(exc_info.value)
            assert unsafe_member.name in str(exc_info.value)

    def test_unpack_members_securely_empty_list(
        self, safe_tar_file: Path, temp_dest_dir: Path
    ) -> None:
        """Test extraction with empty member list."""
        with tarfile.open(safe_tar_file, "r:gz") as tar:
            extracted = unpack_members_securely(tar, temp_dest_dir, [])

        assert len(extracted) == 0

    def test_unpack_members_securely_verifies_content(
        self, safe_tar_file: Path, temp_dest_dir: Path
    ) -> None:
        """Test that extracted members have correct content."""
        with tarfile.open(safe_tar_file, "r:gz") as tar:
            members = tar.getmembers()
            member = next(m for m in members if m.name == "file1.txt")
            unpack_members_securely(tar, temp_dest_dir, [member])

        assert (temp_dest_dir / "file1.txt").read_text() == "content1"

    def test_unpack_members_securely_stops_on_first_unsafe(
        self, tmp_path: Path, temp_dest_dir: Path
    ) -> None:
        """Test that extraction stops at first unsafe member."""
        tar_path = tmp_path / "mixed.tar.gz"
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        (source_dir / "safe1.txt").write_text("safe1")
        (source_dir / "evil.txt").write_text("evil")
        (source_dir / "safe2.txt").write_text("safe2")

        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(source_dir / "safe1.txt", arcname="safe1.txt")
            tar.add(source_dir / "evil.txt", arcname="../evil.txt")
            tar.add(source_dir / "safe2.txt", arcname="safe2.txt")

        with tarfile.open(tar_path, "r:gz") as tar:
            members = tar.getmembers()

            # Try to extract all members
            with pytest.raises(TarfileSecurityError):
                unpack_members_securely(tar, temp_dest_dir, members)

        # First file should be extracted
        assert (temp_dest_dir / "safe1.txt").exists()
        # Third file should not be extracted (stopped at unsafe)
        assert not (temp_dest_dir / "safe2.txt").exists()


class TestTarfileSecurityError:
    """Tests for TarfileSecurityError exception."""

    def test_security_error_can_be_raised(self) -> None:
        """Test that TarfileSecurityError can be raised."""
        msg = "Security violation"
        with pytest.raises(TarfileSecurityError):
            raise TarfileSecurityError(msg)

    def test_security_error_is_exception(self) -> None:
        """Test that TarfileSecurityError inherits from Exception."""
        assert issubclass(TarfileSecurityError, Exception)
        msg = "Security violation"
        with pytest.raises(TarfileSecurityError, match="Security violation"):
            raise TarfileSecurityError(msg)


class TestTarfileEdgeCases:
    """Additional edge case tests for tarfile utilities."""

    def test_is_path_safe_with_unicode(self, temp_dest_dir: Path) -> None:
        """Test that unicode paths are handled correctly."""
        assert is_path_safe("файл.txt", temp_dest_dir) is True
        assert is_path_safe("文件.txt", temp_dest_dir) is True
        assert is_path_safe("subdir/ファイル.txt", temp_dest_dir) is True

    def test_is_path_safe_with_long_path(self, temp_dest_dir: Path) -> None:
        """Test that long paths are handled."""
        # Create a very long path
        long_path = "/".join(["a" * 50 for _ in range(10)]) + "/file.txt"
        # Should be safe as long as it's relative and doesn't traverse
        assert is_path_safe(long_path, temp_dest_dir) is True

    def test_unpack_tar_securely_with_symlink_archive(
        self, tmp_path: Path, temp_dest_dir: Path
    ) -> None:
        """Test extraction of archive containing symlinks."""
        tar_path = tmp_path / "symlinks.tar.gz"
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        # Create target and symlink
        target = source_dir / "target.txt"
        target.write_text("target content")
        link = source_dir / "link.txt"

        # Create symlink if supported
        try:
            link.symlink_to("target.txt")

            with tarfile.open(tar_path, "w:gz") as tar:
                tar.add(target, arcname="target.txt")
                tar.add(link, arcname="link.txt")

            with tarfile.open(tar_path, "r:gz") as tar:
                extracted = unpack_tar_securely(tar, temp_dest_dir)

            # Both files should be extracted
            assert len(extracted) >= 1  # At least target should be extracted
            assert (temp_dest_dir / "target.txt").exists()

        except (OSError, NotImplementedError):
            # Skip test if symlinks not supported
            pytest.skip("Symlinks not supported on this platform")

    def test_is_member_safe_with_absolute_symlink_target(self, temp_dest_dir: Path) -> None:
        """Test that absolute symlink targets are rejected."""
        member = tarfile.TarInfo(name="link.txt")
        member.type = tarfile.SYMTYPE
        member.linkname = "/etc/passwd"

        assert is_member_safe(member, temp_dest_dir) is False

    def test_unpack_members_securely_with_duplicate_names(
        self, tmp_path: Path, temp_dest_dir: Path
    ) -> None:
        """Test extraction with duplicate member names."""
        tar_path = tmp_path / "duplicate.tar.gz"
        source_dir = tmp_path / "source"
        source_dir.mkdir()

        file1 = source_dir / "file1.txt"
        file1.write_text("first")
        file2 = source_dir / "file2.txt"
        file2.write_text("second")

        with tarfile.open(tar_path, "w:gz") as tar:
            tar.add(file1, arcname="file.txt")
            tar.add(file2, arcname="file.txt")  # Same name

        with tarfile.open(tar_path, "r:gz") as tar:
            members = tar.getmembers()
            extracted = unpack_members_securely(tar, temp_dest_dir, members)

        # Should extract both (second overwrites first)
        assert len(extracted) == 2
        # Content should be from second file
        assert (temp_dest_dir / "file.txt").read_text() == "second"

    def test_is_path_safe_with_windows_paths(self, temp_dest_dir: Path) -> None:
        """Test that Windows-style paths are handled."""
        # Windows paths with backslashes should work
        # Path normalization handles this
        assert is_path_safe("subdir\\file.txt", temp_dest_dir) is True

    def test_unpack_tar_securely_return_order(
        self, safe_tar_file: Path, temp_dest_dir: Path
    ) -> None:
        """Test that returned file list matches extraction order."""
        with tarfile.open(safe_tar_file, "r:gz") as tar:
            safe_members = list(get_safe_members(tar, temp_dest_dir))
            expected_names = [m.name for m in safe_members]

            extracted = unpack_tar_securely(tar, temp_dest_dir)

        assert extracted == expected_names
