#!/usr/bin/env python3
"""Parallel Agent Orchestrator for ai-asst-mgr development.

This script coordinates work between 3 parallel AI agents, manages task
assignments, detects conflicts, and orchestrates staggered merges.

Usage:
    python orchestrator.py assign <agent_id> <issue_number>
    python orchestrator.py status
    python orchestrator.py conflicts
    python orchestrator.py merge-order
    python orchestrator.py validate <agent_id> [--dry-run]
    python orchestrator.py health-check <agent_id>
    python orchestrator.py reset
"""

from __future__ import annotations

import json
import subprocess  # nosec - safe subprocess usage for git commands
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict, cast

# Constants for CLI argument validation
MIN_ARGS_BASE = 2
MIN_ARGS_ASSIGN = 6
MIN_ARGS_START = 3
MIN_ARGS_COMPLETE = 4


class TaskAssignment(TypedDict):
    """Task assignment for an agent."""

    issue_number: int
    title: str
    estimated_hours: float
    status: str  # 'assigned', 'in_progress', 'completed', 'merged'
    assigned_at: str
    started_at: str | None
    completed_at: str | None
    merged_at: str | None
    files_modified: list[str]


class AgentState(TypedDict):
    """State for a single agent."""

    agent_id: int
    worktree_path: str
    branch_name: str
    current_task: TaskAssignment | None
    completed_tasks: list[TaskAssignment]
    total_hours: float


class OrchestratorState(TypedDict):
    """Overall orchestrator state."""

    agents: dict[str, AgentState]
    last_updated: str
    merge_order: list[int]


class Orchestrator:
    """Manages parallel agent development workflow."""

    def __init__(self, state_file: Path | None = None) -> None:
        """Initialize orchestrator.

        Args:
            state_file: Path to agent_tracker.json.
                Defaults to scripts/parallel-dev/agent_tracker.json
        """
        if state_file is None:
            repo_root = self._get_repo_root()
            state_file = repo_root / "scripts" / "parallel-dev" / "agent_tracker.json"

        self.state_file = state_file
        self.state = self._load_state()

    def _get_repo_root(self) -> Path:
        """Get repository root directory."""
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )  # nosec - safe git command with no user input
        return Path(result.stdout.strip())

    def _load_state(self) -> OrchestratorState:
        """Load orchestrator state from JSON file."""
        if not self.state_file.exists():
            # Initialize with default state
            return self._create_default_state()

        with self.state_file.open() as f:
            return cast("OrchestratorState", json.load(f))

    def _create_default_state(self) -> OrchestratorState:
        """Create default orchestrator state."""
        repo_root = self._get_repo_root()
        worktree_dir = repo_root.parent / "ai-asst-mgr-worktrees"

        return {
            "agents": {
                "1": {
                    "agent_id": 1,
                    "worktree_path": str(worktree_dir / "agent-1"),
                    "branch_name": "parallel-dev/agent-1",
                    "current_task": None,
                    "completed_tasks": [],
                    "total_hours": 0.0,
                },
                "2": {
                    "agent_id": 2,
                    "worktree_path": str(worktree_dir / "agent-2"),
                    "branch_name": "parallel-dev/agent-2",
                    "current_task": None,
                    "completed_tasks": [],
                    "total_hours": 0.0,
                },
                "3": {
                    "agent_id": 3,
                    "worktree_path": str(worktree_dir / "agent-3"),
                    "branch_name": "parallel-dev/agent-3",
                    "current_task": None,
                    "completed_tasks": [],
                    "total_hours": 0.0,
                },
            },
            "last_updated": datetime.now(UTC).isoformat(),
            "merge_order": [],
        }

    def _save_state(self) -> None:
        """Save orchestrator state to JSON file."""
        self.state["last_updated"] = datetime.now(UTC).isoformat()

        # Ensure directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

        with self.state_file.open("w") as f:
            json.dump(self.state, f, indent=2)

    def assign_task(
        self, agent_id: int, issue_number: int, title: str, estimated_hours: float
    ) -> None:
        """Assign a task to an agent.

        Args:
            agent_id: Agent ID (1, 2, or 3).
            issue_number: GitHub issue number.
            title: Issue title.
            estimated_hours: Estimated hours to complete.
        """
        agent_key = str(agent_id)
        if agent_key not in self.state["agents"]:
            print(f"❌ Invalid agent ID: {agent_id}")
            sys.exit(1)

        agent = self.state["agents"][agent_key]

        # Check if agent already has a task
        if agent["current_task"] is not None:
            print(f"⚠️  Agent {agent_id} already has task: #{agent['current_task']['issue_number']}")
            print("   Complete or reassign current task first.")
            sys.exit(1)

        # Create task assignment
        task: TaskAssignment = {
            "issue_number": issue_number,
            "title": title,
            "estimated_hours": estimated_hours,
            "status": "assigned",
            "assigned_at": datetime.now(UTC).isoformat(),
            "started_at": None,
            "completed_at": None,
            "merged_at": None,
            "files_modified": [],
        }

        agent["current_task"] = task
        self._save_state()

        print(f"✅ Assigned Issue #{issue_number} to Agent {agent_id}")
        print(f"   Title: {title}")
        print(f"   Estimated: {estimated_hours}h")
        print(f"   Branch: {agent['branch_name']}")

    def start_task(self, agent_id: int) -> None:
        """Mark agent's current task as in progress."""
        agent_key = str(agent_id)
        agent = self.state["agents"][agent_key]

        if agent["current_task"] is None:
            print(f"❌ Agent {agent_id} has no assigned task")
            sys.exit(1)

        agent["current_task"]["status"] = "in_progress"
        agent["current_task"]["started_at"] = datetime.now(UTC).isoformat()
        self._save_state()

        print(f"✅ Agent {agent_id} started Issue #{agent['current_task']['issue_number']}")

    def complete_task(self, agent_id: int, files_modified: list[str]) -> None:
        """Mark agent's current task as completed.

        Args:
            agent_id: Agent ID.
            files_modified: List of modified file paths.
        """
        agent_key = str(agent_id)
        agent = self.state["agents"][agent_key]

        if agent["current_task"] is None:
            print(f"❌ Agent {agent_id} has no current task")
            sys.exit(1)

        task = agent["current_task"]
        task["status"] = "completed"
        task["completed_at"] = datetime.now(UTC).isoformat()
        task["files_modified"] = files_modified

        # Move to completed tasks
        agent["completed_tasks"].append(task)
        agent["total_hours"] += task["estimated_hours"]
        agent["current_task"] = None

        self._save_state()

        print(f"✅ Agent {agent_id} completed Issue #{task['issue_number']}")
        print(f"   Files modified: {len(files_modified)}")
        print(f"   Total hours: {agent['total_hours']}")

    def show_status(self) -> None:
        """Display current status of all agents."""
        print("\n" + "=" * 60)
        print("PARALLEL AGENT STATUS")
        print("=" * 60 + "\n")

        for agent_id in ["1", "2", "3"]:
            agent = self.state["agents"][agent_id]
            print(f"Agent {agent_id}:")
            print(f"  Branch: {agent['branch_name']}")
            print(f"  Total Hours: {agent['total_hours']}")

            if agent["current_task"]:
                task = agent["current_task"]
                print(f"  Current Task: #{task['issue_number']} - {task['title']}")
                print(f"    Status: {task['status']}")
                print(f"    Estimated: {task['estimated_hours']}h")
            else:
                print("  Current Task: None (available)")

            print(f"  Completed Tasks: {len(agent['completed_tasks'])}")
            print()

        print(f"Last Updated: {self.state['last_updated']}")
        print()

    def detect_conflicts(self) -> list[tuple[int, int, list[str]]]:
        """Detect file conflicts between agents.

        Returns:
            List of (agent1_id, agent2_id, conflicting_files).
        """
        conflicts: list[tuple[int, int, list[str]]] = []

        # Get files modified by each agent
        agent_files: dict[int, set[str]] = {}
        for agent_id in ["1", "2", "3"]:
            agent = self.state["agents"][agent_id]
            files: set[str] = set()

            if agent["current_task"] and agent["current_task"]["files_modified"]:
                files.update(agent["current_task"]["files_modified"])

            for task in agent["completed_tasks"]:
                if not task.get("merged_at"):  # Only consider unmerged tasks
                    files.update(task.get("files_modified", []))

            agent_files[int(agent_id)] = files

        # Compare each pair of agents
        for i in range(1, 4):
            for j in range(i + 1, 4):
                common_files = agent_files[i] & agent_files[j]
                if common_files:
                    conflicts.append((i, j, sorted(common_files)))

        return conflicts

    def show_conflicts(self) -> None:
        """Display detected conflicts between agents."""
        conflicts = self.detect_conflicts()

        print("\n" + "=" * 60)
        print("CONFLICT DETECTION")
        print("=" * 60 + "\n")

        if not conflicts:
            print("✅ No conflicts detected between agents")
            print()
            return

        print(f"⚠️  Found {len(conflicts)} conflict(s):\n")

        for agent1, agent2, files in conflicts:
            print(f"Conflict between Agent {agent1} and Agent {agent2}:")
            print(f"  Overlapping files ({len(files)}):")
            for file in files:
                print(f"    - {file}")
            print()

    def calculate_merge_order(self) -> list[int]:
        """Calculate optimal merge order based on conflicts.

        Returns:
            List of agent IDs in merge order.
        """
        # Detect conflicts
        conflicts = self.detect_conflicts()

        # Count conflicts per agent
        conflict_count: dict[int, int] = {1: 0, 2: 0, 3: 0}
        for agent1, agent2, files in conflicts:
            conflict_count[agent1] += len(files)
            conflict_count[agent2] += len(files)

        # Sort by conflict count (ascending) and agent ID
        merge_order = sorted(conflict_count.keys(), key=lambda x: (conflict_count[x], x))

        self.state["merge_order"] = merge_order
        self._save_state()

        return merge_order

    def show_merge_order(self) -> None:
        """Display recommended merge order."""
        merge_order = self.calculate_merge_order()
        conflicts = self.detect_conflicts()

        print("\n" + "=" * 60)
        print("RECOMMENDED MERGE ORDER")
        print("=" * 60 + "\n")

        print("Merge branches in this order to minimize conflicts:\n")

        for idx, agent_id in enumerate(merge_order, 1):
            agent = self.state["agents"][str(agent_id)]
            completed = len([t for t in agent["completed_tasks"] if not t.get("merged_at")])

            print(f"{idx}. Agent {agent_id} ({agent['branch_name']})")
            print(f"   Completed tasks to merge: {completed}")
            print()

        if conflicts:
            print(f"Note: {len(conflicts)} conflict(s) detected. Manual resolution may be needed.")
        else:
            print("No conflicts detected! Merges should be clean.")

        print()

    def reset(self) -> None:
        """Reset orchestrator state."""
        self.state = self._create_default_state()
        self._save_state()
        print("✅ Orchestrator state reset")

    def health_check(  # noqa: PLR0912, PLR0915
        self, agent_id: int
    ) -> dict[str, bool | str | list[str]]:
        """Perform health check on agent's worktree and branch.

        Args:
            agent_id: Agent ID to check.

        Returns:
            Health check report with status and issues.
        """
        agent_key = str(agent_id)
        if agent_key not in self.state["agents"]:
            print(f"❌ Invalid agent ID: {agent_id}")
            sys.exit(1)

        agent = self.state["agents"][agent_key]
        worktree_path = Path(agent["worktree_path"])
        branch_name = agent["branch_name"]

        issues: list[str] = []
        warnings: list[str] = []

        # Check 1: Worktree exists
        if not worktree_path.exists():
            issues.append(f"Worktree does not exist: {worktree_path}")
        # Check 2: Worktree is a git directory
        elif not (worktree_path / ".git").exists():
            issues.append("Worktree is not a git repository")

        # Check 3: Branch exists and is checked out
        try:
            result = subprocess.run(
                ["git", "-C", str(worktree_path), "rev-parse", "--abbrev-ref", "HEAD"],
                capture_output=True,
                text=True,
                check=True,
            )  # nosec - safe git command
            current_branch = result.stdout.strip()
            if current_branch != branch_name:
                warnings.append(
                    f"Expected branch {branch_name}, but {current_branch} is checked out"
                )
        except subprocess.CalledProcessError:
            issues.append("Could not determine current branch")

        # Check 4: Working directory is clean
        try:
            result = subprocess.run(
                ["git", "-C", str(worktree_path), "status", "--porcelain"],
                capture_output=True,
                text=True,
                check=True,
            )  # nosec - safe git command
            if result.stdout.strip():
                uncommitted_files = result.stdout.strip().split("\n")
                warnings.append(
                    f"Working directory has {len(uncommitted_files)} uncommitted changes"
                )
        except subprocess.CalledProcessError:
            issues.append("Could not check working directory status")

        # Check 5: Branch is up to date with remote (if it exists)
        try:
            # Check if branch has remote tracking
            subprocess.run(
                ["git", "-C", str(worktree_path), "rev-parse", "--abbrev-ref", "@{upstream}"],
                capture_output=True,
                text=True,
                check=True,
            )  # nosec - safe git command

            # Fetch latest
            subprocess.run(
                ["git", "-C", str(worktree_path), "fetch"],
                capture_output=True,
                text=True,
                check=False,
            )  # nosec - safe git command

            # Check if behind remote
            result = subprocess.run(
                ["git", "-C", str(worktree_path), "rev-list", "HEAD..@{upstream}", "--count"],
                capture_output=True,
                text=True,
                check=True,
            )  # nosec - safe git command
            behind_count = int(result.stdout.strip())
            if behind_count > 0:
                warnings.append(f"Branch is {behind_count} commit(s) behind remote")
        except subprocess.CalledProcessError:
            # No remote tracking branch - this is OK
            pass

        # Generate report
        healthy = len(issues) == 0
        status = "healthy" if healthy else "unhealthy"

        print(f"\n{'=' * 60}")
        print(f"HEALTH CHECK - Agent {agent_id}")
        print(f"{'=' * 60}\n")
        print(f"Status: {'✅ Healthy' if healthy else '❌ Unhealthy'}")
        print(f"Worktree: {worktree_path}")
        print(f"Branch: {branch_name}\n")

        if issues:
            print(f"❌ Issues ({len(issues)}):")
            for issue in issues:
                print(f"  - {issue}")
            print()

        if warnings:
            print(f"⚠️  Warnings ({len(warnings)}):")
            for warning in warnings:
                print(f"  - {warning}")
            print()

        if not issues and not warnings:
            print("✅ No issues detected\n")

        return {
            "healthy": healthy,
            "status": status,
            "issues": issues,
            "warnings": warnings,
        }

    def validate_merge(  # noqa: PLR0912, PLR0915
        self, agent_id: int, dry_run: bool = False
    ) -> dict[str, bool | int | list[str]]:
        """Validate agent's branch is ready to merge.

        Performs comprehensive pre-merge checks including:
        - Branch health
        - Test suite passing
        - Coverage >= 95%
        - Quality gates (mypy, ruff, bandit)
        - Conflict prediction

        Args:
            agent_id: Agent ID to validate.
            dry_run: If True, only report what would happen (no actual merge).

        Returns:
            Validation report with merge readiness status.
        """
        agent_key = str(agent_id)
        if agent_key not in self.state["agents"]:
            print(f"❌ Invalid agent ID: {agent_id}")
            sys.exit(1)

        agent = self.state["agents"][agent_key]
        worktree_path = Path(agent["worktree_path"])
        branch_name = agent["branch_name"]

        print(f"\n{'=' * 60}")
        print(f"MERGE VALIDATION - Agent {agent_id}")
        if dry_run:
            print("(DRY-RUN MODE)")
        print(f"{'=' * 60}\n")
        print(f"Worktree: {worktree_path}")
        print(f"Branch: {branch_name}\n")

        issues: list[str] = []
        warnings: list[str] = []
        checks_passed = 0
        checks_total = 0

        # Check 1: Health check
        print("1. Running health check...")
        health = self.health_check(agent_id)
        checks_total += 1
        if health["healthy"]:
            print("   ✅ Health check passed\n")
            checks_passed += 1
        else:
            print("   ❌ Health check failed\n")
            issues.extend(health["issues"])  # type: ignore
            warnings.extend(health["warnings"])  # type: ignore

        # Check 2: Tests passing
        print("2. Running test suite...")
        checks_total += 1
        try:
            result = subprocess.run(
                ["uv", "run", "pytest", "-xvs"],
                check=False,
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=300,
            )  # nosec - safe pytest command
            if result.returncode == 0:
                print("   ✅ All tests passing\n")
                checks_passed += 1
            else:
                print("   ❌ Tests failing\n")
                issues.append("Test suite has failures")
                # Show last 10 lines of output
                lines = result.stdout.split("\n")[-10:]
                print("   Last 10 lines of output:")
                for line in lines:
                    print(f"     {line}")
                print()
        except subprocess.TimeoutExpired:
            print("   ❌ Tests timed out\n")
            issues.append("Test suite timed out after 300s")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error running tests: {e}\n")
            issues.append(f"Error running tests: {e}")

        # Check 3: Coverage >= 95%
        print("3. Checking test coverage...")
        checks_total += 1
        try:
            result = subprocess.run(
                ["uv", "run", "pytest", "--cov", "--cov-report=term", "--cov-fail-under=95"],
                check=False,
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=300,
            )  # nosec - safe pytest command
            if result.returncode == 0:
                print("   ✅ Coverage >= 95%\n")
                checks_passed += 1
            else:
                print("   ❌ Coverage below 95%\n")
                issues.append("Test coverage below 95% threshold")
                # Extract coverage percentage from output
                for line in result.stdout.split("\n"):
                    if "TOTAL" in line:
                        print(f"     {line}")
                print()
        except subprocess.TimeoutExpired:
            print("   ❌ Coverage check timed out\n")
            issues.append("Coverage check timed out after 300s")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error checking coverage: {e}\n")
            issues.append(f"Error checking coverage: {e}")

        # Check 4: mypy --strict
        print("4. Running mypy --strict...")
        checks_total += 1
        try:
            result = subprocess.run(
                ["uv", "run", "mypy", "--strict", "src", "tests"],
                check=False,
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=120,
            )  # nosec - safe mypy command
            if result.returncode == 0:
                print("   ✅ mypy --strict passed\n")
                checks_passed += 1
            else:
                print("   ❌ mypy --strict failed\n")
                issues.append("Type checking failed (mypy --strict)")
                # Show first 10 errors
                lines = result.stdout.split("\n")[:10]
                print("   First 10 errors:")
                for line in lines:
                    if line.strip():
                        print(f"     {line}")
                print()
        except subprocess.TimeoutExpired:
            print("   ❌ mypy timed out\n")
            issues.append("Type checking timed out after 120s")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error running mypy: {e}\n")
            issues.append(f"Error running mypy: {e}")

        # Check 5: ruff check
        print("5. Running ruff check...")
        checks_total += 1
        try:
            result = subprocess.run(
                ["uv", "run", "ruff", "check", "src", "tests"],
                check=False,
                cwd=worktree_path,
                capture_output=True,
                text=True,
                timeout=60,
            )  # nosec - safe ruff command
            if result.returncode == 0:
                print("   ✅ ruff check passed\n")
                checks_passed += 1
            else:
                print("   ❌ ruff check failed\n")
                warnings.append("Linting issues found (ruff check)")
                print(f"   Output:\n{result.stdout}\n")
        except subprocess.TimeoutExpired:
            print("   ❌ ruff timed out\n")
            warnings.append("Linting check timed out after 60s")
        except subprocess.CalledProcessError as e:
            print(f"   ❌ Error running ruff: {e}\n")
            warnings.append(f"Error running ruff: {e}")

        # Check 6: Conflict detection
        print("6. Checking for merge conflicts...")
        checks_total += 1
        conflicts = self.detect_conflicts()
        agent_conflicts = [c for c in conflicts if agent_id in (c[0], c[1])]
        if not agent_conflicts:
            print("   ✅ No file conflicts detected\n")
            checks_passed += 1
        else:
            print(f"   ⚠️  {len(agent_conflicts)} conflict(s) detected\n")
            warnings.append(f"{len(agent_conflicts)} file conflict(s) with other agents")
            for agent1, agent2, files in agent_conflicts:
                other_agent = agent2 if agent1 == agent_id else agent1
                print(f"   Conflict with Agent {other_agent}:")
                for file in files:
                    print(f"     - {file}")
            print()

        # Summary
        print(f"{'=' * 60}")
        print("VALIDATION SUMMARY")
        print(f"{'=' * 60}\n")
        print(f"Checks passed: {checks_passed}/{checks_total}")
        print(f"Issues: {len(issues)}")
        print(f"Warnings: {len(warnings)}\n")

        ready_to_merge = len(issues) == 0
        if ready_to_merge:
            print("✅ READY TO MERGE")
            if warnings:
                print(f"   ({len(warnings)} warning(s) - review recommended)")
        else:
            print("❌ NOT READY TO MERGE")
            print("\nBlocking issues:")
            for issue in issues:
                print(f"  - {issue}")

        if dry_run:
            print("\n(This was a dry-run - no merge performed)")

        print()

        return {
            "ready": ready_to_merge,
            "checks_passed": checks_passed,
            "checks_total": checks_total,
            "issues": issues,
            "warnings": warnings,
        }


def main() -> None:  # noqa: PLR0912, PLR0915
    """Main CLI entry point."""
    if len(sys.argv) < MIN_ARGS_BASE:
        print("Usage:")
        print("  orchestrator.py assign <agent_id> <issue_number> <title> <hours>")
        print("  orchestrator.py start <agent_id>")
        print("  orchestrator.py complete <agent_id> <file1> <file2> ...")
        print("  orchestrator.py status")
        print("  orchestrator.py conflicts")
        print("  orchestrator.py merge-order")
        print("  orchestrator.py health-check <agent_id>")
        print("  orchestrator.py validate <agent_id> [--dry-run]")
        print("  orchestrator.py reset")
        sys.exit(1)

    orchestrator = Orchestrator()
    command = sys.argv[1]

    if command == "assign":
        if len(sys.argv) < MIN_ARGS_ASSIGN:
            print("Usage: orchestrator.py assign <agent_id> <issue_number> <title> <hours>")
            sys.exit(1)
        agent_id = int(sys.argv[2])
        issue_number = int(sys.argv[3])
        title = sys.argv[4]
        hours = float(sys.argv[5])
        orchestrator.assign_task(agent_id, issue_number, title, hours)

    elif command == "start":
        if len(sys.argv) < MIN_ARGS_START:
            print("Usage: orchestrator.py start <agent_id>")
            sys.exit(1)
        agent_id = int(sys.argv[2])
        orchestrator.start_task(agent_id)

    elif command == "complete":
        if len(sys.argv) < MIN_ARGS_COMPLETE:
            print("Usage: orchestrator.py complete <agent_id> <file1> <file2> ...")
            sys.exit(1)
        agent_id = int(sys.argv[2])
        files_modified = sys.argv[3:]
        orchestrator.complete_task(agent_id, files_modified)

    elif command == "status":
        orchestrator.show_status()

    elif command == "conflicts":
        orchestrator.show_conflicts()

    elif command == "merge-order":
        orchestrator.show_merge_order()

    elif command == "health-check":
        if len(sys.argv) < MIN_ARGS_START:
            print("Usage: orchestrator.py health-check <agent_id>")
            sys.exit(1)
        agent_id = int(sys.argv[2])
        orchestrator.health_check(agent_id)

    elif command == "validate":
        if len(sys.argv) < MIN_ARGS_START:
            print("Usage: orchestrator.py validate <agent_id> [--dry-run]")
            sys.exit(1)
        agent_id = int(sys.argv[2])
        dry_run = "--dry-run" in sys.argv
        result = orchestrator.validate_merge(agent_id, dry_run=dry_run)
        # Exit with non-zero if not ready to merge
        sys.exit(0 if result["ready"] else 1)

    elif command == "reset":
        orchestrator.reset()

    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
