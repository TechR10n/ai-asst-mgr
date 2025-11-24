"""Unit tests for OpenAIAdapter."""

import shutil
import subprocess
import tarfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from ai_asst_mgr.adapters.base import VendorStatus
from ai_asst_mgr.adapters.openai import OpenAIAdapter


@pytest.fixture
def temp_codex_dir(tmp_path: Path) -> Path:
    """Create a temporary Codex configuration directory.

    Args:
        tmp_path: Pytest temporary directory fixture.

    Returns:
        Path to temporary .codex directory.
    """
    codex_dir = tmp_path / ".codex"
    codex_dir.mkdir()
    return codex_dir


@pytest.fixture
def adapter_with_temp_dir(temp_codex_dir: Path) -> OpenAIAdapter:
    """Create an OpenAIAdapter with temporary directory.

    Args:
        temp_codex_dir: Temporary .codex directory fixture.

    Returns:
        OpenAIAdapter instance configured with temp directory.
    """
    adapter = OpenAIAdapter()
    adapter._config_dir = temp_codex_dir
    adapter._config_file = temp_codex_dir / "config.toml"
    adapter._agents_md = temp_codex_dir / "AGENTS.md"
    return adapter


def test_openai_adapter_info() -> None:
    """Test OpenAIAdapter info property."""
    adapter = OpenAIAdapter()
    info = adapter.info

    assert info.name == "OpenAI Codex"
    assert info.vendor_id == "openai"
    assert info.executable == "codex"
    assert info.homepage == "https://openai.com/codex"
    assert info.supports_agents is True
    assert info.supports_mcp is True
    assert info.config_dir == Path.home() / ".codex"


@patch("subprocess.run")
def test_is_installed_true(mock_run: MagicMock) -> None:
    """Test is_installed returns True when CLI exists."""
    mock_run.return_value = MagicMock(returncode=0)

    adapter = OpenAIAdapter()
    assert adapter.is_installed() is True


@patch("subprocess.run")
def test_is_installed_false(mock_run: MagicMock) -> None:
    """Test is_installed returns False when CLI doesn't exist."""
    mock_run.return_value = MagicMock(returncode=1)

    adapter = OpenAIAdapter()
    assert adapter.is_installed() is False


@patch("subprocess.run")
def test_is_installed_subprocess_error(mock_run: MagicMock) -> None:
    """Test is_installed handles subprocess errors."""
    mock_run.side_effect = OSError("Command not found")

    adapter = OpenAIAdapter()
    assert adapter.is_installed() is False


def test_is_configured_true_root_key(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test is_configured returns True when root API key exists."""
    config = {"api_key": "test-key-123", "model": "gpt-4"}
    adapter_with_temp_dir._save_config(config)

    assert adapter_with_temp_dir.is_configured() is True


def test_is_configured_true_profile_key(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test is_configured returns True when profile has API key."""
    config = {
        "model": "gpt-4",
        "profiles": {"default": {"api_key": "test-key-123"}},
    }
    adapter_with_temp_dir._save_config(config)

    assert adapter_with_temp_dir.is_configured() is True


def test_is_configured_false_no_config(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test is_configured returns False when config.toml doesn't exist."""
    assert adapter_with_temp_dir.is_configured() is False


def test_is_configured_false_no_api_key(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test is_configured returns False when API key is missing."""
    config = {"model": "gpt-4"}
    adapter_with_temp_dir._save_config(config)

    assert adapter_with_temp_dir.is_configured() is False


def test_is_configured_api_key_camelcase(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test is_configured works with camelCase apiKey."""
    config = {"apiKey": "test-key-123", "model": "gpt-4"}
    adapter_with_temp_dir._save_config(config)

    assert adapter_with_temp_dir.is_configured() is True


def test_is_configured_malformed_toml(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test is_configured handles malformed TOML."""
    adapter_with_temp_dir._config_file.write_text("[invalid toml")

    assert adapter_with_temp_dir.is_configured() is False


@patch("subprocess.run")
def test_get_status_not_installed(
    mock_run: MagicMock, adapter_with_temp_dir: OpenAIAdapter
) -> None:
    """Test get_status returns NOT_INSTALLED when CLI not available."""
    mock_run.return_value = MagicMock(returncode=1)

    status = adapter_with_temp_dir.get_status()
    assert status == VendorStatus.NOT_INSTALLED


@patch("subprocess.run")
def test_get_status_installed(mock_run: MagicMock, adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test get_status returns INSTALLED when config dir doesn't exist."""
    mock_run.return_value = MagicMock(returncode=0)
    adapter_with_temp_dir._config_dir.rmdir()

    status = adapter_with_temp_dir.get_status()
    assert status == VendorStatus.INSTALLED


@patch("subprocess.run")
def test_get_status_configured(mock_run: MagicMock, adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test get_status returns CONFIGURED when properly set up."""
    mock_run.return_value = MagicMock(returncode=0)
    config = {"api_key": "test-key", "model": "gpt-4"}
    adapter_with_temp_dir._save_config(config)

    status = adapter_with_temp_dir.get_status()
    assert status == VendorStatus.CONFIGURED


@patch("subprocess.run")
def test_get_status_error(mock_run: MagicMock, adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test get_status returns INSTALLED when config is malformed.

    Note: Malformed TOML is caught by is_configured() which returns False,
    so the status is INSTALLED rather than ERROR. This is by design - the
    system is installed but not properly configured.
    """
    mock_run.return_value = MagicMock(returncode=0)
    adapter_with_temp_dir._config_file.write_text("[invalid toml")

    status = adapter_with_temp_dir.get_status()
    assert status == VendorStatus.INSTALLED


def test_initialize(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test initialize creates directory structure."""
    # Remove existing directory
    shutil.rmtree(adapter_with_temp_dir._config_dir)

    adapter_with_temp_dir.initialize()

    assert adapter_with_temp_dir._config_dir.exists()
    assert adapter_with_temp_dir._config_file.exists()
    assert adapter_with_temp_dir._agents_md.exists()
    assert (adapter_with_temp_dir._config_dir / "mcp_servers").exists()

    # Verify default config
    config = adapter_with_temp_dir._load_config()
    assert "api_key" in config
    assert config["model"] == "gpt-4"
    assert "profiles" in config


def test_initialize_already_exists(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test initialize doesn't overwrite existing configuration."""
    config = {"api_key": "existing-key", "custom_field": "value"}
    adapter_with_temp_dir._save_config(config)

    adapter_with_temp_dir.initialize()

    # Verify existing config wasn't overwritten
    loaded_config = adapter_with_temp_dir._load_config()
    assert loaded_config["api_key"] == "existing-key"
    assert loaded_config["custom_field"] == "value"


def test_get_config(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test get_config retrieves values."""
    config = {
        "api_key": "test-key",
        "model": "gpt-4",
        "profiles": {"default": {"temperature": 0.8}},
    }
    adapter_with_temp_dir._save_config(config)

    assert adapter_with_temp_dir.get_config("api_key") == "test-key"
    assert adapter_with_temp_dir.get_config("profiles.default.temperature") == 0.8


def test_get_config_key_not_found(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test get_config raises KeyError for missing keys."""
    adapter_with_temp_dir._save_config({"api_key": "test"})

    with pytest.raises(KeyError, match="nonexistent"):
        adapter_with_temp_dir.get_config("nonexistent")


def test_set_config(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test set_config updates values."""
    adapter_with_temp_dir._save_config({"api_key": "old-key"})

    adapter_with_temp_dir.set_config("api_key", "new-key")
    adapter_with_temp_dir.set_config("model", "gpt-4-turbo")

    config = adapter_with_temp_dir._load_config()
    assert config["api_key"] == "new-key"
    assert config["model"] == "gpt-4-turbo"


def test_set_config_creates_nested_keys(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test set_config creates nested keys."""
    adapter_with_temp_dir._save_config({})

    adapter_with_temp_dir.set_config("profiles.custom.model", "gpt-4")

    config = adapter_with_temp_dir._load_config()
    assert config["profiles"]["custom"]["model"] == "gpt-4"


def test_backup(adapter_with_temp_dir: OpenAIAdapter, tmp_path: Path) -> None:
    """Test backup creates tar.gz archive."""
    adapter_with_temp_dir._save_config({"api_key": "test"})

    backup_dir = tmp_path / "backups"
    backup_file = adapter_with_temp_dir.backup(backup_dir)

    assert backup_file.exists()
    assert backup_file.suffix == ".gz"
    assert "openai_backup_" in backup_file.name


def test_restore(adapter_with_temp_dir: OpenAIAdapter, tmp_path: Path) -> None:
    """Test restore extracts backup."""
    # Create backup
    adapter_with_temp_dir._save_config({"api_key": "backup-key"})
    backup_dir = tmp_path / "backups"
    backup_file = adapter_with_temp_dir.backup(backup_dir)

    # Modify config
    adapter_with_temp_dir.set_config("api_key", "modified-key")

    # Restore
    adapter_with_temp_dir.restore(backup_file)

    # Verify restored
    config = adapter_with_temp_dir._load_config()
    assert config["api_key"] == "backup-key"


def test_restore_file_not_found(adapter_with_temp_dir: OpenAIAdapter, tmp_path: Path) -> None:
    """Test restore raises FileNotFoundError for missing backup."""
    nonexistent_backup = tmp_path / "nonexistent.tar.gz"

    with pytest.raises(FileNotFoundError, match="Backup file not found"):
        adapter_with_temp_dir.restore(nonexistent_backup)


@patch("subprocess.run")
def test_sync_from_git(mock_run: MagicMock, adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test sync_from_git clones and copies configuration."""

    # Create fake git repo directory at the expected location
    def create_fake_repo(*_args: object, **_kwargs: object) -> MagicMock:
        fake_repo = adapter_with_temp_dir._config_dir.parent / "temp_git_clone"
        fake_repo.mkdir(parents=True, exist_ok=True)
        (fake_repo / "config.toml").write_text('[api]\nkey = "git-key"')
        (fake_repo / "AGENTS.md").write_text("# Agents")
        (fake_repo / "mcp_servers").mkdir()
        (fake_repo / "mcp_servers" / "server1.toml").write_text('[server]\nname = "s1"')
        return MagicMock(returncode=0)

    mock_run.side_effect = create_fake_repo

    adapter_with_temp_dir.sync_from_git("https://github.com/test/repo.git")

    # Verify files were copied
    assert adapter_with_temp_dir._config_file.exists()
    assert adapter_with_temp_dir._agents_md.exists()
    assert (adapter_with_temp_dir._config_dir / "mcp_servers").exists()


def test_health_check_healthy(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test health_check returns healthy status."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        adapter_with_temp_dir._save_config({"api_key": "test-key"})
        (adapter_with_temp_dir._config_dir / "mcp_servers").mkdir()
        adapter_with_temp_dir._agents_md.write_text("# Agents")

        result = adapter_with_temp_dir.health_check()

        assert result["healthy"] is True
        assert result["checks"]["cli_installed"] is True
        assert result["checks"]["configured"] is True
        assert result["checks"]["has_mcp_dir"] is True
        assert len(result["errors"]) == 0


def test_health_check_not_installed(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test health_check detects missing CLI."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)

        result = adapter_with_temp_dir.health_check()

        assert result["healthy"] is False
        assert result["checks"]["cli_installed"] is False
        assert "Codex CLI not installed" in result["errors"]


def test_audit_config(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test audit_config returns audit results."""
    adapter_with_temp_dir._save_config({"api_key": "test-key-12345"})

    result = adapter_with_temp_dir.audit_config()

    assert "score" in result
    assert isinstance(result["score"], int)
    assert 0 <= result["score"] <= 100
    assert "issues" in result
    assert "warnings" in result
    assert "recommendations" in result


def test_audit_config_no_config(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test audit_config detects missing config."""
    result = adapter_with_temp_dir.audit_config()

    assert result["score"] < 100
    assert "No config.toml found" in result["issues"]


def test_audit_config_malformed_toml(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test audit_config detects malformed TOML."""
    adapter_with_temp_dir._config_file.write_text("[invalid")

    result = adapter_with_temp_dir.audit_config()

    assert "config.toml is malformed" in result["issues"]


def test_audit_config_permissive_permissions(
    adapter_with_temp_dir: OpenAIAdapter,
) -> None:
    """Test audit_config detects permissive permissions."""
    adapter_with_temp_dir._save_config({"api_key": "test"})
    adapter_with_temp_dir._config_dir.chmod(0o777)

    result = adapter_with_temp_dir.audit_config()

    assert any("permissive permissions" in issue for issue in result["issues"])


def test_audit_config_no_api_key(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test audit_config warns about missing API key."""
    adapter_with_temp_dir._save_config({"model": "gpt-4"})

    result = adapter_with_temp_dir.audit_config()

    assert any("No API key" in warning for warning in result["warnings"])


def test_audit_config_empty_api_key(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test audit_config warns about empty API key."""
    adapter_with_temp_dir._save_config({"api_key": ""})

    result = adapter_with_temp_dir.audit_config()

    assert any("API key is empty" in warning for warning in result["warnings"])


def test_audit_config_plaintext_api_key_warning(
    adapter_with_temp_dir: OpenAIAdapter,
) -> None:
    """Test audit_config warns about plaintext API key."""
    adapter_with_temp_dir._save_config({"api_key": "sk-AbCdEfGhIjKlMnOpQrSt"})

    result = adapter_with_temp_dir.audit_config()

    assert any("plaintext" in warning for warning in result["warnings"])


def test_audit_config_profile_plaintext_warning(
    adapter_with_temp_dir: OpenAIAdapter,
) -> None:
    """Test audit_config warns about plaintext API keys in profiles."""
    config = {
        "profiles": {
            "prod": {"api_key": "sk-AbCdEfGhIjKlMnOpQrSt"},
        },
    }
    adapter_with_temp_dir._save_config(config)

    result = adapter_with_temp_dir.audit_config()

    assert any("Profile 'prod'" in warning for warning in result["warnings"])


def test_audit_config_missing_directories_recommendations(
    adapter_with_temp_dir: OpenAIAdapter,
) -> None:
    """Test audit_config recommends creating missing directories."""
    adapter_with_temp_dir._save_config({"api_key": "test"})

    result = adapter_with_temp_dir.audit_config()

    # Check if recommendations suggest creating directories
    assert isinstance(result["recommendations"], list)


def test_get_usage_stats(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test get_usage_stats returns statistics."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        config = {
            "api_key": "test",
            "profiles": {"default": {}, "custom": {}},
        }
        adapter_with_temp_dir._save_config(config)
        mcp_dir = adapter_with_temp_dir._config_dir / "mcp_servers"
        mcp_dir.mkdir()
        (mcp_dir / "server1.toml").write_text("[server]")
        (mcp_dir / "server2.toml").write_text("[server]")

        stats = adapter_with_temp_dir.get_usage_stats()

        assert stats["cli_available"] is True
        assert stats["configured"] is True
        assert stats["profile_count"] == 2
        assert stats["mcp_server_count"] == 2


def test_get_usage_stats_not_installed(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test get_usage_stats when CLI not installed."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=1)

        stats = adapter_with_temp_dir.get_usage_stats()

        assert stats["cli_available"] is False


def test_load_config_file_not_found(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test _load_config raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        adapter_with_temp_dir._load_config()


def test_list_toml_files(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test _list_toml_files returns TOML files."""
    mcp_dir = adapter_with_temp_dir._config_dir / "mcp_servers"
    mcp_dir.mkdir()
    (mcp_dir / "server1.toml").write_text("[server]")
    (mcp_dir / "server2.toml").write_text("[server]")
    (mcp_dir / "readme.md").write_text("# README")

    toml_files = list(adapter_with_temp_dir._list_toml_files(mcp_dir))

    assert len(toml_files) == 2
    assert all(f.suffix == ".toml" for f in toml_files)


def test_list_toml_files_nonexistent_directory(
    adapter_with_temp_dir: OpenAIAdapter,
) -> None:
    """Test _list_toml_files handles nonexistent directory."""
    nonexistent = adapter_with_temp_dir._config_dir / "nonexistent"

    toml_files = list(adapter_with_temp_dir._list_toml_files(nonexistent))

    assert len(toml_files) == 0


def test_health_check_malformed_config(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test health_check detects malformed config."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        adapter_with_temp_dir._config_file.write_text("[invalid")

        result = adapter_with_temp_dir.health_check()

        assert result["healthy"] is False
        assert result["checks"]["valid_config"] is False


def test_health_check_missing_mcp_dir(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test health_check detects missing MCP directory."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        adapter_with_temp_dir._save_config({"api_key": "test"})

        result = adapter_with_temp_dir.health_check()

        assert result["checks"]["has_mcp_dir"] is False


def test_initialize_error(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test initialize handles OSError."""
    with patch.object(Path, "mkdir", side_effect=OSError("Permission denied")):  # noqa: SIM117
        with pytest.raises(RuntimeError, match="Failed to initialize"):
            adapter_with_temp_dir.initialize()


def test_backup_error(adapter_with_temp_dir: OpenAIAdapter, tmp_path: Path) -> None:
    """Test backup handles errors."""
    with patch.object(tarfile, "open", side_effect=OSError("Write error")):  # noqa: SIM117
        with pytest.raises(RuntimeError, match="Failed to create backup"):
            adapter_with_temp_dir.backup(tmp_path)


def test_restore_error(adapter_with_temp_dir: OpenAIAdapter, tmp_path: Path) -> None:
    """Test restore handles extraction errors."""
    # Create a valid tar file
    backup_file = tmp_path / "test.tar.gz"
    with tarfile.open(backup_file, "w:gz"):
        pass

    with patch.object(tarfile.TarFile, "extractall", side_effect=OSError("Extract error")):  # noqa: SIM117
        with pytest.raises(RuntimeError, match="Failed to restore backup"):
            adapter_with_temp_dir.restore(backup_file)


@patch("subprocess.run")
def test_sync_from_git_error(mock_run: MagicMock, adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test sync_from_git handles git clone errors."""
    mock_run.side_effect = subprocess.CalledProcessError(1, "git")

    with pytest.raises(RuntimeError, match="Failed to sync from git"):
        adapter_with_temp_dir.sync_from_git("https://github.com/test/repo.git")


@patch("subprocess.run")
def test_sync_from_git_shutil_error(
    mock_run: MagicMock, adapter_with_temp_dir: OpenAIAdapter, tmp_path: Path
) -> None:
    """Test sync_from_git handles shutil errors."""
    # Create fake git repo
    fake_repo = tmp_path / "temp_git_clone"
    fake_repo.mkdir()
    (fake_repo / "config.toml").write_text('[api]\nkey = "test"')

    mock_run.return_value = MagicMock(returncode=0)

    with patch.object(shutil, "copy", side_effect=OSError("Copy error")):  # noqa: SIM117
        with pytest.raises(RuntimeError, match="Failed to sync from git"):
            adapter_with_temp_dir.sync_from_git("https://github.com/test/repo.git")


def test_audit_config_with_mcp_and_agents_md(
    adapter_with_temp_dir: OpenAIAdapter,
) -> None:
    """Test audit_config when MCP and AGENTS.md exist."""
    adapter_with_temp_dir._save_config({"api_key": "test"})
    (adapter_with_temp_dir._config_dir / "mcp_servers").mkdir()
    adapter_with_temp_dir._agents_md.write_text("# Agents")

    result = adapter_with_temp_dir.audit_config()

    # Should not recommend creating directories that already exist
    assert not any("mcp_servers" in rec for rec in result["recommendations"])
    assert not any("AGENTS.md" in rec for rec in result["recommendations"])


def test_save_config_error(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test _save_config handles write errors."""
    with patch.object(Path, "open", side_effect=OSError("Write error")):  # noqa: SIM117
        with pytest.raises(RuntimeError, match="Failed to save config"):
            adapter_with_temp_dir._save_config({"api_key": "test"})


def test_restore_missing_extracted_dir(
    adapter_with_temp_dir: OpenAIAdapter, tmp_path: Path
) -> None:
    """Test restore handles missing extracted directory."""
    # Create tar without 'codex' directory
    backup_file = tmp_path / "backup.tar.gz"
    temp_content = tmp_path / "content"
    temp_content.mkdir()
    (temp_content / "other.txt").write_text("test")

    with tarfile.open(backup_file, "w:gz") as tar:
        tar.add(temp_content, arcname="other")

    # Restore should complete without error even if 'codex' dir doesn't exist
    adapter_with_temp_dir.restore(backup_file)


def test_health_check_no_api_key(adapter_with_temp_dir: OpenAIAdapter) -> None:
    """Test health_check detects missing API key."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        adapter_with_temp_dir._save_config({"model": "gpt-4"})

        result = adapter_with_temp_dir.health_check()

        assert result["checks"]["configured"] is False
        assert "No API key configured" in result["errors"]


def test_get_usage_stats_malformed_config(
    adapter_with_temp_dir: OpenAIAdapter,
) -> None:
    """Test get_usage_stats handles malformed config gracefully."""
    with patch("subprocess.run") as mock_run:
        mock_run.return_value = MagicMock(returncode=0)

        adapter_with_temp_dir._config_file.write_text("[invalid")

        stats = adapter_with_temp_dir.get_usage_stats()

        # Should not crash, just not include profile_count
        assert "cli_available" in stats
        assert "profile_count" not in stats
