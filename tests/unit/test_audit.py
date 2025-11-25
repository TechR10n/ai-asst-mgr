"""Tests for the audit module."""

from __future__ import annotations

import json
import os
import stat
import tempfile
from pathlib import Path
from typing import TYPE_CHECKING
from unittest.mock import patch

from ai_asst_mgr.audit import (
    AuditCategory,
    AuditCheck,
    AuditReport,
    AuditSeverity,
    ClaudeAuditor,
    CodexAuditor,
    GeminiAuditor,
)

if TYPE_CHECKING:
    from ai_asst_mgr.audit.base import BaseAuditor

# Error messages for test exceptions
ERR_CANNOT_READ_FILE = "Cannot read file"
ERR_READ_ERROR = "Read error"
ERR_CANNOT_READ_SKILL = "Cannot read skill file"
ERR_CANNOT_READ = "Cannot read"
ERR_CANNOT_STAT = "Cannot stat file"
ERR_CANNOT_READ_ASSISTANT = "Cannot read assistant file"


class TestAuditSeverity:
    """Tests for AuditSeverity enum."""

    def test_severity_ordering_lt(self) -> None:
        """Test severity levels less than comparison."""
        assert AuditSeverity.INFO < AuditSeverity.WARNING
        assert AuditSeverity.WARNING < AuditSeverity.ERROR
        assert AuditSeverity.ERROR < AuditSeverity.CRITICAL

    def test_severity_ordering_ge(self) -> None:
        """Test severity levels greater than or equal comparison."""
        assert AuditSeverity.CRITICAL >= AuditSeverity.ERROR
        assert AuditSeverity.ERROR >= AuditSeverity.WARNING
        assert AuditSeverity.WARNING >= AuditSeverity.INFO
        assert AuditSeverity.ERROR >= AuditSeverity.ERROR

    def test_severity_lt_with_non_severity(self) -> None:
        """Test lt comparison with non-AuditSeverity returns NotImplemented."""
        result = AuditSeverity.INFO.__lt__("string")
        assert result is NotImplemented

    def test_severity_ge_with_non_severity(self) -> None:
        """Test ge comparison with non-AuditSeverity returns NotImplemented."""
        result = AuditSeverity.INFO.__ge__("string")
        assert result is NotImplemented

    def test_severity_values(self) -> None:
        """Test severity enum values."""
        assert AuditSeverity.INFO.value == "info"
        assert AuditSeverity.WARNING.value == "warning"
        assert AuditSeverity.ERROR.value == "error"
        assert AuditSeverity.CRITICAL.value == "critical"


class TestAuditCategory:
    """Tests for AuditCategory enum."""

    def test_category_values(self) -> None:
        """Test category enum values."""
        assert AuditCategory.SECURITY.value == "security"
        assert AuditCategory.CONFIG.value == "config"
        assert AuditCategory.QUALITY.value == "quality"
        assert AuditCategory.USAGE.value == "usage"


class TestAuditCheck:
    """Tests for AuditCheck dataclass."""

    def test_create_audit_check(self) -> None:
        """Test creating an AuditCheck."""
        check = AuditCheck(
            name="test_check",
            category=AuditCategory.SECURITY,
            severity=AuditSeverity.ERROR,
            passed=False,
            message="Test message",
            recommendation="Fix it",
            details={"key": "value"},
        )
        assert check.name == "test_check"
        assert check.category == AuditCategory.SECURITY
        assert check.severity == AuditSeverity.ERROR
        assert not check.passed
        assert check.message == "Test message"
        assert check.recommendation == "Fix it"
        assert check.details == {"key": "value"}

    def test_check_defaults(self) -> None:
        """Test AuditCheck default values."""
        check = AuditCheck(
            name="test",
            category=AuditCategory.CONFIG,
            severity=AuditSeverity.INFO,
            passed=True,
            message="OK",
        )
        assert check.recommendation is None
        assert check.details == {}


class TestAuditReport:
    """Tests for AuditReport dataclass."""

    def test_empty_report(self) -> None:
        """Test empty report properties."""
        report = AuditReport(vendor_id="test", timestamp="2024-01-01T00:00:00Z")
        assert report.total_checks == 0
        assert report.passed_checks == 0
        assert report.failed_checks == 0
        assert report.score == 100.0

    def test_report_with_checks(self) -> None:
        """Test report with checks calculates correctly."""
        checks = [
            AuditCheck(
                name="pass1",
                category=AuditCategory.SECURITY,
                severity=AuditSeverity.INFO,
                passed=True,
                message="OK",
            ),
            AuditCheck(
                name="fail1",
                category=AuditCategory.CONFIG,
                severity=AuditSeverity.ERROR,
                passed=False,
                message="Failed",
            ),
        ]
        report = AuditReport(
            vendor_id="test",
            timestamp="2024-01-01T00:00:00Z",
            checks=checks,
        )
        assert report.total_checks == 2
        assert report.passed_checks == 1
        assert report.failed_checks == 1
        assert report.score == 50.0

    def test_severity_counts(self) -> None:
        """Test severity count calculations."""
        checks = [
            AuditCheck(
                name="critical",
                category=AuditCategory.SECURITY,
                severity=AuditSeverity.CRITICAL,
                passed=False,
                message="Critical",
            ),
            AuditCheck(
                name="error",
                category=AuditCategory.CONFIG,
                severity=AuditSeverity.ERROR,
                passed=False,
                message="Error",
            ),
            AuditCheck(
                name="warning",
                category=AuditCategory.QUALITY,
                severity=AuditSeverity.WARNING,
                passed=False,
                message="Warning",
            ),
            AuditCheck(
                name="info_fail",
                category=AuditCategory.USAGE,
                severity=AuditSeverity.INFO,
                passed=False,
                message="Info fail",
            ),
            AuditCheck(
                name="pass",
                category=AuditCategory.USAGE,
                severity=AuditSeverity.INFO,
                passed=True,
                message="OK",
            ),
        ]
        report = AuditReport(
            vendor_id="test",
            timestamp="2024-01-01T00:00:00Z",
            checks=checks,
        )
        assert report.critical_count == 1
        assert report.error_count == 1
        assert report.warning_count == 1
        assert report.info_count == 1

    def test_filter_by_severity(self) -> None:
        """Test filtering checks by severity."""
        checks = [
            AuditCheck(
                name="info",
                category=AuditCategory.CONFIG,
                severity=AuditSeverity.INFO,
                passed=False,
                message="Info",
            ),
            AuditCheck(
                name="error",
                category=AuditCategory.CONFIG,
                severity=AuditSeverity.ERROR,
                passed=False,
                message="Error",
            ),
        ]
        report = AuditReport(
            vendor_id="test",
            timestamp="2024-01-01T00:00:00Z",
            checks=checks,
        )
        filtered = report.filter_by_severity(AuditSeverity.ERROR)
        assert len(filtered) == 1
        assert filtered[0].name == "error"

    def test_filter_by_category(self) -> None:
        """Test filtering checks by category."""
        checks = [
            AuditCheck(
                name="security",
                category=AuditCategory.SECURITY,
                severity=AuditSeverity.ERROR,
                passed=False,
                message="Security",
            ),
            AuditCheck(
                name="config",
                category=AuditCategory.CONFIG,
                severity=AuditSeverity.ERROR,
                passed=True,
                message="Config",
            ),
        ]
        report = AuditReport(
            vendor_id="test",
            timestamp="2024-01-01T00:00:00Z",
            checks=checks,
        )
        filtered = report.filter_by_category(AuditCategory.SECURITY)
        assert len(filtered) == 1
        assert filtered[0].name == "security"

    def test_to_dict(self) -> None:
        """Test report to dictionary conversion."""
        check = AuditCheck(
            name="test",
            category=AuditCategory.CONFIG,
            severity=AuditSeverity.INFO,
            passed=True,
            message="OK",
        )
        report = AuditReport(
            vendor_id="test",
            timestamp="2024-01-01T00:00:00Z",
            checks=[check],
        )
        data = report.to_dict()
        assert data["vendor_id"] == "test"
        assert data["timestamp"] == "2024-01-01T00:00:00Z"
        assert data["summary"]["total_checks"] == 1
        assert len(data["checks"]) == 1

    def test_to_json(self) -> None:
        """Test report to JSON conversion."""
        report = AuditReport(vendor_id="test", timestamp="2024-01-01T00:00:00Z")
        json_str = report.to_json()
        data = json.loads(json_str)
        assert data["vendor_id"] == "test"


class TestClaudeAuditor:
    """Tests for ClaudeAuditor."""

    def test_audit_missing_config_dir(self) -> None:
        """Test audit with missing config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "nonexistent"
            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            assert report.failed_checks > 0
            security_checks = report.filter_by_category(AuditCategory.SECURITY)
            assert len(security_checks) > 0

    def test_audit_empty_config_dir(self) -> None:
        """Test audit with empty config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            assert report.total_checks > 0

    def test_audit_with_settings_file(self) -> None:
        """Test audit with settings.json file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            settings_file = config_dir / "settings.json"
            settings_file.write_text('{"theme": "dark"}')

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            config_checks = [c for c in report.checks if c.category == AuditCategory.CONFIG]
            passed = [c for c in config_checks if c.passed]
            assert len(passed) > 0

    def test_audit_invalid_json(self) -> None:
        """Test audit with invalid JSON."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            settings_file = config_dir / "settings.json"
            settings_file.write_text("invalid json{")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            assert report.failed_checks > 0

    def test_audit_api_key_detection_openai(self) -> None:
        """Test OpenAI API key detection in settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            settings_file = config_dir / "settings.json"
            settings_file.write_text('{"key": "sk-12345678901234567890"}')

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            security_checks = [
                c for c in report.checks if c.category == AuditCategory.SECURITY and not c.passed
            ]
            assert len(security_checks) > 0

    def test_audit_api_key_detection_google(self) -> None:
        """Test Google API key detection in settings."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            settings_file = config_dir / "settings.json"
            settings_file.write_text('{"key": "AIzaSyC12345678901234567890"}')

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            security_checks = [
                c for c in report.checks if c.category == AuditCategory.SECURITY and not c.passed
            ]
            assert len(security_checks) > 0

    def test_audit_world_writable_permissions(self) -> None:
        """Test detection of world-writable config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            # Make world-writable
            config_dir.chmod(stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            # Restore permissions for cleanup
            config_dir.chmod(stat.S_IRWXU)

            critical_checks = [
                c for c in report.checks if c.severity == AuditSeverity.CRITICAL and not c.passed
            ]
            assert len(critical_checks) > 0

    def test_audit_world_readable_permissions(self) -> None:
        """Test detection of world-readable config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            # Make world-readable but not writable
            config_dir.chmod(stat.S_IRWXU | stat.S_IROTH)

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            # Restore permissions for cleanup
            config_dir.chmod(stat.S_IRWXU)

            warning_checks = [
                c
                for c in report.checks
                if c.severity == AuditSeverity.WARNING
                and not c.passed
                and "readable" in c.message.lower()
            ]
            assert len(warning_checks) > 0

    def test_audit_permission_check_oserror(self) -> None:
        """Test handling OSError during permission check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            auditor = ClaudeAuditor(config_dir)

            with patch.object(Path, "stat", side_effect=OSError("Permission denied")):
                report = auditor.run_audit()

            error_checks = [
                c
                for c in report.checks
                if c.severity == AuditSeverity.ERROR and "permission" in c.name.lower()
            ]
            assert len(error_checks) > 0

    def test_audit_sensitive_files_credentials(self) -> None:
        """Test detection of credentials.json file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            (config_dir / "credentials.json").write_text("{}")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            sensitive_checks = [
                c for c in report.checks if "sensitive" in c.name.lower() and not c.passed
            ]
            assert len(sensitive_checks) > 0

    def test_audit_sensitive_files_secrets(self) -> None:
        """Test detection of secrets.json file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            (config_dir / "secrets.json").write_text("{}")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            sensitive_checks = [
                c for c in report.checks if "sensitive" in c.name.lower() and not c.passed
            ]
            assert len(sensitive_checks) > 0

    def test_audit_sensitive_files_env(self) -> None:
        """Test detection of .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            (config_dir / ".env").write_text("KEY=value")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            sensitive_checks = [
                c for c in report.checks if "sensitive" in c.name.lower() and not c.passed
            ]
            assert len(sensitive_checks) > 0

    def test_audit_settings_file_read_error(self) -> None:
        """Test handling of settings file read error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            settings_file = config_dir / "settings.json"
            settings_file.write_text('{"valid": "json"}')

            auditor = ClaudeAuditor(config_dir)

            # Mock read_text to raise OSError
            original_read = Path.read_text

            def mock_read(self: Path, *args: object, **kwargs: object) -> str:
                if self.name == "settings.json":
                    raise OSError(ERR_CANNOT_READ_FILE)
                return original_read(self, *args, **kwargs)

            with patch.object(Path, "read_text", mock_read):
                report = auditor.run_audit()

            error_checks = [
                c
                for c in report.checks
                if c.severity == AuditSeverity.ERROR and "settings" in c.name.lower()
            ]
            assert len(error_checks) > 0

    def test_audit_commands_directory(self) -> None:
        """Test audit with commands directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            commands_dir = config_dir / "commands"
            commands_dir.mkdir()
            (commands_dir / "test.md").write_text("# Test command")
            (commands_dir / "other.md").write_text("# Other command")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            cmd_checks = [c for c in report.checks if "commands" in c.name.lower()]
            assert len(cmd_checks) > 0
            assert any("2" in c.message for c in cmd_checks)

    def test_audit_agents_yaml_valid(self) -> None:
        """Test audit with valid agent YAML frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            agents_dir = config_dir / "agents"
            agents_dir.mkdir()
            (agents_dir / "test.md").write_text("---\nname: test\n---\nContent here")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            yaml_checks = [c for c in report.checks if "yaml" in c.name.lower() and c.passed]
            assert len(yaml_checks) > 0

    def test_audit_agents_yaml_invalid(self) -> None:
        """Test audit with invalid agent YAML frontmatter."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            agents_dir = config_dir / "agents"
            agents_dir.mkdir()
            # Missing closing ---
            (agents_dir / "test.md").write_text("---\nname: test\nContent here")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            yaml_checks = [c for c in report.checks if "yaml" in c.name.lower() and not c.passed]
            assert len(yaml_checks) > 0

    def test_audit_agent_descriptions_short(self) -> None:
        """Test audit with short agent descriptions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            agents_dir = config_dir / "agents"
            agents_dir.mkdir()
            (agents_dir / "test.md").write_text("---\nname: test\n---\nHi")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            desc_checks = [
                c for c in report.checks if "description" in c.name.lower() and not c.passed
            ]
            assert len(desc_checks) > 0

    def test_audit_agent_descriptions_adequate(self) -> None:
        """Test audit with adequate agent descriptions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            agents_dir = config_dir / "agents"
            agents_dir.mkdir()
            long_desc = "This is a long description that is more than 20 characters"
            (agents_dir / "test.md").write_text(f"---\nname: test\n---\n{long_desc}")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            desc_checks = [c for c in report.checks if "description" in c.name.lower() and c.passed]
            assert len(desc_checks) > 0

    def test_audit_skills_empty(self) -> None:
        """Test audit with empty skills."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            skills_dir = config_dir / "skills"
            skills_dir.mkdir()
            (skills_dir / "test.md").write_text("Hi")  # Too short

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            skill_checks = [c for c in report.checks if "skill" in c.name.lower() and not c.passed]
            assert len(skill_checks) > 0

    def test_audit_skills_complete(self) -> None:
        """Test audit with complete skills."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            skills_dir = config_dir / "skills"
            skills_dir.mkdir()
            (skills_dir / "test.md").write_text("This is a complete skill with enough content")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            skill_checks = [c for c in report.checks if "skill" in c.name.lower() and c.passed]
            assert len(skill_checks) > 0

    def test_audit_duplicate_agents(self) -> None:
        """Test audit duplicate check runs (case sensitivity depends on filesystem)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            agents_dir = config_dir / "agents"
            agents_dir.mkdir()
            # Create files - on case-insensitive fs only one will exist
            (agents_dir / "Test.md").write_text("Content")
            (agents_dir / "test.md").write_text("Different content")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            # Find the duplicate check - it should exist regardless of outcome
            dup_checks = [c for c in report.checks if "duplicate" in c.name.lower()]
            # On case-insensitive fs (macOS), only one file exists -> passes
            # On case-sensitive fs (Linux), both exist with same stem -> fails
            assert len(dup_checks) > 0

    def test_audit_no_duplicate_agents(self) -> None:
        """Test audit with unique agent names."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            agents_dir = config_dir / "agents"
            agents_dir.mkdir()
            (agents_dir / "agent1.md").write_text("Content")
            (agents_dir / "agent2.md").write_text("Content")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            dup_checks = [c for c in report.checks if "duplicate" in c.name.lower() and c.passed]
            assert len(dup_checks) > 0

    def test_audit_unused_agents(self) -> None:
        """Test audit reports agent count."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            agents_dir = config_dir / "agents"
            agents_dir.mkdir()
            (agents_dir / "agent1.md").write_text("Content")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            usage_checks = [c for c in report.checks if "agent_usage" in c.name]
            assert len(usage_checks) > 0

    def test_audit_mcp_servers_valid(self) -> None:
        """Test audit with valid MCP servers config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            mcp_file = config_dir / "mcp_servers.json"
            mcp_file.write_text('{"server1": {}, "server2": {}}')

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            mcp_checks = [c for c in report.checks if "mcp" in c.name.lower() and c.passed]
            assert len(mcp_checks) > 0

    def test_audit_mcp_servers_invalid_json(self) -> None:
        """Test audit with invalid MCP servers config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            mcp_file = config_dir / "mcp_servers.json"
            mcp_file.write_text("invalid json{")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            mcp_checks = [c for c in report.checks if "mcp" in c.name.lower() and not c.passed]
            assert len(mcp_checks) > 0

    def test_audit_agent_yaml_read_error(self) -> None:
        """Test audit handles OSError when reading agent files for YAML check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            agents_dir = config_dir / "agents"
            agents_dir.mkdir()
            agent_file = agents_dir / "test.md"
            agent_file.write_text("---\nname: test\n---\nContent")

            auditor = ClaudeAuditor(config_dir)

            # Mock read_text to raise OSError
            with patch.object(Path, "read_text", side_effect=OSError("Permission denied")):
                report = auditor.run_audit()

            # Should handle error gracefully and count as invalid
            yaml_checks = [c for c in report.checks if "yaml" in c.name.lower()]
            assert len(yaml_checks) > 0

    def test_audit_agent_description_read_error(self) -> None:
        """Test audit handles OSError when reading agent files for description check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            agents_dir = config_dir / "agents"
            agents_dir.mkdir()
            agent_file = agents_dir / "test.md"
            agent_file.write_text("Long enough description for the agent")

            auditor = ClaudeAuditor(config_dir)

            # Patch at method level to only affect _check_agent_descriptions
            original_read = Path.read_text
            call_count = [0]

            def mock_read_text(self: Path, *args: object, **kwargs: object) -> str:
                # Only raise on specific call patterns
                call_count[0] += 1
                if "agents" in str(self) and call_count[0] > 3:
                    raise OSError(ERR_READ_ERROR)
                return original_read(self, *args, **kwargs)

            with patch.object(Path, "read_text", mock_read_text):
                report = auditor.run_audit()

            # Check should still complete
            assert report.total_checks > 0

    def test_audit_skill_read_error(self) -> None:
        """Test audit handles OSError when reading skill files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            skills_dir = config_dir / "skills"
            skills_dir.mkdir()
            skill_file = skills_dir / "test.md"
            skill_file.write_text("Content")

            auditor = ClaudeAuditor(config_dir)

            original_read = Path.read_text
            read_count = [0]

            def mock_skill_read(self: Path, *args: object, **kwargs: object) -> str:
                read_count[0] += 1
                if "skills" in str(self) and self.suffix == ".md" and read_count[0] > 5:
                    raise OSError(ERR_CANNOT_READ_SKILL)
                return original_read(self, *args, **kwargs)

            with patch.object(Path, "read_text", mock_skill_read):
                report = auditor.run_audit()

            # Check should complete and count unreadable file as empty
            skill_checks = [c for c in report.checks if "skill" in c.name.lower()]
            assert len(skill_checks) > 0

    def test_audit_empty_agents_dir(self) -> None:
        """Test audit with empty agents directory (no md files)."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            agents_dir = config_dir / "agents"
            agents_dir.mkdir()
            # Create a non-md file so directory is not truly empty
            (agents_dir / "readme.txt").write_text("Some text")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            # Should not produce agent_usage check since no .md files
            agent_usage = [c for c in report.checks if c.name == "agent_usage"]
            assert len(agent_usage) == 0

    def test_audit_skill_read_error_direct(self) -> None:
        """Test audit handles OSError when reading skill files directly."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            skills_dir = config_dir / "skills"
            skills_dir.mkdir()
            skill_file = skills_dir / "test.md"
            skill_file.write_text("Content")

            # Make file unreadable (Unix-only)
            skill_file.chmod(0o000)

            try:
                auditor = ClaudeAuditor(config_dir)
                report = auditor.run_audit()

                # Should count unreadable file as empty skill
                skill_checks = [
                    c for c in report.checks if "skill" in c.name.lower() and not c.passed
                ]
                assert len(skill_checks) > 0
            finally:
                # Restore permissions for cleanup
                skill_file.chmod(0o644)


class TestGeminiAuditor:
    """Tests for GeminiAuditor."""

    def test_audit_missing_config_dir(self) -> None:
        """Test audit with missing config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "nonexistent"
            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            assert report.failed_checks > 0

    def test_audit_with_gemini_md(self) -> None:
        """Test audit with GEMINI.md file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            gemini_md = config_dir / "GEMINI.md"
            gemini_md.write_text("# Instructions\n" * 20)

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            quality_checks = [c for c in report.checks if c.category == AuditCategory.QUALITY]
            passed = [c for c in quality_checks if c.passed]
            assert len(passed) > 0

    def test_audit_short_gemini_md(self) -> None:
        """Test audit with short GEMINI.md file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            gemini_md = config_dir / "GEMINI.md"
            gemini_md.write_text("Hi")

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            quality_checks = [
                c for c in report.checks if c.category == AuditCategory.QUALITY and not c.passed
            ]
            assert len(quality_checks) > 0

    def test_audit_world_writable_permissions(self) -> None:
        """Test detection of world-writable config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_dir.chmod(stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            config_dir.chmod(stat.S_IRWXU)

            critical_checks = [
                c for c in report.checks if c.severity == AuditSeverity.CRITICAL and not c.passed
            ]
            assert len(critical_checks) > 0

    def test_audit_permission_check_oserror(self) -> None:
        """Test handling OSError during permission check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            auditor = GeminiAuditor(config_dir)

            with patch.object(Path, "stat", side_effect=OSError("Permission denied")):
                report = auditor.run_audit()

            error_checks = [
                c
                for c in report.checks
                if c.severity == AuditSeverity.ERROR and "permission" in c.name.lower()
            ]
            assert len(error_checks) > 0

    def test_audit_api_key_in_config(self) -> None:
        """Test Google API key detection in config files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            settings_file = config_dir / "settings.json"
            settings_file.write_text('{"key": "AIzaSyC12345678901234567890"}')

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            critical_checks = [
                c for c in report.checks if c.severity == AuditSeverity.CRITICAL and not c.passed
            ]
            assert len(critical_checks) > 0

    def test_audit_api_key_in_gemini_md(self) -> None:
        """Test Google API key detection in GEMINI.md."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            gemini_md = config_dir / "GEMINI.md"
            gemini_md.write_text("My key is AIzaSyC12345678901234567890")

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            critical_checks = [
                c for c in report.checks if c.severity == AuditSeverity.CRITICAL and not c.passed
            ]
            assert len(critical_checks) > 0

    def test_audit_no_gemini_md(self) -> None:
        """Test audit without GEMINI.md file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            md_checks = [c for c in report.checks if "gemini_md_exists" in c.name]
            assert len(md_checks) > 0
            assert md_checks[0].passed

    def test_audit_settings_invalid_json(self) -> None:
        """Test audit with invalid settings.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            settings_file = config_dir / "settings.json"
            settings_file.write_text("invalid{")

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            error_checks = [
                c
                for c in report.checks
                if c.severity == AuditSeverity.ERROR and "settings" in c.name
            ]
            assert len(error_checks) > 0

    def test_audit_mcp_config_valid(self) -> None:
        """Test audit with valid mcp.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            mcp_file = config_dir / "mcp.json"
            mcp_file.write_text('{"servers": [{"name": "test"}]}')

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            mcp_checks = [c for c in report.checks if "mcp_config" in c.name and c.passed]
            assert len(mcp_checks) > 0

    def test_audit_mcp_config_invalid(self) -> None:
        """Test audit with invalid mcp.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            mcp_file = config_dir / "mcp.json"
            mcp_file.write_text("invalid{")

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            mcp_checks = [c for c in report.checks if "mcp_config" in c.name and not c.passed]
            assert len(mcp_checks) > 0

    def test_audit_gemini_md_read_error(self) -> None:
        """Test handling of GEMINI.md read error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            gemini_md = config_dir / "GEMINI.md"
            gemini_md.write_text("Content that is long enough to pass length check")

            auditor = GeminiAuditor(config_dir)

            original_read = Path.read_text

            def mock_read(self: Path, *args: object, **kwargs: object) -> str:
                if self.name == "GEMINI.md" and "_check_gemini_md_quality" in str(self):
                    raise OSError(ERR_CANNOT_READ)
                return original_read(self, *args, **kwargs)

            # Instead of mocking, create unreadable file
            gemini_md.write_text("x" * 100)
            gemini_md.chmod(0o000)

            try:
                report = auditor.run_audit()
            finally:
                gemini_md.chmod(0o644)

            # The file was unreadable, so quality check should fail
            quality_checks = [
                c for c in report.checks if "gemini_md_quality" in c.name and not c.passed
            ]
            assert len(quality_checks) > 0

    def test_audit_high_import_count(self) -> None:
        """Test detection of high import count in GEMINI.md."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            gemini_md = config_dir / "GEMINI.md"
            # Create content with more than 10 @ symbols
            gemini_md.write_text(
                "@file1 @file2 @file3 @file4 @file5 @file6 "
                "@file7 @file8 @file9 @file10 @file11 @file12"
            )

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            import_checks = [c for c in report.checks if "import_chain" in c.name and not c.passed]
            assert len(import_checks) > 0

    def test_audit_reasonable_import_count(self) -> None:
        """Test reasonable import count in GEMINI.md."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            gemini_md = config_dir / "GEMINI.md"
            gemini_md.write_text("@file1 @file2 @file3 plus other content to meet length")

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            import_checks = [c for c in report.checks if "import_chain" in c.name and c.passed]
            assert len(import_checks) > 0

    def test_audit_large_context_files(self) -> None:
        """Test detection of large context files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            large_file = config_dir / "large.md"
            # Create file > 100KB
            large_file.write_text("x" * (101 * 1024))

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            size_checks = [
                c for c in report.checks if "context_file_sizes" in c.name and not c.passed
            ]
            assert len(size_checks) > 0

    def test_audit_reasonable_context_files(self) -> None:
        """Test reasonable context file sizes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            small_file = config_dir / "small.md"
            small_file.write_text("Small content")

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            size_checks = [c for c in report.checks if "context_file_sizes" in c.name and c.passed]
            assert len(size_checks) > 0

    def test_audit_circular_imports(self) -> None:
        """Test circular imports check completes."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            auditor = GeminiAuditor(config_dir)
            report = auditor.run_audit()

            circular_checks = [c for c in report.checks if "circular" in c.name]
            assert len(circular_checks) > 0

    def test_audit_context_file_stat_error(self) -> None:
        """Test audit handles OSError when stat-ing context files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            md_file = config_dir / "test.md"
            md_file.write_text("Some content")

            auditor = GeminiAuditor(config_dir)

            original_stat = Path.stat

            def mock_stat(self: Path, *args: object, **kwargs: object) -> os.stat_result:
                if str(self).endswith(".md"):
                    raise OSError(ERR_CANNOT_STAT)
                return original_stat(self, *args, **kwargs)

            with patch.object(Path, "stat", mock_stat):
                report = auditor.run_audit()

            # Should handle error gracefully
            size_checks = [c for c in report.checks if "context_file_sizes" in c.name]
            assert len(size_checks) > 0


class TestCodexAuditor:
    """Tests for CodexAuditor."""

    def test_audit_missing_config_dir(self) -> None:
        """Test audit with missing config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir) / "nonexistent"
            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            assert report.failed_checks > 0

    def test_audit_with_config_file(self) -> None:
        """Test audit with config.json file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            config_file.write_text('{"model": "gpt-4"}')

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            config_checks = [c for c in report.checks if c.category == AuditCategory.CONFIG]
            passed = [c for c in config_checks if c.passed]
            assert len(passed) > 0

    def test_audit_api_key_in_config(self) -> None:
        """Test API key detection in config."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            config_file.write_text('{"api_key": "sk-12345678901234567890"}')

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            security_checks = [
                c for c in report.checks if c.category == AuditCategory.SECURITY and not c.passed
            ]
            assert len(security_checks) > 0

    def test_audit_world_writable_permissions(self) -> None:
        """Test detection of world-writable config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_dir.chmod(stat.S_IRWXU | stat.S_IRWXG | stat.S_IRWXO)

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            config_dir.chmod(stat.S_IRWXU)

            critical_checks = [
                c for c in report.checks if c.severity == AuditSeverity.CRITICAL and not c.passed
            ]
            assert len(critical_checks) > 0

    def test_audit_world_readable_permissions(self) -> None:
        """Test detection of world-readable config directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_dir.chmod(stat.S_IRWXU | stat.S_IROTH)

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            config_dir.chmod(stat.S_IRWXU)

            warning_checks = [
                c
                for c in report.checks
                if c.severity == AuditSeverity.WARNING
                and not c.passed
                and "readable" in c.message.lower()
            ]
            assert len(warning_checks) > 0

    def test_audit_permission_check_oserror(self) -> None:
        """Test handling OSError during permission check."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            auditor = CodexAuditor(config_dir)

            with patch.object(Path, "stat", side_effect=OSError("Permission denied")):
                report = auditor.run_audit()

            error_checks = [
                c
                for c in report.checks
                if c.severity == AuditSeverity.ERROR and "permission" in c.name.lower()
            ]
            assert len(error_checks) > 0

    def test_audit_env_file_exists(self) -> None:
        """Test detection of .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            (config_dir / ".env").write_text("KEY=value")

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            env_checks = [c for c in report.checks if "env" in c.name.lower() and not c.passed]
            assert len(env_checks) > 0

    def test_audit_no_env_file(self) -> None:
        """Test audit without .env file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            env_checks = [c for c in report.checks if "env" in c.name.lower() and c.passed]
            assert len(env_checks) > 0

    def test_audit_config_invalid_json(self) -> None:
        """Test audit with invalid config.json."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            config_file.write_text("invalid{")

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            error_checks = [
                c
                for c in report.checks
                if c.severity == AuditSeverity.ERROR and "config_file" in c.name
            ]
            assert len(error_checks) > 0

    def test_audit_config_read_error(self) -> None:
        """Test handling of config.json read error."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            config_file.write_text('{"valid": "json"}')
            config_file.chmod(0o000)

            try:
                auditor = CodexAuditor(config_dir)
                report = auditor.run_audit()
            finally:
                config_file.chmod(0o644)

            error_checks = [
                c
                for c in report.checks
                if c.severity == AuditSeverity.ERROR and "config_file" in c.name
            ]
            assert len(error_checks) > 0

    def test_audit_assistants_directory(self) -> None:
        """Test audit with assistants directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            assistants_dir = config_dir / "assistants"
            assistants_dir.mkdir()
            (assistants_dir / "helper.json").write_text(
                '{"name": "helper", "instructions": "Help with coding tasks please"}'
            )

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            config_checks = [c for c in report.checks if "assistant" in c.name.lower()]
            assert any(c.passed for c in config_checks)

    def test_audit_functions_valid(self) -> None:
        """Test audit with valid function definitions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            functions_dir = config_dir / "functions"
            functions_dir.mkdir()
            (functions_dir / "func.json").write_text(
                '{"name": "test_func", "description": "A test function"}'
            )

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            func_checks = [
                c for c in report.checks if "function_definitions" in c.name and c.passed
            ]
            assert len(func_checks) > 0

    def test_audit_functions_invalid(self) -> None:
        """Test audit with invalid function definitions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            functions_dir = config_dir / "functions"
            functions_dir.mkdir()
            (functions_dir / "func.json").write_text('{"invalid": "no name field"}')

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            func_checks = [
                c for c in report.checks if "function_definitions" in c.name and not c.passed
            ]
            assert len(func_checks) > 0

    def test_audit_functions_invalid_json(self) -> None:
        """Test audit with invalid JSON in function file."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            functions_dir = config_dir / "functions"
            functions_dir.mkdir()
            (functions_dir / "func.json").write_text("invalid{")

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            func_checks = [
                c for c in report.checks if "function_definitions" in c.name and not c.passed
            ]
            assert len(func_checks) > 0

    def test_audit_assistant_short_instructions(self) -> None:
        """Test audit with short assistant instructions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            assistants_dir = config_dir / "assistants"
            assistants_dir.mkdir()
            (assistants_dir / "helper.json").write_text('{"name": "helper", "instructions": "Hi"}')

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            inst_checks = [
                c for c in report.checks if "instructions" in c.name.lower() and not c.passed
            ]
            assert len(inst_checks) > 0

    def test_audit_assistant_adequate_instructions(self) -> None:
        """Test audit with adequate assistant instructions."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            assistants_dir = config_dir / "assistants"
            assistants_dir.mkdir()
            (assistants_dir / "helper.json").write_text(
                '{"name": "helper", "instructions": "Help with coding tasks and debugging"}'
            )

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            inst_checks = [
                c for c in report.checks if "instructions" in c.name.lower() and c.passed
            ]
            assert len(inst_checks) > 0

    def test_audit_function_missing_description(self) -> None:
        """Test audit with function missing description."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            functions_dir = config_dir / "functions"
            functions_dir.mkdir()
            (functions_dir / "func.json").write_text('{"name": "test"}')

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            schema_checks = [
                c for c in report.checks if "function_schema" in c.name and not c.passed
            ]
            assert len(schema_checks) > 0

    def test_audit_function_with_description(self) -> None:
        """Test audit with function including description."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            functions_dir = config_dir / "functions"
            functions_dir.mkdir()
            (functions_dir / "func.json").write_text(
                '{"name": "test", "description": "A useful function"}'
            )

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            schema_checks = [c for c in report.checks if "function_schema" in c.name and c.passed]
            assert len(schema_checks) > 0

    def test_audit_deprecated_model(self) -> None:
        """Test detection of deprecated model."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            config_file.write_text('{"model": "gpt-3.5-turbo-0301"}')

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            model_checks = [c for c in report.checks if "model" in c.name.lower() and not c.passed]
            assert len(model_checks) > 0

    def test_audit_current_model(self) -> None:
        """Test with current model."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            config_file.write_text('{"model": "gpt-4-turbo"}')

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            model_checks = [c for c in report.checks if "model_configured" in c.name and c.passed]
            assert len(model_checks) > 0

    def test_audit_rate_limit_configured(self) -> None:
        """Test with rate limit configured."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            config_file = config_dir / "config.json"
            config_file.write_text('{"rate_limit": 100}')

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            rate_checks = [c for c in report.checks if "rate_limit" in c.name and c.passed]
            assert len(rate_checks) > 0

    def test_audit_no_rate_limit(self) -> None:
        """Test without rate limit configuration."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            rate_checks = [c for c in report.checks if "rate_limit" in c.name and c.passed]
            assert len(rate_checks) > 0

    def test_audit_token_usage_tracking(self) -> None:
        """Test with token usage tracking enabled."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            (config_dir / "usage.json").write_text('{"tokens": 1000}')

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            usage_checks = [c for c in report.checks if "token_usage" in c.name and c.passed]
            assert len(usage_checks) > 0

    def test_audit_no_token_usage_tracking(self) -> None:
        """Test without token usage tracking."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            auditor = CodexAuditor(config_dir)
            report = auditor.run_audit()

            usage_checks = [c for c in report.checks if "token_usage" in c.name and c.passed]
            assert len(usage_checks) > 0

    def test_audit_assistant_instructions_read_error(self) -> None:
        """Test audit handles OSError when reading assistant instruction files."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)
            assistants_dir = config_dir / "assistants"
            assistants_dir.mkdir()
            (assistants_dir / "helper.json").write_text(
                '{"name": "helper", "instructions": "Help"}'
            )

            auditor = CodexAuditor(config_dir)

            original_read = Path.read_text
            read_count = [0]

            def mock_read(self: Path, *args: object, **kwargs: object) -> str:
                read_count[0] += 1
                # Raise OSError on later reads (after initial config reads)
                if "assistants" in str(self) and read_count[0] > 5:
                    raise OSError(ERR_CANNOT_READ_ASSISTANT)
                return original_read(self, *args, **kwargs)

            with patch.object(Path, "read_text", mock_read):
                report = auditor.run_audit()

            # Should handle error gracefully
            assert report.total_checks > 0


class TestAuditorIntegration:
    """Integration tests for auditors."""

    def test_all_auditors_produce_reports(self) -> None:
        """Test all auditors produce valid reports."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            auditors: list[BaseAuditor] = [
                ClaudeAuditor(config_dir),
                GeminiAuditor(config_dir),
                CodexAuditor(config_dir),
            ]

            for auditor in auditors:
                report = auditor.run_audit()
                assert report.vendor_id in ["claude", "gemini", "openai"]
                assert report.timestamp
                assert isinstance(report.checks, list)

    def test_report_json_serializable(self) -> None:
        """Test all audit reports are JSON serializable."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            auditors: list[BaseAuditor] = [
                ClaudeAuditor(config_dir),
                GeminiAuditor(config_dir),
                CodexAuditor(config_dir),
            ]

            for auditor in auditors:
                report = auditor.run_audit()
                json_str = report.to_json()
                data = json.loads(json_str)
                assert "vendor_id" in data
                assert "checks" in data

    def test_comprehensive_audit_scenario(self) -> None:
        """Test a comprehensive audit scenario with various configurations."""
        with tempfile.TemporaryDirectory() as temp_dir:
            config_dir = Path(temp_dir)

            # Create various files
            (config_dir / "settings.json").write_text('{"theme": "dark"}')
            commands_dir = config_dir / "commands"
            commands_dir.mkdir()
            (commands_dir / "test.md").write_text("# Test")

            agents_dir = config_dir / "agents"
            agents_dir.mkdir()
            (agents_dir / "agent.md").write_text(
                "---\nname: agent\n---\nThis is a detailed description"
            )

            skills_dir = config_dir / "skills"
            skills_dir.mkdir()
            (skills_dir / "skill.md").write_text("This is a complete skill")

            auditor = ClaudeAuditor(config_dir)
            report = auditor.run_audit()

            assert report.total_checks >= 10
            assert report.score > 0
