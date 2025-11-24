#!/usr/bin/env bash
# Setup git worktrees for parallel agent development
# This script creates 3 separate worktrees for 3 AI agents to work in parallel

set -euo pipefail

# Colors for output
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

# Configuration
REPO_ROOT="$(git rev-parse --show-toplevel)"
WORKTREE_DIR="${REPO_ROOT}/../ai-asst-mgr-worktrees"
MAIN_BRANCH="main"

echo "🚀 Setting up parallel development worktrees..."
echo ""

# Check if we're in a git repository
if ! git rev-parse --git-dir > /dev/null 2>&1; then
    echo -e "${RED}Error: Not in a git repository${NC}"
    exit 1
fi

# Check if on main branch
CURRENT_BRANCH=$(git branch --show-current)
if [ "$CURRENT_BRANCH" != "$MAIN_BRANCH" ]; then
    echo -e "${YELLOW}Warning: Currently on branch '$CURRENT_BRANCH', not '$MAIN_BRANCH'${NC}"
    echo "Continuing anyway..."
fi

# Create worktree parent directory
if [ ! -d "$WORKTREE_DIR" ]; then
    mkdir -p "$WORKTREE_DIR"
    echo -e "${GREEN}✓${NC} Created worktree directory: $WORKTREE_DIR"
else
    echo -e "${YELLOW}⚠${NC}  Worktree directory already exists: $WORKTREE_DIR"
fi

# Function to create a worktree
create_worktree() {
    local agent_id=$1
    local worktree_path="${WORKTREE_DIR}/agent-${agent_id}"
    local branch_name="parallel-dev/agent-${agent_id}"

    echo ""
    echo "Setting up agent-${agent_id}..."

    # Check if worktree already exists
    if [ -d "$worktree_path" ]; then
        echo -e "${YELLOW}⚠${NC}  Worktree already exists: $worktree_path"
        echo "   Skipping creation..."
        return 0
    fi

    # Check if branch exists
    if git show-ref --verify --quiet "refs/heads/$branch_name"; then
        echo -e "${YELLOW}⚠${NC}  Branch '$branch_name' already exists"
        echo "   Using existing branch..."
        git worktree add "$worktree_path" "$branch_name"
    else
        # Create new branch and worktree
        git worktree add -b "$branch_name" "$worktree_path" "$MAIN_BRANCH"
    fi

    if [ -d "$worktree_path" ]; then
        echo -e "${GREEN}✓${NC} Created worktree: $worktree_path"
        echo -e "${GREEN}✓${NC} Branch: $branch_name"

        # Create agent-specific marker file
        echo "Agent ${agent_id} workspace - $(date)" > "${worktree_path}/.agent-${agent_id}"

        # Copy development standards to each worktree
        if [ -f "${REPO_ROOT}/.claude/DEVELOPMENT_STANDARDS.md" ]; then
            cp "${REPO_ROOT}/.claude/DEVELOPMENT_STANDARDS.md" "${worktree_path}/.claude/"
            echo -e "${GREEN}✓${NC} Copied development standards"
        fi
    else
        echo -e "${RED}✗${NC} Failed to create worktree for agent-${agent_id}"
        return 1
    fi
}

# Create worktrees for 3 agents
echo "Creating 3 agent worktrees..."
echo ""

create_worktree 1
create_worktree 2
create_worktree 3

echo ""
echo "========================================="
echo "✅ Parallel development setup complete!"
echo "========================================="
echo ""
echo "Worktree locations:"
echo "  Agent 1: ${WORKTREE_DIR}/agent-1"
echo "  Agent 2: ${WORKTREE_DIR}/agent-2"
echo "  Agent 3: ${WORKTREE_DIR}/agent-3"
echo ""
echo "Each agent should:"
echo "  1. cd into their worktree directory"
echo "  2. Verify they're on their branch: git branch"
echo "  3. Start working on assigned issues"
echo "  4. Commit and push to their branch"
echo ""
echo "Orchestrator will manage task assignments and merge order."
echo ""

# List all worktrees
echo "Current worktrees:"
git worktree list
