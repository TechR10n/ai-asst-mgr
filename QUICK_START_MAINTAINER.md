# Quick Start for Maintainer

This guide helps you (the maintainer) quickly set up the repository with single-maintainer control.

## 🎯 Goal

Create a **public, findable repository** that:
- ✅ Anyone can view and fork
- ✅ Anyone can contribute via PRs
- ⚠️ Only you can approve and merge changes
- 🔒 Main branch is protected

## 🚀 Quick Setup

### ⚡ Automated Setup (Recommended - 3 minutes)

**New!** Use the automated bootstrap script:

```bash
# Install GitHub CLI
brew install gh
gh auth login

# Run complete setup (one command!)
python3 scripts/bootstrap_repository.py --dry-run  # Preview first
python3 scripts/bootstrap_repository.py            # Apply changes

# Verify
python3 scripts/bootstrap_repository.py --verify-only
```

**Done!** ✅ Everything is configured automatically.

See **[AUTOMATION_COMPLETE.md](./AUTOMATION_COMPLETE.md)** for details.

### 🔧 Manual Setup (Alternative - 15 minutes)

If you prefer manual control or the automated script fails:

#### Step 1: Make Repository Public (2 min)

```bash
# On GitHub:
# Settings → Danger Zone → Change visibility → Make public
```

Or via GitHub CLI:
```bash
gh repo edit TechR10n/ai-asst-mgr --visibility public
```

### Step 2: Protect Main Branch (3 min)

1. Go to: https://github.com/TechR10n/ai-asst-mgr/settings/branches
2. Click "Add branch protection rule"
3. Branch name pattern: `main`
4. Enable:
   - ✅ Require a pull request before merging
     - Required approvals: 1
     - Require review from Code Owners
   - ✅ Require status checks to pass before merging
   - ✅ Require conversation resolution before merging
   - ✅ Include administrators (optional - recommended)
5. Save changes

**Or use GitHub CLI:**
```bash
# Create branch protection rule
gh api repos/TechR10n/ai-asst-mgr/branches/main/protection \
  --method PUT \
  --field required_pull_request_reviews[required_approving_review_count]=1 \
  --field required_pull_request_reviews[require_code_owner_reviews]=true \
  --field enforce_admins=true \
  --field restrictions=null
```

### Step 3: Verify CODEOWNERS (1 min)

The file `.github/CODEOWNERS` already exists with:
```
* @TechR10n
```

This ensures all PRs require your approval.

**Verify**:
```bash
cat .github/CODEOWNERS
```

### Step 4: Enable GitHub Features (2 min)

Go to: https://github.com/TechR10n/ai-asst-mgr/settings

Enable:
- ✅ **Issues**
- ✅ **Wikis**
- ✅ **Discussions**
- ✅ **Projects**

Configure Pull Requests:
- ✅ Allow squash merging (recommended)
- ✅ Automatically delete head branches

### Step 5: Add Repository Topics (2 min)

1. Go to: https://github.com/TechR10n/ai-asst-mgr
2. Click gear icon next to "About"
3. Add topics:
   ```
   ai, claude, gemini, codex, ai-assistant, configuration-management,
   python, cli, fastapi, developer-tools, automation
   ```

### Step 6: Enable Security Features (2 min)

Go to: https://github.com/TechR10n/ai-asst-mgr/settings/security_analysis

Enable:
- ✅ **Dependency graph**
- ✅ **Dependabot alerts**
- ✅ **Dependabot security updates**

### Step 7: Run GitHub Setup Scripts (3 min)

```bash
cd ~/Developer/ai-asst-mgr

# Install GitHub CLI if needed
brew install gh
gh auth login

# Preview what will be created
python3 scripts/setup_github.py --dry-run

# Create labels, milestones, and issues
python3 scripts/setup_github.py
```

This creates:
- 29 labels
- 2 milestones
- 57 issues

## ✅ Verification Checklist

After setup, verify:

- [ ] Repository is public
- [ ] Main branch is protected
- [ ] CODEOWNERS file exists
- [ ] Issues, Wiki, Discussions enabled
- [ ] Topics added
- [ ] Dependabot enabled
- [ ] Labels created (29 total)
- [ ] Milestones created (2 total)
- [ ] Issues created (57 total)

**Quick check:**
```bash
# Check visibility
gh repo view TechR10n/ai-asst-mgr --json isPrivate

# Check branch protection
gh api repos/TechR10n/ai-asst-mgr/branches/main/protection

# Check labels
gh label list --repo TechR10n/ai-asst-mgr --limit 100

# Check issues
gh issue list --repo TechR10n/ai-asst-mgr --limit 100
```

## 📋 Daily Workflow as Maintainer

### When Someone Opens an Issue

1. **Auto-labeled** - GitHub Actions auto-applies labels
2. **Review** - Read the issue
3. **Triage**:
   - Add priority label if missing
   - Add to milestone if appropriate
   - Assign to yourself if you'll work on it
4. **Respond** - Comment with questions or confirmation

```bash
# From CLI
gh issue view 42
gh issue comment 42 --body "Thanks! I'll look into this."
gh issue edit 42 --add-label priority-high --milestone "MVP (v0.1.0)"
```

### When Someone Opens a PR

1. **Auto-assigned** - You're automatically requested as reviewer
2. **Review** - Check code, tests, documentation
3. **Request changes** or **Approve**:
   ```bash
   # View PR
   gh pr view 42

   # Check out locally to test
   gh pr checkout 42

   # Run tests
   uv run pytest

   # Approve
   gh pr review 42 --approve

   # Or request changes
   gh pr review 42 --request-changes --body "Please add tests"
   ```
4. **Merge** when approved and CI passes:
   ```bash
   # Squash merge (recommended)
   gh pr merge 42 --squash --delete-branch

   # Or regular merge
   gh pr merge 42 --merge --delete-branch
   ```

### Weekly Maintenance

**Check stale items** (automated, but review):
```bash
gh issue list --label stale
gh pr list --label stale
```

**Review open PRs**:
```bash
gh pr list --state open
```

**Check project board**:
```bash
open https://github.com/users/TechR10n/projects/5
```

### Monthly Tasks

- Review and update labels if needed
- Check milestone progress
- Update documentation
- Review security advisories:
  ```bash
  gh api repos/TechR10n/ai-asst-mgr/dependabot/alerts
  ```

## 🛠️ Useful Commands

### Issues

```bash
# List all issues
gh issue list

# Create issue
gh issue create --title "Bug: something broke" --body "Details"

# Close issue
gh issue close 42

# Reopen issue
gh issue reopen 42

# View issue
gh issue view 42
```

### Pull Requests

```bash
# List all PRs
gh pr list

# View PR
gh pr view 42

# Check out PR locally
gh pr checkout 42

# Review PR
gh pr review 42 --approve
gh pr review 42 --request-changes --body "Needs tests"

# Merge PR
gh pr merge 42 --squash

# Close PR without merging
gh pr close 42
```

### Labels

```bash
# List labels
gh label list

# Create label
gh label create "new-label" --color "FF0000" --description "Description"

# Edit label
gh label edit "old-label" --name "new-name"

# Delete label
gh label delete "label-name"
```

### Milestones

```bash
# List milestones
gh api repos/TechR10n/ai-asst-mgr/milestones

# Create milestone
gh api repos/TechR10n/ai-asst-mgr/milestones \
  --method POST \
  --field title="v0.2.0" \
  --field description="Next release" \
  --field due_on="2025-12-31T23:59:59Z"
```

## 📖 Related Documentation

- **[REPOSITORY_SETTINGS.md](./REPOSITORY_SETTINGS.md)** - Detailed settings guide
- **[CONTRIBUTING.md](./CONTRIBUTING.md)** - Contributor guidelines
- **[Development Wiki](https://github.com/TechR10n/ai-asst-mgr/wiki)** - Development guides
- **[.github/SECURITY.md](./.github/SECURITY.md)** - Security policy

## 🤖 Automation in Place

You have the following automation already configured:

### Auto-labeling (`.github/workflows/auto-label.yml`)
- Automatically labels PRs based on branch name
- Automatically labels issues/PRs based on title
- Auto-assigns you as reviewer on PRs
- Welcomes first-time contributors

### Stale bot (`.github/workflows/stale.yml`)
- Marks issues stale after 60 days
- Closes stale issues after 7 days
- Marks PRs stale after 30 days
- Closes stale PRs after 14 days
- Exempts high-priority and assigned items

### Dependabot (configured in GitHub)
- Automatically creates PRs for security updates
- Monitors dependencies for vulnerabilities

## 🎯 Your Control Summary

### ✅ You Control:
- Merging PRs (only you)
- Main branch (protected)
- Releases (only you)
- Repository settings
- Label/milestone management
- Who gets write access (no one)

### ✅ Others Can:
- View all code (public repo)
- Fork repository
- Create issues
- Create PRs from forks
- Comment and discuss
- Star and watch

### ❌ Others Cannot:
- Push to main
- Merge PRs
- Change settings
- Delete anything
- Create releases

## 🚨 Emergency: Revoking Access

If someone somehow gets unauthorized access:

```bash
# List collaborators
gh api repos/TechR10n/ai-asst-mgr/collaborators

# Remove collaborator
gh api repos/TechR10n/ai-asst-mgr/collaborators/USERNAME \
  --method DELETE

# Check deploy keys
gh api repos/TechR10n/ai-asst-mgr/keys

# Revoke tokens in GitHub settings
open https://github.com/settings/tokens
```

## ✨ You're Ready!

Your repository is now:
- ✅ Public and findable
- ✅ Open to contributions
- ✅ Under your complete control
- ✅ Automated for efficiency

Start developing or review incoming contributions! 🚀
