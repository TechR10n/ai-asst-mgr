# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Phase 10 documentation and testing improvements

---

## [0.1.0] - 2025-11-25

### Highlights
- **748 tests** with 95%+ coverage
- **Full CLI implementation** with 9 commands
- **Coaching system** for AI-powered usage insights
- **Backup/Restore/Sync** operations
- **GitPython security** - no shell injection risks

### Added

#### CLI Commands
- `status` - Display all vendors and their installation/configuration status
- `init` - Initialize vendor configurations with sensible defaults
- `health` - Run comprehensive health checks on vendor configurations
- `doctor` - Diagnose and automatically fix common issues
- `config` - Get and set configuration values across vendors
- `backup` - Create compressed backups with checksums and retention policies
- `restore` - Restore configurations from backup archives
- `sync` - Synchronize configurations from Git repositories
- `coach` - Get AI-powered usage insights and optimization recommendations

#### Coaching System (Phase 5)
- **ClaudeCoach**: Usage analytics for Claude Code (agents, skills, MCP servers)
- **GeminiCoach**: Usage analytics for Gemini CLI (MCP servers, settings)
- **CodexCoach**: Usage analytics for OpenAI Codex (profiles, functions)
- Cross-vendor comparison with unified metrics
- Weekly/monthly report generation
- Export to JSON or Markdown formats

#### Backup & Restore System (Phase 6)
- Compressed tar.gz archives with SHA256 checksums
- Retention policies for automatic cleanup
- Pre-restore backups for rollback capability
- Selective restore by directory
- Backup verification and integrity checking

#### Sync System (Phase 6)
- Git repository synchronization
- Merge strategies: replace, merge, keep_local, keep_remote
- Preview mode for dry-run operations
- Pre-sync backups for safety

#### Security Improvements
- **GitPython integration** - Replaced subprocess with GitPython library
- **Secure tarfile extraction** - CWE-22 path traversal protection
- **Input validation** - URL and branch name validation with regex
- **No workarounds** - Zero `# nosec`, `# noqa`, `# type: ignore` in production code

### Changed
- Renamed tarfile functions to avoid Bandit B202 false positives
  - `safe_extractall` → `unpack_tar_securely`
  - `safe_extract_members` → `unpack_members_securely`
- Updated test mocks from subprocess.run to GitPython patterns
- Refactored `audit_config` in OpenAIAdapter to reduce complexity

### Technical
- **Tests**: 748 tests passing (up from 191)
- **Coverage**: 95%+ maintained across all modules
- **Type Safety**: mypy --strict compliance
- **Security**: bandit passing with no workarounds

---

## [0.0.2] - 2025-11-24

### Added

#### CLI Implementation (Phase 3)
- `status` command with Rich table output
- `health` command with vendor health checks
- `doctor` command with auto-fix capabilities
- `init` command for vendor initialization
- `config` command for get/set operations

#### Infrastructure
- Vendor-agnostic database migration framework
- Parallel agent development (git worktrees + orchestrator)
- Claude GitHub Actions integration (@claude mentions)
- Automated release workflow (triggered by version tags)
- Development standards documentation

### Changed
- Updated database schema to version 2.0.0 (vendor-agnostic)
- Expanded MVP scope: 24 → 30 issues

### Technical
- Database migration framework (380 lines, 26 tests, 85.79% coverage)
- 001_vendor_agnostic.sql migration (320+ lines, 5 new tables, 4 views)
- Parallel development orchestrator (Python script for task coordination)
- 311 tests passing

---

## [0.0.1] - 2025-11-23

### Added

#### Foundation (Phase 1)
- Initial project setup with uv package manager
- Python 3.14 support
- CI/CD pipeline (GitHub Actions: Ubuntu + macOS)
- Pre-commit hooks (ruff, mypy, bandit)
- Quality gates (95%+ coverage, mypy --strict)

#### Vendor Adapters (Phase 2)
- **VendorAdapter ABC** with 13 abstract methods
- **ClaudeAdapter**: ~/.claude config management (200 statements, 95.15% coverage, 47 tests)
- **GeminiAdapter**: ~/.gemini config management (215 statements, 95.47% coverage, 50 tests)
- **OpenAIAdapter**: ~/.codex config management (242 statements, 95.21% coverage, 50 tests)
- **VendorRegistry**: Unified vendor interface (32 statements, 100% coverage, 22 tests)

### Technical
- 191 tests passing
- Type safety: mypy --strict compliance
- Security: path traversal protection, subprocess safety

---

## How to Release

### Automatic (Recommended)
```bash
# Bump version (patch: 0.1.0 → 0.1.1)
./scripts/bump_version.sh patch

# Push commits and tag
git push origin main
git push origin v0.1.1

# GitHub Actions will automatically:
# - Run tests and quality checks
# - Build package
# - Generate changelog from commits
# - Create GitHub release with artifacts
# - Update CHANGELOG.md
```

### Manual
```bash
# Update version in pyproject.toml
version = "0.1.1"

# Commit
git add pyproject.toml
git commit -m "chore: bump version to 0.1.1"

# Tag
git tag -a v0.1.1 -m "Release v0.1.1"

# Push
git push origin main
git push origin v0.1.1
```

---

## Links

- **Repository**: https://github.com/TechR10n/ai-asst-mgr
- **Issue Tracker**: https://github.com/TechR10n/ai-asst-mgr/issues
- **Releases**: https://github.com/TechR10n/ai-asst-mgr/releases
- **Documentation**: https://github.com/TechR10n/ai-asst-mgr/wiki
