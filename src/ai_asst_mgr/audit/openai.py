"""OpenAI Codex-specific configuration auditor.

This module provides audit checks specific to OpenAI Codex configurations,
including API key validation, function definitions, and assistant settings.
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
MIN_INSTRUCTION_LENGTH = 20


class CodexAuditor(BaseAuditor):
    """Auditor for OpenAI Codex configurations.

    Performs security, configuration, quality, and usage audits
    specific to OpenAI Codex installations.
    """

    def __init__(self, config_dir: Path) -> None:
        """Initialize the Codex auditor.

        Args:
            config_dir: Path to ~/.openai or OpenAI config directory.
        """
        super().__init__("openai", config_dir)
        self.config_file = config_dir / "config.json"
        self.assistants_dir = config_dir / "assistants"
        self.functions_dir = config_dir / "functions"

    def audit_security(self) -> None:
        """Run security-related audit checks for OpenAI Codex."""
        self._check_config_permissions()
        self._check_api_key_storage()
        self._check_env_file()

    def audit_configuration(self) -> None:
        """Run configuration validity checks for OpenAI Codex."""
        self._check_config_file()
        self._check_assistants_config()
        self._check_function_definitions()

    def audit_quality(self) -> None:
        """Run quality assessment checks for OpenAI Codex."""
        self._check_assistant_instructions()
        self._check_function_schemas()
        self._check_model_configuration()

    def audit_usage(self) -> None:
        """Run usage pattern checks for OpenAI Codex."""
        self._check_rate_limit_settings()
        self._check_token_usage()

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
                    recommendation="Create OpenAI configuration directory",
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
                        recommendation="Run: chmod 700 on config directory",
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
                        recommendation="Run: chmod 700 on config directory",
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

    def _check_api_key_storage(self) -> None:
        """Check for API keys stored in config files."""
        if not self.config_file.exists():
            return

        try:
            content = self.config_file.read_text()
            if "sk-" in content:
                self._add_check(
                    AuditCheck(
                        name="no_api_key_in_config",
                        category=AuditCategory.SECURITY,
                        severity=AuditSeverity.CRITICAL,
                        passed=False,
                        message="OpenAI API key found in config.json",
                        recommendation="Use OPENAI_API_KEY environment variable instead",
                        details={"file": str(self.config_file)},
                    )
                )
                return

            self._add_check(
                AuditCheck(
                    name="no_api_key_in_config",
                    category=AuditCategory.SECURITY,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No API keys found in configuration files",
                )
            )
        except OSError:
            pass

    def _check_env_file(self) -> None:
        """Check for .env file with exposed credentials."""
        env_file = self.config_dir / ".env"
        if env_file.exists():
            self._add_check(
                AuditCheck(
                    name="no_env_file",
                    category=AuditCategory.SECURITY,
                    severity=AuditSeverity.WARNING,
                    passed=False,
                    message="Found .env file in config directory",
                    recommendation="Ensure .env is not committed to version control",
                    details={"path": str(env_file)},
                )
            )
        else:
            self._add_check(
                AuditCheck(
                    name="no_env_file",
                    category=AuditCategory.SECURITY,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No .env file in config directory",
                )
            )

    def _check_config_file(self) -> None:
        """Check config.json validity."""
        if not self.config_file.exists():
            self._add_check(
                AuditCheck(
                    name="config_file_exists",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No config.json file (using defaults)",
                )
            )
            return

        try:
            content = self.config_file.read_text()
            json.loads(content)
            self._add_check(
                AuditCheck(
                    name="config_file_valid",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="config.json is valid JSON",
                )
            )
        except json.JSONDecodeError as e:
            self._add_check(
                AuditCheck(
                    name="config_file_valid",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.ERROR,
                    passed=False,
                    message=f"Invalid JSON in config.json: {e}",
                    recommendation="Fix JSON syntax errors in config.json",
                )
            )
        except OSError as e:
            self._add_check(
                AuditCheck(
                    name="config_file_readable",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.ERROR,
                    passed=False,
                    message=f"Cannot read config.json: {e}",
                )
            )

    def _check_assistants_config(self) -> None:
        """Check assistants directory configuration."""
        if not self.assistants_dir.exists():
            self._add_check(
                AuditCheck(
                    name="assistants_config",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No assistants directory configured",
                )
            )
            return

        json_files = list(self.assistants_dir.glob("*.json"))
        self._add_check(
            AuditCheck(
                name="assistants_config",
                category=AuditCategory.CONFIG,
                severity=AuditSeverity.INFO,
                passed=True,
                message=f"Found {len(json_files)} assistant configuration(s)",
                details={"count": len(json_files)},
            )
        )

    def _check_function_definitions(self) -> None:
        """Check function definitions validity."""
        if not self.functions_dir.exists():
            self._add_check(
                AuditCheck(
                    name="function_definitions",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No functions directory",
                )
            )
            return

        json_files = list(self.functions_dir.glob("*.json"))
        invalid_count = 0

        for json_file in json_files:
            try:
                content = json_file.read_text()
                data = json.loads(content)
                if not isinstance(data, dict) or "name" not in data:
                    invalid_count += 1
            except (json.JSONDecodeError, OSError):
                invalid_count += 1

        if invalid_count > 0:
            self._add_check(
                AuditCheck(
                    name="function_definitions",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.WARNING,
                    passed=False,
                    message=f"{invalid_count} function definition(s) are invalid",
                    recommendation="Fix function definitions to include 'name' field",
                    details={"invalid_count": invalid_count},
                )
            )
        else:
            self._add_check(
                AuditCheck(
                    name="function_definitions",
                    category=AuditCategory.CONFIG,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message=f"All {len(json_files)} function definition(s) are valid",
                )
            )

    def _check_assistant_instructions(self) -> None:
        """Check quality of assistant instructions."""
        if not self.assistants_dir.exists():
            return

        json_files = list(self.assistants_dir.glob("*.json"))
        short_instructions = 0

        for json_file in json_files:
            try:
                content = json_file.read_text()
                data = json.loads(content)
                instructions = data.get("instructions", "")

                if len(instructions) < MIN_INSTRUCTION_LENGTH:
                    short_instructions += 1
            except (json.JSONDecodeError, OSError):
                pass

        if short_instructions > 0:
            self._add_check(
                AuditCheck(
                    name="assistant_instructions_quality",
                    category=AuditCategory.QUALITY,
                    severity=AuditSeverity.WARNING,
                    passed=False,
                    message=f"{short_instructions} assistant(s) have short instructions",
                    recommendation="Add detailed instructions for better context",
                    details={
                        "short_count": short_instructions,
                        "min_length": MIN_INSTRUCTION_LENGTH,
                    },
                )
            )
        elif len(json_files) > 0:
            self._add_check(
                AuditCheck(
                    name="assistant_instructions_quality",
                    category=AuditCategory.QUALITY,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="All assistants have adequate instructions",
                )
            )

    def _check_function_schemas(self) -> None:
        """Check function schema quality."""
        if not self.functions_dir.exists():
            return

        json_files = list(self.functions_dir.glob("*.json"))
        missing_descriptions = 0

        for json_file in json_files:
            try:
                content = json_file.read_text()
                data = json.loads(content)

                if "description" not in data or not data.get("description"):
                    missing_descriptions += 1
            except (json.JSONDecodeError, OSError):
                pass

        if missing_descriptions > 0:
            self._add_check(
                AuditCheck(
                    name="function_schema_quality",
                    category=AuditCategory.QUALITY,
                    severity=AuditSeverity.WARNING,
                    passed=False,
                    message=f"{missing_descriptions} function(s) missing descriptions",
                    recommendation="Add descriptions to all function definitions",
                    details={"missing_count": missing_descriptions},
                )
            )
        elif len(json_files) > 0:
            self._add_check(
                AuditCheck(
                    name="function_schema_quality",
                    category=AuditCategory.QUALITY,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="All functions have descriptions",
                )
            )

    def _check_model_configuration(self) -> None:
        """Check model configuration settings."""
        if not self.config_file.exists():
            return

        try:
            content = self.config_file.read_text()
            data = json.loads(content)

            model = data.get("model", "")
            deprecated_models = ["gpt-3.5-turbo-0301", "gpt-4-0314"]

            if model in deprecated_models:
                self._add_check(
                    AuditCheck(
                        name="model_not_deprecated",
                        category=AuditCategory.QUALITY,
                        severity=AuditSeverity.WARNING,
                        passed=False,
                        message=f"Using deprecated model: {model}",
                        recommendation="Update to a current model version",
                        details={"model": model},
                    )
                )
            elif model:
                self._add_check(
                    AuditCheck(
                        name="model_configured",
                        category=AuditCategory.QUALITY,
                        severity=AuditSeverity.INFO,
                        passed=True,
                        message=f"Model configured: {model}",
                        details={"model": model},
                    )
                )
        except (json.JSONDecodeError, OSError):
            pass

    def _check_rate_limit_settings(self) -> None:
        """Check rate limiting configuration."""
        if not self.config_file.exists():
            self._add_check(
                AuditCheck(
                    name="rate_limit_config",
                    category=AuditCategory.USAGE,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No rate limit configuration (using defaults)",
                )
            )
            return

        try:
            content = self.config_file.read_text()
            data = json.loads(content)

            if "rate_limit" in data or "max_requests_per_minute" in data:
                self._add_check(
                    AuditCheck(
                        name="rate_limit_config",
                        category=AuditCategory.USAGE,
                        severity=AuditSeverity.INFO,
                        passed=True,
                        message="Rate limiting is configured",
                        details={
                            "config": {k: v for k, v in data.items() if "rate" in k.lower()},
                        },
                    )
                )
            else:
                self._add_check(
                    AuditCheck(
                        name="rate_limit_config",
                        category=AuditCategory.USAGE,
                        severity=AuditSeverity.INFO,
                        passed=True,
                        message="No rate limit configuration (using defaults)",
                    )
                )
        except (json.JSONDecodeError, OSError):
            pass

    def _check_token_usage(self) -> None:
        """Check token usage tracking."""
        usage_file = self.config_dir / "usage.json"

        if usage_file.exists():
            self._add_check(
                AuditCheck(
                    name="token_usage_tracking",
                    category=AuditCategory.USAGE,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="Token usage tracking is enabled",
                    details={"path": str(usage_file)},
                )
            )
        else:
            self._add_check(
                AuditCheck(
                    name="token_usage_tracking",
                    category=AuditCategory.USAGE,
                    severity=AuditSeverity.INFO,
                    passed=True,
                    message="No token usage tracking configured",
                )
            )
