"""Unit tests for package version."""

import ai_asst_mgr


def test_version_exists() -> None:
    """Test that version attribute exists."""
    assert hasattr(ai_asst_mgr, "__version__")


def test_version_format() -> None:
    """Test that version follows semantic versioning."""
    version = ai_asst_mgr.__version__
    parts = version.split(".")
    assert len(parts) == 3
    assert all(part.isdigit() for part in parts)


def test_author_exists() -> None:
    """Test that author attribute exists."""
    assert hasattr(ai_asst_mgr, "__author__")
    assert isinstance(ai_asst_mgr.__author__, str)
    assert len(ai_asst_mgr.__author__) > 0
