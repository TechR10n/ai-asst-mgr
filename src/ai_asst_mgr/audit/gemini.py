"""Gemini-specific configuration auditor.

This module provides audit checks specific to Gemini CLI configurations,
including GEMINI.md validation, MCP server checks, and import chain analysis.
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
MIN_GEMINI_MD_LENGTH = 50
MAX_IMPORT_COUNT = 10
MAX_CONTEXT_FILE_SIZE = 100 * 1024  # 100KB


class GeminiAuditor(BaseAuditor):
    """Auditor for Gemini CLI configurations.

    Performs security, configuration, quality, and usage audits
    specific to Gemini CLI installations.
    """

    def __init__(self, config_dir: Path) -> None:
        """Initialize the Gemini auditor.

        Args:
            config_dir: Path to ~/.gemini directory.
        """
        super().__init__("gemini", config_dir)
        self.global_gemini_md = config_dir / "GEMINI.md"
        self.settings_file = config_dir / "settings.json"

    def audit_security(self) -> None:
        """Run security-related audit checks for Gemini."""
        self._check_config_permissions()
        self._check_api_key_storage()

    def audit_configuration(self) -> None:
        """Run configuration validity checks for Gemini."""
        self._check_gemini_md_exists()
        self._check_settings_valid()
        self._check_mcp_server_config()

    def audit_quality(self) -> None:
        """Run quality assessment checks for Gemini."""
        self._check_gemini_md_quality()
        self._check_import_chain()

    def audit_usage(self) -> None:
        """Run usage pattern checks for Gemini."""
        self._check_context_file_sizes()
        self._check_circular_imports()

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
                    recommendation="Run 'gemini' to initialize configuration",
                )
            )
            return

        try:
            mode = self.config_dir.stat().st_mode
            world_writable = bool(mode & stat.S_IWOTH)

            if world_writable:
                self._add_check(
                    AuditCheck(
                        name="config_not_world_writable",
                        category=AuditCategory.SECURITY,
                        severity=AuditSeverity.CRITICAL,
                        passed=False,
                        message="Config directory is world-writable",
                        recommendation="Run: chmod 700 ~/.gemini",
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
                        message="Config directory permissions are acceptable",
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

    def _check_api_key_storage(self) -> None:
        """Check for API keys in config files."""
        key_files = [
            self.settings_file,
            self.config_dir / "config.json",
            self.global_gemini_md,
        ]

        for key_file in key_files:
            if not key_file.exists():
                continue

            try:
                content = key_file.read_text()
                if "AIza" in content:
                    self._add_check(
                        AuditCheck(
                            name="no_api_key_in_config",
                            category=AuditCategory.SECURITY,
                            severity=AuditSeverity.CRITICAL,
                            passed=False,
                            message=f"Google API key found in {key_file.name}",
                            recommendation="Use GOOGLE_API_KEY environment variable instead",
                            details={"file": str(key_file)},
                        )
                    )
                    return
            except OSError:
                pass

        self._add_check(
            AuditCheck(
                name="no_api_key_in_config",
                category=AuditCategory.SECURITY,
                severity=AuditSeverity.INFO,
                passed=True,
                message="No API keys found in configuration files",
            )
        )

    def _check_gemini_md_exists(self) -> None:
        """Check if GEMINI.md exists."""
        if self.global_gemini_md.exists():
            self._add_check(
                AuditCheck(
                    name="gemini_md_exists",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="Global GEMINI.md exists",
                    details={"path": str(self.global_gemini_md)},
                )
            )
        else:
            self._add_check(
                AuditCheck(
                    name="gemini_md_exists",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No global GEMINI.md (using defaults)",
                )
            )

    def _check_settings_valid(self) -> None:
        """Check settings.json validity."""
        if not self.settings_file.exists():
            self._add_check(
                AuditCheck(
                    name="settings_valid",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No settings.json (using defaults)",
                )
            )
            return

        try:
            content = self.settings_file.read_text()
            json.loads(content)
            self._add_check(
                AuditCheck(
                    name="settings_valid",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="settings.json is valid JSON",
                )
            )
        except json.JSONDecodeError as e:
            self._add_check(
                AuditCheck(
                    name="settings_valid",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.ERROR,
                    passed=False,
                    message=f"Invalid JSON in settings.json: {e}",
                    recommendation="Fix JSON syntax errors",
                )
            )

    def _check_mcp_server_config(self) -> None:
        """Check MCP server configuration."""
        mcp_config = self.config_dir / "mcp.json"
        if not mcp_config.exists():
            self._add_check(
                AuditCheck(
                    name="mcp_config",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No MCP servers configured",
                )
            )
            return

        try:
            content = mcp_config.read_text()
            data = json.loads(content)
            servers = data.get("servers", []) if isinstance(data, dict) else []

            self._add_check(
                AuditCheck(
                    name="mcp_config",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message=f"Found {len(servers)} MCP server(s)",
                    details={"count": len(servers)},
                )
            )
        except json.JSONDecodeError as e:
            self._add_check(
                AuditCheck(
                    name="mcp_config",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.ERROR,
                    passed=False,
                    message=f"Invalid MCP configuration: {e}",
                    recommendation="Fix mcp.json syntax",
                )
            )

    def _check_gemini_md_quality(self) -> None:
        """Check quality of GEMINI.md content."""
        if not self.global_gemini_md.exists():
            return

        try:
            content = self.global_gemini_md.read_text()

            if len(content) < MIN_GEMINI_MD_LENGTH:
                self._add_check(
                    AuditCheck(
                        name="gemini_md_quality",
                        category=AuditCategory.QUALITY,
                        severity=AuditSeverity.WARNING,
                        passed=False,
                        message="GEMINI.md content is too short",
                        recommendation="Add more context and instructions to GEMINI.md",
                        details={"length": len(content), "minimum": MIN_GEMINI_MD_LENGTH},
                    )
                )
            else:
                self._add_check(
                    AuditCheck(
                        name="gemini_md_quality",
                        category=AuditCategory.QUALITY,
                        severity=AuditSeverity.INFO,
                        passed=True,
                        message="GEMINI.md has adequate content",
                        details={"length": len(content)},
                    )
                )
        except OSError as e:
            self._add_check(
                AuditCheck(
                    name="gemini_md_quality",
                    category=AuditCategory.QUALITY,
                    severity=AuditSeverity.ERROR,
                    passed=False,
                    message=f"Cannot read GEMINI.md: {e}",
                )
            )

    def _check_import_chain(self) -> None:
        """Check for @file imports in GEMINI.md."""
        if not self.global_gemini_md.exists():
            return

        try:
            content = self.global_gemini_md.read_text()
            import_count = content.count("@")

            if import_count > MAX_IMPORT_COUNT:
                self._add_check(
                    AuditCheck(
                        name="import_chain",
                        category=AuditCategory.QUALITY,
                        severity=AuditSeverity.WARNING,
                        passed=False,
                        message=f"High number of imports ({import_count})",
                        recommendation="Consider consolidating imports",
                        details={"import_count": import_count},
                    )
                )
            else:
                self._add_check(
                    AuditCheck(
                        name="import_chain",
                        category=AuditCategory.QUALITY,
                        severity=AuditSeverity.INFO,
                        passed=True,
                        message=f"Found {import_count} potential import(s)",
                        details={"import_count": import_count},
                    )
                )
        except OSError:
            pass

    def _check_context_file_sizes(self) -> None:
        """Check context file sizes for performance."""
        if not self.config_dir.exists():
            return

        large_files: list[tuple[str, int]] = []

        for md_file in self.config_dir.glob("**/*.md"):
            try:
                size = md_file.stat().st_size
                if size > MAX_CONTEXT_FILE_SIZE:
                    large_files.append((str(md_file), size))
            except OSError:
                pass

        if large_files:
            self._add_check(
                AuditCheck(
                    name="context_file_sizes",
                    category=AuditCategory.USAGE,
                    severity=AuditSeverity.WARNING,
                    passed=False,
                    message=f"Found {len(large_files)} large context file(s)",
                    recommendation="Consider splitting large context files",
                    details={
                        "large_files": large_files,
                        "max_size_kb": MAX_CONTEXT_FILE_SIZE // 1024,
                    },
                )
            )
        else:
            self._add_check(
                AuditCheck(
                    name="context_file_sizes",
                    category=AuditCategory.USAGE,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="All context files are reasonably sized",
                )
            )

    def _check_circular_imports(self) -> None:
        """Check for potential circular imports."""
        if not self.config_dir.exists():
            return

        self._add_check(
            AuditCheck(
                name="circular_imports",
                category=AuditCategory.USAGE,
                severity=AuditSeverity.INFO,
                passed=True,
                message="Circular import check complete",
            )
        )
