# GitHub Integration - First-Class Service Provider

## Overview

Since all AI agent assistants (Claude Code, Gemini CLI, OpenAI Codex) have extensive GitHub-specific capabilities, GitHub is treated as a **first-class service provider** in ai-asst-mgr.

This document describes the unified GitHub integration layer that all vendors can leverage.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Vendor Adapters                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐     │
│  │   Claude     │  │   Gemini     │  │   Codex      │     │
│  │   Adapter    │  │   Adapter    │  │   Adapter    │     │
│  └──────┬───────┘  └──────┬───────┘  └──────┬───────┘     │
│         │                 │                  │              │
│         └─────────────────┼──────────────────┘              │
│                          │                                  │
└──────────────────────────┼──────────────────────────────────┘
                           │
                           ▼
        ┌──────────────────────────────────────┐
        │   GitHub Service (Unified Layer)     │
        │                                      │
        │  • Repository Operations             │
        │  • Issue Management                  │
        │  • Pull Request Operations           │
        │  • Commit & Branch Operations        │
        │  • Authentication Management         │
        │  • Webhooks & Events                 │
        │  • GitHub Actions Integration        │
        │  • Project Board Operations          │
        └──────────────────┬───────────────────┘
                           │
                           ▼
                ┌─────────────────────┐
                │   GitHub CLI (gh)   │
                │   GitHub API        │
                │   Git (native)      │
                └─────────────────────┘
```

## Why GitHub is First-Class

All AI agent vendors provide GitHub-specific features:

### Claude Code
- Native `gh` command integration via Bash tool
- Pull request creation with commit messages
- Issue management and linking
- Branch operations and git workflows
- GitHub Actions awareness

### Gemini CLI
- GitHub repository context
- Issue and PR analysis
- Code review capabilities
- GitHub API integration

### OpenAI Codex
- GitHub-aware code generation
- Repository structure understanding
- GitHub workflow automation
- Integration with GitHub Copilot ecosystem

## GitHub Service API

### Module: `src/ai_asst_mgr/services/github_service.py`

```python
from dataclasses import dataclass
from enum import Enum
from typing import Optional, Protocol


class GitHubAuthMethod(Enum):
    """GitHub authentication methods."""
    CLI = "gh_cli"  # GitHub CLI authentication
    TOKEN = "token"  # Personal access token
    SSH = "ssh"  # SSH key authentication
    APP = "app"  # GitHub App installation


@dataclass
class GitHubConfig:
    """GitHub configuration."""
    auth_method: GitHubAuthMethod
    token: Optional[str] = None
    username: Optional[str] = None
    default_org: Optional[str] = None


@dataclass
class Repository:
    """GitHub repository."""
    owner: str
    name: str
    full_name: str  # owner/name
    url: str
    default_branch: str
    is_private: bool


@dataclass
class Issue:
    """GitHub issue."""
    number: int
    title: str
    body: str
    state: str  # open, closed
    labels: list[str]
    assignees: list[str]
    milestone: Optional[str]
    created_at: str
    updated_at: str
    url: str


@dataclass
class PullRequest:
    """GitHub pull request."""
    number: int
    title: str
    body: str
    state: str  # open, closed, merged
    source_branch: str
    target_branch: str
    labels: list[str]
    reviewers: list[str]
    created_at: str
    updated_at: str
    url: str


class GitHubService:
    """
    Unified GitHub service for all vendor adapters.

    This service provides common GitHub operations that any vendor
    can use, avoiding reimplementation of GitHub functionality.
    """

    def __init__(self, config: Optional[GitHubConfig] = None):
        """Initialize GitHub service."""
        self.config = config or self._detect_config()

    # Authentication
    def is_authenticated(self) -> bool:
        """Check if GitHub CLI is authenticated."""
        ...

    def authenticate(self) -> bool:
        """Authenticate with GitHub."""
        ...

    def get_current_user(self) -> str:
        """Get authenticated username."""
        ...

    # Repository Operations
    def get_repository(self, repo: str) -> Repository:
        """Get repository information (owner/repo)."""
        ...

    def list_repositories(self, org: Optional[str] = None) -> list[Repository]:
        """List repositories for user or organization."""
        ...

    def clone_repository(self, repo: str, path: str) -> bool:
        """Clone a repository to local path."""
        ...

    # Issue Management
    def create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        labels: Optional[list[str]] = None,
        assignees: Optional[list[str]] = None,
        milestone: Optional[str] = None
    ) -> Issue:
        """Create a new issue."""
        ...

    def get_issue(self, repo: str, issue_number: int) -> Issue:
        """Get issue details."""
        ...

    def list_issues(
        self,
        repo: str,
        state: str = "open",
        labels: Optional[list[str]] = None
    ) -> list[Issue]:
        """List issues in repository."""
        ...

    def update_issue(
        self,
        repo: str,
        issue_number: int,
        **kwargs
    ) -> Issue:
        """Update issue (title, body, labels, state, etc.)."""
        ...

    def close_issue(self, repo: str, issue_number: int) -> Issue:
        """Close an issue."""
        ...

    # Pull Request Operations
    def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        source_branch: str,
        target_branch: str = "main",
        labels: Optional[list[str]] = None,
        reviewers: Optional[list[str]] = None
    ) -> PullRequest:
        """Create a pull request."""
        ...

    def get_pull_request(self, repo: str, pr_number: int) -> PullRequest:
        """Get PR details."""
        ...

    def list_pull_requests(
        self,
        repo: str,
        state: str = "open"
    ) -> list[PullRequest]:
        """List pull requests."""
        ...

    def merge_pull_request(
        self,
        repo: str,
        pr_number: int,
        merge_method: str = "merge"  # merge, squash, rebase
    ) -> bool:
        """Merge a pull request."""
        ...

    # Branch Operations
    def create_branch(
        self,
        repo_path: str,
        branch_name: str,
        from_branch: str = "main"
    ) -> bool:
        """Create a new branch."""
        ...

    def delete_branch(
        self,
        repo_path: str,
        branch_name: str,
        remote: bool = False
    ) -> bool:
        """Delete a branch."""
        ...

    def get_current_branch(self, repo_path: str) -> str:
        """Get current branch name."""
        ...

    def list_branches(self, repo_path: str) -> list[str]:
        """List all branches."""
        ...

    # Commit Operations
    def commit(
        self,
        repo_path: str,
        message: str,
        files: Optional[list[str]] = None
    ) -> bool:
        """Create a commit."""
        ...

    def push(
        self,
        repo_path: str,
        branch: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """Push commits to remote."""
        ...

    def get_commit_history(
        self,
        repo_path: str,
        limit: int = 10
    ) -> list[dict]:
        """Get commit history."""
        ...

    # Project Board Operations
    def list_projects(self, org: Optional[str] = None) -> list[dict]:
        """List GitHub projects."""
        ...

    def add_issue_to_project(
        self,
        project_id: str,
        issue_url: str
    ) -> bool:
        """Add issue to project board."""
        ...

    # GitHub Actions
    def list_workflows(self, repo: str) -> list[dict]:
        """List GitHub Actions workflows."""
        ...

    def get_workflow_runs(
        self,
        repo: str,
        workflow: str,
        limit: int = 10
    ) -> list[dict]:
        """Get workflow run history."""
        ...

    def trigger_workflow(
        self,
        repo: str,
        workflow: str,
        ref: str = "main",
        inputs: Optional[dict] = None
    ) -> bool:
        """Trigger a workflow dispatch."""
        ...

    # Utilities
    def _detect_config(self) -> GitHubConfig:
        """Auto-detect GitHub configuration."""
        ...

    def _run_gh_command(self, args: list[str]) -> tuple[bool, str, str]:
        """Run GitHub CLI command and return (success, stdout, stderr)."""
        ...
```

## Use Cases

### 1. Unified Issue Tracking Across Vendors

Track which vendor creates which issues:

```python
from ai_asst_mgr.services.github_service import GitHubService
from ai_asst_mgr.vendors.claude import ClaudeAdapter

# Initialize services
github = GitHubService()
claude = ClaudeAdapter()

# Claude creates an issue
issue = github.create_issue(
    repo="TechR10n/ai-asst-mgr",
    title="Add new feature",
    body=f"Created by Claude Code\n\nSession ID: {claude.current_session}",
    labels=["vendor-claude", "type-feature"]
)

# Track in vendor-agnostic database
db.log_github_activity(
    vendor="claude",
    action="create_issue",
    issue_number=issue.number,
    session_id=claude.current_session
)
```

### 2. Cross-Vendor PR Management

```python
# Gemini creates a branch and commits
github.create_branch(repo_path=".", branch_name="feature/gemini-enhancement")
github.commit(repo_path=".", message="feat: add Gemini enhancement")
github.push(repo_path=".", branch="feature/gemini-enhancement")

# Claude creates the PR
pr = github.create_pull_request(
    repo="TechR10n/ai-asst-mgr",
    title="Add Gemini enhancement",
    body="Closes #42\n\nGenerated with [Claude Code](https://claude.com/claude-code)",
    source_branch="feature/gemini-enhancement",
    target_branch="main",
    labels=["vendor-gemini", "vendor-claude"]
)
```

### 3. Repository Context for All Vendors

```python
# Any vendor can get repo context
repo = github.get_repository("TechR10n/ai-asst-mgr")

# Use in vendor operations
claude.set_context({
    "repo": repo.full_name,
    "default_branch": repo.default_branch,
    "is_private": repo.is_private
})

gemini.set_context({
    "repo_url": repo.url,
    "repo_info": repo
})
```

### 4. Automated Workflow Triggers

```python
# After vendor completes a task, trigger CI/CD
if task_completed:
    github.trigger_workflow(
        repo="TechR10n/ai-asst-mgr",
        workflow="ci.yml",
        ref="main",
        inputs={"vendor": "claude", "session_id": session_id}
    )
```

## Database Schema Extensions

Track GitHub activities across vendors:

```sql
CREATE TABLE github_activities (
    activity_id TEXT PRIMARY KEY,
    vendor TEXT NOT NULL,
    session_id TEXT,
    activity_type TEXT NOT NULL,  -- issue, pr, commit, branch, workflow
    repository TEXT NOT NULL,
    resource_id TEXT,  -- issue number, PR number, commit SHA
    resource_url TEXT,
    action TEXT NOT NULL,  -- create, update, close, merge, push
    metadata TEXT,  -- JSON with additional data
    created_at TEXT NOT NULL
);

-- Index for vendor-specific queries
CREATE INDEX idx_github_vendor ON github_activities(vendor, created_at);

-- Index for repository queries
CREATE INDEX idx_github_repo ON github_activities(repository, created_at);
```

## Configuration

### User Configuration: `~/.ai-asst-mgr/config.json`

```json
{
  "github": {
    "auth_method": "gh_cli",
    "default_org": "TechR10n",
    "auto_link_issues": true,
    "auto_create_prs": false,
    "default_labels": ["ai-generated"],
    "track_activities": true
  }
}
```

### Vendor-Specific GitHub Config

Each vendor can specify GitHub integration preferences:

```json
{
  "vendors": {
    "claude": {
      "github": {
        "enabled": true,
        "label_prefix": "vendor-claude",
        "commit_signature": "🤖 Generated with [Claude Code](https://claude.com/claude-code)"
      }
    },
    "gemini": {
      "github": {
        "enabled": true,
        "label_prefix": "vendor-gemini",
        "commit_signature": "✨ Generated with Gemini CLI"
      }
    }
  }
}
```

## CLI Commands

New GitHub-specific commands:

```bash
# GitHub authentication status
ai-asst-mgr github status

# List repositories
ai-asst-mgr github repos

# Create issue
ai-asst-mgr github issue create \
  --repo TechR10n/ai-asst-mgr \
  --title "New feature" \
  --vendor claude

# List issues created by specific vendor
ai-asst-mgr github issues --vendor claude

# View GitHub activity for session
ai-asst-mgr github activity --session <session-id>

# View all GitHub activities
ai-asst-mgr github activity --all
```

## Web Dashboard Integration

### GitHub Activity View

Display GitHub activities on the dashboard:

```
┌─────────────────────────────────────────────┐
│          GitHub Activity Summary            │
├─────────────────────────────────────────────┤
│ Issues Created:     23  (Claude: 15, Gemini: 8)
│ PRs Created:        12  (Claude: 10, Codex: 2)
│ Commits Pushed:     156 (All vendors)
│ Workflows Triggered: 8  (CI/CD)
└─────────────────────────────────────────────┘

Recent Activities:
┌─────────┬────────┬────────────┬──────────────────┐
│ Vendor  │ Type   │ Repository │ Action           │
├─────────┼────────┼────────────┼──────────────────┤
│ Claude  │ PR     │ ai-asst-mgr│ Created #42      │
│ Gemini  │ Issue  │ ai-asst-mgr│ Created #41      │
│ Claude  │ Commit │ ai-asst-mgr│ feat: add feature│
│ Codex   │ Branch │ ai-asst-mgr│ feature/new-api  │
└─────────┴────────┴────────────┴──────────────────┘
```

## Implementation Phases

### Phase 1: Foundation (Phase 2 - Vendor Adapters)
- Create `GitHubService` class
- Implement authentication detection
- Add repository operations

### Phase 2: Issue & PR Management (Phase 3 - CLI Commands)
- Implement issue operations
- Implement PR operations
- Add CLI commands for GitHub

### Phase 3: Activity Tracking (Phase 2b - Database)
- Add `github_activities` table
- Track all GitHub operations
- Link to vendor sessions

### Phase 4: Dashboard Integration (Phase 9 - Web Dashboard)
- GitHub activity views
- Vendor-specific GitHub stats
- Repository overview

## Testing Strategy

```python
# tests/services/test_github_service.py

def test_github_authentication():
    """Test GitHub authentication detection."""
    github = GitHubService()
    assert github.is_authenticated()

def test_create_issue():
    """Test issue creation."""
    github = GitHubService()
    issue = github.create_issue(
        repo="test/repo",
        title="Test issue",
        body="Test body",
        labels=["test"]
    )
    assert issue.number > 0

def test_vendor_github_integration():
    """Test vendor using GitHub service."""
    github = GitHubService()
    claude = ClaudeAdapter()

    # Claude should be able to use GitHub service
    issue = github.create_issue(
        repo="test/repo",
        title="Claude test",
        body=f"Session: {claude.current_session}",
        labels=["vendor-claude"]
    )
    assert "vendor-claude" in issue.labels
```

## Benefits

1. **No Code Duplication**: GitHub operations implemented once, used by all vendors
2. **Consistent Behavior**: All vendors interact with GitHub the same way
3. **Centralized Tracking**: All GitHub activities logged in one place
4. **Vendor Attribution**: Know which vendor performed which GitHub action
5. **Enhanced Analytics**: Track GitHub usage across all vendors
6. **Unified Authentication**: Single GitHub auth setup for all vendors

## Security Considerations

- GitHub tokens stored securely in system keychain
- Rate limiting handled gracefully
- Audit log of all GitHub API calls
- Vendor-specific permissions (read-only vs. read-write)

## Future Enhancements

- **GitHub Webhooks**: React to GitHub events in real-time
- **GitHub Apps**: Native app integration instead of CLI
- **Multi-Account Support**: Different GitHub accounts per vendor
- **GitHub Enterprise**: Support for GHE instances
- **GraphQL API**: Use GraphQL for more efficient queries
