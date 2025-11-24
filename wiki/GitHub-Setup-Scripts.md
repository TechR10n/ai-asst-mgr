# GitHub Setup Scripts

The `scripts/` directory contains automation tools for setting up the GitHub repository with labels, milestones, and issues.

## Overview

We use GitHub as a **first-class service provider** for project management. These scripts automate the creation of our project infrastructure.

## Scripts

### 1. `setup_github.py` - Master Script

**Purpose**: Run all setup scripts in correct order

**Usage**:
```bash
# Dry run (preview)
python scripts/setup_github.py --dry-run

# Actually create everything
python scripts/setup_github.py
```

**What it does**:
1. Creates all 29 labels
2. Creates 2 milestones
3. Creates all 57 issues

### 2. `create_labels.py` - Create Labels

**Purpose**: Create all GitHub labels for the project

**Labels Created**:
- **Phase labels** (11): `phase-1-foundation` through `phase-10-testing`
- **Priority labels** (3): `priority-high`, `priority-medium`, `priority-low`
- **Type labels** (4): `type-feature`, `type-bug`, `type-docs`, `type-refactor`
- **Vendor labels** (3): `vendor-claude`, `vendor-gemini`, `vendor-openai`
- **Special labels** (3): `good-first-issue`, `help-wanted`, `blocked`

**Usage**:
```bash
# Dry run
python scripts/create_labels.py --dry-run

# Create labels
python scripts/create_labels.py
```

### 3. `create_milestones.py` - Create Milestones

**Purpose**: Create project milestones with due dates

**Milestones**:
1. **MVP (v0.1.0)** - Due 2 weeks from creation
   - Phases 1, 2, 2b, 3, 6
   - Core functionality: vendor management, CLI, backups

2. **Full Release (v1.0.0)** - Due 5 weeks from creation
   - Phases 4, 5, 7, 8, 9, 10
   - Complete feature set: web dashboard, coaching, capabilities

**Usage**:
```bash
# Dry run
python scripts/create_milestones.py --dry-run

# Create milestones
python scripts/create_milestones.py
```

### 4. `create_issues.py` - Create Issues

**Purpose**: Parse `GITHUB_ISSUES.md` and create all 57 issues

**Issue Breakdown**:
- Phase 1: Foundation (4 issues)
- Phase 2: Vendor Adapters (6 issues)
- Phase 2b: Database Migration (4 issues)
- Phase 3: CLI Commands (7 issues)
- Phase 4: Audit System (5 issues)
- Phase 5: Coaching System (6 issues)
- Phase 6: Backup Operations (3 issues)
- Phase 7: Cross-Platform Scheduling (4 issues)
- Phase 8: Capability Abstraction (5 issues)
- Phase 9: Web Dashboard (8 issues)
- Phase 10: Testing & Documentation (5 issues)

**Usage**:
```bash
# Dry run
python scripts/create_issues.py --dry-run

# Create issues
python scripts/create_issues.py
```

## Prerequisites

### 1. Install GitHub CLI

```bash
# macOS
brew install gh

# Linux
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

### 2. Authenticate

```bash
gh auth login
```

Follow the prompts to authenticate with GitHub.

### 3. Verify Authentication

```bash
gh auth status
```

Should show:
```
✓ Logged in to github.com as <username>
✓ Git operations for github.com configured to use https protocol.
```

## Workflow

### First-Time Setup

```bash
# 1. Clone repository
git clone https://github.com/TechR10n/ai-asst-mgr.git
cd ai-asst-mgr

# 2. Preview what will be created
python scripts/setup_github.py --dry-run

# 3. Create everything
python scripts/setup_github.py

# 4. Verify on GitHub
open https://github.com/TechR10n/ai-asst-mgr/issues
open https://github.com/users/TechR10n/projects/5
```

### Adding to Project Board

After issues are created:

1. Go to https://github.com/users/TechR10n/projects/5
2. Click "Add items"
3. Search for issues
4. Add all issues to "Backlog" column

Or use GitHub CLI:
```bash
# Add all issues to project
gh project item-add 5 --owner TechR10n --url https://github.com/TechR10n/ai-asst-mgr/issues/1
# Repeat for all issues, or write a script
```

## Implementation Details

### Parsing GITHUB_ISSUES.md

The `create_issues.py` script parses issues using this structure:

```markdown
## Issue #N: Title
**Labels:** `label1`, `label2`, `label3`
**Milestone:** Milestone Name

### Description
Issue description here

### Tasks
- [ ] Task 1
- [ ] Task 2

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2

### Estimated Time
X hours
```

The parser:
1. Splits on `## Issue #N` pattern
2. Extracts issue number and title
3. Parses labels from `**Labels:**` line
4. Parses milestone from `**Milestone:**` line
5. Captures body from `### Description` onwards

### Label Colors

Labels use specific hex colors for consistency:

```python
phase_colors = {
    "phase-1-foundation": "0052CC",
    "phase-2-vendors": "1D76DB",
    "phase-2b-database": "5319E7",
    # ... etc
}
```

### Dynamic Due Dates

Milestones calculate due dates dynamically:

```python
from datetime import datetime, timedelta

def get_due_date(weeks_from_now: int) -> str:
    due = datetime.now() + timedelta(weeks=weeks_from_now)
    return due.strftime("%Y-%m-%d")
```

This ensures milestones are always relative to when they're created.

## Troubleshooting

### "Label already exists"

This is normal. The script detects existing labels and skips them.

```
⊙ Label already exists: phase-1-foundation
```

### "Milestone already exists"

This is normal. The script detects existing milestones and skips them.

```
⊙ Milestone already exists: MVP (v0.1.0)
```

### Issue creation fails

**Causes**:
1. Labels don't exist yet → Run `create_labels.py` first
2. Milestone doesn't exist → Run `create_milestones.py` first
3. Authentication expired → Run `gh auth login` again

**Solution**:
```bash
# Run in order
python scripts/create_labels.py
python scripts/create_milestones.py
python scripts/create_issues.py
```

### Rate limiting

GitHub API has rate limits. If you hit them:

```bash
# Check rate limit status
gh api rate_limit

# Wait and retry
sleep 60
python scripts/create_issues.py
```

## Maintenance

### Updating Issues

If you need to update issues after creation:

1. **Edit GITHUB_ISSUES.md**
2. **Manually update on GitHub** (recommended for small changes)

Or:

1. **Edit GITHUB_ISSUES.md**
2. **Close old issues**
3. **Re-run script** to create new issues

### Adding New Issues

1. Add to `GITHUB_ISSUES.md` following the format
2. Run `python scripts/create_issues.py`
3. Script will only create new issues (won't duplicate)

## Testing

### Dry Run Mode

Always test with `--dry-run` first:

```bash
python scripts/setup_github.py --dry-run
```

This shows what would be created without actually creating anything.

### Test Repository

For testing script changes:

1. Create a test repository
2. Update repo name in scripts
3. Run scripts against test repo
4. Verify results
5. Delete test repo

## See Also

- [[Development Workflow]] - Branch strategy and PR process
- [[Project Structure]] - Repository organization
- [[Issue Triage]] - How we manage issues
- [GITHUB_ISSUES.md](../GITHUB_ISSUES.md) - All issue details
- [PROJECT_SETUP.md](../PROJECT_SETUP.md) - Complete setup guide

## GitHub Context

These scripts operate in the **SELF context** (see [[GitHub Integration]]):
- Creating issues for ai-asst-mgr development
- Managing our own project infrastructure
- Using ai-asst-mgr to build ai-asst-mgr (dogfooding)
