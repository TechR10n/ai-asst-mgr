# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Vendor-agnostic database migration framework
- Parallel agent development infrastructure (git worktrees + orchestrator)
- Claude GitHub Actions integration (@claude mentions in issues/PRs)
- Automated release workflow (triggered by version tags)
- Development standards documentation
- 6 new MVP feature issues (#58-#63)

### Changed
- Updated database schema to version 2.0.0 (vendor-agnostic)
- Revised database issues #11-14 estimates based on implementation
- Marked Issue #15 as duplicate (Typer CLI already exists)
- Expanded MVP scope: 24 → 30 issues

### Technical
- Database migration framework (380 lines, 26 tests, 85.79% coverage)
- 001_vendor_agnostic.sql migration (320+ lines, 5 new tables, 4 views)
- Parallel development orchestrator (Python script for task coordination)
- Claude assistant workflow (GitHub Actions integration)
- Automated release workflow (changelog generation, package building)

## [0.0.1] - 2025-11-23

### Added
- Initial project setup with uv package manager
- VendorAdapter ABC with 13 methods
- ClaudeAdapter implementation (200 statements, 95.15% coverage)
- GeminiAdapter implementation (215 statements, 95.47% coverage)
- OpenAIAdapter implementation (242 statements, 95.21% coverage)
- VendorRegistry for centralized adapter management (32 statements, 100% coverage)
- Comprehensive test suite (169 vendor tests, 191 total tests)
- CI/CD pipeline (GitHub Actions: Ubuntu + macOS)
- Pre-commit hooks (ruff, mypy, bandit)
- Quality gates (95%+ coverage, mypy --strict, ruff, bandit)
- Type safety (mypy --strict compliance throughout)
- Security measures (path traversal protection, subprocess safety)

### Technical Details
**Phase 1: Foundation (Completed)**
- Python 3.14, uv for dependency management
- pytest (95%+ coverage), mypy (strict mode), ruff (linting)
- GitHub Actions CI: cross-platform testing (Ubuntu, macOS)
- Pre-commit hooks: automated quality checks

**Phase 2: Vendor Adapters (Completed)**
- ClaudeAdapter: ~/.claude config management, 47 tests
- GeminiAdapter: ~/.gemini config management, 50 tests
- OpenAIAdapter: ~/.codex config management (TOML), 50 tests
- VendorRegistry: Unified vendor interface, 22 tests
- Achieved 95-100% coverage on all vendor code

### Initial Commit
- Project structure established
- Development standards defined
- Quality gates implemented
- Cross-platform CI/CD working

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
# - Generate changelog
# - Create GitHub release
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

- **Repository**: https://github.com/yourusername/ai-asst-mgr
- **Issue Tracker**: https://github.com/yourusername/ai-asst-mgr/issues
- **Releases**: https://github.com/yourusername/ai-asst-mgr/releases
