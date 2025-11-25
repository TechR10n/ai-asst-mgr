"""Claude-specific configuration auditor.

This module provides audit checks specific to Claude Code configurations,
including agent validation, skill checks, and MCP server verification.
"""

from __future__ import annotations

import json
import stat
from typing import TYPE_CHECKING

from ai_asst_mgr.audit.base import (
    AuditCategory,
    AuditCheck,
    AuditSeverity,
    BaseAuditor,
)

if TYPE_CHECKING:
    from pathlib import Path

# Quality thresholds
MIN_SKILL_CONTENT_LENGTH = 10
MIN_AGENT_DESCRIPTION_LENGTH = 20


class ClaudeAuditor(BaseAuditor):
    """Auditor for Claude Code configurations.

    Performs security, configuration, quality, and usage audits
    specific to Claude Code installations.
    """

    def __init__(self, config_dir: Path) -> None:
        """Initialize the Claude auditor.

        Args:
            config_dir: Path to ~/.claude directory.
        """
        super().__init__("claude", config_dir)
        self.commands_dir = config_dir / "commands"
        self.settings_file = config_dir / "settings.json"

    def audit_security(self) -> None:
        """Run security-related audit checks for Claude."""
        self._check_config_permissions()
        self._check_sensitive_files()
        self._check_api_key_exposure()

    def audit_configuration(self) -> None:
        """Run configuration validity checks for Claude."""
        self._check_settings_file()
        self._check_commands_directory()
        self._check_agent_yaml_validity()

    def audit_quality(self) -> None:
        """Run quality assessment checks for Claude."""
        self._check_agent_descriptions()
        self._check_skill_completeness()
        self._check_duplicate_agents()

    def audit_usage(self) -> None:
        """Run usage pattern checks for Claude."""
        self._check_unused_agents()
        self._check_mcp_server_health()

    def _check_config_permissions(self) -> None:
        """Check file permissions on config directory."""
        if not self.config_dir.exists():
            self._add_check(
                AuditCheck(
                    name="config_directory_exists",
                    category=AuditCategory.SECURITY,
                    severity=AuditSeverity.ERROR,
                    passed=False,
                    message=f"Config directory does not exist: {self.config_dir}",
                    recommendation="Run 'claude' to initialize configuration",
                )
            )
            return

        try:
            mode = self.config_dir.stat().st_mode
            world_readable = bool(mode & stat.S_IROTH)
            world_writable = bool(mode & stat.S_IWOTH)

            if world_writable:
                self._add_check(
                    AuditCheck(
                        name="config_not_world_writable",
                        category=AuditCategory.SECURITY,
                        severity=AuditSeverity.CRITICAL,
                        passed=False,
                        message="Config directory is world-writable",
                        recommendation="Run: chmod 700 ~/.claude",
                        details={"mode": oct(mode)},
                    )
                )
            elif world_readable:
                self._add_check(
                    AuditCheck(
                        name="config_not_world_readable",
                        category=AuditCategory.SECURITY,
                        severity=AuditSeverity.WARNING,
                        passed=False,
                        message="Config directory is world-readable",
                        recommendation="Run: chmod 700 ~/.claude",
                        details={"mode": oct(mode)},
                    )
                )
            else:
                self._add_check(
                    AuditCheck(
                        name="config_permissions",
                        category=AuditCategory.SECURITY,
                        severity=AuditSeverity.INFO,
                        passed=True,
                        message="Config directory permissions are secure",
                        details={"mode": oct(mode)},
                    )
                )
        except OSError as e:
            self._add_check(
                AuditCheck(
                    name="config_permissions",
                    category=AuditCategory.SECURITY,
                    severity=AuditSeverity.ERROR,
                    passed=False,
                    message=f"Cannot check permissions: {e}",
                )
            )

    def _check_sensitive_files(self) -> None:
        """Check for sensitive files that should not exist."""
        sensitive_patterns = [
            ("credentials.json", "API credentials"),
            ("secrets.json", "Secret data"),
            (".env", "Environment variables"),
        ]

        for filename, description in sensitive_patterns:
            filepath = self.config_dir / filename
            if filepath.exists():
                self._add_check(
                    AuditCheck(
                        name=f"no_sensitive_file_{filename}",
                        category=AuditCategory.SECURITY,
                        severity=AuditSeverity.WARNING,
                        passed=False,
                        message=f"Found sensitive file: {filename} ({description})",
                        recommendation=f"Consider encrypting or removing {filepath}",
                        details={"path": str(filepath)},
                    )
                )

    def _check_api_key_exposure(self) -> None:
        """Check for API keys in configuration files."""
        if not self.settings_file.exists():
            return

        try:
            content = self.settings_file.read_text()
            exposed_patterns = [
                ("sk-", "OpenAI API key"),
                ("AIza", "Google API key"),
            ]

            for pattern, key_type in exposed_patterns:
                if pattern in content:
                    self._add_check(
                        AuditCheck(
                            name=f"no_exposed_{key_type.lower().replace(' ', '_')}",
                            category=AuditCategory.SECURITY,
                            severity=AuditSeverity.CRITICAL,
                            passed=False,
                            message=f"Possible {key_type} exposed in settings",
                            recommendation="Use environment variables for API keys",
                        )
                    )
                    return

            self._add_check(
                AuditCheck(
                    name="no_api_key_exposure",
                    category=AuditCategory.SECURITY,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No API keys found in configuration files",
                )
            )
        except OSError:
            pass

    def _check_settings_file(self) -> None:
        """Check settings.json validity."""
        if not self.settings_file.exists():
            self._add_check(
                AuditCheck(
                    name="settings_file_exists",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No settings.json file (using defaults)",
                )
            )
            return

        try:
            content = self.settings_file.read_text()
            json.loads(content)
            self._add_check(
                AuditCheck(
                    name="settings_file_valid",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="settings.json is valid JSON",
                )
            )
        except json.JSONDecodeError as e:
            self._add_check(
                AuditCheck(
                    name="settings_file_valid",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.ERROR,
                    passed=False,
                    message=f"Invalid JSON in settings.json: {e}",
                    recommendation="Fix JSON syntax errors in settings.json",
                )
            )
        except OSError as e:
            self._add_check(
                AuditCheck(
                    name="settings_file_readable",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.ERROR,
                    passed=False,
                    message=f"Cannot read settings.json: {e}",
                )
            )

    def _check_commands_directory(self) -> None:
        """Check commands directory structure."""
        if not self.commands_dir.exists():
            self._add_check(
                AuditCheck(
                    name="commands_directory",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No custom commands directory",
                )
            )
            return

        md_files = list(self.commands_dir.glob("*.md"))
        self._add_check(
            AuditCheck(
                name="commands_directory",
                category=AuditCategory.CONFIG,
                severity=AuditSeverity.INFO,
                passed=True,
                message=f"Found {len(md_files)} custom command(s)",
                details={"count": len(md_files)},
            )
        )

    def _check_agent_yaml_validity(self) -> None:
        """Check YAML frontmatter in agent files."""
        agents_dir = self.config_dir / "agents"
        if not agents_dir.exists():
            self._add_check(
                AuditCheck(
                    name="agents_yaml_valid",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No agents directory",
                )
            )
            return

        md_files = list(agents_dir.glob("*.md"))
        invalid_count = 0

        for md_file in md_files:
            try:
                content = md_file.read_text()
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end == -1:
                        invalid_count += 1
            except OSError:
                invalid_count += 1

        if invalid_count > 0:
            self._add_check(
                AuditCheck(
                    name="agents_yaml_valid",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.WARNING,
                    passed=False,
                    message=f"{invalid_count} agent(s) have invalid YAML frontmatter",
                    recommendation="Fix YAML frontmatter syntax in agent files",
                    details={"invalid_count": invalid_count},
                )
            )
        else:
            self._add_check(
                AuditCheck(
                    name="agents_yaml_valid",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message=f"All {len(md_files)} agent(s) have valid frontmatter",
                )
            )

    def _check_agent_descriptions(self) -> None:
        """Check quality of agent descriptions."""
        agents_dir = self.config_dir / "agents"
        if not agents_dir.exists():
            return

        md_files = list(agents_dir.glob("*.md"))
        short_descriptions = 0

        for md_file in md_files:
            try:
                content = md_file.read_text()
                body = content
                if content.startswith("---"):
                    end = content.find("---", 3)
                    if end != -1:
                        body = content[end + 3 :].strip()

                if len(body) < MIN_AGENT_DESCRIPTION_LENGTH:
                    short_descriptions += 1
            except OSError:
                pass

        if short_descriptions > 0:
            self._add_check(
                AuditCheck(
                    name="agent_description_quality",
                    category=AuditCategory.QUALITY,
                    severity=AuditSeverity.WARNING,
                    passed=False,
                    message=f"{short_descriptions} agent(s) have short descriptions",
                    recommendation="Add detailed descriptions to agents for better context",
                    details={
                        "short_count": short_descriptions,
                        "min_length": MIN_AGENT_DESCRIPTION_LENGTH,
                    },
                )
            )
        elif len(md_files) > 0:
            self._add_check(
                AuditCheck(
                    name="agent_description_quality",
                    category=AuditCategory.QUALITY,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="All agents have adequate descriptions",
                )
            )

    def _check_skill_completeness(self) -> None:
        """Check skill file completeness."""
        skills_dir = self.config_dir / "skills"
        if not skills_dir.exists():
            self._add_check(
                AuditCheck(
                    name="skills_complete",
                    category=AuditCategory.QUALITY,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No skills directory",
                )
            )
            return

        md_files = list(skills_dir.glob("*.md"))
        empty_skills = 0

        for md_file in md_files:
            try:
                content = md_file.read_text().strip()
                if len(content) < MIN_SKILL_CONTENT_LENGTH:
                    empty_skills += 1
            except OSError:
                empty_skills += 1

        if empty_skills > 0:
            self._add_check(
                AuditCheck(
                    name="skills_complete",
                    category=AuditCategory.QUALITY,
                    severity=AuditSeverity.WARNING,
                    passed=False,
                    message=f"{empty_skills} skill(s) appear empty or incomplete",
                    recommendation="Add content to skill files",
                    details={"empty_count": empty_skills},
                )
            )
        elif len(md_files) > 0:
            self._add_check(
                AuditCheck(
                    name="skills_complete",
                    category=AuditCategory.QUALITY,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message=f"All {len(md_files)} skill(s) have content",
                )
            )

    def _check_duplicate_agents(self) -> None:
        """Check for duplicate agent names."""
        agents_dir = self.config_dir / "agents"
        if not agents_dir.exists():
            return

        agent_names: dict[str, list[str]] = {}
        for md_file in agents_dir.glob("*.md"):
            name = md_file.stem.lower()
            if name not in agent_names:
                agent_names[name] = []
            agent_names[name].append(str(md_file))

        duplicates = {k: v for k, v in agent_names.items() if len(v) > 1}

        if duplicates:
            self._add_check(
                AuditCheck(
                    name="no_duplicate_agents",
                    category=AuditCategory.QUALITY,
                    severity=AuditSeverity.WARNING,
                    passed=False,
                    message=f"Found {len(duplicates)} duplicate agent name(s)",
                    recommendation="Rename agents to have unique names",
                    details={"duplicates": duplicates},
                )
            )
        elif agent_names:
            self._add_check(
                AuditCheck(
                    name="no_duplicate_agents",
                    category=AuditCategory.QUALITY,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No duplicate agent names",
                )
            )

    def _check_unused_agents(self) -> None:
        """Check for agents that haven't been used recently."""
        agents_dir = self.config_dir / "agents"
        if not agents_dir.exists():
            return

        md_files = list(agents_dir.glob("*.md"))
        if not md_files:
            return

        self._add_check(
            AuditCheck(
                name="agent_usage",
                category=AuditCategory.USAGE,
                severity=AuditSeverity.INFO,
                passed=True,
                message=f"Found {len(md_files)} agent(s) configured",
                details={"count": len(md_files)},
            )
        )

    def _check_mcp_server_health(self) -> None:
        """Check MCP server configuration health."""
        mcp_config = self.config_dir / "mcp_servers.json"
        if not mcp_config.exists():
            self._add_check(
                AuditCheck(
                    name="mcp_servers",
                    category=AuditCategory.USAGE,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No MCP servers configured",
                )
            )
            return

        try:
            content = mcp_config.read_text()
            servers = json.loads(content)
            server_count = len(servers) if isinstance(servers, (list, dict)) else 0

            self._add_check(
                AuditCheck(
                    name="mcp_servers",
                    category=AuditCategory.USAGE,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message=f"Found {server_count} MCP server(s) configured",
                    details={"count": server_count},
                )
            )
        except (json.JSONDecodeError, OSError) as e:
            self._add_check(
                AuditCheck(
                    name="mcp_servers",
                    category=AuditCategory.USAGE,
                    severity=AuditSeverity.ERROR,
                    passed=False,
                    message=f"Invalid MCP server configuration: {e}",
                    recommendation="Fix mcp_servers.json syntax",
                )
            )
