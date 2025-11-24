# Development Setup

Complete guide for setting up your local development environment for ai-asst-mgr.

## Prerequisites

### 1. Python 3.14

ai-asst-mgr requires **Python 3.14 exactly** (not 3.12+).

**macOS (using pyenv)**:
```bash
# Install pyenv
brew install pyenv

# Install Python 3.14
pyenv install 3.14.0

# Set as local version in project
cd ai-asst-mgr
pyenv local 3.14.0
```

**Linux (using pyenv)**:
```bash
# Install dependencies
sudo apt update
sudo apt install -y make build-essential libssl-dev zlib1g-dev \
    libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
    libncursesw5-dev xz-utils tk-dev libxml2-dev libxmlsec1-dev \
    libffi-dev liblzma-dev

# Install pyenv
curl https://pyenv.run | bash

# Add to ~/.bashrc or ~/.zshrc
export PATH="$HOME/.pyenv/bin:$PATH"
eval "$(pyenv init -)"
eval "$(pyenv virtualenv-init -)"

# Install Python 3.14
pyenv install 3.14.0

# Set as local version
cd ai-asst-mgr
pyenv local 3.14.0
```

**Verify**:
```bash
python --version
# Should output: Python 3.14.0 or 3.14.x
```

### 2. uv Package Manager

**macOS / Linux**:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

**Verify**:
```bash
uv --version
```

### 3. Git

**macOS**:
```bash
brew install git
```

**Linux**:
```bash
sudo apt install git
```

### 4. GitHub CLI (Optional but Recommended)

**macOS**:
```bash
brew install gh
```

**Linux**:
```bash
# See https://github.com/cli/cli/blob/trunk/docs/install_linux.md
curl -fsSL https://cli.github.com/packages/githubcli-archive-keyring.gpg | sudo dd of=/usr/share/keyrings/githubcli-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/githubcli-archive-keyring.gpg] https://cli.github.com/packages stable main" | sudo tee /etc/apt/sources.list.d/github-cli.list > /dev/null
sudo apt update
sudo apt install gh
```

**Authenticate**:
```bash
gh auth login
```

## Initial Setup

### 1. Fork and Clone

```bash
# Fork the repository on GitHub first
# Then clone your fork
git clone https://github.com/YOUR_USERNAME/ai-asst-mgr.git
cd ai-asst-mgr

# Add upstream remote
git remote add upstream https://github.com/TechR10n/ai-asst-mgr.git
```

### 2. Install Dependencies

```bash
# Install all dependencies (including dev dependencies)
uv sync

# Verify installation
uv run python -c "import ai_asst_mgr; print(ai_asst_mgr.__version__)"
```

This creates:
- `.venv/` directory with virtual environment
- `.python-version` file (if using pyenv)
- `uv.lock` lockfile

### 3. Install Pre-commit Hooks

```bash
# Install pre-commit
uv pip install pre-commit

# Install hooks
pre-commit install
```

Pre-commit hooks run automatically before each commit and check:
- Code formatting (ruff format)
- Linting (ruff check)
- Type checking (mypy)
- Import sorting
- Trailing whitespace
- File size limits

### 4. Set up Editor

#### VS Code

Install extensions:
```bash
code --install-extension ms-python.python
code --install-extension ms-python.vscode-pylance
code --install-extension charliermarsh.ruff
```

**`.vscode/settings.json`**:
```json
{
  "python.defaultInterpreterPath": ".venv/bin/python",
  "python.analysis.typeCheckingMode": "strict",
  "editor.formatOnSave": true,
  "editor.codeActionsOnSave": {
    "source.organizeImports": true
  },
  "[python]": {
    "editor.defaultFormatter": "charliermarsh.ruff",
    "editor.formatOnSave": true
  },
  "ruff.lint.enable": true,
  "ruff.format.enable": true
}
```

#### PyCharm

1. **Set Python interpreter**: Settings → Project → Python Interpreter → Add → Virtualenv Environment → Existing → Select `.venv/bin/python`
2. **Enable ruff**: Settings → Tools → Ruff → Enable ruff
3. **Enable mypy**: Settings → Tools → External Tools → Add mypy

## Verify Setup

### Run Tests

```bash
# Run all tests
uv run pytest

# Run with coverage
uv run pytest --cov=src/ai_asst_mgr --cov-report=html

# View coverage report
open htmlcov/index.html  # macOS
xdg-open htmlcov/index.html  # Linux
```

### Run Linter

```bash
# Check code
uv run ruff check src/

# Auto-fix issues
uv run ruff check --fix src/
```

### Run Formatter

```bash
# Check formatting
uv run ruff format --check src/

# Format code
uv run ruff format src/
```

### Run Type Checker

```bash
# Type check
uv run mypy src/
```

### Run All Quality Checks

```bash
# Run everything
uv run pytest && \
uv run ruff check src/ && \
uv run ruff format --check src/ && \
uv run mypy src/
```

## Development Tools

### CLI Development

Run the CLI during development:

```bash
# Run CLI
uv run ai-asst-mgr --help

# Or use python -m
uv run python -m ai_asst_mgr --help
```

### Web Dashboard Development

```bash
# Start with auto-reload
uv run ai-asst-mgr serve --reload --port 8080

# Open in browser
open http://127.0.0.1:8080
```

### Database Inspection

```bash
# SQLite CLI
sqlite3 ~/Data/ai-asst-mgr/sessions.db

# Query tables
sqlite> .tables
sqlite> SELECT * FROM sessions LIMIT 5;
sqlite> .exit
```

### Debug Logging

Set environment variable for debug logging:

```bash
export AI_ASST_MGR_LOG_LEVEL=DEBUG
uv run ai-asst-mgr status
```

## Project Structure

```
ai-asst-mgr/
├── src/
│   └── ai_asst_mgr/          # Main package
│       ├── __init__.py
│       ├── __main__.py        # Entry point
│       ├── cli.py             # CLI commands
│       ├── vendors/           # Vendor adapters
│       ├── services/          # Services (GitHub, etc.)
│       ├── database/          # Database operations
│       ├── operations/        # Operations (backup, audit, etc.)
│       ├── capabilities/      # Capability abstraction
│       ├── platform/          # Platform-specific code
│       └── web/               # Web dashboard
├── tests/                     # Tests
├── docs/                      # Documentation
├── scripts/                   # Automation scripts
├── wiki/                      # Development wiki (this)
├── pyproject.toml             # Project config
├── uv.lock                    # Lockfile
└── README.md                  # User documentation
```

## Common Issues

### Python version mismatch

**Error**: `Requires Python 3.14, but found 3.12`

**Solution**:
```bash
pyenv local 3.14.0
uv sync
```

### uv not found

**Error**: `command not found: uv`

**Solution**:
```bash
# Re-run installer
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add to PATH (add to ~/.bashrc or ~/.zshrc)
export PATH="$HOME/.local/bin:$PATH"
source ~/.bashrc  # or ~/.zshrc
```

### Pre-commit hooks fail

**Error**: Pre-commit hooks fail on commit

**Solution**:
```bash
# Run hooks manually
pre-commit run --all-files

# Fix issues
uv run ruff check --fix src/
uv run ruff format src/

# Commit again
git commit
```

### Import errors during development

**Error**: `ModuleNotFoundError: No module named 'ai_asst_mgr'`

**Solution**:
```bash
# Install in editable mode
uv pip install -e .

# Or use uv run
uv run python -m ai_asst_mgr
```

## Next Steps

1. **Read [[Project Structure]]** - Understand the codebase layout
2. **Read [[Development Workflow]]** - Learn branch strategy and PR process
3. **Pick an issue** - Find a [good first issue](https://github.com/TechR10n/ai-asst-mgr/labels/good-first-issue)
4. **Start coding!** - Follow the [[Development Workflow]]

## See Also

- [[Project Structure]] - Detailed codebase organization
- [[Development Workflow]] - Branch strategy and PR process
- [[Writing Tests]] - Testing guidelines
- [[Coding Standards]] - Python style guide
- [[Troubleshooting]] - Common development issues
