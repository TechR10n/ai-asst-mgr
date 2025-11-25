# ai-asst-mgr Development Wiki

Welcome to the **ai-asst-mgr development wiki**! This wiki is dedicated to building and maturing the ai-asst-mgr project itself.

> **Note**: This wiki is for **contributors and maintainers** working on ai-asst-mgr.
> For **end-user documentation**, see the [main README](https://github.com/TechR10n/ai-asst-mgr).

---

## 📊 Current Project Status

**Last Updated:** November 25, 2025

| Metric | Value |
|--------|-------|
| **Tests** | 1,520 passing |
| **Coverage** | 95.03% |
| **Type Safety** | mypy --strict ✅ |
| **Security** | bandit passing ✅ |
| **Python Version** | 3.14 |

### Phase Progress

| Phase | Status | PRs |
|-------|--------|-----|
| Phase 1: Foundation | ✅ Complete | #62 |
| Phase 2: Vendor Adapters | ✅ Complete | #64, #66, #67, #68 |
| Phase 3: CLI Commands | ✅ Complete | #71, #72 |
| Phase 5: Coaching System | ✅ Complete | #74 |
| Phase 6: Backup & Restore | ✅ Complete | #75, #76 |
| Phase 8: Capabilities | ✅ Complete | #43, #44 |
| Phase 9: Web Dashboard | ✅ Complete | #45-52 |
| Phase 10: Testing & Docs | ✅ Complete | #90 |
| Phase 11: GitHub Integration | 🔄 In Progress | #91 (partial) |

### Current Milestone: Phase 11 - GitHub Integration

**Completed Issues:**
- ✅ #82 - GitHub Activity Logger
- ✅ #83 - Vendor Attribution System

**Remaining Issues:**
- 🔲 #84 - GitHub Activity Dashboard Page
- 🔲 #85 - Context Separation for GitHub Operations
- 🔲 #86 - GitHub Projects API Integration
- 🔲 #87 - Unified GitHub API Module
- 🔲 #89 - Vendor GitHub Actions Support

---

## 📚 Wiki Contents

### Getting Started
- **[[Development Setup]]** - Setting up your development environment
- **[[Project Structure]]** - Understanding the codebase organization
- **[[Development Workflow]]** - Branch strategy, commits, PRs

### Architecture & Design
- **[[Architecture Overview]]** - High-level system architecture
- **[[Vendor Adapter Design]]** - How vendor adapters work
- **[[GitHub Integration]]** - GitHub as first-class service
- **[[Database Schema]]** - SQLite schema and migrations
- **[[Web Dashboard Architecture]]** - FastAPI + HTMX design

### Development Guides
- **[[Adding a New Vendor]]** - How to add support for a new AI assistant
- **[[Adding CLI Commands]]** - Creating new commands with Typer
- **[[Adding Web Routes]]** - Creating new dashboard routes
- **[[Writing Tests]]** - Testing guidelines and patterns
- **[[Documentation Guide]]** - Writing and maintaining documentation

### Processes
- **[[Release Process]]** - How to cut a new release
- **[[Issue Triage]]** - Triaging and labeling issues
- **[[Code Review Guidelines]]** - What to look for in reviews
- **[[Performance Testing]]** - Benchmarking and optimization

### Tools & Automation
- **[[GitHub Setup Scripts]]** - Automated issue/label/milestone creation
- **[[CI/CD Pipeline]]** - GitHub Actions workflows
- **[[Local Development Tools]]** - Scripts and utilities

### Reference
- **[[Coding Standards]]** - Python style guide and conventions
- **[[API Reference]]** - Internal API documentation
- **[[Troubleshooting]]** - Common development issues
- **[[FAQ]]** - Frequently asked questions

---

## 🎯 Quick Links

- **Repository**: https://github.com/TechR10n/ai-asst-mgr
- **Issues**: https://github.com/TechR10n/ai-asst-mgr/issues
- **Project Board**: https://github.com/users/TechR10n/projects/5
- **Discussions**: https://github.com/TechR10n/ai-asst-mgr/discussions

---

## 🚀 Getting Started

1. **Clone the repository**
   ```bash
   git clone https://github.com/TechR10n/ai-asst-mgr.git
   cd ai-asst-mgr
   ```

2. **Set up development environment**
   ```bash
   # Install Python 3.14
   # Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh

   # Install dependencies
   uv sync

   # Install pre-commit hooks
   pre-commit install
   ```

3. **Read the development guides**
   - [[Development Setup]]
   - [[Project Structure]]
   - [[Development Workflow]]

4. **Pick an issue and start coding!**
   - Check the [good first issue](https://github.com/TechR10n/ai-asst-mgr/labels/good-first-issue) label
   - Follow the [[Development Workflow]]

---

## 📝 Contributing

See [[Development Workflow]] for:
- Branch naming conventions
- Commit message format
- PR process
- Code review expectations

---

## 🛠️ Self-Development vs. User Documentation

This wiki separates **two concerns**:

### 1. **Building ai-asst-mgr** (This Wiki - SELF Context)
- How to develop and contribute to ai-asst-mgr
- Architecture and design decisions
- Development processes and tools
- Internal APIs and implementation details

### 2. **Using ai-asst-mgr** (Main Docs - USER Context)
- How to install and use ai-asst-mgr
- End-user CLI commands
- Configuration guides
- Troubleshooting for users

**Guideline**: If it's about *building* ai-asst-mgr, it goes in the **Wiki**.
If it's about *using* ai-asst-mgr, it goes in the **main docs**.

---

## 💡 Philosophy

ai-asst-mgr is built on these principles:

1. **Vendor Independence** - Respect each vendor's autonomy
2. **Plugin Architecture** - Easy to extend
3. **Privacy First** - All data stays local
4. **Dogfooding** - We use ai-asst-mgr to build ai-asst-mgr
5. **GitHub First-Class** - GitHub as core service provider

---

## 🤝 Community

- **Ask questions**: [GitHub Discussions](https://github.com/TechR10n/ai-asst-mgr/discussions)
- **Report bugs**: [GitHub Issues](https://github.com/TechR10n/ai-asst-mgr/issues)
- **Chat**: *Coming soon*

---

## 📜 License

MIT License - See [LICENSE](https://github.com/TechR10n/ai-asst-mgr/blob/main/LICENSE)
