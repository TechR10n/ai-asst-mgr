# GitHub Issues for ai-asst-mgr

This document contains all issues to be created for the project. Copy each issue into GitHub with the specified labels and milestones.

**Project:** https://github.com/TechR10n/ai-asst-mgr
**GitHub Project Board:** https://github.com/users/TechR10n/projects/5

---

## Labels to Create First

```
Phase Labels:
- phase-1-foundation
- phase-2-vendors
- phase-2b-database
- phase-3-cli
- phase-4-audit
- phase-5-coaching
- phase-6-backup
- phase-7-scheduling
- phase-8-capabilities
- phase-9-web-dashboard
- phase-10-testing

Priority Labels:
- priority-high
- priority-medium
- priority-low

Type Labels:
- type-feature
- type-bug
- type-docs
- type-refactor

Special Labels:
- good-first-issue
- help-wanted
- blocked

Vendor Labels:
- vendor-claude
- vendor-gemini
- vendor-openai
```

---

## Milestones

1. **MVP (v0.1.0)** - Due: Week 2
   - Phases 1, 2, 2b, 3, 6
   - Description: Core functionality with vendor management and backups

2. **Full Release (v1.0.0)** - Due: Week 5
   - All phases complete
   - Description: Complete feature set with web dashboard

---

# Phase 1: Foundation

## Issue #1: Initialize uv project structure
**Labels:** `phase-1-foundation`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Initialize the project with uv package manager and create the basic directory structure.

### Tasks
- [ ] Run `uv init --package ai-asst-mgr`
- [ ] Set Python version to 3.14 in `.python-version`
- [ ] Create `src/ai_asst_mgr/` directory structure
- [ ] Create `__init__.py` with version
- [ ] Create `__main__.py` for `python -m ai_asst_mgr`

### Acceptance Criteria
- [ ] Project initializes with uv
- [ ] Directory structure follows plan
- [ ] Can run `python -m ai_asst_mgr --help` (even if empty)

### Estimated Time
1 hour

---

## Issue #2: Configure pyproject.toml with all dependencies
**Labels:** `phase-1-foundation`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Configure pyproject.toml with all required dependencies and project metadata.

### Tasks
- [ ] Set `requires-python = "==3.14"`
- [ ] Add core dependencies (typer, rich, platformdirs, etc.)
- [ ] Add web dependencies (fastapi, uvicorn)
- [ ] Add dev dependencies (pytest, mypy, ruff)
- [ ] Configure CLI entry point: `ai-asst-mgr = "ai_asst_mgr.cli:app"`
- [ ] Set project metadata (name, version, description, license)
- [ ] Configure build system (hatchling)
- [ ] Configure tool settings (ruff, mypy, pytest)

### Acceptance Criteria
- [ ] All dependencies specified
- [ ] `uv sync` works
- [ ] Project metadata complete
- [ ] Tool configurations present

### Estimated Time
1 hour

---

## Issue #3: Create base directory structure
**Labels:** `phase-1-foundation`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create all subdirectories and placeholder files for the project.

### Tasks
- [ ] Create `src/ai_asst_mgr/vendors/`
- [ ] Create `src/ai_asst_mgr/database/`
- [ ] Create `src/ai_asst_mgr/tracking/`
- [ ] Create `src/ai_asst_mgr/operations/`
- [ ] Create `src/ai_asst_mgr/capabilities/`
- [ ] Create `src/ai_asst_mgr/platform/`
- [ ] Create `src/ai_asst_mgr/web/`
- [ ] Create `tests/` structure
- [ ] Create `docs/` structure
- [ ] Create `data/` structure
- [ ] Add `__init__.py` to all packages

### Acceptance Criteria
- [ ] All directories exist
- [ ] Can import from all packages
- [ ] Structure matches architecture diagram

### Estimated Time
30 minutes

---

## Issue #4: Setup GitHub Actions CI workflow
**Labels:** `phase-1-foundation`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create GitHub Actions workflow for continuous integration.

### Tasks
- [ ] Create `.github/workflows/ci.yml`
- [ ] Configure matrix testing (Ubuntu, macOS)
- [ ] Install uv in workflow
- [ ] Run `uv sync`
- [ ] Run `pytest`
- [ ] Run `mypy src/`
- [ ] Run `ruff check src/`
- [ ] Generate coverage report
- [ ] Add status badge to README

### Acceptance Criteria
- [ ] CI runs on push and PR
- [ ] Tests run on Ubuntu and macOS
- [ ] All quality checks pass
- [ ] Coverage report generated

### Estimated Time
1 hour

---

# Phase 2: Vendor Adapters

## Issue #5: Create VendorAdapter abstract base class
**Labels:** `phase-2-vendors`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create the abstract base class that all vendor adapters will implement.

### Tasks
- [ ] Create `src/ai_asst_mgr/vendors/base.py`
- [ ] Define `VendorInfo` dataclass
- [ ] Define `VendorStatus` enum
- [ ] Create `VendorAdapter` ABC
- [ ] Define all abstract methods:
  - `info` property
  - `is_installed()`
  - `is_configured()`
  - `get_status()`
  - `initialize()`
  - `get_config()`
  - `set_config()`
  - `backup()`
  - `restore()`
  - `sync_from_git()`
  - `health_check()`
  - `audit_config()`
  - `get_usage_stats()`
- [ ] Add comprehensive docstrings
- [ ] Add type hints

### Acceptance Criteria
- [ ] ABC defined with all methods
- [ ] Type hints complete
- [ ] Docstrings comprehensive
- [ ] Can import and use as base class

### Estimated Time
1.5 hours

---

## Issue #6: Implement ClaudeAdapter
**Labels:** `phase-2-vendors`, `vendor-claude`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Implement full vendor adapter for Claude Code.

### Tasks
- [ ] Create `src/ai_asst_mgr/vendors/claude.py`
- [ ] Implement `info` property (config_dir, format, etc.)
- [ ] Implement `is_installed()` (check ~/.claude/)
- [ ] Implement `is_configured()` (check settings.json)
- [ ] Implement `get_status()` (INSTALLED/CONFIGURED/HEALTHY)
- [ ] Implement `initialize()` (create directory structure)
- [ ] Implement `get_config()` (parse settings.json)
- [ ] Implement `set_config()` (update settings.json)
- [ ] Implement `backup()` (tar.gz archive)
- [ ] Implement `restore()` (extract archive)
- [ ] Implement `sync_from_git()` (git clone + copy dirs)
- [ ] Implement `health_check()` (verify directories, parse agents/skills)
- [ ] Add helper: parse YAML frontmatter from agents/*.md
- [ ] Add helper: list agents
- [ ] Add helper: list skills

### Acceptance Criteria
- [ ] All methods implemented
- [ ] Can detect Claude Code installation
- [ ] Can parse agents and skills
- [ ] Health checks work
- [ ] Backup/restore functional

### Estimated Time
2 hours

---

## Issue #7: Implement GeminiAdapter
**Labels:** `phase-2-vendors`, `vendor-gemini`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Implement full vendor adapter for Gemini CLI.

### Tasks
- [ ] Create `src/ai_asst_mgr/vendors/gemini.py`
- [ ] Implement `info` property
- [ ] Implement `is_installed()` (check `gemini` CLI)
- [ ] Implement `is_configured()` (check settings.json + API key)
- [ ] Implement `get_status()`
- [ ] Implement `initialize()` (create ~/.gemini/, settings.json)
- [ ] Implement `get_config()` (parse settings.json)
- [ ] Implement `set_config()`
- [ ] Implement `backup()`
- [ ] Implement `restore()`
- [ ] Implement `sync_from_git()`
- [ ] Implement `health_check()` (CLI installed, API key, GEMINI.md)
- [ ] Add helper: list MCP servers from config
- [ ] Add helper: parse GEMINI.md hierarchy

### Acceptance Criteria
- [ ] All methods implemented
- [ ] Can detect Gemini CLI
- [ ] Can validate API key presence
- [ ] Can list MCP servers
- [ ] Health checks work

### Estimated Time
1.5 hours

---

## Issue #8: Implement OpenAIAdapter
**Labels:** `phase-2-vendors`, `vendor-openai`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Implement full vendor adapter for OpenAI Codex.

### Tasks
- [ ] Create `src/ai_asst_mgr/vendors/openai.py`
- [ ] Implement `info` property
- [ ] Implement `is_installed()` (check `codex` CLI)
- [ ] Implement `is_configured()` (check config.toml)
- [ ] Implement `get_status()`
- [ ] Implement `initialize()` (create ~/.codex/, config.toml)
- [ ] Implement `get_config()` (parse TOML)
- [ ] Implement `set_config()` (update TOML)
- [ ] Implement `backup()`
- [ ] Implement `restore()`
- [ ] Implement `sync_from_git()`
- [ ] Implement `health_check()` (CLI, config, API key, AGENTS.md)
- [ ] Add helper: list profiles from config.toml
- [ ] Add helper: list MCP servers
- [ ] Add helper: parse AGENTS.md hierarchy

### Acceptance Criteria
- [ ] All methods implemented
- [ ] Can detect Codex CLI
- [ ] Can parse TOML config
- [ ] Can list profiles
- [ ] Health checks work

### Estimated Time
1.5 hours

---

## Issue #9: Create VendorRegistry
**Labels:** `phase-2-vendors`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create the central registry for managing all vendor adapters.

### Tasks
- [ ] Update `src/ai_asst_mgr/vendors/__init__.py`
- [ ] Create `VendorRegistry` class
- [ ] Register all three vendors (Claude, Gemini, OpenAI)
- [ ] Implement `get_vendor(name)` method
- [ ] Implement `get_all_vendors()` method
- [ ] Implement `get_installed_vendors()` method
- [ ] Implement `get_configured_vendors()` method
- [ ] Implement `register_vendor()` for extensibility
- [ ] Add vendor name validation

### Acceptance Criteria
- [ ] Can get vendor by name
- [ ] Can list all/installed/configured vendors
- [ ] Can register new vendors
- [ ] Proper error handling for unknown vendors

### Estimated Time
1 hour

---

## Issue #10: Add vendor adapter unit tests
**Labels:** `phase-2-vendors`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create comprehensive unit tests for all vendor adapters.

### Tasks
- [ ] Create `tests/test_vendors/test_claude.py`
- [ ] Create `tests/test_vendors/test_gemini.py`
- [ ] Create `tests/test_vendors/test_openai.py`
- [ ] Create `tests/test_vendors/test_registry.py`
- [ ] Test detection logic (mock directories)
- [ ] Test config parsing (mock config files)
- [ ] Test health checks
- [ ] Test registry methods
- [ ] Add pytest fixtures for temp directories
- [ ] Achieve 80%+ coverage for vendors module

### Acceptance Criteria
- [ ] All adapter methods tested
- [ ] Registry tested
- [ ] Fixtures reusable
- [ ] 80%+ coverage

### Estimated Time
2 hours

---

# Phase 2b: Database Migration

## Issue #11: Create vendor-agnostic database schema
**Labels:** `phase-2b-database`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)
**Status:** ✅ COMPLETED (PR #TBD)

### Description
Create the vendor-agnostic database schema that extends the existing SessionLogger database to support multiple AI vendors (Claude, Gemini, OpenAI, plugins).

### Tasks
- [x] Create `src/ai_asst_mgr/database/migrations/001_vendor_agnostic.sql`
- [x] Define `vendor_profiles` table (vendor registry)
- [x] Define `vendor_versions` table (model costs/capabilities)
- [x] Define `session_costs` table (token usage/costs per session)
- [x] Define `github_integrations` table (GitHub activity attribution)
- [x] Define `capabilities` table (polymorphic agents/skills/MCP servers/tools)
- [x] Extend `sessions` table with vendor columns (vendor_id, actor_type, execution_context)
- [x] Extend `events` table with vendor_id column
- [x] Rename `subagent_profiles` → `claude_agent_profiles`
- [x] Rename `skill_profiles` → `claude_skill_profiles`
- [x] Migrate existing agents/skills to capabilities table
- [x] Create 23 performance indexes
- [x] Seed 3 default vendors (claude, gemini, openai)
- [x] Seed 5 model versions with cost data
- [x] Create 4 analytical views (vendor_comparison, cost_analysis, github_attribution, capability_performance)
- [x] Update schema version to 2.0.0

### Acceptance Criteria
- [x] Complete schema defined
- [x] All tables have proper indexes
- [x] Foreign keys defined with CASCADE
- [x] Views created for analytics
- [x] Schema version tracked in metadata
- [x] Tested on actual database copy (41 agents + skills migrated)

### Actual Time
3 hours (database analysis, schema design, SQL writing, testing)

### Notes
- Migration uses SQLite-compatible syntax (`INSERT OR IGNORE` instead of `ON CONFLICT`)
- Preserves all existing SessionLogger data
- Backwards compatible (existing tables unchanged, only extended)
- Successfully tested: migrated 5 agents + 36 skills to capabilities table

---

## Issue #12: Implement VendorDatabaseManager
**Labels:** `phase-2b-database`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create the VendorDatabaseManager class for vendor-agnostic database operations, querying the new schema views and tables.

### Tasks
- [ ] Create `src/ai_asst_mgr/database/manager.py`
- [ ] Implement `VendorDatabaseManager` class
- [ ] Implement `__init__(db_path)` - connection setup
- [ ] Implement `get_vendor_comparison()` - query vendor_comparison view
- [ ] Implement `get_cost_analysis(vendor_id, days)` - query cost_analysis view
- [ ] Implement `get_github_attribution(vendor_id, activity_type)` - query github_attribution view
- [ ] Implement `get_capability_performance(vendor_id, capability_type)` - query capability_performance view
- [ ] Implement `get_vendor_stats(vendor_id, days)` - aggregated usage stats
- [ ] Implement `get_session_costs(session_id)` - get costs for specific session
- [ ] Implement `track_github_activity(session_id, vendor_id, actor_type, activity_type, github_url)` - log GitHub events
- [ ] Implement `update_capability_usage(vendor_id, capability_type, capability_name)` - increment usage counters
- [ ] Add connection context manager support
- [ ] Add error handling with descriptive messages
- [ ] Add type hints (mypy strict)
- [ ] Write comprehensive docstrings

### Acceptance Criteria
- [ ] All query methods implemented
- [ ] Uses new vendor-agnostic views/tables
- [ ] Proper error handling with user-friendly messages
- [ ] Connection management (context manager)
- [ ] Returns structured data (dataclasses or TypedDicts)
- [ ] Type-safe (mypy --strict passing)
- [ ] Comprehensive unit tests (95%+ coverage)

### Estimated Time
3 hours (implementation + tests)

### Dependencies
- Issue #11 (database schema) - completed

---

## Issue #13: Create VendorSessionTracker
**Labels:** `phase-2b-database`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create a vendor-agnostic session tracking class that logs sessions/events for any AI vendor (Claude, Gemini, OpenAI) to the new database schema.

### Tasks
- [ ] Create `src/ai_asst_mgr/tracking/session_tracker.py`
- [ ] Implement `VendorSessionTracker` class
- [ ] Implement `start_session(vendor_id, project_name, actor_type, execution_context)`
- [ ] Implement `end_session(session_id, outcome, summary)`
- [ ] Implement `log_event(session_id, event_type, details)`
- [ ] Implement `log_tool_call(session_id, tool_name, duration_ms)`
- [ ] Implement `log_agent_spawn(session_id, agent_name)`
- [ ] Implement `log_error(session_id, error_type, error_message)`
- [ ] Implement `track_session_cost(session_id, vendor_id, input_tokens, output_tokens, cost_usd)`
- [ ] Implement `track_github_activity(session_id, vendor_id, actor_type, activity_type, github_url)`
- [ ] Implement credential redaction for sensitive data
- [ ] Add database path using platformdirs
- [ ] Add connection pooling/reuse
- [ ] Add type hints (mypy strict)
- [ ] Write comprehensive docstrings
- [ ] Create unit tests (95%+ coverage)

### Acceptance Criteria
- [ ] Vendor-agnostic (works with any vendor)
- [ ] Logs to new schema tables (sessions, events, session_costs, github_integrations)
- [ ] Credential redaction for API keys/tokens
- [ ] Uses platformdirs for database path
- [ ] Type-safe (mypy --strict passing)
- [ ] Well-tested (95%+ coverage)
- [ ] Clear error messages

### Estimated Time
3 hours (implementation + tests)

### Dependencies
- Issue #11 (database schema) - completed

### Notes
- This is a NEW implementation, not a refactor of existing SessionLogger
- Existing SessionLogger remains in ~/.claude/tools/ for Claude Code
- VendorSessionTracker is for ai-asst-mgr to track ALL vendors

---

## Issue #14: Create database migration framework
**Labels:** `phase-2b-database`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)
**Status:** ✅ COMPLETED (PR #TBD)

### Description
Create a migration framework to safely apply schema changes to the database, with backup and rollback capabilities.

### Tasks
- [x] Create `src/ai_asst_mgr/database/migrate.py`
- [x] Implement `Migration` class (version, name, sql_file)
- [x] Implement `MigrationManager` class
- [x] Implement `discover_migrations()` - find migration files
- [x] Implement `get_current_version()` - read from schema_metadata
- [x] Implement `get_applied_migrations()` - read from _migrations table
- [x] Implement `get_pending_migrations()` - calculate unapplied migrations
- [x] Implement `create_backup()` - backup database before migration
- [x] Implement `apply_migration(migration, dry_run)` - apply single migration
- [x] Implement `upgrade(target_version, dry_run, backup)` - apply all pending
- [x] Implement `validate_schema(expected_version)` - verify version
- [x] Implement `get_migration_status()` - current state
- [x] Implement `migrate_database()` convenience function
- [x] Add migration tracking table (_migrations)
- [x] Add error handling with descriptive messages
- [x] Create comprehensive unit tests (26 tests, 85.79% coverage)
- [x] Test on actual database copy (successful migration to v2.0.0)

### Acceptance Criteria
- [x] Can discover and apply migrations
- [x] Automatic backup creation before migration
- [x] Dry-run mode for validation
- [x] No data loss (verified on test database)
- [x] Rollback via backup restoration
- [x] Version tracking in schema_metadata
- [x] Type-safe (mypy --strict passing)
- [x] Well-tested (26 unit tests passing)

### Actual Time
2.5 hours (implementation + tests + real database testing)

### Dependencies
- Issue #11 (database schema) - completed

### Notes
- Migration framework similar to Alembic but simpler
- Migrations are SQL files named `NNN_name.sql` (e.g., `001_vendor_agnostic.sql`)
- Framework handles multiple migrations in sequence
- Tested successfully on ~/Data/claude-sessions/sessions.db
- Migrated 5 agents + 36 skills without data loss

---

# Phase 3: Core CLI

## Issue #15: Setup Typer CLI application
**Labels:** `phase-3-cli`, `type-feature`, `priority-high`, `duplicate`
**Milestone:** MVP (v0.1.0)
**Status:** ✅ DUPLICATE - Completed in Phase 1 (PR #62)

### Description
Create the main CLI application structure with Typer and Rich.

### Reason for Closure
This issue is a **duplicate**. The Typer CLI application was already created in Phase 1 (Issue #1) as part of the initial project setup.

**Evidence:**
- `src/ai_asst_mgr/cli.py` already exists with 63 lines
- Typer app initialized with Rich console
- Version callback implemented: `ai-asst-mgr --version` works
- Help text working: `ai-asst-mgr --help` works
- Error handling in place
- Three command stubs already created: `status`, `init`, `health`

**Created in:** PR #62 (feat: initial project setup with complete automation)

### Recommendation
**CLOSE** this issue as duplicate and continue with Issue #16 (implement status command) which just needs to wire the existing CLI command to the VendorRegistry.

### Original Estimated Time
1 hour (already spent in Phase 1)

---

## Issue #16: Implement status command
**Labels:** `phase-3-cli`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create the status command to show all vendors and their status.

### Tasks
- [ ] Add `@app.command()` for status
- [ ] Query all vendors from registry
- [ ] Get status for each vendor
- [ ] Check API key status
- [ ] Create Rich table
- [ ] Add color-coded indicators (✓ ✗ ⚠ ○)
- [ ] Add vendor filter option
- [ ] Show config directories
- [ ] Add timing information

### Acceptance Criteria
- [ ] Shows all vendors in table
- [ ] Status indicators accurate
- [ ] API key status shown
- [ ] Can filter by vendor

### Estimated Time
1 hour

---

## Issue #17: Implement init command
**Labels:** `phase-3-cli`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create the init command to initialize vendor configurations.

### Tasks
- [ ] Add `@app.command()` for init
- [ ] Add `--vendor` option (optional)
- [ ] Add `--force` flag
- [ ] If no vendor specified, init all detected
- [ ] Call `vendor.initialize()` for each
- [ ] Add confirmation prompts
- [ ] Show progress with Rich progress bar
- [ ] Report success/failure for each vendor

### Acceptance Criteria
- [ ] Can init single vendor
- [ ] Can init all vendors
- [ ] Force flag works
- [ ] Proper error messages

### Estimated Time
1 hour

---

## Issue #18: Implement health command
**Labels:** `phase-3-cli`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create the health command to run health checks on vendors.

### Tasks
- [ ] Add `@app.command()` for health
- [ ] Add `--vendor` option
- [ ] Add `--verbose` flag
- [ ] Call `vendor.health_check()` for each
- [ ] Display results in Rich table
- [ ] Color-code check results (pass/fail)
- [ ] Show details in verbose mode
- [ ] Suggest fixes for failures
- [ ] Exit code based on results

### Acceptance Criteria
- [ ] Runs all health checks
- [ ] Clear pass/fail indicators
- [ ] Helpful error messages
- [ ] Suggests fixes

### Estimated Time
1 hour

---

## Issue #19: Implement config command
**Labels:** `phase-3-cli`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create the config command to manage configurations.

### Tasks
- [ ] Add `@app.command()` for config
- [ ] Support get: `config KEY`
- [ ] Support set: `config KEY VALUE`
- [ ] Support list: `config --list`
- [ ] Support vendor-specific: `config VENDOR KEY [VALUE]`
- [ ] Handle nested keys with dot notation
- [ ] Display config in Rich table
- [ ] Add validation for values
- [ ] Confirm before setting

### Acceptance Criteria
- [ ] Can list all config
- [ ] Can get specific value
- [ ] Can set value
- [ ] Vendor-specific config works
- [ ] Dot notation works

### Estimated Time
1.5 hours

---

## Issue #20: Implement doctor command
**Labels:** `phase-3-cli`, `type-feature`, `priority-medium`
**Milestone:** MVP (v0.1.0)

### Description
Create the doctor command to diagnose and fix problems.

### Tasks
- [ ] Add `@app.command()` for doctor
- [ ] Run all health checks
- [ ] Detect common issues
- [ ] Suggest fixes
- [ ] Offer to auto-fix where possible
- [ ] Add `--fix` flag for auto-fixes
- [ ] Report what was fixed
- [ ] Show summary at end

### Acceptance Criteria
- [ ] Detects common issues
- [ ] Suggests fixes
- [ ] Can auto-fix with --fix flag
- [ ] Clear reporting

### Estimated Time
1.5 hours

---

## Issue #21: Add CLI unit tests
**Labels:** `phase-3-cli`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create comprehensive tests for all CLI commands.

### Tasks
- [ ] Create `tests/test_cli.py`
- [ ] Use `typer.testing.CliRunner`
- [ ] Test status command
- [ ] Test init command
- [ ] Test health command
- [ ] Test config command
- [ ] Test doctor command
- [ ] Test error handling
- [ ] Test help text
- [ ] Mock vendor adapters
- [ ] Achieve 80%+ coverage

### Acceptance Criteria
- [ ] All commands tested
- [ ] Edge cases covered
- [ ] Mocking works
- [ ] 80%+ coverage

### Estimated Time
2 hours

---

# Phase 4: Audit System

## Issue #22: Create audit framework
**Labels:** `phase-4-audit`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Create the base framework for configuration audits.

### Tasks
- [ ] Create `src/ai_asst_mgr/operations/audit.py`
- [ ] Define `AuditCheck` dataclass
- [ ] Define `AuditCategory` enum (security, config, usage, quality)
- [ ] Define `AuditSeverity` enum (info, warning, error, critical)
- [ ] Create `VendorAuditor` base class
- [ ] Define audit methods: security, configuration, quality
- [ ] Add audit report generation
- [ ] Add JSON export

### Acceptance Criteria
- [ ] Framework complete
- [ ] Base class defined
- [ ] Can generate reports
- [ ] JSON export works

### Estimated Time
1.5 hours

---

## Issue #23: Implement ClaudeAuditor
**Labels:** `phase-4-audit`, `vendor-claude`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Implement Claude-specific configuration audits.

### Tasks
- [ ] Create `ClaudeAuditor` class
- [ ] Check YAML frontmatter validity (agents/skills)
- [ ] Check database connectivity
- [ ] Detect unused agents (no sessions in 30 days)
- [ ] Validate MCP server configs
- [ ] Check file permissions on sensitive files
- [ ] Score agent description quality
- [ ] Validate skill dependencies
- [ ] Check for duplicate agents/skills

### Acceptance Criteria
- [ ] All checks implemented
- [ ] Returns structured results
- [ ] Severity levels accurate
- [ ] Recommendations helpful

### Estimated Time
1.5 hours

---

## Issue #24: Implement GeminiAuditor
**Labels:** `phase-4-audit`, `vendor-gemini`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Implement Gemini-specific configuration audits.

### Tasks
- [ ] Create `GeminiAuditor` class
- [ ] Validate GEMINI.md hierarchy
- [ ] Check MCP server endpoint validity
- [ ] Validate API key format
- [ ] Check model availability
- [ ] Validate context file sizes
- [ ] Check import chain (@file.md syntax)
- [ ] Detect circular imports

### Acceptance Criteria
- [ ] All checks implemented
- [ ] Returns structured results
- [ ] Severity levels accurate
- [ ] Recommendations helpful

### Estimated Time
1 hour

---

## Issue #25: Implement CodexAuditor
**Labels:** `phase-4-audit`, `vendor-openai`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Implement OpenAI Codex-specific configuration audits.

### Tasks
- [ ] Create `CodexAuditor` class
- [ ] Validate AGENTS.md hierarchy
- [ ] Check profile syntax (TOML validation)
- [ ] Validate execpolicy rules
- [ ] Review sandbox settings
- [ ] Check API key vs OAuth status
- [ ] Validate MCP server connectivity
- [ ] Check for unused profiles

### Acceptance Criteria
- [ ] All checks implemented
- [ ] Returns structured results
- [ ] Severity levels accurate
- [ ] Recommendations helpful

### Estimated Time
1 hour

---

## Issue #26: Add audit CLI command
**Labels:** `phase-4-audit`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Create the audit CLI command.

### Tasks
- [ ] Add `@app.command()` for audit
- [ ] Add `--vendor` option
- [ ] Add `--severity` filter
- [ ] Add `--category` filter
- [ ] Display results in Rich table
- [ ] Color-code by severity
- [ ] Add `--export` flag for JSON
- [ ] Show summary statistics
- [ ] Exit code based on severity

### Acceptance Criteria
- [ ] Can audit all vendors
- [ ] Can filter results
- [ ] Clear display
- [ ] JSON export works

### Estimated Time
1 hour

---

# Phase 5: Coaching System

## Issue #27: Create coaching framework
**Labels:** `phase-5-coaching`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Create the base framework for usage coaching and insights.

### Tasks
- [ ] Create `src/ai_asst_mgr/operations/coaching.py`
- [ ] Define `CoachingInsight` dataclass
- [ ] Define `InsightCategory` enum (efficiency, best_practice, optimization, discovery)
- [ ] Define `InsightPriority` enum (low, medium, high)
- [ ] Create `VendorCoach` base class
- [ ] Define methods: analyze_usage, suggest_optimizations, generate_report
- [ ] Add weekly report generation
- [ ] Add cross-vendor comparison

### Acceptance Criteria
- [ ] Framework complete
- [ ] Base class defined
- [ ] Can generate reports
- [ ] Insights actionable

### Estimated Time
1.5 hours

---

## Issue #28: Implement ClaudeCoach
**Labels:** `phase-5-coaching`, `vendor-claude`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Implement Claude-specific usage coaching.

### Tasks
- [ ] Create `ClaudeCoach` class
- [ ] Query sessions.db for usage patterns
- [ ] Identify most/least used agents
- [ ] Analyze tool call frequencies
- [ ] Track session durations
- [ ] Detect parallel operation patterns
- [ ] Calculate productivity metrics
- [ ] Generate specific recommendations:
  - Unused agents (suggest removal)
  - Frequent patterns (suggest new agents)
  - Session optimization
  - Skill suggestions

### Acceptance Criteria
- [ ] Queries database correctly
- [ ] Insights data-driven
- [ ] Recommendations specific
- [ ] Priority levels accurate

### Estimated Time
2 hours

---

## Issue #29: Implement GeminiCoach
**Labels:** `phase-5-coaching`, `vendor-gemini`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Implement Gemini-specific usage coaching.

### Tasks
- [ ] Create `GeminiCoach` class
- [ ] Analyze GEMINI.md file sizes
- [ ] Track MCP server usage patterns
- [ ] Analyze model selection
- [ ] Detect context optimization opportunities
- [ ] Generate recommendations:
  - Split large GEMINI.md files
  - Remove unused MCP servers
  - Model selection optimization
  - Context file organization

### Acceptance Criteria
- [ ] Analyzes configs correctly
- [ ] Insights helpful
- [ ] Recommendations actionable
- [ ] Priority levels accurate

### Estimated Time
1 hour

---

## Issue #30: Implement CodexCoach
**Labels:** `phase-5-coaching`, `vendor-openai`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Implement OpenAI Codex-specific usage coaching.

### Tasks
- [ ] Create `CodexCoach` class
- [ ] Analyze profile usage patterns
- [ ] Track exec command approvals
- [ ] Monitor AGENTS.md coverage
- [ ] Analyze model selection
- [ ] Generate recommendations:
  - Remove unused profiles
  - Optimize sandbox settings
  - Add AGENTS.md to projects
  - Profile optimization

### Acceptance Criteria
- [ ] Analyzes configs correctly
- [ ] Insights helpful
- [ ] Recommendations actionable
- [ ] Priority levels accurate

### Estimated Time
1 hour

---

## Issue #31: Add coach CLI command
**Labels:** `phase-5-coaching`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Create the coach CLI command.

### Tasks
- [ ] Add `@app.command()` for coach
- [ ] Add `--vendor` option
- [ ] Add `--report` option (weekly, monthly)
- [ ] Add `--compare` flag (cross-vendor)
- [ ] Add `--export` flag (JSON)
- [ ] Display insights in Rich panels
- [ ] Color-code by priority
- [ ] Show weekly stats
- [ ] Generate comprehensive reports

### Acceptance Criteria
- [ ] Can coach all vendors
- [ ] Weekly reports work
- [ ] Cross-vendor comparison works
- [ ] Clear, actionable output

### Estimated Time
1.5 hours

---

# Phase 6: Backup & Sync

## Issue #32: Implement backup operations
**Labels:** `phase-6-backup`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create backup functionality for vendor configurations.

### Tasks
- [ ] Create `src/ai_asst_mgr/operations/backup.py`
- [ ] Implement `backup_vendor(vendor, backup_dir)` function
- [ ] Create timestamped tar.gz archives
- [ ] Implement retention policy (keep last N)
- [ ] Add incremental backup support
- [ ] Implement `backup_all_vendors()` function
- [ ] Add progress indicators
- [ ] Verify backup integrity

### Acceptance Criteria
- [ ] Can backup single vendor
- [ ] Can backup all vendors
- [ ] Archives created correctly
- [ ] Retention policy works
- [ ] Verification works

### Estimated Time
1.5 hours

---

## Issue #33: Implement restore operations
**Labels:** `phase-6-backup`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create restore functionality from backups.

### Tasks
- [ ] Implement `restore_vendor(backup_path, vendor)` function
- [ ] Validate backup before restore
- [ ] Add confirmation prompt
- [ ] Create backup of current state before restore
- [ ] Extract archive to correct location
- [ ] Verify restore success
- [ ] Add rollback capability
- [ ] Selective restore (specific directories)

### Acceptance Criteria
- [ ] Can restore from backup
- [ ] Validation works
- [ ] Confirmation prompts present
- [ ] Rollback works

### Estimated Time
1 hour

---

## Issue #34: Implement git sync operations
**Labels:** `phase-6-backup`, `type-feature`, `priority-medium`
**Milestone:** MVP (v0.1.0)

### Description
Create git synchronization functionality.

### Tasks
- [ ] Create `src/ai_asst_mgr/operations/sync.py`
- [ ] Implement `sync_from_git(vendor, repo_url, branch)` function
- [ ] Clone repo to temp directory
- [ ] Copy vendor-specific directories:
  - Claude: agents/, skills/, commands/
  - Gemini: GEMINI.md, MCP configs
  - OpenAI: AGENTS.md, profiles, execpolicy
- [ ] Implement merge strategies
- [ ] Detect conflicts
- [ ] Add dry-run mode
- [ ] Show diff before syncing

### Acceptance Criteria
- [ ] Can sync from git
- [ ] Merge strategies work
- [ ] Conflict detection works
- [ ] Dry-run mode works

### Estimated Time
1.5 hours

---

## Issue #35: Add backup/restore/sync CLI commands
**Labels:** `phase-6-backup`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Create CLI commands for backup, restore, and sync operations.

### Tasks
- [ ] Add `@app.command()` for backup
- [ ] Add `@app.command()` for restore
- [ ] Add `@app.command()` for sync
- [ ] Add appropriate options and flags
- [ ] Display progress with Rich
- [ ] Show backup location on completion
- [ ] Add listing backups command
- [ ] Test all commands

### Acceptance Criteria
- [ ] All commands work
- [ ] Progress indicators clear
- [ ] Error handling robust
- [ ] Help text comprehensive

### Estimated Time
1 hour

---

# Phase 7: Cross-Platform Scheduling

## Issue #36: Create platform abstraction base
**Labels:** `phase-7-scheduling`, `type-feature`, `priority-medium`
**Milestone:** Full Release (v1.0.0)

### Description
Create abstract base class for platform-specific scheduling.

### Tasks
- [ ] Create `src/ai_asst_mgr/platform/base.py`
- [ ] Define `IntervalType` enum
- [ ] Create `PlatformBackupScheduler` ABC
- [ ] Define abstract methods:
  - `setup_schedule(script_path, interval)`
  - `remove_schedule()`
  - `is_scheduled()`
- [ ] Add platform detection function

### Acceptance Criteria
- [ ] ABC defined
- [ ] All methods specified
- [ ] Platform detection works

### Estimated Time
45 minutes

---

## Issue #37: Implement macOS LaunchAgent scheduler
**Labels:** `phase-7-scheduling`, `type-feature`, `priority-medium`
**Milestone:** Full Release (v1.0.0)

### Description
Implement backup scheduling for macOS using LaunchAgent.

### Tasks
- [ ] Create `src/ai_asst_mgr/platform/macos.py`
- [ ] Create `MacOSScheduler` class
- [ ] Implement `setup_schedule()` - create plist
- [ ] Map intervals to StartCalendarInterval
- [ ] Write plist to ~/Library/LaunchAgents/
- [ ] Load agent with launchctl
- [ ] Implement `remove_schedule()` - unload and remove
- [ ] Implement `is_scheduled()` - check launchctl list
- [ ] Setup logging

### Acceptance Criteria
- [ ] Can create LaunchAgent
- [ ] Agent runs on schedule
- [ ] Logs to file
- [ ] Can remove agent

### Estimated Time
1.5 hours

---

## Issue #38: Implement Linux cron scheduler
**Labels:** `phase-7-scheduling`, `type-feature`, `priority-medium`
**Milestone:** Full Release (v1.0.0)

### Description
Implement backup scheduling for Linux using cron.

### Tasks
- [ ] Create `src/ai_asst_mgr/platform/linux.py`
- [ ] Create `LinuxScheduler` class
- [ ] Implement `setup_schedule()` - add cron job
- [ ] Map intervals to cron expressions
- [ ] Add marker comment for identification
- [ ] Update crontab safely
- [ ] Implement `remove_schedule()` - remove job
- [ ] Implement `is_scheduled()` - check crontab

### Acceptance Criteria
- [ ] Can add cron job
- [ ] Job runs on schedule
- [ ] Can remove job
- [ ] Safe crontab updates

### Estimated Time
1 hour

---

# Phase 8: Capability Abstraction

## Issue #39: Create capability base classes
**Labels:** `phase-8-capabilities`, `type-feature`, `priority-medium`
**Milestone:** Full Release (v1.0.0)

### Description
Create abstract interfaces for capability abstraction.

### Tasks
- [ ] Create `src/ai_asst_mgr/capabilities/base.py`
- [ ] Define `Agent` dataclass
- [ ] Define `Skill` dataclass
- [ ] Create `AgentCapability` ABC
- [ ] Create `SkillCapability` ABC
- [ ] Define all abstract methods:
  - `list_agents/skills()`
  - `create_agent/skill()`
  - `invoke_agent/skill()`
  - `get_usage()`
- [ ] Add comprehensive docstrings

### Acceptance Criteria
- [ ] All interfaces defined
- [ ] Dataclasses complete
- [ ] ABCs have all methods
- [ ] Docstrings comprehensive

### Estimated Time
1.5 hours

---

## Issue #40: Implement Claude capabilities
**Labels:** `phase-8-capabilities`, `vendor-claude`, `type-feature`, `priority-medium`
**Milestone:** Full Release (v1.0.0)

### Description
Implement capability adapters for Claude (native).

### Tasks
- [ ] Create `src/ai_asst_mgr/capabilities/claude_agent.py`
- [ ] Create `src/ai_asst_mgr/capabilities/claude_skill.py`
- [ ] Implement `ClaudeAgentCapability` - native agents
- [ ] Implement `ClaudeSkillCapability` - native skills
- [ ] List from agents/*.md and skills/*/SKILL.md
- [ ] Parse YAML frontmatter
- [ ] Get usage from database
- [ ] Create new agents/skills

### Acceptance Criteria
- [ ] Can list agents/skills
- [ ] Can create agents/skills
- [ ] Usage data accurate
- [ ] Native format preserved

### Estimated Time
1.5 hours

---

## Issue #41: Implement Gemini capabilities
**Labels:** `phase-8-capabilities`, `vendor-gemini`, `type-feature`, `priority-medium`
**Milestone:** Full Release (v1.0.0)

### Description
Implement capability adapters for Gemini (via A2A MCP).

### Tasks
- [ ] Create `src/ai_asst_mgr/capabilities/gemini_agent.py`
- [ ] Create `src/ai_asst_mgr/capabilities/gemini_tool.py`
- [ ] Implement `GeminiAgentCapability` - via A2A MCP
- [ ] List MCP servers as "agents"
- [ ] Create agents by adding MCP server configs
- [ ] Update settings.json and GEMINI.md
- [ ] Implement tool listing

### Acceptance Criteria
- [ ] Can list MCP servers as agents
- [ ] Can create MCP agents
- [ ] Settings.json updated correctly
- [ ] GEMINI.md updated

### Estimated Time
1 hour

---

## Issue #42: Implement Codex capabilities
**Labels:** `phase-8-capabilities`, `vendor-openai`, `type-feature`, `priority-medium`
**Milestone:** Full Release (v1.0.0)

### Description
Implement capability adapters for Codex (via MCP + AGENTS.md).

### Tasks
- [ ] Create `src/ai_asst_mgr/capabilities/codex_agent.py`
- [ ] Create `src/ai_asst_mgr/capabilities/codex_tool.py`
- [ ] Implement `CodexAgentCapability` - via MCP
- [ ] List MCP servers as "agents"
- [ ] Create agents by adding MCP + AGENTS.md entry
- [ ] Update config.toml and AGENTS.md
- [ ] Implement tool listing

### Acceptance Criteria
- [ ] Can list MCP servers as agents
- [ ] Can create MCP agents
- [ ] config.toml updated correctly
- [ ] AGENTS.md updated

### Estimated Time
1 hour

---

## Issue #43: Create UniversalAgentManager
**Labels:** `phase-8-capabilities`, `type-feature`, `priority-medium`
**Milestone:** Full Release (v1.0.0)

### Description
Create the universal agent manager for cross-vendor operations.

### Tasks
- [ ] Create `src/ai_asst_mgr/capabilities/manager.py`
- [ ] Create `UniversalAgentManager` class
- [ ] Initialize capabilities for all vendors
- [ ] Implement `list_all_agents()` - unified view
- [ ] Implement `create_agent_for_vendor()`
- [ ] Implement `sync_agent_across_vendors()`
- [ ] Handle vendor-specific features
- [ ] Add filtering and search

### Acceptance Criteria
- [ ] Lists agents from all vendors
- [ ] Can create for any vendor
- [ ] Can sync across vendors
- [ ] Unified interface works

### Estimated Time
1.5 hours

---

## Issue #44: Add agents CLI command
**Labels:** `phase-8-capabilities`, `type-feature`, `priority-medium`
**Milestone:** Full Release (v1.0.0)

### Description
Create CLI commands for universal agent management.

### Tasks
- [ ] Add `@app.command()` for agents
- [ ] Add subcommands: list, create, sync
- [ ] Implement `agents list` - show all agents
- [ ] Implement `agents create` - create new agent
- [ ] Implement `agents sync` - sync across vendors
- [ ] Add filtering options
- [ ] Display in Rich table
- [ ] Add usage statistics

### Acceptance Criteria
- [ ] All subcommands work
- [ ] Can list unified agents
- [ ] Can create for specific vendor
- [ ] Can sync across vendors

### Estimated Time
1.5 hours

---

# Phase 9: Web Dashboard

## Issue #45: Setup FastAPI application
**Labels:** `phase-9-web-dashboard`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Create the FastAPI application structure for web dashboard.

### Tasks
- [ ] Create `src/ai_asst_mgr/web/app.py`
- [ ] Initialize FastAPI app
- [ ] Configure static files mounting
- [ ] Setup Jinja2 templates
- [ ] Create AppState for managers
- [ ] Add startup/shutdown hooks
- [ ] Configure CORS if needed
- [ ] Add error handlers

### Acceptance Criteria
- [ ] FastAPI app initializes
- [ ] Static files served
- [ ] Templates render
- [ ] Can start with uvicorn

### Estimated Time
1 hour

---

## Issue #46: Create base template and navigation
**Labels:** `phase-9-web-dashboard`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Create the base HTML template with navigation and styling.

### Tasks
- [ ] Create `src/ai_asst_mgr/web/templates/base.html`
- [ ] Add HTML structure
- [ ] Include HTMX, Alpine.js, Chart.js
- [ ] Include Tailwind CSS (CDN)
- [ ] Create navigation bar
- [ ] Add loading indicators
- [ ] Add footer
- [ ] Style with Tailwind

### Acceptance Criteria
- [ ] Base template complete
- [ ] All libraries included
- [ ] Navigation works
- [ ] Responsive design

### Estimated Time
1 hour

---

## Issue #47: Implement dashboard page
**Labels:** `phase-9-web-dashboard`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Create the main dashboard page with metrics and charts.

### Tasks
- [ ] Create `src/ai_asst_mgr/web/routes/dashboard.py`
- [ ] Create `src/ai_asst_mgr/web/templates/dashboard.html`
- [ ] Add route for main dashboard page
- [ ] Create HTMX endpoint for metrics cards
- [ ] Create HTMX endpoint for chart data
- [ ] Create HTMX endpoint for insights
- [ ] Create metrics card component
- [ ] Create chart component (Chart.js)
- [ ] Create insights component
- [ ] Add auto-refresh with HTMX

### Acceptance Criteria
- [ ] Dashboard loads
- [ ] Metrics display correctly
- [ ] Chart renders
- [ ] Insights shown
- [ ] Auto-refresh works

### Estimated Time
2 hours

---

## Issue #48: Implement weekly review page
**Labels:** `phase-9-web-dashboard`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Create the weekly performance review page.

### Tasks
- [ ] Create `src/ai_asst_mgr/web/routes/review.py`
- [ ] Create `src/ai_asst_mgr/web/templates/review.html`
- [ ] Add route for review page
- [ ] Create review form with fields:
  - What went well
  - Challenges
  - Goals
  - Rating (1-5 stars)
- [ ] Add HTMX form submission
- [ ] Show AI insights sidebar
- [ ] Display week statistics
- [ ] Show previous reviews
- [ ] Add export to PDF

### Acceptance Criteria
- [ ] Form loads and works
- [ ] HTMX submission works
- [ ] Data saves to database
- [ ] AI insights displayed
- [ ] Previous reviews shown

### Estimated Time
2 hours

---

## Issue #49: Implement agent browser page
**Labels:** `phase-9-web-dashboard`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Create the universal agent browser page.

### Tasks
- [ ] Create `src/ai_asst_mgr/web/routes/agents.py`
- [ ] Create `src/ai_asst_mgr/web/templates/agents.html`
- [ ] Add route for agents page
- [ ] Display all agents in cards
- [ ] Add search functionality (HTMX)
- [ ] Add vendor filter (HTMX)
- [ ] Create agent details modal
- [ ] Show usage statistics
- [ ] Add create agent button
- [ ] Implement agent creation form

### Acceptance Criteria
- [ ] Agents displayed
- [ ] Search works
- [ ] Filters work
- [ ] Details modal works
- [ ] Can create agents

### Estimated Time
2 hours

---

## Issue #50: Create HTMX components
**Labels:** `phase-9-web-dashboard`, `type-feature`, `priority-medium`
**Milestone:** Full Release (v1.0.0)

### Description
Create reusable HTMX components for the dashboard.

### Tasks
- [ ] Create `templates/components/metrics_card.html`
- [ ] Create `templates/components/chart_section.html`
- [ ] Create `templates/components/insights_list.html`
- [ ] Create `templates/components/agent_card.html`
- [ ] Create `templates/components/agent_list.html`
- [ ] Create `templates/components/agent_details.html`
- [ ] Style with Tailwind
- [ ] Test HTMX swapping

### Acceptance Criteria
- [ ] All components render
- [ ] HTMX swapping works
- [ ] Components reusable
- [ ] Styling consistent

### Estimated Time
1.5 hours

---

## Issue #51: Add serve CLI command
**Labels:** `phase-9-web-dashboard`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Create the serve CLI command to start the web dashboard.

### Tasks
- [ ] Add `@app.command()` for serve
- [ ] Add `--host` option (default 127.0.0.1)
- [ ] Add `--port` option (default 8080)
- [ ] Add `--reload` flag (dev mode)
- [ ] Start uvicorn server
- [ ] Display URL to user
- [ ] Handle keyboard interrupt gracefully

### Acceptance Criteria
- [ ] Command starts server
- [ ] Options work
- [ ] URL displayed
- [ ] Can stop with Ctrl+C

### Estimated Time
30 minutes

---

## Issue #52: Add web dashboard API endpoints
**Labels:** `phase-9-web-dashboard`, `type-feature`, `priority-low`
**Milestone:** Full Release (v1.0.0)

### Description
Create JSON API endpoints for external tools.

### Tasks
- [ ] Create `src/ai_asst_mgr/web/routes/api.py`
- [ ] Add `/api/stats` - overall statistics
- [ ] Add `/api/vendors` - vendor list with status
- [ ] Add `/api/coaching` - coaching insights
- [ ] Add `/api/agents` - agent list
- [ ] Return JSON responses
- [ ] Add API documentation
- [ ] Add rate limiting (optional)

### Acceptance Criteria
- [ ] All endpoints work
- [ ] JSON responses correct
- [ ] Documentation clear

### Estimated Time
1 hour

---

# Phase 10: Testing & Documentation

## Issue #53: Add comprehensive unit tests
**Labels:** `phase-10-testing`, `type-feature`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Ensure 80%+ test coverage across all modules.

### Tasks
- [ ] Add tests for database module
- [ ] Add tests for tracking module
- [ ] Add tests for operations module
- [ ] Add tests for capabilities module
- [ ] Add tests for platform module
- [ ] Add tests for web routes
- [ ] Add integration tests
- [ ] Achieve 80%+ coverage
- [ ] Fix any failing tests

### Acceptance Criteria
- [ ] All modules tested
- [ ] 80%+ coverage
- [ ] All tests pass
- [ ] CI passes

### Estimated Time
3 hours

---

## Issue #54: Write comprehensive documentation
**Labels:** `phase-10-testing`, `type-docs`, `priority-high`
**Milestone:** Full Release (v1.0.0)

### Description
Create complete user and developer documentation.

### Tasks
- [ ] Write `docs/installation.md`
- [ ] Write `docs/commands.md` - complete CLI reference
- [ ] Write `docs/auditing.md`
- [ ] Write `docs/coaching.md`
- [ ] Write `docs/architecture.md`
- [ ] Write `docs/vendors/claude.md`
- [ ] Write `docs/vendors/gemini.md`
- [ ] Write `docs/vendors/openai.md`
- [ ] Write `docs/api/web-api.md`
- [ ] Add screenshots where helpful
- [ ] Review and edit all docs

### Acceptance Criteria
- [ ] All docs complete
- [ ] Clear and helpful
- [ ] Examples included
- [ ] Screenshots added

### Estimated Time
3 hours

---

## Issue #55: Create GitHub release workflow
**Labels:** `phase-10-testing`, `type-feature`, `priority-medium`
**Milestone:** Full Release (v1.0.0)

### Description
Setup automated GitHub releases.

### Tasks
- [ ] Create `.github/workflows/release.yml`
- [ ] Trigger on version tags
- [ ] Build package with uv
- [ ] Generate changelog
- [ ] Create GitHub release
- [ ] Attach wheel file
- [ ] Publish release notes

### Acceptance Criteria
- [ ] Workflow triggers on tags
- [ ] Release created automatically
- [ ] Wheel attached
- [ ] Changelog generated

### Estimated Time
1 hour

---

## Issue #56: Update README with examples
**Labels:** `phase-10-testing`, `type-docs`, `priority-medium`
**Milestone:** Full Release (v1.0.0)

### Description
Enhance README with real examples and screenshots.

### Tasks
- [ ] Add usage examples
- [ ] Add screenshots of CLI
- [ ] Add screenshots of web dashboard
- [ ] Add GIFs of key features
- [ ] Update feature list
- [ ] Update roadmap with completion status
- [ ] Add badges (build, coverage)
- [ ] Review and polish

### Acceptance Criteria
- [ ] Examples clear
- [ ] Screenshots added
- [ ] Badges working
- [ ] Professional appearance

### Estimated Time
1 hour

---

## Issue #57: Create CHANGELOG.md
**Labels:** `phase-10-testing`, `type-docs`, `priority-low`
**Milestone:** Full Release (v1.0.0)

### Description
Document all changes in CHANGELOG.

### Tasks
- [ ] Create `CHANGELOG.md`
- [ ] Follow Keep a Changelog format
- [ ] Document all features added
- [ ] Document bug fixes
- [ ] Document breaking changes
- [ ] Group by version
- [ ] Add release dates

### Acceptance Criteria
- [ ] CHANGELOG complete
- [ ] Format correct
- [ ] All changes documented

### Estimated Time
30 minutes

---

# Phase 11: Enhanced MVP Features

## Issue #58: Configuration Schema Validation
**Labels:** `phase-11-enhanced`, `type-feature`, `priority-medium`
**Milestone:** MVP (v0.1.0)

### Description
Implement JSON/TOML schema validation for vendor configurations with better error messages when configs are malformed.

### Tasks
- [ ] Create `src/ai_asst_mgr/validation/schemas.py`
- [ ] Define JSON Schema for Claude settings.json
- [ ] Define TOML Schema for OpenAI config.toml
- [ ] Define JSON Schema for Gemini settings.json
- [ ] Implement `validate_config(vendor, config_dict)` function
- [ ] Generate user-friendly error messages for validation failures
- [ ] Add `--validate` flag to `ai-asst-mgr config` command
- [ ] Integrate validation into adapter `set_config()` methods
- [ ] Add validation to `ai-asst-mgr doctor` command
- [ ] Write comprehensive unit tests (95%+ coverage)

### Acceptance Criteria
- [ ] All vendor config formats validated
- [ ] Clear error messages (e.g., "Missing required field 'api_key' in settings.json")
- [ ] Integrated into config commands
- [ ] Type-safe (mypy --strict passing)
- [ ] Well-tested (95%+ coverage)

### Estimated Time
2 hours

---

## Issue #59: Plugin Architecture
**Labels:** `phase-11-enhanced`, `type-feature`, `priority-medium`
**Milestone:** MVP (v0.1.0)

### Description
Allow users to add custom vendor adapters via plugin system, enabling support for vendors beyond Claude/Gemini/OpenAI.

### Tasks
- [ ] Create `src/ai_asst_mgr/plugins/loader.py`
- [ ] Define plugin interface (must inherit from VendorAdapter)
- [ ] Implement `discover_plugins(plugin_dir)` - find plugins in ~/.ai-asst-mgr/plugins/
- [ ] Implement `load_plugin(plugin_path)` - dynamically import plugin class
- [ ] Implement `register_plugin(vendor_id, plugin_class)` - add to VendorRegistry
- [ ] Create example plugin template at `docs/examples/custom_vendor_plugin.py`
- [ ] Add `ai-asst-mgr plugins list` command
- [ ] Add `ai-asst-mgr plugins validate <path>` command
- [ ] Document plugin development guide
- [ ] Write comprehensive unit tests (95%+ coverage)

### Acceptance Criteria
- [ ] Can discover plugins from ~/.ai-asst-mgr/plugins/
- [ ] Can load and register custom vendors
- [ ] Example plugin template provided
- [ ] CLI commands for plugin management
- [ ] Clear documentation for plugin development
- [ ] Type-safe (mypy --strict passing)
- [ ] Well-tested (95%+ coverage)

### Estimated Time
3 hours

---

## Issue #60: Dry-Run Mode
**Labels:** `phase-11-enhanced`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Add `--dry-run` flag to all destructive operations to preview changes before applying them, improving safety for production use.

### Tasks
- [ ] Add `--dry-run` global flag to CLI
- [ ] Implement dry-run for `ai-asst-mgr init` (show what would be created)
- [ ] Implement dry-run for `ai-asst-mgr config set` (show what would change)
- [ ] Implement dry-run for `ai-asst-mgr backup` (show what would be backed up)
- [ ] Implement dry-run for `ai-asst-mgr restore` (show what would be restored)
- [ ] Implement dry-run for `ai-asst-mgr sync` (show what would be synced)
- [ ] Add clear output prefix: `[DRY RUN]` for all dry-run operations
- [ ] Add `--dry-run` to all VendorAdapter methods that modify state
- [ ] Update documentation with dry-run examples
- [ ] Write comprehensive unit tests (95%+ coverage)

### Acceptance Criteria
- [ ] All destructive operations support --dry-run
- [ ] Clear indication when running in dry-run mode
- [ ] No actual changes made in dry-run mode
- [ ] Output shows exactly what would happen
- [ ] Type-safe (mypy --strict passing)
- [ ] Well-tested (95%+ coverage)

### Estimated Time
2.5 hours

---

## Issue #61: Config Diff Tool
**Labels:** `phase-11-enhanced`, `type-feature`, `priority-low`
**Milestone:** MVP (v0.1.0)

### Description
Implement `ai-asst-mgr diff` command to compare configurations across vendors or compare local vs remote (git).

### Tasks
- [ ] Create `src/ai_asst_mgr/operations/diff.py`
- [ ] Implement `compare_configs(vendor1, vendor2)` - compare two vendor configs
- [ ] Implement `compare_with_git(vendor, git_url, branch)` - compare local vs remote
- [ ] Implement Rich-formatted diff output (side-by-side with colors)
- [ ] Add `ai-asst-mgr diff <vendor1> <vendor2>` command
- [ ] Add `ai-asst-mgr diff <vendor> --git <url>` command
- [ ] Add `--format` option (unified, side-by-side, json)
- [ ] Support nested config comparison (handle JSON/TOML structures)
- [ ] Highlight meaningful differences (ignore whitespace, formatting)
- [ ] Write comprehensive unit tests (95%+ coverage)

### Acceptance Criteria
- [ ] Can compare configs across vendors
- [ ] Can compare local vs remote git configs
- [ ] Rich-formatted, colored diff output
- [ ] Multiple output formats supported
- [ ] Type-safe (mypy --strict passing)
- [ ] Well-tested (95%+ coverage)

### Estimated Time
2.5 hours

---

## Issue #62: Automated Config Fixes (doctor --fix)
**Labels:** `phase-11-enhanced`, `type-feature`, `priority-high`
**Milestone:** MVP (v0.1.0)

### Description
Add `--fix` flag to `ai-asst-mgr doctor` command to automatically fix common issues (permissions, missing directories, etc.).

### Tasks
- [ ] Add `--fix` flag to doctor command
- [ ] Implement auto-fix for missing directories (create them)
- [ ] Implement auto-fix for incorrect permissions (chmod 700 for config dirs)
- [ ] Implement auto-fix for missing config files (create defaults)
- [ ] Implement auto-fix for malformed JSON/TOML (offer to recreate)
- [ ] Implement guided setup for missing API keys (interactive prompts)
- [ ] Add confirmation prompts for destructive fixes (unless --yes flag)
- [ ] Add `--yes` flag to skip confirmations
- [ ] Log all fixes to stdout with clear messages
- [ ] Write comprehensive unit tests (95%+ coverage)

### Acceptance Criteria
- [ ] Can fix common configuration issues automatically
- [ ] Clear confirmation prompts for destructive actions
- [ ] Detailed output of what was fixed
- [ ] Safe defaults (no data loss)
- [ ] Type-safe (mypy --strict passing)
- [ ] Well-tested (95%+ coverage)

### Estimated Time
3 hours

---

## Issue #63: Health Score Dashboard (Rich TUI)
**Labels:** `phase-11-enhanced`, `type-feature`, `priority-medium`
**Milestone:** MVP (v0.1.0)

### Description
Create a real-time Terminal UI dashboard using Rich to display health scores and status for all vendors, replacing the basic text output.

### Tasks
- [ ] Create `src/ai_asst_mgr/ui/dashboard.py`
- [ ] Implement Rich Live display with auto-refresh
- [ ] Create health score gauge (0-100) with color coding
- [ ] Create vendor status table with live updates
- [ ] Display key metrics: installed, configured, healthy, agents/skills count
- [ ] Add color coding: green (healthy), yellow (warning), red (error)
- [ ] Add `ai-asst-mgr dashboard` command
- [ ] Add `--refresh` option (default: 5 seconds)
- [ ] Add keyboard shortcuts: q (quit), r (refresh now), h (help)
- [ ] Make dashboard responsive to terminal size
- [ ] Write comprehensive unit tests (95%+ coverage)

### Acceptance Criteria
- [ ] Real-time dashboard with auto-refresh
- [ ] Health scores calculated and displayed
- [ ] Color-coded status indicators
- [ ] Keyboard navigation working
- [ ] Terminal responsive design
- [ ] Type-safe (mypy --strict passing)
- [ ] Well-tested (95%+ coverage)

### Estimated Time
3 hours

---

## Summary Statistics

**Total Issues:** 63 (originally 57, added 6 new features)
**Phases:** 11 (added Phase 11: Enhanced MVP Features)
**Milestones:** 2
- MVP (v0.1.0): 30 issues (24 original + 6 new)
- Full Release (v1.0.0): 33 issues

**By Priority:**
- High: 44 issues (+2: dry-run, automated fixes)
- Medium: 17 issues (+4: schema validation, plugins, dashboard, config diff)
- Low: 2 issues

**By Type:**
- Feature: 59 issues (+6 new features)
- Docs: 3 issues
- Refactor: 1 issue

**Estimated Total Time:** ~86 hours (70 hours original + 16 hours new features)

**New Features Added (Phase 11):**
1. Issue #58: Configuration Schema Validation (2h)
2. Issue #59: Plugin Architecture (3h)
3. Issue #60: Dry-Run Mode (2.5h)
4. Issue #61: Config Diff Tool (2.5h)
5. Issue #62: Automated Config Fixes (3h)
6. Issue #63: Health Score Dashboard (3h)

---

## Next Steps

1. Create all labels in GitHub
2. Create both milestones
3. Create all 57 issues
4. Add issues to GitHub Project board
5. Start with Phase 1, Issue #1

Use this document as a reference when creating issues in GitHub.
