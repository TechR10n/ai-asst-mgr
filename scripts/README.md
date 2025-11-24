# Setup Scripts

This directory contains automation scripts for complete GitHub repository setup and configuration.

## Prerequisites

1. **Install GitHub CLI:**
   ```bash
   brew install gh
   ```

2. **Authenticate:**
   ```bash
   gh auth login
   ```

3. **Verify authentication:**
   ```bash
   gh auth status
   ```

## 🚀 Quick Start (Recommended)

**Run complete bootstrap (everything at once):**
```bash
# Preview all changes (dry run)
python scripts/bootstrap_repository.py --dry-run

# Actually apply all changes
python scripts/bootstrap_repository.py
```

This will:
1. **Configure repository** (visibility, features, security, branch protection)
2. **Create 29 labels** (phases, priorities, types, vendors)
3. **Create 2 milestones** (MVP v0.1.0, Full Release v1.0.0)
4. **Create 57 issues** (all organized by phase)
5. **Verify configuration**

**Total time: ~3-5 minutes** ⏱️

## Scripts Overview

### 🎯 Master Scripts (Use These)

#### `bootstrap_repository.py` - Complete Setup
**Purpose**: Run everything in correct order

**Usage**:
```bash
# Preview all changes
python scripts/bootstrap_repository.py --dry-run

# Apply all changes
python scripts/bootstrap_repository.py

# Only verify current configuration
python scripts/bootstrap_repository.py --verify-only

# Skip repository configuration (only create labels/milestones/issues)
python scripts/bootstrap_repository.py --skip-config

# Skip issue creation (only configure repository)
python scripts/bootstrap_repository.py --skip-issues
```

**What it does**:
- Configures repository settings
- Creates labels, milestones, issues
- Verifies everything worked

#### `configure_repository.py` - Repository Configuration
**Purpose**: Configure all GitHub repository settings

**Usage**:
```bash
# Preview configuration changes
python scripts/configure_repository.py --dry-run

# Apply configuration
python scripts/configure_repository.py

# Verify configuration
python scripts/configure_repository.py --verify-only
```

**What it does**:
- Sets repository visibility (public)
- Enables features (Issues, Wiki, Discussions, Projects)
- Configures PR settings (squash merge, auto-delete branches)
- Adds repository topics
- Enables security features (Dependabot)
- Configures branch protection for `main`

### 📋 Individual Scripts (For Fine-Grained Control)

These are called by the master scripts but can be run individually:

## Individual Scripts

If you want more control, you can run each script separately:

### 1. Create Labels

```bash
# Preview
python scripts/create_labels.py --dry-run

# Create
python scripts/create_labels.py
```

Creates all GitHub labels:
- **Phase labels:** `phase-1-foundation` through `phase-10-testing`
- **Priority labels:** `priority-high`, `priority-medium`, `priority-low`
- **Type labels:** `type-feature`, `type-bug`, `type-docs`, `type-refactor`
- **Vendor labels:** `vendor-claude`, `vendor-gemini`, `vendor-openai`
- **Special labels:** `good-first-issue`, `help-wanted`, `blocked`

### 2. Create Milestones

```bash
# Preview
python scripts/create_milestones.py --dry-run

# Create
python scripts/create_milestones.py
```

Creates two milestones:
- **MVP (v0.1.0)** - Due in 2 weeks - 24 issues
- **Full Release (v1.0.0)** - Due in 5 weeks - 33 issues

### 3. Create Issues

```bash
# Preview
python scripts/create_issues.py --dry-run

# Create
python scripts/create_issues.py
```

Creates all 57 issues from `GITHUB_ISSUES.md`:
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

## Troubleshooting

### "GitHub CLI is not installed"

```bash
brew install gh
```

### "GitHub CLI is not authenticated"

```bash
gh auth login
# Follow the prompts
```

### "Label already exists"

This is normal and safe to ignore. The script will skip existing labels.

### "Milestone already exists"

This is normal and safe to ignore. The script will skip existing milestones.

### Issues creation fails

Make sure labels and milestones exist first:
```bash
python scripts/create_labels.py
python scripts/create_milestones.py
python scripts/create_issues.py
```

## After Setup

Once all scripts complete successfully:

1. **View issues:**
   ```bash
   gh issue list --repo TechR10n/ai-asst-mgr
   ```

2. **Visit the repository:**
   - Issues: https://github.com/TechR10n/ai-asst-mgr/issues
   - Project: https://github.com/users/TechR10n/projects/5

3. **Add issues to project board:**
   - Go to the project board
   - Add all issues to the "Backlog" column
   - Set up automation rules (see PROJECT_SETUP.md)

4. **Start development:**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b phase-1/setup-project-structure
   ```

## Script Details

### create_labels.py
- Parses label definitions from code
- Creates labels with colors and descriptions
- Skips existing labels gracefully

### create_milestones.py
- Creates two milestones with due dates
- Calculates due dates dynamically (2 weeks, 5 weeks)
- Includes full descriptions

### create_issues.py
- Parses GITHUB_ISSUES.md
- Extracts issue metadata (title, labels, milestone, body)
- Creates issues using `gh issue create`
- Preserves markdown formatting in issue bodies

### setup_github.py
- Master orchestration script
- Runs all three scripts in correct order
- Provides progress updates
- Handles errors gracefully

## Maintenance

If you need to update issues:

1. **Edit GITHUB_ISSUES.md**
2. **Re-run the script:**
   ```bash
   python scripts/create_issues.py
   ```

Note: The script won't create duplicate issues if they already exist with the same title.

## Files

```
scripts/
├── README.md              # This file
├── setup_github.py        # Master script (run this)
├── create_labels.py       # Step 1: Create labels
├── create_milestones.py   # Step 2: Create milestones
└── create_issues.py       # Step 3: Create issues
```

## See Also

- `../PROJECT_SETUP.md` - Complete setup guide
- `../GITHUB_ISSUES.md` - All issue details
- `../CONTRIBUTING.md` - Contributor guidelines
