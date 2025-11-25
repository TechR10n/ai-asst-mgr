#!/usr/bin/env python3
"""Create GitHub milestones

This script creates the two project milestones using GitHub CLI (gh).

Prerequisites:
- GitHub CLI installed: brew install gh
- Authenticated: gh auth login
- Repository: https://github.com/TechR10n/ai-asst-mgr

Usage:
    python scripts/create_milestones.py [--dry-run]
"""

import subprocess
import sys
from datetime import UTC, datetime, timedelta


class Milestone:
    """Represents a GitHub milestone."""

    def __init__(self, title: str, due_date: str, description: str):
        self.title = title
        self.due_date = due_date
        self.description = description

    def __repr__(self) -> str:
        return f"Milestone({self.title}, due: {self.due_date})"


def get_due_date(weeks_from_now: int) -> str:
    """Calculate due date N weeks from now in ISO format."""
    due = datetime.now(tz=UTC) + timedelta(weeks=weeks_from_now)
    return due.strftime("%Y-%m-%d")


def get_all_milestones() -> list[Milestone]:
    """Return all milestones to be created."""
    mvp_description = (
        "Core functionality with vendor management, CLI commands, and backup operations.\n"
        "\n"
        "Includes:\n"
        "- Phase 1: Project foundation\n"
        "- Phase 2: Vendor adapters\n"
        "- Phase 2b: Database migration\n"
        "- Phase 3: Core CLI commands\n"
        "- Phase 6: Backup operations\n"
        "\n"
        "This milestone delivers a working CLI tool that can manage configurations "
        "across Claude Code, Gemini CLI, and OpenAI Codex."
    )

    full_description = (
        "Complete feature set with audit, coaching, capabilities, and web dashboard.\n"
        "\n"
        "Includes:\n"
        "- Phase 4: Audit system\n"
        "- Phase 5: Coaching system\n"
        "- Phase 7: Cross-platform scheduling\n"
        "- Phase 8: Capability abstraction\n"
        "- Phase 9: Web dashboard\n"
        "- Phase 10: Testing & documentation\n"
        "\n"
        "This milestone delivers the full ai-asst-mgr experience with web UI, "
        "analytics, and advanced capabilities."
    )

    return [
        Milestone(title="MVP (v0.1.0)", due_date=get_due_date(2), description=mvp_description),
        Milestone(
            title="Full Release (v1.0.0)", due_date=get_due_date(5), description=full_description
        ),
    ]


def create_github_milestone(milestone: Milestone, dry_run: bool = False) -> bool:
    """Create a GitHub milestone using gh CLI."""
    cmd = [
        "gh",
        "api",
        "--method",
        "POST",
        "-H",
        "Accept: application/vnd.github+json",
        "-H",
        "X-GitHub-Api-Version: 2022-11-28",
        "/repos/TechR10n/ai-asst-mgr/milestones",
        "-f",
        f"title={milestone.title}",
        "-f",
        f"description={milestone.description}",
        "-f",
        f"due_on={milestone.due_date}T23:59:59Z",
    ]

    if dry_run:
        print(f"[DRY RUN] Would create: {milestone.title}")
        print(f"  Due: {milestone.due_date}")
        print(f"  Description: {milestone.description[:60]}...")
        return True

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        # Check if milestone already exists
        if "already_exists" in e.stderr.lower() or "Validation Failed" in e.stderr:
            print(f"⊙ Milestone already exists: {milestone.title}")
            return True
        print(f"✗ Failed to create milestone: {milestone.title}")
        print(f"  Error: {e.stderr}")
        return False
    else:
        print(f"✓ Created milestone: {milestone.title}")
        print(f"  Due: {milestone.due_date}")
        return True


def check_gh_cli() -> bool:
    """Check if GitHub CLI is installed and authenticated."""
    # Check if gh is installed
    try:
        subprocess.run(["gh", "--version"], capture_output=True, check=True)
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("Error: GitHub CLI (gh) is not installed.")
        print("Install with: brew install gh")
        return False

    # Check if authenticated
    try:
        subprocess.run(["gh", "auth", "status"], capture_output=True, check=True)
    except subprocess.CalledProcessError:
        print("Error: GitHub CLI is not authenticated.")
        print("Run: gh auth login")
        return False

    return True


def main() -> int:
    """Main entry point."""
    # Parse arguments
    dry_run = "--dry-run" in sys.argv

    # Check prerequisites
    if not check_gh_cli():
        return 1

    milestones = get_all_milestones()
    print(f"Creating {len(milestones)} milestones...\n")

    if dry_run:
        print("=" * 70)
        print("DRY RUN MODE - No milestones will be created")
        print("=" * 70)
        print()

    # Create milestones
    success_count = 0
    for milestone in milestones:
        if create_github_milestone(milestone, dry_run=dry_run):
            success_count += 1

    print(f"\n{'=' * 70}")
    if dry_run:
        print(f"DRY RUN: Would create {success_count}/{len(milestones)} milestones")
        print("\nTo actually create milestones, run without --dry-run:")
        print("  python scripts/create_milestones.py")
    else:
        print(f"Successfully processed {success_count}/{len(milestones)} milestones")

    return 0


if __name__ == "__main__":
    sys.exit(main())
