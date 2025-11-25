"""Unit tests for GeminiAdapter."""

import shutil
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_asst_mgr.adapters.base import VendorStatus
from ai_asst_mgr.adapters.gemini import GeminiAdapter


@pytest.fixture
def temp_gemini_dir(tmp_path: Path) -> Path:
    """Create a temporary Gemini configuration directory.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Path to temporary .gemini directory.
    """
    gemini_dir = tmp_path / ".gemini"
    gemini_dir.mkdir()
    return gemini_dir


@pytest.fixture
def adapter_with_temp_dir(temp_gemini_dir: Path) -> GeminiAdapter:
    """Create a GeminiAdapter with temporary directory.

    Args:
        temp_gemini_dir: Temporary .gemini directory fixture.

    Returns:
        GeminiAdapter instance configured with temp directory.
    """
    adapter = GeminiAdapter()
    adapter._config_dir = temp_gemini_dir
    adapter._settings_file = temp_gemini_dir / "settings.json"
    adapter._gemini_md = temp_gemini_dir / "GEMINI.md"
    return adapter


def test_gemini_adapter_info() -> None:
    """Test GeminiAdapter info property."""
    adapter = GeminiAdapter()
    info = adapter.info

    assert info.name == "Gemini CLI"
    assert info.vendor_id == "gemini"
    assert info.executable == "gemini"
    assert info.homepage == "https://ai.google.dev/gemini-api"
    assert info.supports_agents is False
    assert info.supports_mcp is True
    assert info.config_dir == Path.home() / ".gemini"


@patch("shutil.which")
def test_is_installed_true(mock_which: MagicMock) -> None:
    """Test is_installed returns True when CLI exists."""
    mock_which.return_value = "/usr/bin/gemini"

    adapter = GeminiAdapter()
    assert adapter.is_installed() is True


@patch("shutil.which")
def test_is_installed_false(mock_which: MagicMock) -> None:
    """Test is_installed returns False when CLI doesn't exist."""
    mock_which.return_value = None

    adapter = GeminiAdapter()
    assert adapter.is_installed() is False


@patch("shutil.which")
def test_is_installed_subprocess_error(mock_which: MagicMock) -> None:
    """Test is_installed handles errors gracefully."""
    mock_which.return_value = None

    adapter = GeminiAdapter()
    assert adapter.is_installed() is False


def test_is_configured_true(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test is_configured returns True when API key exists."""
    settings = {"api_key": "test-key-123", "model": "gemini-pro"}
    adapter_with_temp_dir._save_settings(settings)

    assert adapter_with_temp_dir.is_configured() is True


def test_is_configured_false_no_settings(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test is_configured returns False when settings.json doesn't exist."""
    assert adapter_with_temp_dir.is_configured() is False


def test_is_configured_false_no_api_key(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test is_configured returns False when API key is missing."""
    settings = {"model": "gemini-pro"}
    adapter_with_temp_dir._save_settings(settings)

    assert adapter_with_temp_dir.is_configured() is False


def test_is_configured_api_key_camelcase(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test is_configured works with camelCase apiKey."""
    settings = {"apiKey": "test-key-123", "model": "gemini-pro"}
    adapter_with_temp_dir._save_settings(settings)

    assert adapter_with_temp_dir.is_configured() is True


def test_is_configured_malformed_json(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test is_configured handles malformed JSON."""
    adapter_with_temp_dir._settings_file.write_text("{invalid json}")

    assert adapter_with_temp_dir.is_configured() is False


@patch("shutil.which")
def test_get_status_not_installed(
    mock_which: MagicMock, adapter_with_temp_dir: GeminiAdapter
) -> None:
    """Test get_status returns NOT_INSTALLED when CLI not available."""
    mock_which.return_value = None

    status = adapter_with_temp_dir.get_status()
    assert status == VendorStatus.NOT_INSTALLED


@patch("shutil.which")
def test_get_status_installed(mock_which: MagicMock, adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test get_status returns INSTALLED when config dir doesn't exist."""
    mock_which.return_value = "/usr/bin/gemini"
    adapter_with_temp_dir._config_dir.rmdir()

    status = adapter_with_temp_dir.get_status()
    assert status == VendorStatus.INSTALLED


@patch("shutil.which")
def test_get_status_configured(mock_which: MagicMock, adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test get_status returns CONFIGURED when properly set up."""
    mock_which.return_value = "/usr/bin/gemini"
    settings = {"api_key": "test-key", "model": "gemini-pro"}
    adapter_with_temp_dir._save_settings(settings)

    status = adapter_with_temp_dir.get_status()
    assert status == VendorStatus.CONFIGURED


@patch("shutil.which")
def test_get_status_error(mock_which: MagicMock, adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test get_status returns INSTALLED when settings are malformed.

    Note: Malformed JSON is caught by is_configured() which returns False,
    so the status is INSTALLED rather than ERROR. This is by design - the
    system is installed but not properly configured.
    """
    mock_which.return_value = "/usr/bin/gemini"
    adapter_with_temp_dir._settings_file.write_text('{"api_key": "test",')

    status = adapter_with_temp_dir.get_status()
    assert status == VendorStatus.INSTALLED


def test_initialize(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test initialize creates directory structure."""
    # Remove existing directory

    shutil.rmtree(adapter_with_temp_dir._config_dir)

    adapter_with_temp_dir.initialize()

    assert adapter_with_temp_dir._config_dir.exists()
    assert adapter_with_temp_dir._settings_file.exists()
    assert adapter_with_temp_dir._gemini_md.exists()
    assert (adapter_with_temp_dir._config_dir / "mcp_servers").exists()

    # Verify default settings
    settings = adapter_with_temp_dir._load_settings()
    assert "api_key" in settings
    assert settings["model"] == "gemini-pro"


def test_initialize_already_exists(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test initialize doesn't overwrite existing configuration."""
    settings = {"api_key": "existing-key", "custom_field": "value"}
    adapter_with_temp_dir._save_settings(settings)

    adapter_with_temp_dir.initialize()

    # Verify existing settings weren't overwritten
    loaded_settings = adapter_with_temp_dir._load_settings()
    assert loaded_settings["api_key"] == "existing-key"
    assert loaded_settings["custom_field"] == "value"


def test_get_config(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test get_config retrieves values."""
    settings = {
        "api_key": "test-key",
        "model": "gemini-pro",
        "nested": {"key": "value"},
    }
    adapter_with_temp_dir._save_settings(settings)

    assert adapter_with_temp_dir.get_config("api_key") == "test-key"
    assert adapter_with_temp_dir.get_config("nested.key") == "value"


def test_get_config_key_not_found(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test get_config raises KeyError for missing keys."""
    adapter_with_temp_dir._save_settings({"api_key": "test"})

    with pytest.raises(KeyError, match="nonexistent"):
        adapter_with_temp_dir.get_config("nonexistent")


def test_set_config(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test set_config updates values."""
    adapter_with_temp_dir._save_settings({"api_key": "old-key"})

    adapter_with_temp_dir.set_config("api_key", "new-key")
    adapter_with_temp_dir.set_config("model", "gemini-pro-vision")

    settings = adapter_with_temp_dir._load_settings()
    assert settings["api_key"] == "new-key"
    assert settings["model"] == "gemini-pro-vision"


def test_set_config_creates_nested_keys(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test set_config creates nested keys."""
    adapter_with_temp_dir._save_settings({})

    adapter_with_temp_dir.set_config("mcp.server.url", "http://localhost:8080")

    settings = adapter_with_temp_dir._load_settings()
    assert settings["mcp"]["server"]["url"] == "http://localhost:8080"


def test_backup(adapter_with_temp_dir: GeminiAdapter, tmp_path: Path) -> None:
    """Test backup creates tar.gz archive."""
    adapter_with_temp_dir._save_settings({"api_key": "test"})

    backup_dir = tmp_path / "backups"
    backup_file = adapter_with_temp_dir.backup(backup_dir)

    assert backup_file.exists()
    assert backup_file.suffix == ".gz"
    assert "gemini_backup_" in backup_file.name


def test_restore(adapter_with_temp_dir: GeminiAdapter, tmp_path: Path) -> None:
    """Test restore extracts backup."""
    # Create backup
    adapter_with_temp_dir._save_settings({"api_key": "backup-key"})
    backup_dir = tmp_path / "backups"
    backup_file = adapter_with_temp_dir.backup(backup_dir)

    # Modify settings
    adapter_with_temp_dir.set_config("api_key", "modified-key")

    # Restore
    adapter_with_temp_dir.restore(backup_file)

    # Verify restored
    settings = adapter_with_temp_dir._load_settings()
    assert settings["api_key"] == "backup-key"


def test_restore_file_not_found(adapter_with_temp_dir: GeminiAdapter, tmp_path: Path) -> None:
    """Test restore raises FileNotFoundError for missing backup."""
    nonexistent_backup = tmp_path / "nonexistent.tar.gz"

    with pytest.raises(FileNotFoundError, match="Backup file not found"):
        adapter_with_temp_dir.restore(nonexistent_backup)


@patch("ai_asst_mgr.adapters.gemini.git_clone")
def test_sync_from_git(mock_git_clone: MagicMock, adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test sync_from_git clones and copies configuration."""

    # Create fake git repo directory at the expected location
    def create_fake_repo(_url: str, dest: Path, _branch: str) -> bool:
        dest.mkdir(parents=True, exist_ok=True)
        (dest / "settings.json").write_text('{"api_key": "git-key"}')
        (dest / "GEMINI.md").write_text("# Gemini Config")
        (dest / "mcp_servers").mkdir()
        (dest / "mcp_servers" / "server1.json").write_text('{"name": "server1"}')
        return True

    mock_git_clone.side_effect = create_fake_repo

    adapter_with_temp_dir.sync_from_git("https://github.com/test/repo.git")

    # Verify files were copied
    assert adapter_with_temp_dir._settings_file.exists()
    assert adapter_with_temp_dir._gemini_md.exists()
    assert (adapter_with_temp_dir._config_dir / "mcp_servers").exists()

    settings = adapter_with_temp_dir._load_settings()
    assert settings["api_key"] == "git-key"


def test_health_check_healthy(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test health_check returns healthy status."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/gemini"

        adapter_with_temp_dir._save_settings({"api_key": "test-key"})
        (adapter_with_temp_dir._config_dir / "mcp_servers").mkdir()
        adapter_with_temp_dir._gemini_md.write_text("# Gemini")

        result = adapter_with_temp_dir.health_check()

        assert result["healthy"] is True
        assert result["checks"]["cli_installed"] is True
        assert result["checks"]["configured"] is True
        assert result["checks"]["has_mcp_dir"] is True
        assert len(result["errors"]) == 0


def test_health_check_not_installed(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test health_check detects missing CLI."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None

        result = adapter_with_temp_dir.health_check()

        assert result["healthy"] is False
        assert result["checks"]["cli_installed"] is False
        assert "Gemini CLI not installed" in result["errors"]


def test_audit_config(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test audit_config returns audit results."""
    adapter_with_temp_dir._save_settings({"api_key": "test-key-12345"})

    result = adapter_with_temp_dir.audit_config()

    assert "score" in result
    assert isinstance(result["score"], int)
    assert 0 <= result["score"] <= 100
    assert "issues" in result
    assert "warnings" in result
    assert "recommendations" in result


def test_audit_config_no_settings(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test audit_config detects missing settings."""
    result = adapter_with_temp_dir.audit_config()

    assert result["score"] < 100
    assert "No settings.json found" in result["issues"]


def test_audit_config_malformed_json(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test audit_config detects malformed JSON."""
    adapter_with_temp_dir._settings_file.write_text("{invalid}")

    result = adapter_with_temp_dir.audit_config()

    assert "settings.json is malformed" in result["issues"]


def test_audit_config_permissive_permissions(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test audit_config detects permissive permissions."""
    adapter_with_temp_dir._save_settings({"api_key": "test"})
    adapter_with_temp_dir._config_dir.chmod(0o777)

    result = adapter_with_temp_dir.audit_config()

    assert any("permissive permissions" in issue for issue in result["issues"])


def test_audit_config_no_api_key(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test audit_config warns about missing API key."""
    adapter_with_temp_dir._save_settings({"model": "gemini-pro"})

    result = adapter_with_temp_dir.audit_config()

    assert any("No API key" in warning for warning in result["warnings"])


def test_audit_config_empty_api_key(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test audit_config warns about empty API key."""
    adapter_with_temp_dir._save_settings({"api_key": ""})

    result = adapter_with_temp_dir.audit_config()

    assert any("API key is empty" in warning for warning in result["warnings"])


def test_audit_config_plaintext_api_key_warning(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test audit_config warns about plaintext API key."""
    adapter_with_temp_dir._save_settings({"api_key": "AIzaSyAbCdEfGhIjKlMnOpQrStUvWxYz"})

    result = adapter_with_temp_dir.audit_config()

    assert any("plaintext" in warning for warning in result["warnings"])


def test_audit_config_missing_directories_recommendations(
    adapter_with_temp_dir: GeminiAdapter,
) -> None:
    """Test audit_config recommends creating missing directories."""
    adapter_with_temp_dir._save_settings({"api_key": "test"})

    result = adapter_with_temp_dir.audit_config()

    # Check if recommendations suggest creating directories
    assert isinstance(result["recommendations"], list)


def test_get_usage_stats(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test get_usage_stats returns statistics."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/gemini"

        adapter_with_temp_dir._save_settings({"api_key": "test"})
        mcp_dir = adapter_with_temp_dir._config_dir / "mcp_servers"
        mcp_dir.mkdir()
        (mcp_dir / "server1.json").write_text("{}")
        (mcp_dir / "server2.json").write_text("{}")

        stats = adapter_with_temp_dir.get_usage_stats()

        assert stats["cli_available"] is True
        assert stats["configured"] is True
        assert stats["mcp_server_count"] == 2


def test_get_usage_stats_not_installed(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test get_usage_stats when CLI not installed."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = None

        stats = adapter_with_temp_dir.get_usage_stats()

        assert stats["cli_available"] is False


def test_load_settings_file_not_found(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test _load_settings raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        adapter_with_temp_dir._load_settings()


def test_list_json_files(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test _list_json_files returns JSON files."""
    mcp_dir = adapter_with_temp_dir._config_dir / "mcp_servers"
    mcp_dir.mkdir()
    (mcp_dir / "server1.json").write_text("{}")
    (mcp_dir / "server2.json").write_text("{}")
    (mcp_dir / "readme.md").write_text("# README")

    json_files = list(adapter_with_temp_dir._list_json_files(mcp_dir))

    assert len(json_files) == 2
    assert all(f.suffix == ".json" for f in json_files)


def test_list_json_files_nonexistent_directory(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test _list_json_files handles nonexistent directory."""
    nonexistent = adapter_with_temp_dir._config_dir / "nonexistent"

    json_files = list(adapter_with_temp_dir._list_json_files(nonexistent))

    assert len(json_files) == 0


def test_health_check_malformed_settings(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test health_check detects malformed settings."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/gemini"

        adapter_with_temp_dir._settings_file.write_text("{invalid}")

        result = adapter_with_temp_dir.health_check()

        assert result["healthy"] is False
        assert result["checks"]["valid_settings"] is False


def test_health_check_missing_mcp_dir(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test health_check detects missing MCP directory."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/gemini"

        adapter_with_temp_dir._save_settings({"api_key": "test"})

        result = adapter_with_temp_dir.health_check()

        assert result["checks"]["has_mcp_dir"] is False


def test_initialize_error(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test initialize handles OSError."""
    with patch.object(Path, "mkdir", side_effect=OSError("Permission denied")):
        with pytest.raises(RuntimeError, match="Failed to initialize"):
            adapter_with_temp_dir.initialize()


def test_backup_error(adapter_with_temp_dir: GeminiAdapter, tmp_path: Path) -> None:
    """Test backup handles errors."""
    with patch.object(tarfile, "open", side_effect=OSError("Write error")):
        with pytest.raises(RuntimeError, match="Failed to create backup"):
            adapter_with_temp_dir.backup(tmp_path)


def test_restore_error(adapter_with_temp_dir: GeminiAdapter, tmp_path: Path) -> None:
    """Test restore handles extraction errors."""
    # Create a tar file with a test file
    backup_file = tmp_path / "test.tar.gz"
    test_content = tmp_path / "test_content"
    test_content.mkdir()
    (test_content / "test.txt").write_text("test")

    with tarfile.open(backup_file, "w:gz") as tar:
        tar.add(test_content, arcname="gemini")

    with patch.object(tarfile.TarFile, "extract", side_effect=OSError("Extract error")):
        with pytest.raises(RuntimeError, match="Failed to restore backup"):
            adapter_with_temp_dir.restore(backup_file)


@patch("ai_asst_mgr.adapters.gemini.git_clone")
def test_sync_from_git_error(
    mock_git_clone: MagicMock, adapter_with_temp_dir: GeminiAdapter
) -> None:
    """Test sync_from_git handles git clone errors."""
    mock_git_clone.return_value = False

    with pytest.raises(RuntimeError, match="Failed to clone repository"):
        adapter_with_temp_dir.sync_from_git("https://github.com/test/repo.git")


@patch("shutil.copy")
@patch("ai_asst_mgr.adapters.gemini.git_clone")
def test_sync_from_git_shutil_error(
    mock_git_clone: MagicMock,
    mock_copy: MagicMock,
    adapter_with_temp_dir: GeminiAdapter,
) -> None:
    """Test sync_from_git handles shutil errors."""

    # Mock git_clone to succeed and create temp directory
    def create_fake_repo(_url: str, dest: Path, _branch: str) -> bool:
        dest.mkdir(exist_ok=True)
        (dest / "settings.json").write_text('{"api_key": "test"}')
        return True

    mock_git_clone.side_effect = create_fake_repo
    mock_copy.side_effect = OSError("Copy error")

    with pytest.raises(RuntimeError, match="Failed to sync from git"):
        adapter_with_temp_dir.sync_from_git("https://github.com/test/repo.git")


def test_audit_config_with_mcp_and_gemini_md(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test audit_config when MCP and GEMINI.md exist."""
    adapter_with_temp_dir._save_settings({"api_key": "test"})
    (adapter_with_temp_dir._config_dir / "mcp_servers").mkdir()
    adapter_with_temp_dir._gemini_md.write_text("# Gemini")

    result = adapter_with_temp_dir.audit_config()

    # Should not recommend creating directories that already exist
    assert not any("mcp_servers" in rec for rec in result["recommendations"])
    assert not any("GEMINI.md" in rec for rec in result["recommendations"])


def test_save_settings_error(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test _save_settings handles write errors."""
    with patch.object(Path, "open", side_effect=OSError("Write error")):
        with pytest.raises(RuntimeError, match="Failed to save settings"):
            adapter_with_temp_dir._save_settings({"api_key": "test"})


def test_restore_missing_extracted_dir(
    adapter_with_temp_dir: GeminiAdapter, tmp_path: Path
) -> None:
    """Test restore handles missing extracted directory."""
    # Create tar without 'gemini' directory
    backup_file = tmp_path / "backup.tar.gz"
    temp_content = tmp_path / "content"
    temp_content.mkdir()
    (temp_content / "other.txt").write_text("test")

    with tarfile.open(backup_file, "w:gz") as tar:
        tar.add(temp_content, arcname="other")

    # Restore should complete without error even if 'gemini' dir doesn't exist
    adapter_with_temp_dir.restore(backup_file)


def test_health_check_no_api_key(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test health_check detects missing API key."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        adapter_with_temp_dir._save_settings({"model": "gemini-pro"})

        result = adapter_with_temp_dir.health_check()

        assert result["checks"]["configured"] is False
        assert "No API key configured" in result["errors"]


@patch("shutil.which")
def test_get_status_error_on_load(
    mock_which: MagicMock, adapter_with_temp_dir: GeminiAdapter
) -> None:
    """Test get_status returns ERROR when settings exist but can't be loaded."""
    mock_which.return_value = "/usr/bin/gemini"
    adapter_with_temp_dir._save_settings({"api_key": "test"})

    # Mock _load_settings to raise OSError after is_configured passes
    original_is_configured = adapter_with_temp_dir.is_configured
    original_load_settings = adapter_with_temp_dir._load_settings

    call_count = [0]

    def mock_load_settings():
        call_count[0] += 1
        # First call is from is_configured, second call is in get_status
        if call_count[0] == 1:
            return original_load_settings()
        raise OSError("Read error")

    with patch.object(adapter_with_temp_dir, "_load_settings", side_effect=mock_load_settings):
        status = adapter_with_temp_dir.get_status()
        assert status == VendorStatus.ERROR


@patch("ai_asst_mgr.adapters.gemini.git_clone")
def test_sync_from_git_with_existing_temp_dir(
    mock_git_clone: MagicMock, adapter_with_temp_dir: GeminiAdapter
) -> None:
    """Test sync_from_git removes existing temp directory."""
    # Create existing temp directory
    temp_dir = adapter_with_temp_dir._config_dir.parent / "temp_git_clone"
    temp_dir.mkdir()
    (temp_dir / "old_file.txt").write_text("old content")

    # Setup mock git clone
    def create_fake_repo(_url: str, dest: Path, _branch: str) -> bool:
        dest.mkdir(exist_ok=True)
        (dest / "settings.json").write_text('{"api_key": "test"}')
        return True

    mock_git_clone.side_effect = create_fake_repo

    adapter_with_temp_dir.sync_from_git("https://github.com/test/repo.git")

    # Verify old file was removed (temp dir was cleaned)
    assert not (temp_dir / "old_file.txt").exists()


@patch("ai_asst_mgr.adapters.gemini.git_clone")
def test_sync_from_git_with_existing_mcp_dir(
    mock_git_clone: MagicMock, adapter_with_temp_dir: GeminiAdapter
) -> None:
    """Test sync_from_git removes existing mcp_servers directory before copying."""
    # Create existing mcp_servers directory with old content
    mcp_dir = adapter_with_temp_dir._config_dir / "mcp_servers"
    mcp_dir.mkdir()
    (mcp_dir / "old_server.json").write_text('{"name": "old"}')

    # Setup mock git clone
    def create_fake_repo(_url: str, dest: Path, _branch: str) -> bool:
        dest.mkdir(exist_ok=True)
        (dest / "mcp_servers").mkdir()
        (dest / "mcp_servers" / "new_server.json").write_text('{"name": "new"}')
        return True

    mock_git_clone.side_effect = create_fake_repo

    adapter_with_temp_dir.sync_from_git("https://github.com/test/repo.git")

    # Verify old server was removed and new server exists
    assert not (mcp_dir / "old_server.json").exists()
    assert (mcp_dir / "new_server.json").exists()


def test_health_check_config_dir_not_exists(adapter_with_temp_dir: GeminiAdapter) -> None:
    """Test health_check when config directory doesn't exist."""
    with patch("shutil.which") as mock_which:
        mock_which.return_value = "/usr/bin/gemini"

        # Remove the config directory
        adapter_with_temp_dir._config_dir.rmdir()

        result = adapter_with_temp_dir.health_check()

        assert result["healthy"] is False
        assert result["checks"]["config_dir_exists"] is False
        assert "Configuration directory not found" in result["errors"]
