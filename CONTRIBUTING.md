# Contributing to AI Assistant Manager

Thank you for considering contributing to ai-asst-mgr! This document provides guidelines and information for contributors.

---

## 👥 **Contribution Model**

This project uses a **single-maintainer model**:

- ✅ **Public Repository** - Anyone can view, fork, and use
- ✅ **Open to Contributions** - We welcome PRs, issues, and discussions
- ⚠️ **Maintainer Approval Required** - Only @TechR10n can approve and merge PRs
- 🔒 **Protected Main Branch** - Direct pushes to `main` are disabled

**How This Works:**
1. **You fork** the repository (creates your own copy)
2. **You make changes** in your fork
3. **You create a PR** from your fork to the main repository
4. **Maintainer reviews** your PR
5. **Maintainer merges** (or requests changes)

This ensures code quality while staying open to community contributions.

---

## 🎯 **Project Vision**

ai-asst-mgr aims to be the universal management tool for AI assistants across different vendors, providing unified operations while respecting vendor independence.

---

## 🚀 **Getting Started**

### **Prerequisites**
- Python 3.14
- uv package manager
- Git
- At least one AI assistant (Claude Code, Gemini CLI, or Codex) for testing

### **Development Setup**

```bash
# Fork the repository on GitHub
# Clone your fork
git clone https://github.com/YOUR_USERNAME/ai-asst-mgr.git
cd ai-asst-mgr

# Add upstream remote
git remote add upstream https://github.com/TechR10n/ai-asst-mgr.git

# Install dependencies
uv sync

# Install development dependencies
uv sync --group dev

# Run tests to verify setup
uv run pytest
```

---

## 📋 **How to Contribute**

### **1. Find an Issue**
- Check the [GitHub Project](https://github.com/users/TechR10n/projects/5) for tasks
- Look for issues labeled `good-first-issue` if you're new
- Comment on the issue to let others know you're working on it

### **2. Create a Branch**

```bash
# Update main branch
git checkout main
git pull upstream main

# Create feature branch
git checkout -b phase-N/feature-name
```

**Branch Naming Convention:**
- `phase-N/feature-name` - New features
- `fix/issue-description` - Bug fixes
- `docs/update-description` - Documentation updates
- `refactor/component-name` - Code refactoring

### **3. Make Changes**

#### **Code Style**
- Follow PEP 8 style guide
- Use type hints (Python 3.14 style)
- Maximum line length: 100 characters
- Use docstrings for all public functions/classes

#### **Commit Messages**
Follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `style`: Code style changes (formatting, no logic change)
- `refactor`: Code refactoring
- `test`: Adding or updating tests
- `chore`: Maintenance tasks

**Examples:**
```bash
git commit -m "feat(vendors): add GeminiAdapter implementation"
git commit -m "fix(cli): resolve status command timeout issue"
git commit -m "docs(readme): update installation instructions"
```

### **4. Write Tests**

All new code should include tests:

```python
# tests/test_feature.py

def test_feature_behavior():
    """Test that feature works as expected."""
    result = my_feature(input_data)
    assert result == expected_output
```

**Run tests:**
```bash
# Run all tests
uv run pytest

# Run specific test file
uv run pytest tests/test_vendors/test_claude.py

# Run with coverage
uv run pytest --cov=ai_asst_mgr --cov-report=html
```

### **5. Run Quality Checks**

```bash
# Type checking
uv run mypy src/

# Linting
uv run ruff check src/

# Auto-fix linting issues
uv run ruff check --fix src/

# Format code
uv run ruff format src/
```

### **6. Push and Create PR**

```bash
# Push branch
git push origin phase-N/feature-name

# Create Pull Request on GitHub
# Use the PR template and fill in all sections
```

---

## 📝 **Pull Request Guidelines**

### **Before Submitting**
- [ ] Tests pass locally
- [ ] Type checking passes (`mypy`)
- [ ] Linting passes (`ruff`)
- [ ] Code is formatted (`ruff format`)
- [ ] Documentation is updated
- [ ] CHANGELOG.md is updated (if applicable)

### **PR Title**
Use the same format as commit messages:
```
feat(vendors): add GeminiAdapter implementation
```

### **PR Description**
Use the provided template and include:
- Clear description of changes
- Related issue number(s)
- Testing performed
- Screenshots (if UI changes)
- Breaking changes (if any)

### **Review Process**
1. Maintainer will review your PR
2. Address any feedback
3. Once approved, maintainer will merge
4. Your contribution will be included in the next release

---

## 🏗️ **Project Structure**

```
ai-asst-mgr/
├── src/ai_asst_mgr/          # Main package
│   ├── vendors/              # Vendor adapters (plugins)
│   ├── database/             # Database layer
│   ├── tracking/             # Session tracking
│   ├── operations/           # Operations (backup, audit, coaching)
│   ├── capabilities/         # Capability abstraction
│   ├── platform/             # Platform-specific code
│   ├── web/                  # Web dashboard
│   └── cli.py                # CLI application
├── tests/                    # Test suite
├── docs/                     # Documentation
└── data/                     # Template data
```

---

## 🧪 **Testing Guidelines**

### **Test Categories**

1. **Unit Tests** - Test individual functions/classes
   - Located in `tests/test_*.py`
   - Mock external dependencies
   - Fast execution

2. **Integration Tests** - Test component interactions
   - Located in `tests/integration/`
   - May use temporary files/databases
   - Slower execution

3. **End-to-End Tests** - Test full workflows
   - Located in `tests/e2e/`
   - Test CLI commands
   - Test web dashboard

### **Test Fixtures**

Use pytest fixtures for common test setup:

```python
@pytest.fixture
def temp_claude_dir(tmp_path):
    """Create temporary Claude directory."""
    claude_dir = tmp_path / ".claude"
    claude_dir.mkdir()
    return claude_dir
```

### **Test Coverage**

- Aim for 80%+ coverage
- All new features must have tests
- Bug fixes must include regression tests

---

## 📚 **Documentation**

### **Code Documentation**

Use docstrings for all public APIs:

```python
def backup_vendor(vendor: str, backup_dir: Path) -> Path:
    """
    Backup a vendor's configuration.

    Args:
        vendor: Vendor name ('claude', 'gemini', 'openai')
        backup_dir: Directory to store backup

    Returns:
        Path to the backup archive

    Raises:
        VendorNotFoundError: If vendor is not installed
        BackupError: If backup fails

    Example:
        >>> backup_path = backup_vendor('claude', Path('/backups'))
        >>> print(backup_path)
        /backups/claude_20250124_120000.tar.gz
    """
    ...
```

### **User Documentation**

Update docs when adding features:
- `docs/commands.md` - CLI command reference
- `docs/vendors/` - Vendor-specific guides
- `README.md` - High-level overview

---

## 🎨 **Code Style Guide**

### **Python Style**

```python
# Good: Type hints and clear names
def get_vendor_status(vendor_name: str) -> VendorStatus:
    """Get the status of a vendor."""
    adapter = VendorRegistry.get_vendor(vendor_name)
    return adapter.get_status()

# Bad: No type hints, unclear names
def get_status(v):
    a = get_vendor(v)
    return a.status()
```

### **Import Order**

```python
# 1. Standard library
import os
from pathlib import Path
from typing import List, Optional

# 2. Third-party
import typer
from rich.console import Console

# 3. Local
from ai_asst_mgr.vendors import VendorRegistry
from ai_asst_mgr.database import DatabaseManager
```

### **Error Handling**

```python
# Specific exceptions
class VendorNotFoundError(Exception):
    """Raised when vendor is not found."""
    pass

# Use in code
try:
    vendor = VendorRegistry.get_vendor(name)
except VendorNotFoundError:
    console.print(f"[red]Vendor '{name}' not found[/red]")
    raise typer.Exit(1)
```

---

## 🐛 **Reporting Bugs**

### **Before Reporting**
1. Check existing issues
2. Verify bug on latest version
3. Collect debug information

### **Bug Report Should Include**
- Clear description of the issue
- Steps to reproduce
- Expected behavior
- Actual behavior
- Environment details:
  - OS and version
  - Python version
  - ai-asst-mgr version
  - Installed vendors
- Logs or error messages

---

## 💡 **Suggesting Features**

### **Feature Request Should Include**
- Clear description of the feature
- Use case / motivation
- Proposed implementation (optional)
- Examples of similar features in other tools
- Impact on existing functionality

---

## 🏷️ **Issue Labels**

- `phase-1-foundation` through `phase-10-testing` - Implementation phases
- `priority-high`, `priority-medium`, `priority-low` - Priority levels
- `type-feature`, `type-bug`, `type-docs` - Issue types
- `good-first-issue` - Good for newcomers
- `help-wanted` - Need community help
- `blocked` - Blocked by other issues
- `vendor-claude`, `vendor-gemini`, `vendor-openai` - Vendor-specific

---

## 📦 **Adding New Vendors**

To add support for a new AI assistant:

1. **Create Vendor Adapter**
   ```python
   # src/ai_asst_mgr/vendors/myvendor.py
   class MyVendorAdapter(VendorAdapter):
       @property
       def info(self) -> VendorInfo:
           return VendorInfo(
               name="myvendor",
               display_name="My Vendor",
               config_dir=Path.home() / ".myvendor",
               ...
           )

       def is_installed(self) -> bool:
           # Check if vendor is installed
           ...
   ```

2. **Register Vendor**
   ```python
   # src/ai_asst_mgr/vendors/__init__.py
   VendorRegistry.register_vendor("myvendor", MyVendorAdapter)
   ```

3. **Add Tests**
   ```python
   # tests/test_vendors/test_myvendor.py
   def test_myvendor_detection():
       ...
   ```

4. **Update Documentation**
   - Add `docs/vendors/myvendor.md`
   - Update README.md vendor matrix
   - Update architecture.md

---

## 🔐 **Security**

- Never commit API keys or credentials
- Use environment variables for secrets
- Report security issues privately to maintainers
- Follow responsible disclosure practices

---

## 📞 **Getting Help**

- **Questions:** [GitHub Discussions](https://github.com/TechR10n/ai-asst-mgr/discussions)
- **Chat:** [Discord/Slack/etc] (if available)
- **Email:** [maintainer email] (for private matters)

---

## 🙏 **Thank You!**

Every contribution makes ai-asst-mgr better. Whether it's code, documentation, bug reports, or suggestions—thank you for your help!

---

## 📜 **Code of Conduct**

Please note that this project is released with a [Contributor Code of Conduct](CODE_OF_CONDUCT.md). By participating in this project you agree to abide by its terms.
