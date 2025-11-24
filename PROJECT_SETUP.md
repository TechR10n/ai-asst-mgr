# AI Assistant Manager - Project Setup Guide

**Repository:** https://github.com/TechR10n/ai-asst-mgr
**Project Board:** https://github.com/users/TechR10n/projects/5
**Owner:** TechR10n

---

## 📁 Files Created

### ✅ Documentation
- [x] `README.md` - Comprehensive project overview
- [x] `CONTRIBUTING.md` - Contributor guidelines
- [x] `GITHUB_ISSUES.md` - All 57 issues with details
- [x] `PROJECT_SETUP.md` - This file

### ✅ GitHub Templates
- [x] `.github/ISSUE_TEMPLATE/bug_report.md`
- [x] `.github/ISSUE_TEMPLATE/feature_request.md`
- [x] `.github/pull_request_template.md`

---

## 🏷️ GitHub Labels to Create

Copy and paste this into your GitHub labels:

### Phase Labels
```
phase-1-foundation         #0052CC
phase-2-vendors           #1D76DB
phase-2b-database         #5319E7
phase-3-cli               #0E8A16
phase-4-audit             #B60205
phase-5-coaching          #FBCA04
phase-6-backup            #D93F0B
phase-7-scheduling        #006B75
phase-8-capabilities      #C5DEF5
phase-9-web-dashboard     #FEF2C0
phase-10-testing          #BFD4F2
```

### Priority Labels
```
priority-high             #D73A4A
priority-medium           #FBCA04
priority-low              #0E8A16
```

### Type Labels
```
type-feature              #A2EEEF
type-bug                  #D73A4A
type-docs                 #0075CA
type-refactor             #C5DEF5
```

### Special Labels
```
good-first-issue          #7057FF
help-wanted               #008672
blocked                   #D93F0B
```

### Vendor Labels
```
vendor-claude             #5319E7
vendor-gemini             #FBCA04
vendor-openai             #0E8A16
```

---

## 🎯 Milestones to Create

### Milestone 1: MVP (v0.1.0)
- **Title:** MVP (v0.1.0)
- **Due Date:** 2 weeks from start
- **Description:**
  ```
  Core functionality with vendor management, CLI commands, and backup operations.

  Includes:
  - Phase 1: Project foundation
  - Phase 2: Vendor adapters
  - Phase 2b: Database migration
  - Phase 3: Core CLI commands
  - Phase 6: Backup operations
  ```

### Milestone 2: Full Release (v1.0.0)
- **Title:** Full Release (v1.0.0)
- **Due Date:** 5 weeks from start
- **Description:**
  ```
  Complete feature set with audit, coaching, capabilities, and web dashboard.

  Includes:
  - Phase 4: Audit system
  - Phase 5: Coaching system
  - Phase 7: Cross-platform scheduling
  - Phase 8: Capability abstraction
  - Phase 9: Web dashboard
  - Phase 10: Testing & documentation
  ```

---

## 🌿 Branch Strategy

### Main Branch
- **Branch:** `main`
- **Protection:**
  - Require pull request reviews
  - Require status checks to pass
  - No direct pushes

### Feature Branches
```
phase-N/feature-name
```

**Examples:**
```
phase-1/setup-project-structure
phase-1/configure-pyproject
phase-2/vendor-base-class
phase-2/claude-adapter
phase-2/gemini-adapter
phase-3/cli-status-command
phase-4/audit-framework
phase-9/web-dashboard-base
```

### Bug Fix Branches
```
fix/issue-description
```

**Examples:**
```
fix/status-command-timeout
fix/backup-path-error
```

### Documentation Branches
```
docs/update-description
```

**Examples:**
```
docs/update-readme
docs/add-coaching-guide
```

### Workflow
```bash
# Start new feature
git checkout main
git pull origin main
git checkout -b phase-1/setup-project-structure

# Make changes
git add .
git commit -m "feat(foundation): initialize uv project structure"

# Push to GitHub
git push origin phase-1/setup-project-structure

# Create Pull Request on GitHub
# Get review and merge
# Delete branch after merge
```

---

## 📋 Creating GitHub Issues

### Method 1: Manually (Recommended)

1. Go to https://github.com/TechR10n/ai-asst-mgr/issues
2. Click "New Issue"
3. Copy issue from `GITHUB_ISSUES.md`
4. Fill in:
   - Title
   - Description (tasks, acceptance criteria, estimated time)
   - Labels
   - Milestone
   - Project (ai-asst-mgr project)
5. Click "Submit new issue"
6. Repeat for all 57 issues

### Method 2: GitHub CLI (Faster)

```bash
# Install GitHub CLI if not installed
brew install gh

# Authenticate
gh auth login

# Create issue (example)
gh issue create \
  --title "Initialize uv project structure" \
  --body "$(cat issue-template.md)" \
  --label "phase-1-foundation,type-feature,priority-high" \
  --milestone "MVP (v0.1.0)" \
  --project "ai-asst-mgr"
```

### Method 3: Script (Fastest)

Create a script to parse `GITHUB_ISSUES.md` and create all issues automatically.

---

## 🗂️ GitHub Project Setup

### Project Structure

**Columns:**
1. 📋 **Backlog** - Issues not yet started
2. 🏗️ **In Progress** - Currently working on
3. 👀 **In Review** - Pull request open, awaiting review
4. ✅ **Done** - Merged and complete

### Views

**View 1: By Phase**
- Group by: Labels (phase-*)
- Sort by: Priority

**View 2: By Priority**
- Group by: Priority labels
- Sort by: Creation date

**View 3: Sprint (Current Week)**
- Filter: In Progress or Review
- Sort by: Updated date

### Automation

Set up GitHub Project automation:
- When issue is assigned → Move to "In Progress"
- When PR is created → Move to "In Review"
- When PR is merged → Move to "Done"
- When issue is closed → Move to "Done"

---

## 🚀 Getting Started

### Step 1: Create Labels
1. Go to https://github.com/TechR10n/ai-asst-mgr/labels
2. Create all labels from the list above
3. Use the hex colors provided

### Step 2: Create Milestones
1. Go to https://github.com/TechR10n/ai-asst-mgr/milestones
2. Create "MVP (v0.1.0)" milestone
3. Create "Full Release (v1.0.0)" milestone

### Step 3: Create Issues
1. Open `GITHUB_ISSUES.md`
2. Create all 57 issues
3. Add to milestones
4. Add to project board

### Step 4: Configure Project Board
1. Go to https://github.com/users/TechR10n/projects/5
2. Add columns: Backlog, In Progress, Review, Done
3. Add all created issues to Backlog
4. Set up automation rules

### Step 5: Start Development
1. Clone repository locally
2. Pick first issue (#1: Initialize uv project structure)
3. Create branch: `phase-1/setup-project-structure`
4. Start coding!

---

## 📊 Progress Tracking

### Dashboard View

Your GitHub Project will show:
- **Total Issues:** 57
- **MVP Issues:** 24
- **Full Release Issues:** 33
- **Current Sprint:** Issues in progress
- **Completed:** Issues done

### Burndown

Track velocity:
- Week 1: Complete Phase 1 (4 issues)
- Week 2: Complete Phase 2-3 (13 issues)
- Week 3: Complete Phase 4-5 (11 issues)
- Week 4-5: Complete Phase 6-10 (29 issues)

---

## 🔄 Workflow Example

### Scenario: Working on Issue #6 (Implement ClaudeAdapter)

1. **Assign Issue**
   ```
   Go to issue #6
   Click "Assignees" → Add yourself
   Issue moves to "In Progress" (automation)
   ```

2. **Create Branch**
   ```bash
   git checkout main
   git pull origin main
   git checkout -b phase-2/claude-adapter
   ```

3. **Write Code**
   ```bash
   # Create src/ai_asst_mgr/vendors/claude.py
   # Implement ClaudeAdapter
   # Write tests
   ```

4. **Commit**
   ```bash
   git add .
   git commit -m "feat(vendors): implement ClaudeAdapter

   - Add ClaudeAdapter class
   - Implement all required methods
   - Parse YAML frontmatter
   - Add agent/skill listing
   - Add health checks

   Closes #6"
   ```

5. **Push and Create PR**
   ```bash
   git push origin phase-2/claude-adapter

   # On GitHub:
   # Click "Create Pull Request"
   # Use PR template
   # Link to issue: "Closes #6"
   # Request review
   ```

6. **Review Process**
   - Issue moves to "Review" (automation)
   - Reviewer comments
   - Make changes if needed
   - Push updates

7. **Merge**
   - Reviewer approves
   - Merge PR
   - Issue closes and moves to "Done" (automation)
   - Branch is deleted

8. **Next Issue**
   - Pick Issue #7 (Implement GeminiAdapter)
   - Repeat process

---

## 📝 Commit Message Convention

Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `style`: Formatting
- `refactor`: Code refactoring
- `test`: Adding tests
- `chore`: Maintenance

### Examples

```bash
# Simple feature
git commit -m "feat(vendors): add GeminiAdapter"

# Feature with body
git commit -m "feat(cli): implement status command

Display all vendors in a Rich table with color-coded status
indicators. Shows config directories and API key status.

Closes #16"

# Bug fix
git commit -m "fix(backup): resolve path expansion issue

Fixes issue where ~ was not expanded in backup paths.

Fixes #42"

# Breaking change
git commit -m "feat(database): migrate to vendor-agnostic schema

BREAKING CHANGE: Database schema has changed. Run migration
before upgrading.

Closes #11"
```

---

## 🎯 Quick Reference

### Key Commands
```bash
# See all issues
gh issue list

# Create issue
gh issue create --title "Title" --body "Body"

# See project
gh project list

# Create PR
gh pr create --title "Title" --body "Body"

# View PR status
gh pr status
```

### Important URLs
- **Repository:** https://github.com/TechR10n/ai-asst-mgr
- **Issues:** https://github.com/TechR10n/ai-asst-mgr/issues
- **Project:** https://github.com/users/TechR10n/projects/5
- **Actions:** https://github.com/TechR10n/ai-asst-mgr/actions

---

## ✅ Checklist

Before starting development:

- [ ] All labels created
- [ ] Both milestones created
- [ ] All 57 issues created
- [ ] Issues added to project board
- [ ] Project columns configured
- [ ] Automation rules set up
- [ ] Repository cloned locally
- [ ] Ready to start Issue #1

---

## 🎉 You're Ready!

Everything is set up and ready to go. Start with Issue #1 and work through the phases systematically.

Good luck building **ai-asst-mgr**! 🚀
