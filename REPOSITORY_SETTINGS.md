# Repository Settings Guide

This guide configures the repository to be **public and findable** while maintaining **single-maintainer control** (only you can merge changes).

## Repository Visibility

### Make Repository Public

1. Go to https://github.com/TechR10n/ai-asst-mgr/settings
2. Scroll to "Danger Zone"
3. Click "Change visibility"
4. Select "Make public"
5. Confirm

**This makes the repo**:
- ✅ Searchable on GitHub
- ✅ Google-indexable
- ✅ Visible to everyone
- ✅ Allows anyone to fork and star
- ✅ Enables external contributions

## Branch Protection Rules

### Protect Main Branch (Only You Can Merge)

1. Go to https://github.com/TechR10n/ai-asst-mgr/settings/branches
2. Click "Add branch protection rule"
3. Branch name pattern: `main`

**Configure these settings**:

#### Protect matching branches
- ✅ **Require a pull request before merging**
  - Required approvals: 1
  - ✅ Dismiss stale pull request approvals when new commits are pushed
  - ✅ Require review from Code Owners

- ✅ **Require status checks to pass before merging**
  - ✅ Require branches to be up to date before merging
  - Required checks:
    - `test (ubuntu-latest)` (when CI is set up)
    - `test (macos-latest)` (when CI is set up)
    - `lint`
    - `type-check`

- ✅ **Require conversation resolution before merging**

- ✅ **Require signed commits** (optional but recommended)

- ✅ **Require linear history** (prevents merge commits, only squash or rebase)

- ✅ **Do not allow bypassing the above settings**
  - ❌ **UNCHECK** "Allow specified actors to bypass required pull requests"

  OR if you want to allow yourself to bypass:
  - ✅ Check "Allow specified actors to bypass"
  - Add yourself (TechR10n) as the only allowed actor

#### Rules applied to everyone including administrators
- ✅ **Include administrators** (This ensures even you follow the rules, or...)
- ❌ **UNCHECK** if you want to be able to push directly

**Recommended**: Keep "Include administrators" checked and use the normal PR workflow even for your own changes. This ensures quality.

#### Restrict who can push to matching branches
- ✅ **Restrict pushes that create matching branches**
- Add: `TechR10n` (only you)

4. Click "Create" or "Save changes"

## Code Owners (Only You Approve PRs)

Create a CODEOWNERS file that designates you as the owner of all code:

**File**: `.github/CODEOWNERS`
```
# All files require review from TechR10n
* @TechR10n

# Specific overrides (if you want different owners for different areas)
# /docs/ @TechR10n
# /src/ai_asst_mgr/vendors/ @TechR10n
```

This means:
- ✅ All PRs require your approval
- ✅ GitHub auto-requests you as reviewer
- ✅ PRs cannot merge without your approval

## Repository Settings

### General Settings

Go to https://github.com/TechR10n/ai-asst-mgr/settings

#### Features
- ✅ **Wikis** - Enable (for development wiki)
- ✅ **Issues** - Enable
- ✅ **Sponsorships** - Optional (if you want GitHub Sponsors)
- ✅ **Projects** - Enable
- ✅ **Discussions** - Enable (for Q&A, ideas)

#### Pull Requests
- ✅ **Allow merge commits** - Your choice
- ✅ **Allow squash merging** - Recommended (keeps history clean)
- ✅ **Allow rebase merging** - Optional
- ✅ **Always suggest updating pull request branches**
- ✅ **Automatically delete head branches** - Yes (cleanup after merge)

#### Pushes
- ❌ **Allow force pushes** - Disabled for safety
- ❌ **Allow deletions** - Disabled for safety

## Collaboration Workflow

### How Others Contribute (Fork-Based)

Contributors **cannot** push to your repository. Instead:

1. **Fork** your repository (creates their own copy)
2. **Clone** their fork
3. **Make changes** in their fork
4. **Create PR** from their fork to your main repo
5. **You review** and approve/reject
6. **You merge** (or request changes)

### Settings for External Contributors

#### Issues
- ✅ Anyone can create issues
- ✅ You triage and label
- ✅ You assign (to yourself or close)

#### Pull Requests
- ✅ Anyone can create PRs from forks
- ✅ Only you can approve PRs
- ✅ Only you can merge PRs

#### Discussions
- ✅ Anyone can participate
- ✅ You moderate

## Security Settings

Go to https://github.com/TechR10n/ai-asst-mgr/settings/security_analysis

### Enable These
- ✅ **Dependency graph**
- ✅ **Dependabot alerts** - Notifies you of security issues
- ✅ **Dependabot security updates** - Auto-creates PRs for security fixes
- ❌ **Dependabot version updates** - Optional (can be noisy)

### Security Policy
Create `.github/SECURITY.md`:
```markdown
# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| 1.0.x   | :white_check_mark: |
| < 1.0   | :x:                |

## Reporting a Vulnerability

**Please do not report security vulnerabilities through public GitHub issues.**

Instead, email: [your-email@example.com]

You should receive a response within 48 hours.
```

## Actions Settings

Go to https://github.com/TechR10n/ai-asst-mgr/settings/actions

### General
- ✅ **Allow all actions and reusable workflows**
- ✅ **Allow actions created by GitHub**

### Workflow permissions
- ✅ **Read and write permissions** (for automation)
- ✅ **Allow GitHub Actions to create and approve pull requests**

## GitHub Pages (Optional - For Documentation)

If you want to host documentation:

1. Go to https://github.com/TechR10n/ai-asst-mgr/settings/pages
2. Source: Deploy from a branch
3. Branch: `main` (or `gh-pages`)
4. Folder: `/docs` (or `/root`)
5. Save

This creates: https://techr10n.github.io/ai-asst-mgr

## Labels and Issue Templates

Already created! But verify:

1. Go to https://github.com/TechR10n/ai-asst-mgr/labels
2. Verify all 29 labels exist (create with scripts if not)

3. Go to https://github.com/TechR10n/ai-asst-mgr/issues/templates
4. Verify bug_report and feature_request templates exist

## Project Board Settings

1. Go to https://github.com/users/TechR10n/projects/5/settings
2. **Visibility**: Public (anyone can view)
3. **Access**: Only you can edit

## Community Standards

Check your repository's community profile:

1. Go to https://github.com/TechR10n/ai-asst-mgr/community
2. Should show:
   - ✅ Description
   - ✅ README
   - ✅ Code of conduct (add if missing)
   - ✅ Contributing guidelines
   - ✅ License
   - ✅ Issue templates
   - ✅ Pull request template

## Topics (For Discoverability)

1. Go to https://github.com/TechR10n/ai-asst-mgr
2. Click gear icon next to "About"
3. Add topics:
   - `ai`
   - `claude`
   - `gemini`
   - `codex`
   - `ai-assistant`
   - `configuration-management`
   - `python`
   - `cli`
   - `fastapi`
   - `developer-tools`

## README Badges

Add badges to README for discoverability and credibility:

```markdown
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![GitHub issues](https://img.shields.io/github/issues/TechR10n/ai-asst-mgr)](https://github.com/TechR10n/ai-asst-mgr/issues)
[![GitHub stars](https://img.shields.io/github/stars/TechR10n/ai-asst-mgr)](https://github.com/TechR10n/ai-asst-mgr/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/TechR10n/ai-asst-mgr)](https://github.com/TechR10n/ai-asst-mgr/network)
```

## Summary: Your Control Level

With these settings:

### ✅ You Control
- Merging PRs (only you can merge)
- Main branch (protected)
- Releases (only you can create)
- Repository settings
- Project board edits
- Label management
- Milestone management

### ✅ Others Can Do
- View all code (public)
- Fork repository
- Create issues
- Create PRs from forks
- Comment on issues/PRs
- Star and watch
- Participate in discussions

### ❌ Others Cannot Do
- Push directly to main
- Merge PRs
- Change settings
- Delete anything
- Force push
- Create releases

## Quick Setup Checklist

- [ ] Make repository public
- [ ] Set up branch protection on `main`
- [ ] Create `.github/CODEOWNERS` file
- [ ] Enable Dependabot
- [ ] Add repository topics
- [ ] Add badges to README
- [ ] Enable Discussions
- [ ] Enable Wiki
- [ ] Create `.github/SECURITY.md`
- [ ] Verify community standards

## Testing the Setup

### Test Branch Protection
```bash
# Try to push to main (should fail)
git checkout main
echo "test" >> test.txt
git add test.txt
git commit -m "test"
git push origin main
# Should get: "refusing to allow an OAuth App to create or update workflow"
# or require PR
```

### Test Fork Workflow
1. Have someone fork your repo
2. They make changes in their fork
3. They create PR to your repo
4. You review and merge (or close)

## Automation

See [[GitHub Actions for Maintainer Control]] for:
- Auto-labeling issues
- Auto-assigning you to PRs
- Auto-closing stale issues
- Release automation

## See Also
- [[Development Workflow]] - Your workflow as maintainer
- [[Issue Triage]] - How to manage incoming issues
- [GitHub Branch Protection Docs](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-protected-branches)
