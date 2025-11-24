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

# Start web dashboard
ai-asst-mgr serve
# Open browser to http://127.0.0.1:8080
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

### **✅ Phase 0: Infrastructure (Completed)**
- [x] Project documentation (README, CONTRIBUTING, guides)
- [x] GitHub repository configuration (single-maintainer control)
- [x] Automation scripts (bootstrap, configuration, labels, milestones, issues)
- [x] Development wiki (setup, workflow, automation)
- [x] GitHub templates (issue templates, PR template, workflows)
- [x] Security policy and CODEOWNERS

### **🚧 Phase 1: Foundation (Week 1)**
- [ ] Initialize uv project structure
- [ ] Configure pyproject.toml
- [ ] Create base directory structure
- [ ] Setup GitHub Actions CI

### **📋 Phase 2: Vendor Adapters (Week 1-2)**
- [ ] Vendor adapter base class
- [ ] Claude adapter implementation
- [ ] Gemini adapter implementation
- [ ] OpenAI Codex adapter implementation
- [ ] Database migration to vendor-agnostic schema

### **🔧 Phase 3: CLI & Operations (Week 2-3)**
- [ ] Core CLI commands (status, init, health, config)
- [ ] Backup operations
- [ ] Audit system
- [ ] Coaching insights

### **🌐 Phase 4: Web & Advanced (Week 4-5)**
- [ ] Web dashboard (HTMX)
- [ ] Capability abstraction
- [ ] Cross-platform scheduling
- [ ] Comprehensive testing

See the [GitHub Project](https://github.com/users/TechR10n/projects/5) for detailed task tracking.

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
