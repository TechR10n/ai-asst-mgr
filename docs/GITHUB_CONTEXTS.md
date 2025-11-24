# GitHub Context Separation

## Problem Statement

The ai-asst-mgr project needs to:

1. **Self-Development**: Use GitHub for building and maturing the ai-asst-mgr project itself
   - Our own issues, PRs, commits
   - Project management for ai-asst-mgr
   - CI/CD for our codebase

2. **Vendor Tracking**: Track GitHub operations that AI vendors perform on behalf of users
   - Issues/PRs created by Claude in user repos
   - Commits made by Gemini in user projects
   - GitHub activities across all vendor sessions

These are **different contexts** and need clear separation.

## Solution: Context-Based Architecture

```python
from enum import Enum

class GitHubContext(Enum):
    """GitHub operation context."""
    SELF = "self"        # ai-asst-mgr project operations
    VENDOR = "vendor"    # Vendor operations in user repos
    USER = "user"        # User's own GitHub operations


class GitHubService:
    """GitHub service with context awareness."""

    def __init__(self, context: GitHubContext = GitHubContext.USER):
        self.context = context
        self.config = self._load_config(context)

    def create_issue(self, repo: str, **kwargs):
        """Create issue in the appropriate context."""

        if self.context == GitHubContext.SELF:
            # Operations on ai-asst-mgr itself
            # Add special labeling, tracking, etc.
            return self._create_self_issue(repo, **kwargs)

        elif self.context == GitHubContext.VENDOR:
            # Vendor operations - track attribution
            return self._create_vendor_issue(repo, **kwargs)

        else:  # USER context
            # User's own operations
            return self._create_user_issue(repo, **kwargs)
```

## Context Definitions

### 1. SELF Context (ai-asst-mgr Development)

**Purpose**: Manage the ai-asst-mgr project itself

**Repository**: `TechR10n/ai-asst-mgr`

**Use Cases**:
- Creating issues for ai-asst-mgr development
- Managing PRs for ai-asst-mgr features
- Running CI/CD for ai-asst-mgr
- Project board management
- Release management

**Example**:
```python
# Development script for ai-asst-mgr
from ai_asst_mgr.services.github_service import GitHubService, GitHubContext

# Self context - operating on ai-asst-mgr itself
github = GitHubService(context=GitHubContext.SELF)

# Create issue for ai-asst-mgr development
issue = github.create_issue(
    repo="TechR10n/ai-asst-mgr",
    title="Add new vendor adapter",
    body="We need to add support for new AI vendor",
    labels=["type-feature", "priority-high"]
)
# Automatically tagged as self-development in tracking
```

**Database Tracking**:
```sql
-- Self-development activities
INSERT INTO github_activities (
    activity_id,
    vendor,
    context,
    repository,
    activity_type,
    action
) VALUES (
    'uuid',
    'system',  -- Not a vendor operation
    'self',    -- Self-development context
    'TechR10n/ai-asst-mgr',
    'issue',
    'create'
);
```

### 2. VENDOR Context (AI Vendor Operations)

**Purpose**: Track GitHub operations performed by AI vendors

**Repositories**: Any user repository where vendors operate

**Use Cases**:
- Claude creates an issue in user's project
- Gemini commits code to user's repo
- Codex creates a PR in user's repo
- Track which vendor did what
- Analytics on vendor GitHub usage

**Example**:
```python
# Vendor adapter code
from ai_asst_mgr.services.github_service import GitHubService, GitHubContext
from ai_asst_mgr.vendors.claude import ClaudeAdapter

# Vendor context - Claude operating on user repo
github = GitHubService(context=GitHubContext.VENDOR)
claude = ClaudeAdapter()

# Claude creates issue in user's repo
issue = github.create_issue(
    repo="user/their-project",
    title="Bug fix needed",
    body=f"Created by Claude Code\nSession: {claude.current_session}",
    labels=["vendor-claude", "bug"],
    vendor="claude",  # Attribution
    session_id=claude.current_session
)
```

**Database Tracking**:
```sql
-- Vendor operations
INSERT INTO github_activities (
    activity_id,
    vendor,
    session_id,
    context,
    repository,
    activity_type,
    action,
    metadata
) VALUES (
    'uuid',
    'claude',
    'session-123',
    'vendor',  -- Vendor operation context
    'user/their-project',
    'issue',
    'create',
    '{"issue_number": 42, "labels": ["vendor-claude", "bug"]}'
);
```

### 3. USER Context (User's Own Operations)

**Purpose**: User's own GitHub operations via ai-asst-mgr CLI

**Repositories**: Any repository the user works with

**Use Cases**:
- User runs `ai-asst-mgr github issue create`
- User uses ai-asst-mgr as a GitHub CLI wrapper
- Personal GitHub automation
- Not attributed to any vendor

**Example**:
```bash
# User directly using ai-asst-mgr CLI
ai-asst-mgr github issue create \
  --repo user/their-project \
  --title "Manual issue" \
  --body "Created by me, not a vendor"

# This uses USER context by default
```

```python
# Behind the scenes
github = GitHubService(context=GitHubContext.USER)
issue = github.create_issue(
    repo="user/their-project",
    title="Manual issue",
    body="Created by me, not a vendor",
    # No vendor attribution
)
```

**Database Tracking**:
```sql
-- User operations
INSERT INTO github_activities (
    activity_id,
    vendor,
    context,
    repository,
    activity_type,
    action
) VALUES (
    'uuid',
    NULL,  -- No vendor
    'user',  -- User operation context
    'user/their-project',
    'issue',
    'create'
);
```

## Implementation

### GitHubService with Context

```python
# src/ai_asst_mgr/services/github_service.py

from enum import Enum
from typing import Optional
from dataclasses import dataclass


class GitHubContext(Enum):
    """GitHub operation context."""
    SELF = "self"      # ai-asst-mgr project operations
    VENDOR = "vendor"  # Vendor operations
    USER = "user"      # User's own operations


@dataclass
class GitHubOperation:
    """GitHub operation with context."""
    context: GitHubContext
    action: str
    repository: str
    vendor: Optional[str] = None
    session_id: Optional[str] = None
    metadata: Optional[dict] = None


class GitHubService:
    """Context-aware GitHub service."""

    def __init__(
        self,
        context: GitHubContext = GitHubContext.USER,
        vendor: Optional[str] = None,
        session_id: Optional[str] = None
    ):
        self.context = context
        self.vendor = vendor
        self.session_id = session_id
        self.config = self._load_config()
        self.tracker = GitHubActivityTracker()

    def create_issue(
        self,
        repo: str,
        title: str,
        body: str,
        **kwargs
    ) -> Issue:
        """Create issue with context awareness."""

        # Add context-specific metadata
        if self.context == GitHubContext.SELF:
            # Self-development - add special labels
            labels = kwargs.get('labels', [])
            labels.append('ai-asst-mgr-dev')
            kwargs['labels'] = labels

        elif self.context == GitHubContext.VENDOR:
            # Vendor operation - add vendor label and attribution
            labels = kwargs.get('labels', [])
            if self.vendor:
                labels.append(f'vendor-{self.vendor}')
            kwargs['labels'] = labels

            # Add vendor signature to body
            body += f"\n\n---\n*Created by {self.vendor}*"
            if self.session_id:
                body += f" (Session: {self.session_id})"

        # Create the issue
        issue = self._gh_create_issue(repo, title, body, **kwargs)

        # Track the operation
        self.tracker.log_operation(
            GitHubOperation(
                context=self.context,
                action="create_issue",
                repository=repo,
                vendor=self.vendor,
                session_id=self.session_id,
                metadata={
                    "issue_number": issue.number,
                    "title": title
                }
            )
        )

        return issue

    def _load_config(self):
        """Load context-specific configuration."""
        if self.context == GitHubContext.SELF:
            return {
                "default_repo": "TechR10n/ai-asst-mgr",
                "default_labels": ["ai-asst-mgr-dev"],
                "project_board": "https://github.com/users/TechR10n/projects/5"
            }
        elif self.context == GitHubContext.VENDOR:
            return {
                "track_operations": True,
                "add_vendor_labels": True,
                "add_attribution": True
            }
        else:  # USER
            return {
                "track_operations": False
            }
```

### Vendor Adapters Using Context

```python
# src/ai_asst_mgr/vendors/claude.py

from ai_asst_mgr.services.github_service import GitHubService, GitHubContext


class ClaudeAdapter(VendorAdapter):
    """Claude Code adapter with GitHub integration."""

    def __init__(self):
        super().__init__()

        # Create vendor-context GitHub service
        self.github = GitHubService(
            context=GitHubContext.VENDOR,
            vendor="claude",
            session_id=self.current_session_id
        )

    def create_issue_for_user(self, repo: str, title: str, body: str):
        """Claude creates issue in user's repo."""
        return self.github.create_issue(
            repo=repo,
            title=title,
            body=body
            # Automatically tracked as vendor operation
        )
```

### Self-Development Scripts

```python
# scripts/create_issues.py (for ai-asst-mgr development)

from ai_asst_mgr.services.github_service import GitHubService, GitHubContext


def create_project_issues():
    """Create development issues for ai-asst-mgr."""

    # Self context for ai-asst-mgr development
    github = GitHubService(context=GitHubContext.SELF)

    for issue_data in parse_github_issues():
        issue = github.create_issue(
            repo="TechR10n/ai-asst-mgr",
            title=issue_data['title'],
            body=issue_data['body'],
            labels=issue_data['labels']
            # Automatically tagged as self-development
        )
```

## Database Schema

```sql
CREATE TABLE github_activities (
    activity_id TEXT PRIMARY KEY,
    context TEXT NOT NULL,  -- 'self', 'vendor', 'user'
    vendor TEXT,  -- NULL for self/user, vendor name for vendor
    session_id TEXT,  -- Vendor session if applicable
    repository TEXT NOT NULL,
    activity_type TEXT NOT NULL,
    action TEXT NOT NULL,
    resource_id TEXT,
    resource_url TEXT,
    metadata TEXT,
    created_at TEXT NOT NULL
);

-- Index for self-development queries
CREATE INDEX idx_github_self ON github_activities(context, repository)
WHERE context = 'self';

-- Index for vendor operations
CREATE INDEX idx_github_vendor ON github_activities(vendor, session_id)
WHERE context = 'vendor';

-- Index for user operations
CREATE INDEX idx_github_user ON github_activities(created_at)
WHERE context = 'user';
```

## CLI Commands with Context

```bash
# Self-development (ai-asst-mgr project)
ai-asst-mgr github issue create \
  --context self \
  --title "Add new feature" \
  --body "Feature description"
# Defaults to TechR10n/ai-asst-mgr

# Vendor tracking (report on what vendors did)
ai-asst-mgr github activity \
  --context vendor \
  --vendor claude \
  --repo user/their-project

# User operations (personal use)
ai-asst-mgr github issue create \
  --repo user/my-project \
  --title "My issue"
# Defaults to user context
```

## Web Dashboard Views

### Self-Development View

```
┌─────────────────────────────────────────────┐
│    ai-asst-mgr Project Development          │
├─────────────────────────────────────────────┤
│ Repository: TechR10n/ai-asst-mgr            │
│ Open Issues: 23                             │
│ Open PRs: 3                                 │
│ Next Milestone: MVP (v0.1.0) - 12 days left │
└─────────────────────────────────────────────┘
```

### Vendor Activity View

```
┌─────────────────────────────────────────────┐
│    Vendor GitHub Activities                 │
├─────────────────────────────────────────────┤
│ Claude:  15 issues, 10 PRs, 87 commits      │
│ Gemini:  8 issues, 5 PRs, 43 commits        │
│ Codex:   3 issues, 2 PRs, 21 commits        │
└─────────────────────────────────────────────┘
```

### User Activity View

```
┌─────────────────────────────────────────────┐
│    Your GitHub Activities                   │
├─────────────────────────────────────────────┤
│ Direct Issues: 5                            │
│ Via ai-asst-mgr CLI: 12                     │
└─────────────────────────────────────────────┘
```

## Configuration

```json
{
  "github": {
    "contexts": {
      "self": {
        "enabled": true,
        "repository": "TechR10n/ai-asst-mgr",
        "auto_label": true,
        "labels": ["ai-asst-mgr-dev"]
      },
      "vendor": {
        "enabled": true,
        "track_all_operations": true,
        "add_vendor_labels": true,
        "add_attribution": true
      },
      "user": {
        "enabled": true,
        "track_operations": false
      }
    }
  }
}
```

## Benefits of Context Separation

1. **Clear Separation of Concerns**
   - Self-development tracked separately
   - Vendor operations clearly attributed
   - User operations distinct

2. **Better Analytics**
   - Track ai-asst-mgr project health
   - Track vendor GitHub usage patterns
   - Track user's own GitHub activity

3. **Appropriate Tracking**
   - Self: Full tracking for project management
   - Vendor: Full tracking for analytics
   - User: Minimal tracking (privacy)

4. **Context-Specific Behavior**
   - Self: Auto-add project labels
   - Vendor: Auto-add vendor attribution
   - User: Clean, unmodified operations

5. **Dogfooding**
   - Use ai-asst-mgr to build ai-asst-mgr
   - Self-development = using our own tool
   - Proves the tool works

## Testing

```python
def test_self_context():
    """Test self-development context."""
    github = GitHubService(context=GitHubContext.SELF)
    issue = github.create_issue(
        repo="TechR10n/ai-asst-mgr",
        title="Test",
        body="Test"
    )
    # Should have ai-asst-mgr-dev label
    assert "ai-asst-mgr-dev" in issue.labels


def test_vendor_context():
    """Test vendor operation context."""
    github = GitHubService(
        context=GitHubContext.VENDOR,
        vendor="claude",
        session_id="session-123"
    )
    issue = github.create_issue(
        repo="user/project",
        title="Test",
        body="Test"
    )
    # Should have vendor label
    assert "vendor-claude" in issue.labels
    # Should have attribution in body
    assert "Created by claude" in issue.body


def test_user_context():
    """Test user operation context."""
    github = GitHubService(context=GitHubContext.USER)
    issue = github.create_issue(
        repo="user/project",
        title="Test",
        body="Test"
    )
    # Should be clean, no extra labels
    assert "vendor-" not in str(issue.labels)
```

## Summary

**Three Contexts, Three Purposes:**

1. **SELF**: Building and maturing ai-asst-mgr itself
2. **VENDOR**: Tracking what AI vendors do for users
3. **USER**: User's own direct GitHub operations

The same `GitHubService` library handles all three, but with context-aware behavior that's appropriate for each use case.
