# Parallel Agent Development Infrastructure

This directory contains tools for coordinating parallel development across 3 AI agents using git worktrees.

## Overview

The parallel development system enables **3 AI agents to work simultaneously** on different issues without conflicts. Each agent gets:
- **Dedicated git worktree** (separate working directory)
- **Isolated branch** (`parallel-dev/agent-1`, `agent-2`, `agent-3`)
- **Task assignment tracking** via `orchestrator.py`
- **Conflict detection** before merging
- **Staggered merge strategy** to minimize conflicts

## Time Savings

**Without parallel agents:** 51 MVP issues × ~1.5h each = **76.5 hours**

**With 3 parallel agents:**
- Parallelizable work: ~60% (31 issues) = 46.5h
- Sequential work: ~40% (20 issues) = 30h
- Coordination overhead: 3h
- **Total: ~49 hours (37% time savings)**

## Files

### `setup_worktrees.sh`
Creates 3 git worktrees for parallel development.

**Usage:**
```bash
./scripts/parallel-dev/setup_worktrees.sh
```

**Creates:**
- `../ai-asst-mgr-worktrees/agent-1/` → Branch: `parallel-dev/agent-1`
- `../ai-asst-mgr-worktrees/agent-2/` → Branch: `parallel-dev/agent-2`
- `../ai-asst-mgr-worktrees/agent-3/` → Branch: `parallel-dev/agent-3`

Each worktree is a complete copy of the repository on its own branch.

### `orchestrator.py`
Python script for task assignment, conflict detection, and merge coordination.

**Commands:**

#### Assign Task
```bash
python orchestrator.py assign <agent_id> <issue_number> <title> <hours>

# Example
python orchestrator.py assign 1 16 "Implement status command" 2.0
```

#### Start Task
```bash
python orchestrator.py start <agent_id>

# Example
python orchestrator.py start 1
```

#### Complete Task
```bash
python orchestrator.py complete <agent_id> <file1> <file2> ...

# Example
python orchestrator.py complete 1 src/ai_asst_mgr/cli.py tests/unit/test_cli.py
```

#### Check Status
```bash
python orchestrator.py status
```

Output:
```
PARALLEL AGENT STATUS
========================================

Agent 1:
  Branch: parallel-dev/agent-1
  Total Hours: 2.0
  Current Task: None (available)
  Completed Tasks: 1

Agent 2:
  Branch: parallel-dev/agent-2
  Total Hours: 1.5
  Current Task: #17 - Implement init command
    Status: in_progress
    Estimated: 1.5h
  Completed Tasks: 0

Agent 3:
  Branch: parallel-dev/agent-3
  Total Hours: 0.0
  Current Task: None (available)
  Completed Tasks: 0
```

#### Detect Conflicts
```bash
python orchestrator.py conflicts
```

Output:
```
CONFLICT DETECTION
========================================

Conflict between Agent 1 and Agent 2:
  Overlapping files (2):
    - src/ai_asst_mgr/cli.py
    - tests/unit/test_cli.py
```

#### Get Merge Order
```bash
python orchestrator.py merge-order
```

Output:
```
RECOMMENDED MERGE ORDER
========================================

Merge branches in this order to minimize conflicts:

1. Agent 3 (parallel-dev/agent-3)
   Completed tasks to merge: 2

2. Agent 1 (parallel-dev/agent-1)
   Completed tasks to merge: 1

3. Agent 2 (parallel-dev/agent-2)
   Completed tasks to merge: 1

Note: 1 conflict(s) detected. Manual resolution may be needed.
```

#### Reset State
```bash
python orchestrator.py reset
```

### `agent_tracker.json`
Automatically created JSON file tracking all agent state:
- Current task assignments
- Completed tasks
- Files modified per task
- Time tracking
- Merge history

**Structure:**
```json
{
  "agents": {
    "1": {
      "agent_id": 1,
      "worktree_path": "../ai-asst-mgr-worktrees/agent-1",
      "branch_name": "parallel-dev/agent-1",
      "current_task": {
        "issue_number": 16,
        "title": "Implement status command",
        "estimated_hours": 2.0,
        "status": "in_progress",
        "assigned_at": "2025-11-24T10:30:00Z",
        "started_at": "2025-11-24T10:35:00Z",
        "files_modified": []
      },
      "completed_tasks": [],
      "total_hours": 0.0
    },
    ...
  },
  "last_updated": "2025-11-24T10:35:00Z",
  "merge_order": [3, 1, 2]
}
```

## Workflow

### 1. Initial Setup
```bash
# Run once to create worktrees
./scripts/parallel-dev/setup_worktrees.sh

# Verify worktrees created
git worktree list
```

### 2. Assign Work
```bash
# Assign issues to agents based on parallelizability
python orchestrator.py assign 1 16 "Implement status command" 2.0
python orchestrator.py assign 2 17 "Implement init command" 1.5
python orchestrator.py assign 3 18 "Implement health command" 2.0
```

### 3. Agent Development Cycle
Each agent works in their worktree:

```bash
# Agent 1's workflow
cd ../ai-asst-mgr-worktrees/agent-1

# Start task
python ../../ai-asst-mgr/scripts/parallel-dev/orchestrator.py start 1

# Do the work
# - Write code
# - Write tests
# - Run tests: pytest tests/
# - Ensure 95%+ coverage
# - Commit changes

# Complete task
python ../../ai-asst-mgr/scripts/parallel-dev/orchestrator.py complete 1 \
  src/ai_asst_mgr/cli.py \
  tests/unit/test_cli.py

# Push branch
git push -u origin parallel-dev/agent-1
```

### 4. Check for Conflicts
Before merging, check for conflicts:

```bash
python orchestrator.py conflicts
python orchestrator.py merge-order
```

### 5. Staggered Merge
Merge in the recommended order:

```bash
# Agent 3 merges first (fewest conflicts)
cd ../ai-asst-mgr-worktrees/agent-3
git checkout main
git pull origin main
git merge parallel-dev/agent-3
git push origin main

# Agent 1 rebases and merges
cd ../ai-asst-mgr-worktrees/agent-1
git checkout parallel-dev/agent-1
git rebase main
git checkout main
git merge parallel-dev/agent-1
git push origin main

# Agent 2 rebases and merges
cd ../ai-asst-mgr-worktrees/agent-2
git checkout parallel-dev/agent-2
git rebase main
git checkout main
git merge parallel-dev/agent-2
git push origin main
```

### 6. Cleanup (Optional)
```bash
# Remove worktrees after merging
git worktree remove ../ai-asst-mgr-worktrees/agent-1
git worktree remove ../ai-asst-mgr-worktrees/agent-2
git worktree remove ../ai-asst-mgr-worktrees/agent-3

# Delete remote branches
git push origin --delete parallel-dev/agent-1
git push origin --delete parallel-dev/agent-2
git push origin --delete parallel-dev/agent-3
```

## Parallelizable Issues

From Phase 3 (CLI Commands), these can run in parallel:

**Batch 1 (No Dependencies):**
- Agent 1: Issue #16 - Implement status command (2h)
- Agent 2: Issue #17 - Implement init command (1.5h)
- Agent 3: Issue #18 - Implement health command (2h)

**Batch 2 (After Batch 1):**
- Agent 1: Issue #19 - Implement config command (2h)
- Agent 2: Issue #20 - Implement doctor command (2.5h)
- Agent 3: Issue #58 - Configuration Schema Validation (2h)

**Time Saved:**
- Sequential: 12h
- Parallel (3 agents): 5h (including coordination)
- **Savings: 7h (58%)**

## Best Practices

### 1. Small, Focused Tasks
Assign issues that:
- Can be completed in 1-3 hours
- Have minimal file overlap
- Are independent (no dependencies)

### 2. Avoid File Conflicts
- **Coordinate CLI command implementations** (separate files when possible)
- **Don't modify shared files** (base classes) simultaneously
- **Use orchestrator conflicts** command frequently

### 3. Communication
- Update `agent_tracker.json` via orchestrator
- Comment on GitHub issues when starting/completing
- Tag other agents in PRs if conflicts detected

### 4. Quality Standards
All agents must follow `.claude/DEVELOPMENT_STANDARDS.md`:
- 95%+ test coverage
- mypy --strict compliance
- ruff linting passing
- Comprehensive docstrings

### 5. Merge Discipline
- **Never force push** to main
- **Always rebase** before merging
- **Squash commits** for clean history
- **Conventional commit messages**

## Troubleshooting

### Worktree Creation Failed
```bash
# Check existing worktrees
git worktree list

# Remove stale worktrees
git worktree prune

# Retry setup
./scripts/parallel-dev/setup_worktrees.sh
```

### Orchestrator State Corrupted
```bash
# Reset state
python orchestrator.py reset

# Reassign tasks
python orchestrator.py assign 1 16 "Implement status command" 2.0
```

### Merge Conflicts
```bash
# In agent's worktree
git checkout parallel-dev/agent-1
git fetch origin
git rebase origin/main

# Resolve conflicts manually
git add <resolved-files>
git rebase --continue

# Push with force (rebase changes history)
git push --force-with-lease
```

### Lost Work in Worktree
Worktrees are independent git repositories. If work is committed, it's safe:

```bash
# Check commit history
git log --oneline

# Recover lost commits
git reflog
git checkout <commit-hash>
```

## Cost Estimation

**Agent Costs (Claude Sonnet 4):**
- Input: $3/1M tokens
- Output: $15/1M tokens

**Estimated tokens per issue:**
- Reading code/tests: ~50K input
- Writing code/tests: ~20K output
- Total cost per issue: ~$0.50

**Total parallel dev cost:**
- 30 MVP issues × $0.50 = **$15**
- Plus coordination: ~$5
- **Total: ~$20 for parallel development**

**Savings:**
- Time saved: 29 hours
- Value at $50/hour: **$1,450**
- **ROI: 72x**

## References

- Git Worktrees: https://git-scm.com/docs/git-worktree
- Parallel Development Research: https://about.gitlab.com/blog/2024/07/24/ai-merge-agent/
- `.claude/DEVELOPMENT_STANDARDS.md` - Shared coding standards
- `GITHUB_ISSUES.md` - All issues and task breakdown

## Support

Questions? Check:
1. This README
2. Development Standards: `.claude/DEVELOPMENT_STANDARDS.md`
3. Orchestrator help: `python orchestrator.py` (no args)
4. GitHub Issues for specific tasks
