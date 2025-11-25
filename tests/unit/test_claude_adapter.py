"""Unit tests for ClaudeAdapter."""

import json
import shutil
import tarfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from ai_asst_mgr.adapters.base import VendorStatus
from ai_asst_mgr.adapters.claude import ClaudeAdapter


@pytest.fixture
def temp_claude_dir(tmp_path: Path) -> Path:
    """Create a temporary Claude config directory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    return claude_dir


@pytest.fixture
def adapter_with_temp_dir(temp_claude_dir: Path) -> ClaudeAdapter:
    """Create ClaudeAdapter with temporary directory."""
    adapter = ClaudeAdapter()
    adapter._config_dir = temp_claude_dir
    adapter._settings_file = temp_claude_dir / "settings.json"
    return adapter


def test_claude_adapter_info() -> None:
    """Test ClaudeAdapter info property."""
    adapter = ClaudeAdapter()
    info = adapter.info

    assert info.name == "Claude Code"
    assert info.vendor_id == "claude"
    assert info.executable == "claude"
    assert info.homepage == "https://claude.ai/claude-code"
    assert info.supports_agents is True
    assert info.supports_mcp is True


def test_is_installed_true(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test is_installed returns True when directory exists."""
    assert adapter_with_temp_dir.is_installed() is True


def test_is_installed_false() -> None:
    """Test is_installed returns False when directory doesn't exist."""
    adapter = ClaudeAdapter()
    adapter._config_dir = Path("/nonexistent/directory")
    assert adapter.is_installed() is False


def test_is_configured_true(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test is_configured returns True when settings.json exists."""
    adapter_with_temp_dir._settings_file.write_text("{}")
    assert adapter_with_temp_dir.is_configured() is True


def test_is_configured_false(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test is_configured returns False when settings.json doesn't exist."""
    assert adapter_with_temp_dir.is_configured() is False


def test_get_status_not_installed() -> None:
    """Test get_status returns NOT_INSTALLED when directory missing."""
    adapter = ClaudeAdapter()
    adapter._config_dir = Path("/nonexistent/directory")
    assert adapter.get_status() == VendorStatus.NOT_INSTALLED


def test_get_status_installed(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test get_status returns INSTALLED when not configured."""
    assert adapter_with_temp_dir.get_status() == VendorStatus.INSTALLED


def test_get_status_configured(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test get_status returns CONFIGURED when settings.json exists."""
    adapter_with_temp_dir._settings_file.write_text('{"version": "1.0.0"}')
    assert adapter_with_temp_dir.get_status() == VendorStatus.CONFIGURED


def test_get_status_error(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test get_status returns ERROR when settings.json is malformed."""
    adapter_with_temp_dir._settings_file.write_text("invalid json")
    assert adapter_with_temp_dir.get_status() == VendorStatus.ERROR


def test_initialize(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test initialize creates directory structure."""
    # Remove the directory first
    adapter_with_temp_dir._config_dir.rmdir()

    adapter_with_temp_dir.initialize()

    assert adapter_with_temp_dir._config_dir.exists()
    assert (adapter_with_temp_dir._config_dir / "agents").exists()
    assert (adapter_with_temp_dir._config_dir / "skills").exists()
    assert (adapter_with_temp_dir._config_dir / "commands").exists()
    assert (adapter_with_temp_dir._config_dir / "hooks").exists()
    assert (adapter_with_temp_dir._config_dir / "templates").exists()
    assert adapter_with_temp_dir._settings_file.exists()

    # Verify settings content
    settings = json.loads(adapter_with_temp_dir._settings_file.read_text())
    assert settings["version"] == "1.0.0"
    assert settings["theme"] == "dark"
    assert settings["autoSave"] is True


def test_initialize_already_exists(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test initialize works when directory already exists."""
    adapter_with_temp_dir.initialize()
    # Should not raise error
    adapter_with_temp_dir.initialize()


def test_get_config(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test get_config retrieves configuration values."""
    settings = {"version": "1.0.0", "theme": "dark", "nested": {"key": "value"}}
    adapter_with_temp_dir._settings_file.write_text(json.dumps(settings))

    assert adapter_with_temp_dir.get_config("version") == "1.0.0"
    assert adapter_with_temp_dir.get_config("theme") == "dark"
    assert adapter_with_temp_dir.get_config("nested.key") == "value"


def test_get_config_key_not_found(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test get_config raises KeyError for nonexistent key."""
    adapter_with_temp_dir._settings_file.write_text("{}")

    with pytest.raises(KeyError, match="Configuration key not found"):
        adapter_with_temp_dir.get_config("nonexistent")


def test_set_config(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test set_config updates configuration values."""
    adapter_with_temp_dir._settings_file.write_text('{"existing": "value"}')

    adapter_with_temp_dir.set_config("theme", "light")
    adapter_with_temp_dir.set_config("nested.key", "new_value")

    settings = json.loads(adapter_with_temp_dir._settings_file.read_text())
    assert settings["theme"] == "light"
    assert settings["nested"]["key"] == "new_value"
    assert settings["existing"] == "value"


def test_backup(adapter_with_temp_dir: ClaudeAdapter, tmp_path: Path) -> None:
    """Test backup creates tar.gz archive."""
    # Create some content
    adapter_with_temp_dir.initialize()
    (adapter_with_temp_dir._config_dir / "agents").mkdir(exist_ok=True)
    (adapter_with_temp_dir._config_dir / "agents" / "test.md").write_text("# Test")

    backup_dir = tmp_path / "backups"
    backup_file = adapter_with_temp_dir.backup(backup_dir)

    assert backup_file.exists()
    assert backup_file.suffix == ".gz"
    assert "claude_backup_" in backup_file.name

    # Verify archive contents
    with tarfile.open(backup_file, "r:gz") as tar:
        names = tar.getnames()
        assert "claude" in names
        assert "claude/settings.json" in names


def test_restore(adapter_with_temp_dir: ClaudeAdapter, tmp_path: Path) -> None:
    """Test restore extracts backup archive."""
    # Create a backup first
    adapter_with_temp_dir.initialize()
    (adapter_with_temp_dir._config_dir / "agents").mkdir(exist_ok=True)
    test_file = adapter_with_temp_dir._config_dir / "agents" / "test.md"
    test_file.write_text("# Original")

    backup_dir = tmp_path / "backups"
    backup_file = adapter_with_temp_dir.backup(backup_dir)

    # Modify the config
    test_file.write_text("# Modified")

    # Restore
    adapter_with_temp_dir.restore(backup_file)

    # Verify restoration
    assert test_file.read_text() == "# Original"


def test_restore_file_not_found(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test restore raises FileNotFoundError for missing backup."""
    with pytest.raises(FileNotFoundError, match="Backup file not found"):
        adapter_with_temp_dir.restore(Path("/nonexistent/backup.tar.gz"))


@patch("ai_asst_mgr.adapters.claude.git_clone")
def test_sync_from_git(
    mock_git_clone: Mock,
    adapter_with_temp_dir: ClaudeAdapter,
) -> None:
    """Test sync_from_git clones and copies files."""

    # Setup mock git clone to create temp repo
    def create_temp_repo(_url: str, _dest: object, _branch: str) -> bool:
        # Create the temp directory with the expected structure
        temp_dir = adapter_with_temp_dir._config_dir.parent / "temp_git_clone"
        temp_dir.mkdir(exist_ok=True)
        (temp_dir / "agents").mkdir()
        (temp_dir / "agents" / "synced.md").write_text("# Synced")
        (temp_dir / "settings.json").write_text('{"synced": true}')
        return True

    mock_git_clone.side_effect = create_temp_repo

    adapter_with_temp_dir.sync_from_git("https://github.com/test/repo.git")

    # Verify git_clone was called with correct arguments
    mock_git_clone.assert_called_once()
    call_args = mock_git_clone.call_args
    assert call_args[0][0] == "https://github.com/test/repo.git"  # URL
    assert call_args[0][1] == adapter_with_temp_dir._config_dir.parent / "temp_git_clone"  # Dest
    assert call_args[0][2] == "main"  # Branch


def test_health_check_healthy(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test health_check returns healthy status."""
    adapter_with_temp_dir.initialize()
    (adapter_with_temp_dir._config_dir / "agents" / "test.md").write_text("# Test")
    (adapter_with_temp_dir._config_dir / "skills" / "test.md").write_text("# Skill")

    result = adapter_with_temp_dir.health_check()

    assert result["healthy"] is True
    assert result["checks"]["installed"] is True
    assert result["checks"]["configured"] is True
    assert result["checks"]["valid_settings"] is True
    assert result["errors"] == []


def test_health_check_not_installed() -> None:
    """Test health_check with non-existent directory."""
    adapter = ClaudeAdapter()
    adapter._config_dir = Path("/nonexistent")

    result = adapter.health_check()

    assert result["healthy"] is False
    assert result["checks"]["installed"] is False
    assert "Claude Code directory not found" in result["errors"]


def test_audit_config(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test audit_config returns audit results."""
    adapter_with_temp_dir.initialize()

    result = adapter_with_temp_dir.audit_config()

    assert isinstance(result["score"], int)
    assert 0 <= result["score"] <= 100
    assert isinstance(result["issues"], list)
    assert isinstance(result["warnings"], list)
    assert isinstance(result["recommendations"], list)


def test_audit_config_malformed_json(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test audit_config detects malformed settings.json."""
    adapter_with_temp_dir._settings_file.write_text("invalid json")

    result = adapter_with_temp_dir.audit_config()

    assert result["score"] < 100
    assert any("malformed" in issue for issue in result["issues"])


def test_get_usage_stats(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test get_usage_stats returns statistics."""
    adapter_with_temp_dir.initialize()
    (adapter_with_temp_dir._config_dir / "agents" / "agent1.md").write_text("# A1")
    (adapter_with_temp_dir._config_dir / "agents" / "agent2.md").write_text("# A2")
    (adapter_with_temp_dir._config_dir / "skills" / "skill1.md").write_text("# S1")

    result = adapter_with_temp_dir.get_usage_stats()

    assert result["session_count"] == 0
    assert result["agent_count"] == 2
    assert result["skill_count"] == 1


def test_list_markdown_files(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test _list_markdown_files finds markdown files."""
    agents_dir = adapter_with_temp_dir._config_dir / "agents"
    agents_dir.mkdir()
    (agents_dir / "agent1.md").write_text("# Agent 1")
    (agents_dir / "agent2.md").write_text("# Agent 2")
    (agents_dir / "readme.txt").write_text("Not markdown")

    files = list(adapter_with_temp_dir._list_markdown_files(agents_dir))

    assert len(files) == 2
    assert all(f.suffix == ".md" for f in files)


def test_initialize_error(adapter_with_temp_dir: ClaudeAdapter, tmp_path: Path) -> None:
    """Test initialize raises RuntimeError on failure."""
    # Make parent directory read-only
    adapter_with_temp_dir._config_dir = tmp_path / "readonly" / ".claude"
    readonly_parent = tmp_path / "readonly"
    readonly_parent.mkdir()
    readonly_parent.chmod(0o444)

    try:
        with pytest.raises(RuntimeError, match="Failed to initialize"):
            adapter_with_temp_dir.initialize()
    finally:
        readonly_parent.chmod(0o755)


def test_set_config_creates_nested_keys(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test set_config creates nested dictionary keys."""
    adapter_with_temp_dir._settings_file.write_text("{}")

    adapter_with_temp_dir.set_config("deeply.nested.key", "value")

    settings = json.loads(adapter_with_temp_dir._settings_file.read_text())
    assert settings["deeply"]["nested"]["key"] == "value"


def test_backup_error(adapter_with_temp_dir: ClaudeAdapter, tmp_path: Path) -> None:
    """Test backup raises RuntimeError on failure."""
    adapter_with_temp_dir.initialize()

    # Try to backup to read-only directory
    backup_dir = tmp_path / "readonly_backup"
    backup_dir.mkdir()
    backup_dir.chmod(0o444)

    try:
        with pytest.raises(RuntimeError, match="Failed to create backup"):
            adapter_with_temp_dir.backup(backup_dir)
    finally:
        backup_dir.chmod(0o755)


def test_restore_error(adapter_with_temp_dir: ClaudeAdapter, tmp_path: Path) -> None:
    """Test restore raises RuntimeError on failure."""
    # Create an invalid backup file
    backup_file = tmp_path / "invalid_backup.tar.gz"
    backup_file.write_text("not a valid tar file")

    with pytest.raises(RuntimeError, match="Failed to restore backup"):
        adapter_with_temp_dir.restore(backup_file)


@patch("ai_asst_mgr.adapters.claude.git_clone")
def test_sync_from_git_error(
    mock_git_clone: Mock,
    adapter_with_temp_dir: ClaudeAdapter,
) -> None:
    """Test sync_from_git raises RuntimeError on git failure."""
    mock_git_clone.return_value = False

    with pytest.raises(RuntimeError, match="Failed to clone repository"):
        adapter_with_temp_dir.sync_from_git("https://github.com/test/repo.git")


def test_health_check_malformed_settings(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test health_check detects malformed settings.json."""
    adapter_with_temp_dir._settings_file.write_text("invalid json")
    (adapter_with_temp_dir._config_dir / "agents").mkdir()
    (adapter_with_temp_dir._config_dir / "skills").mkdir()

    result = adapter_with_temp_dir.health_check()

    assert result["healthy"] is False
    assert result["checks"]["valid_settings"] is False
    assert any("not valid JSON" in err for err in result["errors"])


def test_health_check_missing_agents_dir(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test health_check detects missing agents directory."""
    adapter_with_temp_dir.initialize()
    (adapter_with_temp_dir._config_dir / "agents").rmdir()

    result = adapter_with_temp_dir.health_check()

    assert result["healthy"] is False
    assert result["checks"]["has_agents_dir"] is False
    assert "agents/ directory not found" in result["errors"]


def test_health_check_missing_skills_dir(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test health_check detects missing skills directory."""
    adapter_with_temp_dir.initialize()
    (adapter_with_temp_dir._config_dir / "skills").rmdir()

    result = adapter_with_temp_dir.health_check()

    assert result["healthy"] is False
    assert result["checks"]["has_skills_dir"] is False
    assert "skills/ directory not found" in result["errors"]


def test_audit_config_permissive_permissions(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test audit_config detects overly permissive directory permissions."""
    adapter_with_temp_dir.initialize()
    adapter_with_temp_dir._config_dir.chmod(0o777)

    try:
        result = adapter_with_temp_dir.audit_config()

        assert result["score"] < 100
        assert any("permissive permissions" in issue for issue in result["issues"])
    finally:
        adapter_with_temp_dir._config_dir.chmod(0o755)


def test_audit_config_no_settings(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test audit_config handles missing settings.json."""
    result = adapter_with_temp_dir.audit_config()

    assert result["score"] < 100
    assert any("No settings.json found" in issue for issue in result["issues"])


def test_audit_config_sensitive_data_warning(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test audit_config warns about potential sensitive data."""
    settings = {"api_key": "secret123", "theme": "dark"}
    adapter_with_temp_dir._settings_file.write_text(json.dumps(settings))

    result = adapter_with_temp_dir.audit_config()

    assert len(result["warnings"]) > 0
    assert any("sensitive data" in warning.lower() for warning in result["warnings"])


def test_audit_config_missing_directories_recommendations(
    adapter_with_temp_dir: ClaudeAdapter,
) -> None:
    """Test audit_config provides recommendations for missing directories."""
    adapter_with_temp_dir._settings_file.write_text("{}")

    result = adapter_with_temp_dir.audit_config()

    assert len(result["recommendations"]) > 0


def test_get_usage_stats_not_installed() -> None:
    """Test get_usage_stats when Claude Code is not installed."""
    adapter = ClaudeAdapter()
    adapter._config_dir = Path("/nonexistent")

    result = adapter.get_usage_stats()

    assert result["session_count"] == 0
    assert "agent_count" not in result
    assert "skill_count" not in result


def test_load_settings_file_not_found(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test _load_settings raises FileNotFoundError when file missing."""
    with pytest.raises(FileNotFoundError, match="Settings file not found"):
        adapter_with_temp_dir._load_settings()


def test_list_markdown_files_nonexistent_directory(
    adapter_with_temp_dir: ClaudeAdapter,
) -> None:
    """Test _list_markdown_files handles nonexistent directory."""
    nonexistent_dir = adapter_with_temp_dir._config_dir / "nonexistent"
    files = list(adapter_with_temp_dir._list_markdown_files(nonexistent_dir))

    assert len(files) == 0


def test_health_check_empty_agents_dir(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test health_check with empty agents directory."""
    adapter_with_temp_dir.initialize()
    # Remove the markdown files
    agents_dir = adapter_with_temp_dir._config_dir / "agents"
    for f in agents_dir.glob("*.md"):
        f.unlink()

    result = adapter_with_temp_dir.health_check()

    assert "agent_count" in result["checks"]
    assert result["checks"]["agent_count"] is False


def test_health_check_empty_skills_dir(adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test health_check with empty skills directory."""
    adapter_with_temp_dir.initialize()
    # Remove the markdown files
    skills_dir = adapter_with_temp_dir._config_dir / "skills"
    for f in skills_dir.glob("*.md"):
        f.unlink()

    result = adapter_with_temp_dir.health_check()

    assert "skill_count" in result["checks"]
    assert result["checks"]["skill_count"] is False


def test_audit_config_not_installed() -> None:
    """Test audit_config when Claude Code is not installed."""
    adapter = ClaudeAdapter()
    adapter._config_dir = Path("/nonexistent")

    result = adapter.audit_config()

    # Should still return valid audit results
    assert isinstance(result["score"], int)
    assert isinstance(result["issues"], list)


def test_restore_missing_extracted_dir(
    adapter_with_temp_dir: ClaudeAdapter, tmp_path: Path
) -> None:
    """Test restore handles backup without expected directory structure."""
    # Create a backup without the expected 'claude' directory
    backup_file = tmp_path / "bad_backup.tar.gz"
    with tarfile.open(backup_file, "w:gz") as tar:
        # Add a file but not in 'claude' directory
        temp_file = tmp_path / "somefile.txt"
        temp_file.write_text("test")
        tar.add(temp_file, arcname="somefile.txt")

    # This should complete without error even though there's no claude directory
    adapter_with_temp_dir.restore(backup_file)


@patch("shutil.copytree")
@patch("ai_asst_mgr.adapters.claude.git_clone")
def test_sync_from_git_shutil_error(
    mock_git_clone: Mock,
    mock_copytree: Mock,
    adapter_with_temp_dir: ClaudeAdapter,
) -> None:
    """Test sync_from_git handles shutil errors."""

    # Mock git_clone to succeed and create temp directory
    def create_temp_repo(_url: str, dest: Path, _branch: str) -> bool:
        dest.mkdir(exist_ok=True)
        (dest / "agents").mkdir()
        return True

    mock_git_clone.side_effect = create_temp_repo
    mock_copytree.side_effect = shutil.Error("Copy failed")

    with pytest.raises(RuntimeError, match="Failed to sync from git"):
        adapter_with_temp_dir.sync_from_git("https://github.com/test/repo.git")


def test_audit_config_with_agents_and_skills_dirs(
    adapter_with_temp_dir: ClaudeAdapter,
) -> None:
    """Test audit_config recommendations when dirs exist."""
    # Set up config with proper structure
    adapter_with_temp_dir.initialize()

    result = adapter_with_temp_dir.audit_config()

    # Should not recommend creating directories that exist
    agent_recs = [r for r in result["recommendations"] if "agents" in r.lower()]
    skill_recs = [r for r in result["recommendations"] if "skills" in r.lower()]

    # If directories exist, there should be no recommendations about creating them
    agents_dir = adapter_with_temp_dir._config_dir / "agents"
    skills_dir = adapter_with_temp_dir._config_dir / "skills"

    if agents_dir.exists():
        assert len(agent_recs) == 0
    if skills_dir.exists():
        assert len(skill_recs) == 0


@patch("json.dump")
def test_save_settings_error(mock_dump: Mock, adapter_with_temp_dir: ClaudeAdapter) -> None:
    """Test _save_settings raises RuntimeError on write failure."""
    mock_dump.side_effect = OSError("Write failed")
    adapter_with_temp_dir._settings_file.touch()

    with pytest.raises(RuntimeError, match="Failed to save settings"):
        adapter_with_temp_dir._save_settings({"key": "value"})
