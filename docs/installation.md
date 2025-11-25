# Installation Guide

This guide covers installing and setting up AI Assistant Manager.

## Prerequisites

- **Python 3.14** or later
- **uv** package manager ([install guide](https://github.com/astral-sh/uv))
- **Git** (for sync functionality)
- At least one AI assistant installed:
  - [Claude Code](https://claude.ai/claude-code) by Anthropic
  - [Gemini CLI](https://github.com/google-gemini/gemini-cli) by Google
  - [OpenAI Codex](https://github.com/openai/codex) by OpenAI

## Installation Methods

### From PyPI (Recommended)

```bash
# Install using uv
uv pip install ai-asst-mgr

# Or using pip
pip install ai-asst-mgr
```

### From GitHub

```bash
# Latest release
uv pip install git+https://github.com/TechR10n/ai-asst-mgr.git

# Specific version
uv pip install git+https://github.com/TechR10n/ai-asst-mgr.git@v0.1.0
```

### Development Installation

```bash
# Clone repository
git clone https://github.com/TechR10n/ai-asst-mgr.git
cd ai-asst-mgr

# Install in development mode
uv sync

# Verify installation
uv run ai-asst-mgr --version
```

## Verifying Installation

After installation, verify everything is working:

```bash
# Check version
ai-asst-mgr --version

# Check vendor status
ai-asst-mgr status

# Run health checks
ai-asst-mgr health
```

## Configuration

AI Assistant Manager uses these configuration directories:

| Vendor | Config Directory | Config File |
|--------|-----------------|-------------|
| Claude Code | `~/.claude/` | `settings.json` |
| Gemini CLI | `~/.gemini/` | `settings.json` |
| OpenAI Codex | `~/.codex/` | `config.toml` |

### Initialize Vendors

```bash
# Initialize all detected vendors
ai-asst-mgr init

# Initialize specific vendor
ai-asst-mgr init --vendor claude
```

### Set Configuration

```bash
# Set a config value
ai-asst-mgr config model claude-sonnet-4

# Get a config value
ai-asst-mgr config model

# Set for specific vendor
ai-asst-mgr config --vendor claude model claude-sonnet-4
```

## Troubleshooting

### Common Issues

#### "Command not found"
Ensure the package is installed and in your PATH:
```bash
# Check if installed
uv pip list | grep ai-asst-mgr

# Reinstall
uv pip install --force-reinstall ai-asst-mgr
```

#### "Vendor not detected"
The vendor CLI must be installed and accessible:
```bash
# Check if vendor CLI is available
which claude  # or gemini, codex

# Verify config directory exists
ls -la ~/.claude/  # or ~/.gemini/, ~/.codex/
```

#### "Permission denied"
Check config directory permissions:
```bash
# Fix permissions
chmod 700 ~/.claude
chmod 600 ~/.claude/settings.json
```

### Getting Help

```bash
# CLI help
ai-asst-mgr --help
ai-asst-mgr status --help

# Run diagnostics
ai-asst-mgr doctor
```

## Next Steps

- [Command Reference](commands.md) - Complete CLI documentation
- [Architecture](architecture.md) - System design overview
- [Contributing](contributing.md) - How to contribute
