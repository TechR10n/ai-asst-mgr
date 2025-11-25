# Architecture

This document describes the architecture and design of AI Assistant Manager.

## Overview

AI Assistant Manager follows a layered architecture with clear separation of concerns:

```
┌─────────────────────────────────────────────────────────────┐
│  CLI Layer (Typer + Rich)                                   │
│  • status, init, health, doctor, config                     │
│  • backup, restore, sync, coach                             │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│  Operations Layer                                            │
│  • BackupManager   • RestoreManager   • SyncManager         │
│  • CoachingSystem  • AuditFramework                         │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│  Vendor Registry                                             │
│  • Discovers and manages vendor adapters                    │
│  • Provides unified access to all vendors                   │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│  Vendor Adapters (Plugin System)                            │
│  • ClaudeAdapter   • GeminiAdapter   • OpenAIAdapter        │
└─────────────────┬───────────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────────┐
│  Vendor Configurations (Independent)                         │
│  ~/.claude/        ~/.gemini/        ~/.codex/              │
└─────────────────────────────────────────────────────────────┘
```

## Design Principles

### 1. Vendor Independence

Each vendor's configuration directory remains autonomous. AI Assistant Manager reads and writes to vendor-specific directories without creating cross-vendor dependencies.

### 2. Plugin Architecture

Vendors are implemented as adapters following the `VendorAdapter` abstract base class. New vendors can be added by implementing this interface.

### 3. Capability Abstraction

Common operations (backup, restore, health check) work across all vendors through a unified interface, while vendor-specific features are still accessible.

### 4. Privacy First

All data stays local. No cloud services, no telemetry, no external dependencies for core functionality.

### 5. Type Safety

Full type annotations throughout, enforced by mypy --strict. This ensures correctness and enables IDE support.

---

## Component Details

### CLI Layer

Built with [Typer](https://typer.tiangolo.com/) and [Rich](https://rich.readthedocs.io/):

```python
# src/ai_asst_mgr/cli.py

@app.command()
def status(vendor: str | None = None) -> None:
    """Display vendor status."""
    registry = VendorRegistry()
    vendors = registry.get_all_vendors()
    # Display status table
```

### Vendor Registry

Central registry for discovering and managing vendors:

```python
# src/ai_asst_mgr/vendors/__init__.py

class VendorRegistry:
    """Registry for vendor adapters."""

    def get_all_vendors(self) -> dict[str, VendorAdapter]:
        """Get all registered vendors."""

    def get_vendor(self, vendor_id: str) -> VendorAdapter:
        """Get specific vendor by ID."""

    def get_installed_vendors(self) -> dict[str, VendorAdapter]:
        """Get only installed vendors."""
```

### Vendor Adapters

Abstract base class defining the vendor interface:

```python
# src/ai_asst_mgr/adapters/base.py

class VendorAdapter(ABC):
    """Abstract base class for vendor adapters."""

    @property
    @abstractmethod
    def info(self) -> VendorInfo:
        """Vendor information."""

    @abstractmethod
    def is_installed(self) -> bool:
        """Check if vendor CLI is installed."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Check if vendor is configured."""

    @abstractmethod
    def get_status(self) -> VendorStatus:
        """Get vendor status."""

    @abstractmethod
    def initialize(self) -> None:
        """Initialize vendor configuration."""

    @abstractmethod
    def get_config(self, key: str) -> object:
        """Get configuration value."""

    @abstractmethod
    def set_config(self, key: str, value: object) -> None:
        """Set configuration value."""

    @abstractmethod
    def backup(self, backup_path: Path) -> None:
        """Create backup of configuration."""

    @abstractmethod
    def restore(self, backup_path: Path) -> None:
        """Restore from backup."""

    @abstractmethod
    def sync_from_git(self, repo_url: str, branch: str) -> None:
        """Sync from git repository."""

    @abstractmethod
    def health_check(self) -> dict[str, object]:
        """Run health checks."""

    @abstractmethod
    def audit_config(self) -> dict[str, object]:
        """Audit configuration."""

    @abstractmethod
    def get_usage_stats(self) -> dict[str, object]:
        """Get usage statistics."""
```

### Operations Layer

#### BackupManager

Handles backup creation with retention policies:

```python
# src/ai_asst_mgr/operations/backup.py

class BackupManager:
    def backup_vendor(self, adapter: VendorAdapter) -> BackupResult:
        """Backup single vendor."""

    def backup_all_vendors(self, vendors: dict[str, VendorAdapter]) -> BackupSummary:
        """Backup all vendors."""

    def list_backups(self, vendor: str | None) -> list[BackupMetadata]:
        """List available backups."""

    def verify_backup(self, backup_path: Path) -> tuple[bool, str]:
        """Verify backup integrity."""
```

#### RestoreManager

Handles restore operations with safety features:

```python
# src/ai_asst_mgr/operations/restore.py

class RestoreManager:
    def restore_vendor(self, adapter: VendorAdapter, backup_path: Path) -> RestoreResult:
        """Restore single vendor."""

    def preview_restore(self, backup_path: Path) -> RestorePreview:
        """Preview what would be restored."""
```

#### SyncManager

Handles Git synchronization with merge strategies:

```python
# src/ai_asst_mgr/operations/sync.py

class SyncManager:
    def sync_from_git(
        self,
        vendors: dict[str, VendorAdapter],
        repo_url: str,
        strategy: MergeStrategy,
    ) -> SyncSummary:
        """Sync from Git repository."""
```

### Coaching System

AI-powered usage analytics:

```python
# src/ai_asst_mgr/coaches/base.py

class CoachBase(ABC):
    @abstractmethod
    def analyze(self, period_days: int) -> UsageReport:
        """Analyze usage patterns."""

    @abstractmethod
    def get_insights(self) -> list[Insight]:
        """Get usage insights."""

    @abstractmethod
    def get_recommendations(self) -> list[Recommendation]:
        """Get optimization recommendations."""
```

---

## Security

### Git Operations

Git operations use GitPython library instead of subprocess to prevent shell injection:

```python
# src/ai_asst_mgr/utils/git.py

def git_clone(url: str, dest_dir: Path, branch: str) -> bool:
    """Clone repository securely using GitPython."""
    if not validate_git_url(url):
        raise GitValidationError(f"Invalid Git URL: {url}")
    git.Repo.clone_from(url, str(dest_dir), branch=branch)
```

### Tarfile Extraction

Secure tarfile extraction prevents path traversal attacks (CWE-22):

```python
# src/ai_asst_mgr/utils/tarfile_safe.py

def unpack_tar_securely(tar: tarfile.TarFile, dest_dir: Path) -> list[str]:
    """Securely unpack tarfile with path traversal protection."""
    safe_members = list(get_safe_members(tar, dest_dir))
    for member in safe_members:
        tar.extract(member, dest_dir)
```

---

## Testing

### Test Structure

```
tests/
├── unit/
│   ├── test_claude_adapter.py
│   ├── test_gemini_adapter.py
│   ├── test_openai_adapter.py
│   ├── test_backup.py
│   ├── test_restore.py
│   ├── test_sync.py
│   ├── test_cli.py
│   └── ...
└── integration/
    └── ...
```

### Quality Standards

- **Coverage**: 95%+ required
- **Type Safety**: mypy --strict
- **Linting**: ruff with comprehensive rules
- **Security**: bandit scanning

---

## Adding New Vendors

To add a new vendor:

1. Create adapter class implementing `VendorAdapter`:
   ```python
   class NewVendorAdapter(VendorAdapter):
       # Implement all abstract methods
   ```

2. Register in `VendorRegistry`:
   ```python
   self._adapters["newvendor"] = NewVendorAdapter()
   ```

3. Add tests in `tests/unit/test_newvendor_adapter.py`

4. Update documentation

---

## See Also

- [Installation Guide](installation.md)
- [Command Reference](commands.md)
- [Contributing](contributing.md)
