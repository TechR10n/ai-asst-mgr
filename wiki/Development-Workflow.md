# Development Workflow

This guide describes the branch strategy, commit conventions, and PR process for ai-asst-mgr.

## Branch Strategy

### Main Branch

**Branch**: `main`

**Rules**:
- Protected branch
- Requires PR for changes
- Requires passing CI checks
- Requires code review
- No direct commits

### Feature Branches

**Format**: `phase-N/feature-name`

**Examples**:
```
phase-1/setup-project-structure
phase-2/claude-adapter
phase-2/gemini-adapter
phase-3/status-command
phase-4/audit-framework
phase-9/web-dashboard-base
```

**Creating a feature branch**:
```bash
# Update main
git checkout main
git pull upstream main

# Create feature branch
git checkout -b phase-2/claude-adapter

# Push to your fork
git push origin phase-2/claude-adapter
```

### Bug Fix Branches

**Format**: `fix/issue-description`

**Examples**:
```
fix/status-command-timeout
fix/backup-path-error
fix/database-connection-leak
```

### Documentation Branches

**Format**: `docs/update-description`

**Examples**:
```
docs/update-readme
docs/add-coaching-guide
docs/fix-typos
```

## Commit Message Convention

We use [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance (dependencies, tooling)
- `perf`: Performance improvement
- `ci`: CI/CD changes

### Scopes

- `vendors`: Vendor adapters
- `cli`: CLI commands
- `web`: Web dashboard
- `database`: Database operations
- `operations`: Operations (backup, audit, etc.)
- `capabilities`: Capability abstraction
- `github`: GitHub integration
- `platform`: Platform-specific code

### Examples

#### Simple Feature

```bash
git commit -m "feat(vendors): add GeminiAdapter"
```

#### Feature with Body

```bash
git commit -m "feat(cli): implement status command

Display all vendors in a Rich table with color-coded status
indicators. Shows config directories and API key status.

Closes #16"
```

#### Bug Fix

```bash
git commit -m "fix(backup): resolve path expansion issue

Fixes issue where ~ was not expanded in backup paths.
Now uses os.path.expanduser() to properly resolve home directory.

Fixes #42"
```

#### Breaking Change

```bash
git commit -m "feat(database): migrate to vendor-agnostic schema

BREAKING CHANGE: Database schema has changed. Run migration
before upgrading.

Closes #11"
```

#### Multiple Issues

```bash
git commit -m "feat(cli): add audit and coach commands

Implements audit command to check vendor configurations
and coach command to provide usage insights.

Closes #28, #29"
```

## Pull Request Process

### 1. Create Feature Branch

```bash
git checkout main
git pull upstream main
git checkout -b phase-2/claude-adapter
```

### 2. Make Changes

```bash
# Make changes
# Write tests
# Update documentation

# Run quality checks
uv run pytest
uv run ruff check src/
uv run ruff format src/
uv run mypy src/
```

### 3. Commit Changes

```bash
# Stage changes
git add .

# Commit with conventional commit message
git commit -m "feat(vendors): implement ClaudeAdapter

- Add ClaudeAdapter class
- Implement all required methods
- Parse YAML frontmatter
- Add agent/skill listing
- Add health checks

Closes #6"
```

### 4. Push to Fork

```bash
git push origin phase-2/claude-adapter
```

### 5. Create Pull Request

**On GitHub**:
1. Go to https://github.com/YOUR_USERNAME/ai-asst-mgr
2. Click "Compare & pull request"
3. Fill out the PR template
4. Link related issues: `Closes #6`
5. Request review
6. Submit PR

**Or use GitHub CLI**:
```bash
gh pr create \
  --title "feat(vendors): implement ClaudeAdapter" \
  --body "$(cat <<'EOF'
## Description
Implements full Claude Code vendor adapter.

## Related Issue
Closes #6

## Type of Change
- [x] New feature

## Changes Made
- Add ClaudeAdapter class
- Implement all required methods
- Parse YAML frontmatter from agents/*.md
- Add helper methods for listing agents and skills

## Testing Performed
- [x] Unit tests added
- [x] All tests pass locally
- [x] Tested with real ~/.claude directory

## Documentation
- [x] Docstrings added for all public methods
- [x] Type hints complete
EOF
)" \
  --base main \
  --head YOUR_USERNAME:phase-2/claude-adapter
```

### 6. Address Review Feedback

```bash
# Make requested changes
# Commit changes
git add .
git commit -m "fix: address review feedback"

# Push updates
git push origin phase-2/claude-adapter
```

### 7. Merge

Once approved:
- Maintainer will merge the PR
- Branch will be deleted automatically
- Issue will close automatically (if using `Closes #N`)

## Code Review Guidelines

### As a Reviewer

**Check for**:
- [ ] Code follows [[Coding Standards]]
- [ ] Tests are comprehensive
- [ ] Documentation is clear
- [ ] No security concerns
- [ ] Type hints are complete
- [ ] Error handling is appropriate
- [ ] No unnecessary complexity

**Use constructive language**:
- ✅ "Consider using a dataclass here for clarity"
- ❌ "This code is bad"

**Approve when**:
- Code quality is good
- Tests pass
- Documentation is sufficient

### As an Author

**Before requesting review**:
- [ ] All tests pass locally
- [ ] Code is formatted (ruff format)
- [ ] Linter passes (ruff check)
- [ ] Type checker passes (mypy)
- [ ] Documentation is updated
- [ ] Commit messages are clear

**Responding to feedback**:
- Be open to suggestions
- Ask questions if unclear
- Make requested changes promptly
- Thank reviewers for their time

## CI/CD Checks

Every PR must pass:

### 1. Tests
```bash
pytest
```

All tests must pass on:
- Ubuntu (latest)
- macOS (latest)

### 2. Linting
```bash
ruff check src/
```

No linting errors allowed.

### 3. Type Checking
```bash
mypy src/
```

Must pass strict type checking.

### 4. Formatting
```bash
ruff format --check src/
```

Code must be formatted.

### 5. Coverage
```bash
pytest --cov=src/ai_asst_mgr --cov-report=term
```

Aim for >80% coverage.

## Workflow Examples

### Example 1: Working on Issue #6 (Implement ClaudeAdapter)

```bash
# 1. Assign issue to yourself on GitHub

# 2. Create branch
git checkout main
git pull upstream main
git checkout -b phase-2/claude-adapter

# 3. Implement ClaudeAdapter
# Create src/ai_asst_mgr/vendors/claude.py
# Write tests in tests/vendors/test_claude.py

# 4. Run tests
uv run pytest tests/vendors/test_claude.py

# 5. Run quality checks
uv run ruff check src/
uv run ruff format src/
uv run mypy src/

# 6. Commit
git add .
git commit -m "feat(vendors): implement ClaudeAdapter

- Add ClaudeAdapter class
- Implement all required methods
- Parse YAML frontmatter
- Add agent/skill listing
- Add health checks

Closes #6"

# 7. Push
git push origin phase-2/claude-adapter

# 8. Create PR on GitHub
gh pr create --title "feat(vendors): implement ClaudeAdapter" --fill

# 9. Wait for review
# 10. Address feedback if needed
# 11. Merge after approval
```

### Example 2: Quick Bug Fix

```bash
# 1. Create branch
git checkout main
git pull upstream main
git checkout -b fix/status-command-timeout

# 2. Fix the bug
# Edit src/ai_asst_mgr/cli.py

# 3. Add test
# Edit tests/test_cli.py

# 4. Commit
git commit -am "fix(cli): resolve status command timeout

Increases timeout from 5s to 30s for slow systems.

Fixes #42"

# 5. Push and create PR
git push origin fix/status-command-timeout
gh pr create --title "fix(cli): resolve status command timeout" --fill
```

### Example 3: Documentation Update

```bash
# 1. Create branch
git checkout -b docs/update-readme

# 2. Update documentation
# Edit README.md or docs/

# 3. Commit
git commit -am "docs: update installation instructions

Add Python 3.14 requirement clarification.
Add troubleshooting section for common issues."

# 4. Push and create PR
git push origin docs/update-readme
gh pr create --title "docs: update installation instructions" --fill
```

## Best Practices

### Commit Frequency

- Commit often (every logical change)
- Each commit should be self-contained
- Don't commit broken code

### Commit Size

- Keep commits focused
- One logical change per commit
- If commit message has "and", consider splitting

### Branch Lifetime

- Keep branches short-lived (1-3 days ideal)
- Don't let branches get stale
- Rebase on main regularly:
  ```bash
  git checkout phase-2/claude-adapter
  git fetch upstream
  git rebase upstream/main
  git push --force-with-lease origin phase-2/claude-adapter
  ```

### Pull Request Size

- Keep PRs small (< 400 lines ideal)
- Large PRs are hard to review
- Split large features into multiple PRs

### Testing

- Write tests first (TDD)
- Test happy path and edge cases
- Mock external dependencies

### Documentation

- Update docs as you code
- Add docstrings to all public functions
- Update README if needed

## Getting Help

- **Questions**: [GitHub Discussions](https://github.com/TechR10n/ai-asst-mgr/discussions)
- **Bugs**: [GitHub Issues](https://github.com/TechR10n/ai-asst-mgr/issues)
- **Code review**: Tag maintainers in PR

## See Also

- [[Development Setup]] - Setting up dev environment
- [[Coding Standards]] - Python style guide
- [[Writing Tests]] - Testing guidelines
- [[Code Review Guidelines]] - Detailed review checklist
- [[GitHub Setup Scripts]] - Automating project setup
