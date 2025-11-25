# AI Assistant Manager (ai-asst-mgr)

[![Build Status](https://github.com/TechR10n/ai-asst-mgr/workflows/CI/badge.svg)](https://github.com/TechR10n/ai-asst-mgr/actions)
[![Python 3.14](https://img.shields.io/badge/python-3.14-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

> **Universal AI assistant configuration manager** for Claude Code, Gemini CLI, OpenAI Codex, and more.

Manage multiple AI assistants from a single unified interface. Track usage, audit configurations, get coaching insights, and sync settings across machines—all while keeping your vendor configs independent.

---

## 🎯 **Mission**

Provide a **vendor-agnostic toolkit** for managing, tracking, auditing, and optimizing AI assistant configurations across different platforms, while respecting each vendor's independence.

---

## ✨ **Features**

### **🔧 Core Management**
- **Multi-Vendor Support** - Manage Claude Code, Gemini CLI, and OpenAI Codex from one tool
- **Unified Commands** - Common interface across all vendors (status, init, health, config)
- **Independent Configs** - Each vendor's `~/.vendor/` directory remains autonomous
- **Cross-Platform** - Works on macOS and Linux

### **📊 Analytics & Tracking**
- **Session Tracking** - Track usage across all AI assistants in one database
- **Performance Metrics** - Sessions, tool calls, duration, success rates
- **Usage Patterns** - Understand how you use each assistant
- **Cross-Vendor Comparison** - Compare productivity across platforms

### **🔍 Audit & Quality**
- **Configuration Audits** - Validate configs for all vendors
- **Security Checks** - Detect misconfigured API keys, permissions
- **Quality Scoring** - Rate agent/skill quality and documentation
- **Health Monitoring** - Continuous health checks and diagnostics

### **🤖 AI Coaching**
- **Usage Insights** - AI-powered recommendations based on actual usage
- **Optimization Tips** - Suggestions to improve productivity
- **Unused Resources** - Identify agents/skills you never use
- **Weekly Reports** - Automated performance summaries

### **🌐 Web Dashboard**
- **Performance Dashboard** - Visual metrics and charts
- **Weekly Reviews** - Reflective performance review forms
- **Agent Browser** - Universal agent/skill browser across vendors
- **HTMX-Powered** - Fast, modern UI without heavy JavaScript

### **💾 Backup & Sync**
- **Automated Backups** - Schedule backups via LaunchAgent (macOS) or cron (Linux)
- **Git Sync** - Sync configurations from git repositories
- **Cross-Machine** - Easy config distribution across multiple machines
- **Restore** - Quick restoration from backups

### **🎭 Capability Abstraction**
- **Universal Agents** - Manage agents across all vendors with common interface
- **Missing Features** - Synthesize missing capabilities using vendor SDKs
- **Cross-Vendor Sync** - Copy agents/skills between vendors

### **🔗 GitHub Integration** (First-Class Service)
- **Unified GitHub API** - Common GitHub operations for all vendors
- **Activity Tracking** - Track vendor GitHub operations (issues, PRs, commits)
- **Context Separation** - Distinguish self-development, vendor ops, and user ops
- **Attribution** - Know which vendor created which GitHub resources
- **Project Management** - GitHub Project Board integration

---

## 🚀 **Quick Start**

### **Prerequisites**
- Python 3.14
- uv package manager
- At least one AI assistant installed (Claude Code, Gemini CLI, or Codex)

### **Installation**

```bash
# Install from GitHub
uv pip install git+https://github.com/TechR10n/ai-asst-mgr.git

# Or clone for development
git clone https://github.com/TechR10n/ai-asst-mgr.git
cd ai-asst-mgr
uv pip install -e .
```

### **Basic Usage**

```bash
# Check vendor status
ai-asst-mgr status

# Initialize all detected vendors
ai-asst-mgr init

# Run health checks
ai-asst-mgr health

# Get coaching insights
ai-asst-mgr coach
```

### **Example Output**

```
$ ai-asst-mgr status

╭─────────────────────────────────────────────────────────────╮
│                    AI Assistant Status                       │
╰─────────────────────────────────────────────────────────────╯

┏━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Vendor         ┃ Status       ┃ Notes                       ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ Claude Code    │ ✓ Configured │ 5 agents, 12 skills         │
│ Gemini CLI     │ ✓ Installed  │ Run 'ai-asst-mgr init'      │
│ OpenAI Codex   │ ✗ Not Found  │ Install from openai.com     │
└────────────────┴──────────────┴─────────────────────────────┘

Summary: 1 configured, 1 installed, 1 not found
```

### **Backup & Restore**

```bash
# Backup all vendors
ai-asst-mgr backup

# Backup specific vendor
ai-asst-mgr backup --vendor claude

# List existing backups
ai-asst-mgr backup --list

# Restore from backup
ai-asst-mgr restore backup.tar.gz

# Preview what would be restored
ai-asst-mgr restore backup.tar.gz --preview
```

### **Sync from Git**

```bash
# Sync configurations from a repository
ai-asst-mgr sync https://github.com/user/my-ai-configs.git

# Sync with preview (dry-run)
ai-asst-mgr sync https://github.com/user/configs.git --preview

# Sync with specific merge strategy
ai-asst-mgr sync https://github.com/user/configs.git --strategy merge
```

### **AI Coaching**

```bash
# Get usage insights for all vendors
ai-asst-mgr coach

# Coach specific vendor
ai-asst-mgr coach --vendor claude

# Compare vendors
ai-asst-mgr coach --compare

# Generate weekly report
ai-asst-mgr coach --report weekly
```

---

## 📖 **Documentation**

- **[Installation Guide](docs/installation.md)** - Detailed setup instructions
- **[Command Reference](docs/commands.md)** - Complete CLI documentation
- **[Auditing Guide](docs/auditing.md)** - Configuration audits and security
- **[Coaching System](docs/coaching.md)** - Usage analytics and insights
- **[Architecture](docs/architecture.md)** - System design and internals
- **[Contributing](docs/contributing.md)** - How to contribute

### **Vendor-Specific Guides**
- [Claude Code Setup](docs/vendors/claude.md)
- [Gemini CLI Setup](docs/vendors/gemini.md)
- [OpenAI Codex Setup](docs/vendors/openai.md)

---

## 🏗️ **Architecture**

```
┌─────────────────────────────────────────────────────────┐
│  CLI / Web Dashboard                                     │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│  Operations Layer                                        │
│  • Backup/Restore  • Audit  • Coaching  • Sync          │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│  Vendor Adapters (Plugin System)                        │
│  • ClaudeAdapter  • GeminiAdapter  • OpenAIAdapter      │
└─────────────────┬───────────────────────────────────────┘
                  │
┌─────────────────▼───────────────────────────────────────┐
│  Vendor Configurations (Independent)                     │
│  ~/.claude/  ~/.gemini/  ~/.codex/                      │
└─────────────────────────────────────────────────────────┘
```

### **Key Design Principles**
1. **Vendor Independence** - Each vendor's config stays independent
2. **Plugin Architecture** - Easy to add new vendors
3. **Capability Abstraction** - Common interface across different features
4. **Privacy First** - All data stays local (no cloud)
5. **Extensibility** - Built for customization

---

## 🛠️ **CLI Commands**

### **Core Commands**
```bash
ai-asst-mgr status                    # Show all vendors and their status
ai-asst-mgr init [--vendor VENDOR]    # Initialize vendor configs
ai-asst-mgr health [--vendor VENDOR]  # Run health checks
ai-asst-mgr config KEY [VALUE]        # Get/set configuration
ai-asst-mgr doctor                    # Diagnose and fix issues
```

### **Backup & Sync**
```bash
ai-asst-mgr backup [--vendor VENDOR]  # Backup configurations
ai-asst-mgr restore BACKUP_PATH       # Restore from backup
ai-asst-mgr sync VENDOR --repo URL    # Sync from git repository
```

### **Audit & Coaching**
```bash
ai-asst-mgr audit [--vendor VENDOR]   # Audit configurations
ai-asst-mgr coach [--vendor VENDOR]   # Get usage insights
ai-asst-mgr coach --report weekly     # Generate weekly report
```

### **Agent Management**
```bash
ai-asst-mgr agents list               # List all agents (all vendors)
ai-asst-mgr agents create             # Create new agent
ai-asst-mgr agents sync AGENT         # Sync agent across vendors
```

### **Web Dashboard**
```bash
ai-asst-mgr serve [--port 8080]       # Start web dashboard
ai-asst-mgr serve --reload            # Development mode
```

---

## 📊 **Vendor Support Matrix**

| Feature | Claude Code | Gemini CLI | OpenAI Codex |
|---------|-------------|------------|--------------|
| **Config Location** | `~/.claude/` | `~/.gemini/` | `~/.codex/` |
| **Config Format** | JSON | JSON | TOML |
| **API Key** | ❌ (Desktop app) | ✅ Required | ✅ Required |
| **Native Agents** | ✅ Yes | ❌ → MCP | ❌ → MCP |
| **Context Files** | ❌ → Synthesized | ✅ GEMINI.md | ✅ AGENTS.md |
| **MCP Servers** | ✅ Yes | ✅ Yes (A2A) | ✅ Yes |
| **Session Tracking** | ✅ Full | ⚠️ Limited | ⚠️ Limited |
| **Profiles** | ❌ → Multiple configs | ❌ → Multiple configs | ✅ Native |

**Legend:**
- ✅ Fully supported
- ⚠️ Partially supported
- ❌ → X Feature synthesized using vendor SDK/MCP

---

## 🤝 **Contributing**

We welcome contributions! Please see our [Contributing Guide](CONTRIBUTING.md) for details.

**For Contributors**:
- 📖 **[Development Wiki](https://github.com/TechR10n/ai-asst-mgr/wiki)** - Complete development guide
- 🛠️ **[Development Setup](https://github.com/TechR10n/ai-asst-mgr/wiki/Development-Setup)** - Get your environment ready
- 🔄 **[Development Workflow](https://github.com/TechR10n/ai-asst-mgr/wiki/Development-Workflow)** - Branch strategy and PR process
- 🏷️ **[GitHub Setup Scripts](https://github.com/TechR10n/ai-asst-mgr/wiki/GitHub-Setup-Scripts)** - Automation tools

### **Development Setup**

```bash
# Clone repository
git clone https://github.com/TechR10n/ai-asst-mgr.git
cd ai-asst-mgr

# Install dependencies
uv sync

# Install pre-commit hooks
pre-commit install

# Run tests
uv run pytest

# Run linter
uv run ruff check src/

# Run type checker
uv run mypy src/
```

### **Project Management**
- **Issues:** https://github.com/TechR10n/ai-asst-mgr/issues
- **Project Board:** https://github.com/users/TechR10n/projects/5
- **Discussions:** https://github.com/TechR10n/ai-asst-mgr/discussions

---

## 🗺️ **Roadmap**

### **✅ Phase 1: Foundation (Completed)**
- [x] Initialize uv project structure (Python 3.14)
- [x] Configure pyproject.toml with all dependencies
- [x] Create base directory structure
- [x] Setup GitHub Actions CI (Ubuntu + macOS)
- [x] Pre-commit hooks (ruff, mypy, bandit)
- [x] Quality gates (95%+ coverage, mypy --strict)

**Completed:** November 23, 2025 | **PRs:** #62

### **✅ Phase 2: Vendor Adapters (Completed)**
- [x] VendorAdapter ABC (13 abstract methods)
- [x] ClaudeAdapter (200 statements, 95.15% coverage, 47 tests)
- [x] GeminiAdapter (215 statements, 95.47% coverage, 50 tests)
- [x] OpenAIAdapter (242 statements, 95.21% coverage, 50 tests)
- [x] VendorRegistry (32 statements, 100% coverage, 22 tests)

**Completed:** November 24, 2025 | **PRs:** #64, #66, #67, #68

### **✅ Phase 3: CLI Implementation (Completed)**
- [x] Implement status command
- [x] Implement health command
- [x] Implement doctor command
- [x] Implement init command
- [x] Implement config command

**Completed:** November 25, 2025 | **PRs:** #71, #72

### **✅ Phase 5: Coaching System (Completed)**
- [x] ClaudeCoach with usage analytics
- [x] GeminiCoach with usage analytics
- [x] CodexCoach with usage analytics
- [x] Cross-vendor comparison
- [x] Weekly/monthly reports

**Completed:** November 25, 2025 | **PRs:** #74

### **✅ Phase 6: Backup & Restore (Completed)**
- [x] BackupManager with retention policies
- [x] RestoreManager with selective restore
- [x] SyncManager with merge strategies
- [x] GitPython-based secure git operations
- [x] CWE-22 path traversal protection

**Completed:** November 25, 2025 | **PRs:** #75, #76

### **✅ Phase 8: Capabilities (Completed)**
- [x] UniversalAgentManager (Issue #43)
- [x] Agents CLI command (Issue #44)
- [x] Agent discovery across vendors
- [x] Cross-vendor agent sync

**Completed:** November 25, 2025 | **Issues:** #43, #44

### **✅ Phase 9: Web Dashboard (Completed)**
- [x] FastAPI application setup (Issue #45)
- [x] HTMX components (Issue #50)
- [x] Dashboard pages (Issues #47-49, #52)
- [x] Session history page with filtering
- [x] Agent browser with search and detail modal
- [x] Database sync integration

**Completed:** November 25, 2025 | **Issues:** #45-52

### **✅ Phase 10: Testing & Documentation (Completed)**
- [x] CHANGELOG.md created
- [x] README.md updated with examples
- [x] GitHub release workflow exists
- [x] Database sync CLI commands (db init, sync, status)
- [x] LaunchAgent for scheduled sync

**Completed:** November 25, 2025

### **🔄 Phase 11: GitHub Integration (In Progress)**
- [x] GitHub Activity Logger (#82)
- [x] Vendor Attribution System (#83)
- [ ] GitHub Activity Dashboard Page (#84)
- [ ] Context Separation for GitHub Operations (#85)
- [ ] GitHub Projects API Integration (#86)
- [ ] Unified GitHub API Module (#87)
- [ ] Vendor GitHub Actions Support (#89)

**Started:** November 25, 2025 | **PRs:** #91 (partial)

### **🎯 Progress Summary**
- **Tests:** 1,520 passing
- **Coverage:** 95.03%
- **Type Safety:** mypy --strict ✅
- **Security:** bandit passing ✅
- **Phases:** 10 completed, Phase 11 in progress

See [GitHub Issues](https://github.com/TechR10n/ai-asst-mgr/issues) for detailed task breakdown.

---

## 🤖 **Development Infrastructure**

### **Parallel Agent Development**
We use git worktrees to enable **3 AI agents to work simultaneously** on different issues:
- **37% time savings** through parallel development
- **Automated orchestration** via `scripts/parallel-dev/orchestrator.py`
- **Conflict detection** before merging
- **Staggered merge strategy** for clean history

```bash
# Setup worktrees
./scripts/parallel-dev/setup_worktrees.sh

# Assign tasks
python scripts/parallel-dev/orchestrator.py assign 1 16 "Implement status command" 2.0

# Check status
python scripts/parallel-dev/orchestrator.py status
```

See [scripts/parallel-dev/README.md](scripts/parallel-dev/README.md) for details.

### **Claude GitHub Actions Integration**
Mention `@claude` in issues or PRs to get AI assistance:

```markdown
I'm implementing Issue #16 but unsure about the best approach.
@claude can you suggest how to structure the Rich table output?
```

Claude will:
- Review code and suggest improvements
- Answer architecture questions
- Help with testing strategies
- Provide code examples
- Troubleshoot issues

See [CLAUDE.md](CLAUDE.md) for usage guide.

### **Automated Releases**
Version bumping and releases are automated:

```bash
# Bump version (patch: 0.1.0 → 0.1.1)
./scripts/bump_version.sh patch

# Push to trigger release
git push origin main
git push origin v0.1.1
```

GitHub Actions will:
- ✅ Run tests and quality checks
- ✅ Build package distributions
- ✅ Generate changelog from commits
- ✅ Create GitHub release with artifacts
- ✅ Update CHANGELOG.md automatically

See [CHANGELOG.md](CHANGELOG.md) for release history.

### **Quality Standards**
All code follows strict quality gates defined in [.claude/DEVELOPMENT_STANDARDS.md](.claude/DEVELOPMENT_STANDARDS.md):
- **95%+ test coverage** (enforced by CI)
- **mypy --strict** type checking
- **ruff** linting (no violations)
- **bandit** security checks
- **Cross-platform CI** (Ubuntu + macOS)

---

## 📄 **License**

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 **Acknowledgments**

- [Claude Code](https://claude.ai/claude-code) by Anthropic
- [Gemini CLI](https://github.com/google-gemini/gemini-cli) by Google
- [OpenAI Codex](https://github.com/openai/codex) by OpenAI
- [HTMX](https://htmx.org/) for modern web interactions
- [FastAPI](https://fastapi.tiangolo.com/) for the web framework
- [Typer](https://typer.tiangolo.com/) for the CLI framework

---

## 📞 **Support**

- **Issues:** [GitHub Issues](https://github.com/TechR10n/ai-asst-mgr/issues)
- **Discussions:** [GitHub Discussions](https://github.com/TechR10n/ai-asst-mgr/discussions)
- **Documentation:** [docs/](docs/)

---

<p align="center">
  Made with ❤️ by the AI Assistant Manager community
</p>
