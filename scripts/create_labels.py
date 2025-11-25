#!/usr/bin/env python3
"""Create all GitHub labels from PROJECT_SETUP.md

This script creates all necessary labels using GitHub CLI (gh).

Prerequisites:
- GitHub CLI installed: brew install gh
- Authenticated: gh auth login
- Repository: https://github.com/TechR10n/ai-asst-mgr

Usage:
    python scripts/create_labels.py [--dry-run]
"""

import subprocess
import sys


class Label:
    """Represents a GitHub label."""

    def __init__(self, name: str, color: str, description: str = ""):
        self.name = name
        self.color = color.lstrip("#")  # Remove # if present
        self.description = description

    def __repr__(self) -> str:
        return f"Label({self.name}, #{self.color})"


def get_all_labels() -> list[Label]:
    """Return all labels to be created."""
    labels = []

    # Phase Labels
    labels.extend(
        [
            Label("phase-1-foundation", "0052CC", "Phase 1: Project foundation"),
            Label("phase-2-vendors", "1D76DB", "Phase 2: Vendor adapters"),
            Label("phase-2b-database", "5319E7", "Phase 2b: Database migration"),
            Label("phase-3-cli", "0E8A16", "Phase 3: CLI commands"),
            Label("phase-4-audit", "B60205", "Phase 4: Audit system"),
            Label("phase-5-coaching", "FBCA04", "Phase 5: Coaching system"),
            Label("phase-6-backup", "D93F0B", "Phase 6: Backup operations"),
            Label("phase-7-scheduling", "006B75", "Phase 7: Cross-platform scheduling"),
            Label("phase-8-capabilities", "C5DEF5", "Phase 8: Capability abstraction"),
            Label("phase-9-web-dashboard", "FEF2C0", "Phase 9: Web dashboard"),
            Label("phase-10-testing", "BFD4F2", "Phase 10: Testing & documentation"),
        ]
    )

    # Priority Labels
    labels.extend(
        [
            Label("priority-high", "D73A4A", "High priority"),
            Label("priority-medium", "FBCA04", "Medium priority"),
            Label("priority-low", "0E8A16", "Low priority"),
        ]
    )

    # Type Labels
    labels.extend(
        [
            Label("type-feature", "A2EEEF", "New feature"),
            Label("type-bug", "D73A4A", "Bug fix"),
            Label("type-docs", "0075CA", "Documentation"),
            Label("type-refactor", "C5DEF5", "Refactoring"),
        ]
    )

    # Special Labels
    labels.extend(
        [
            Label("good-first-issue", "7057FF", "Good for newcomers"),
            Label("help-wanted", "008672", "Extra attention needed"),
            Label("blocked", "D93F0B", "Blocked by another issue"),
        ]
    )

    # Vendor Labels
    labels.extend(
        [
            Label("vendor-claude", "5319E7", "Claude Code specific"),
            Label("vendor-gemini", "FBCA04", "Gemini CLI specific"),
            Label("vendor-openai", "0E8A16", "OpenAI Codex specific"),
        ]
    )

    return labels


def create_github_label(label: Label, dry_run: bool = False) -> bool:
    """Create a GitHub label using gh CLI."""
    cmd = [
        "gh",
        "label",
        "create",
        label.name,
        "--color",
        label.color,
        "--repo",
        "TechR10n/ai-asst-mgr",
    ]

    if label.description:
        cmd.extend(["--description", label.description])

    if dry_run:
        print(f"[DRY RUN] Would create: {label.name} (#{label.color})")
        return True

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        # Label might already exist
        if "already exists" in e.stderr.lower():
            print(f"⊙ Label already exists: {label.name}")
            return True
        print(f"✗ Failed to create label: {label.name}")
        print(f"  Error: {e.stderr}")
        return False
    else:
        print(f"✓ Created label: {label.name} (#{label.color})")
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

    labels = get_all_labels()
    print(f"Creating {len(labels)} labels...\n")

    if dry_run:
        print("=" * 70)
        print("DRY RUN MODE - No labels will be created")
        print("=" * 70)
        print()

    # Create labels
    success_count = 0
    for label in labels:
        if create_github_label(label, dry_run=dry_run):
            success_count += 1

    print(f"\n{'=' * 70}")
    if dry_run:
        print(f"DRY RUN: Would create {success_count}/{len(labels)} labels")
        print("\nTo actually create labels, run without --dry-run:")
        print("  python scripts/create_labels.py")
    else:
        print(f"Successfully processed {success_count}/{len(labels)} labels")

    return 0


if __name__ == "__main__":
    sys.exit(main())
