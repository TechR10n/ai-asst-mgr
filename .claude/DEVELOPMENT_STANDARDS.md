# AI Assistant Manager - Development Standards

**Version:** 1.0
**Last Updated:** November 24, 2025
**Applies To:** All parallel agents and contributors

---

## 🎯 Mission

Build a high-quality, vendor-agnostic AI assistant manager that achieves 95%+ test coverage, maintains strict type safety, and follows security-first principles.

---

## 📋 Quality Gates (Non-Negotiable)

All code merged to `main` MUST meet these criteria:

### 1. Test Coverage: 95%+
- **Target:** 95% coverage on all new code
- **Achievement:** Phases 1-2 exceeded with 95-100% coverage
- **Tool:** pytest-cov
- **Enforcement:** CI blocks PRs below 95%

### 2. Type Safety: mypy --strict
- **Requirement:** Zero mypy errors in strict mode
- **Rules:**
  - All function parameters typed
  - All return types typed
  - No `Any` types without justification
  - No `# type: ignore` without explanation
- **Tool:** mypy
- **Enforcement:** CI blocks PRs with type errors

### 3. Code Quality: ruff
- **Requirement:** Zero ruff violations
- **Configuration:** See `pyproject.toml`
- **Key rules:**
  - PEP 8 compliance
  - No unused imports
  - No magic numbers (use constants)
  - No complex functions (max complexity: 10)
- **Tool:** ruff
- **Enforcement:** pre-commit hooks + CI

### 4. Security: bandit
- **Requirement:** Zero high-severity issues
- **Tool:** bandit
- **Key checks:**
  - No hardcoded credentials
  - Safe subprocess calls
  - Path traversal protection
  - SQL injection prevention

### 5. Cross-Platform: CI on Ubuntu + macOS
- **Requirement:** Tests pass on both platforms
- **GitHub Actions:** Matrix build
- **Python Version:** 3.14

---

## 🏗️ Architecture Patterns

### VendorAdapter Pattern
All vendor implementations inherit from `VendorAdapter` ABC:

```python
class VendorAdapter(ABC):
    @property
    @abstractmethod
    def info(self) -> VendorInfo: ...

    @abstractmethod
    def is_installed(self) -> bool: ...

    @abstractmethod
    def is_configured(self) -> bool: ...

    # ... 10 more methods
```

**Key Principles:**
- Uniform interface across all vendors
- No vendor-specific logic in shared code
- Use `VendorRegistry` for vendor management

### Database Design
- **SQLite** for operational data
- **JSON metadata** for vendor-specific fields
- **Vendor-agnostic schema** (schema version 2.0.0)
- **Migration framework** for schema changes

### Error Handling
- **Descriptive error messages** with remediation steps
- **Custom exceptions** for domain errors
- **No silent failures** - always log or raise
- **User-friendly CLI output** using Rich

---

## 📝 Code Style

### Python Style (PEP 8 + Google Docstrings)

```python
"""Module-level docstring explaining purpose."""

from __future__ import annotations

import stdlib_imports
import third_party_imports
from local_imports import LocalClass

# Constants at module level
DEFAULT_TIMEOUT = 30
MAX_RETRIES = 3


class MyClass:
    """Brief class description.

    Longer description if needed.

    Attributes:
        public_attr: Description.
        _private_attr: Description.
    """

    def public_method(self, param: str) -> bool:
        """Brief method description.

        Longer description if needed.

        Args:
            param: Parameter description.

        Returns:
            Return value description.

        Raises:
            ValueError: When and why.
        """
        if not param:
            msg = "Parameter cannot be empty"
            raise ValueError(msg)

        return self._private_method(param)

    def _private_method(self, value: str) -> bool:
        """Private methods also need docstrings."""
        return bool(value)
```

### Naming Conventions
- **Classes:** `PascalCase` (e.g., `VendorAdapter`)
- **Functions/Methods:** `snake_case` (e.g., `is_installed`)
- **Constants:** `UPPER_SNAKE_CASE` (e.g., `DEFAULT_CONFIG_DIR`)
- **Private:** Prefix with `_` (e.g., `_internal_method`)
- **Type vars:** `T`, `KT`, `VT` etc.

### Import Order
1. `from __future__ import annotations` (first line)
2. Standard library
3. Third-party packages
4. Local imports
5. TYPE_CHECKING imports

```python
from __future__ import annotations

import json
from pathlib import Path
from typing import TYPE_CHECKING

import typer
from rich.console import Console

from ai_asst_mgr.adapters import VendorAdapter

if TYPE_CHECKING:
    from collections.abc import Callable
```

---

## ✅ Testing Standards

### Test Structure
```
tests/
├── unit/              # Unit tests (95%+ coverage required)
│   ├── test_adapters/
│   ├── test_database/
│   └── test_cli/
├── integration/       # Integration tests (optional but recommended)
└── conftest.py       # Shared fixtures
```

### Test Naming
- **File:** `test_<module>.py`
- **Class:** `Test<ClassName><Method>`
- **Function:** `test_<what_it_tests>`

```python
# test_vendor_adapter.py

class TestClaudeAdapterInitialization:
    """Tests for ClaudeAdapter initialization."""

    def test_initializes_with_default_config_dir(self) -> None:
        """Test adapter initializes with ~/.claude as default."""
        adapter = ClaudeAdapter()
        assert adapter._config_dir == Path.home() / ".claude"

    def test_raises_error_for_invalid_config_dir(self) -> None:
        """Test raises ValueError for invalid config directory."""
        with pytest.raises(ValueError, match="Invalid config directory"):
            ClaudeAdapter(config_dir="")
```

### Fixtures Pattern
Reusable fixtures for common setups:

```python
@pytest.fixture
def adapter_with_temp_dir() -> Iterator[ClaudeAdapter]:
    """Create adapter with temporary directory for testing."""
    with tempfile.TemporaryDirectory() as temp_dir:
        adapter = ClaudeAdapter()
        adapter._config_dir = Path(temp_dir)
        # ... setup test environment ...
        yield adapter
        # ... cleanup (automatic) ...
```

### Mocking Strategy
- **Mock external dependencies** (subprocess, network, filesystem)
- **Don't mock the code under test**
- **Use `pytest.MonkeyPatch` or `unittest.mock.patch`**

```python
def test_is_installed_when_cli_exists(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test is_installed returns True when CLI exists."""
    mock_result = subprocess.CompletedProcess(args=[], returncode=0, stdout="", stderr="")
    monkeypatch.setattr(subprocess, "run", lambda *args, **kwargs: mock_result)

    adapter = ClaudeAdapter()
    assert adapter.is_installed() is True
```

---

## 🔒 Security Best Practices

### 1. Path Traversal Protection
```python
# ❌ BAD - Vulnerable to path traversal
def backup(self, output_path: str) -> None:
    with tarfile.open(output_path, "w:gz") as tar:
        tar.add(self._config_dir)

# ✅ GOOD - Path validation
def backup(self, output_path: Path) -> Path:
    # Validate path is safe
    safe_path = output_path.resolve()
    if not safe_path.is_relative_to(Path.home()):
        msg = "Backup path must be in user's home directory"
        raise SecurityError(msg)

    with tarfile.open(safe_path, "w:gz") as tar:
        tar.add(self._config_dir)

    return safe_path
```

### 2. Subprocess Safety
```python
# ❌ BAD - Shell injection vulnerability
subprocess.run(f"git clone {url}", shell=True)

# ✅ GOOD - List arguments, no shell
subprocess.run(
    ["git", "clone", url, str(target_dir)],
    shell=False,  # nosec - safe subprocess call
    check=True,
    capture_output=True
)
```

### 3. Credential Redaction
Never log or display:
- API keys
- Tokens
- Passwords
- Session IDs

```python
def _redact_credentials(self, config: dict[str, Any]) -> dict[str, Any]:
    """Redact sensitive fields from config."""
    sensitive_keys = {"api_key", "apiKey", "token", "password"}

    redacted = config.copy()
    for key in redacted:
        if key.lower() in sensitive_keys:
            redacted[key] = "***REDACTED***"

    return redacted
```

---

## 🚀 Git Workflow

### Branch Naming
- **Feature:** `feat/<issue-number>-<short-description>`
- **Fix:** `fix/<issue-number>-<short-description>`
- **Parallel dev:** `parallel-dev/agent-<1|2|3>`

### Commit Messages (Conventional Commits)
```
<type>(<scope>): <subject>

<body>

<footer>
```

**Types:**
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation
- `test`: Tests only
- `refactor`: Code refactoring
- `chore`: Maintenance

**Example:**
```
feat(adapters): implement GeminiAdapter with comprehensive tests

- Created GeminiAdapter class (215 statements, 95.47% coverage)
- Implemented all 13 VendorAdapter methods
- Added 50 unit tests covering all functionality
- Mock subprocess calls for CLI detection
- Parse JSON config with API key validation

🤖 Generated with Claude Code

Co-Authored-By: Claude <noreply@anthropic.com>
```

### Pull Request Requirements
1. **One issue per PR** (focused changes)
2. **All tests passing** (26+ tests minimum)
3. **Coverage 95%+** (enforced by CI)
4. **No merge conflicts** with main
5. **Descriptive PR description** with issue link
6. **Conventional commit message**

---

## 🤝 Parallel Agent Coordination

### Agent Assignments
Use `orchestrator.py` for task management:

```bash
# Assign task to agent
python scripts/parallel-dev/orchestrator.py assign 1 16 "Implement status command" 2.0

# Start task
python scripts/parallel-dev/orchestrator.py start 1

# Complete task
python scripts/parallel-dev/orchestrator.py complete 1 src/ai_asst_mgr/cli.py tests/unit/test_cli.py

# Check status
python scripts/parallel-dev/orchestrator.py status

# Detect conflicts
python scripts/parallel-dev/orchestrator.py conflicts

# Get merge order
python scripts/parallel-dev/orchestrator.py merge-order
```

### Merge Order (Staggered)
1. **Agent with fewest conflicts** merges first
2. **Agent 2** rebases on main, then merges
3. **Agent 3** rebases on main, then merges

### Conflict Resolution
- **Prevention:** Orchestrator detects overlapping files
- **Detection:** Run `conflicts` command before merging
- **Resolution:** Manual merge with clear commit message
- **Communication:** Update agent_tracker.json

---

## 📚 Documentation Requirements

### Code Documentation
- **All public APIs** need docstrings
- **Google-style format** (Args, Returns, Raises)
- **Type hints everywhere** (no runtime overhead)
- **Examples in docstrings** for complex functions

### User Documentation
- **README.md:** Project overview, installation, quick start
- **ARCHITECTURE.md:** System design, patterns
- **DATABASE_DESIGN.md:** Schema, migrations
- **Contributing guide:** For external contributors

---

## 🎓 Lessons from Phases 1-2

### What Worked Exceptionally Well
1. **Test-first approach** → 95%+ coverage achieved
2. **Type safety (mypy --strict)** → Caught bugs early
3. **Reusable fixtures** → `adapter_with_temp_dir` pattern
4. **Security review** → Path traversal protection
5. **Clean git history** → One branch per issue

### Apply These Patterns
- **Start with tests** before implementation
- **Use constants** instead of magic numbers
- **Mock aggressively** for external dependencies
- **Type everything** (no `Any` types)
- **Document as you go** (not at the end)

---

## 🚨 Red Flags (Code Smells)

Stop and refactor if you see:
- ❌ Test coverage below 95%
- ❌ mypy errors or `# type: ignore`
- ❌ Functions longer than 50 lines
- ❌ Classes with more than 10 methods
- ❌ Hardcoded values (use constants)
- ❌ Nested conditionals (3+ levels deep)
- ❌ Missing docstrings on public APIs
- ❌ Shell=True in subprocess calls
- ❌ No error handling for external calls

---

## ✨ Excellence Checklist

Before submitting a PR, verify:
- [ ] Tests pass locally: `pytest tests/`
- [ ] Coverage ≥ 95%: `pytest --cov=src/ai_asst_mgr --cov-report=term-missing`
- [ ] Type check passes: `mypy src/ tests/`
- [ ] Linting passes: `ruff check src/ tests/`
- [ ] Formatting applied: `ruff format src/ tests/`
- [ ] Security check passes: `bandit -r src/`
- [ ] All docstrings present (public APIs)
- [ ] No credentials in code/tests
- [ ] Conventional commit message
- [ ] Issue linked in PR description

---

## 🔗 Useful Commands

```bash
# Run all quality checks
pytest --cov=src/ai_asst_mgr --cov-report=term-missing
mypy src/ tests/ --strict
ruff check src/ tests/
ruff format src/ tests/
bandit -r src/

# Run specific test file
pytest tests/unit/test_claude_adapter.py -v

# Run with coverage HTML report
pytest --cov=src/ai_asst_mgr --cov-report=html
open htmlcov/index.html

# Install pre-commit hooks
pre-commit install

# Run pre-commit on all files
pre-commit run --all-files

# Clean build artifacts
rm -rf build/ dist/ *.egg-info htmlcov/ .coverage .mypy_cache/ .pytest_cache/ .ruff_cache/
```

---

## 📞 Questions?

If you encounter ambiguity or need clarification:
1. Check this DEVELOPMENT_STANDARDS.md first
2. Review existing code for patterns
3. Check GitHub Issues for context
4. Review .github/BACKLOG_REVIEW.md for strategic decisions
5. Ask the orchestrator or team lead

---

**Remember:** Quality > Speed. It's better to write correct, well-tested code slowly than to rush and create technical debt.

🚀 Happy coding!
