#!/usr/bin/env python3
"""Create all GitHub issues from GITHUB_ISSUES.md

This script parses GITHUB_ISSUES.md and creates issues using GitHub CLI (gh).

Prerequisites:
- GitHub CLI installed: brew install gh
- Authenticated: gh auth login
- Repository: https://github.com/TechR10n/ai-asst-mgr

Usage:
    python scripts/create_issues.py [--dry-run]
"""

import re
import subprocess
import sys
from pathlib import Path


class Issue:
    """Represents a GitHub issue to be created."""

    def __init__(self, number: int, title: str, labels: list[str], milestone: str, body: str):
        self.number = number
        self.title = title
        self.labels = labels
        self.milestone = milestone
        self.body = body

    def __repr__(self) -> str:
        return f"Issue(#{self.number}: {self.title})"


def parse_issues_file(file_path: Path) -> list[Issue]:
    """Parse GITHUB_ISSUES.md and extract all issues."""
    content = file_path.read_text()

    # Split into sections by ## Issue #N pattern
    issue_pattern = r"## Issue #(\d+): (.+?)\n"
    issue_sections = re.split(issue_pattern, content)

    # First element is the preamble (labels, milestones), skip it
    # Then we have triplets: [number, title, body, number, title, body, ...]
    issues = []

    for i in range(1, len(issue_sections), 3):
        if i + 2 > len(issue_sections):
            break

        number = int(issue_sections[i])
        title = issue_sections[i + 1].strip()
        body_text = issue_sections[i + 2]

        # Extract labels
        labels_match = re.search(r"\*\*Labels:\*\*\s*`(.+?)`", body_text)
        labels = []
        if labels_match:
            labels = [label.strip() for label in labels_match.group(1).split(",")]

        # Extract milestone
        milestone_match = re.search(r"\*\*Milestone:\*\*\s*(.+?)(?:\n|$)", body_text)
        milestone = milestone_match.group(1).strip() if milestone_match else ""

        # Build issue body (everything from ### Description onwards)
        body_start = body_text.find("### Description")
        if body_start != -1:
            body = body_text[body_start:].strip()
            # Remove trailing separator if present
            body = re.sub(r"\n---\s*$", "", body)
        else:
            body = body_text.strip()

        issues.append(
            Issue(number=number, title=title, labels=labels, milestone=milestone, body=body)
        )

    return issues


def create_github_issue(issue: Issue, dry_run: bool = False) -> bool:
    """Create a GitHub issue using gh CLI."""
    # Build gh command
    cmd = [
        "gh",
        "issue",
        "create",
        "--title",
        issue.title,
        "--body",
        issue.body,
        "--repo",
        "TechR10n/ai-asst-mgr",
    ]

    # Add labels
    if issue.labels:
        for label in issue.labels:
            cmd.extend(["--label", label])

    # Add milestone
    if issue.milestone:
        cmd.extend(["--milestone", issue.milestone])

    if dry_run:
        print(f"\n[DRY RUN] Would create issue #{issue.number}: {issue.title}")
        print(f"  Labels: {', '.join(issue.labels)}")
        print(f"  Milestone: {issue.milestone}")
        print(f"  Command: {' '.join(cmd[:8])}...")
        return True

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=True)
    except subprocess.CalledProcessError as e:
        print(f"✗ Failed to create issue #{issue.number}: {issue.title}")
        print(f"  Error: {e.stderr}")
        return False
    else:
        print(f"✓ Created issue #{issue.number}: {issue.title}")
        # Extract issue URL from output
        issue_url = result.stdout.strip()
        if issue_url:
            print(f"  {issue_url}")
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

    # Find GITHUB_ISSUES.md
    issues_file = Path(__file__).parent.parent / "GITHUB_ISSUES.md"
    if not issues_file.exists():
        print(f"Error: {issues_file} not found")
        return 1

    print(f"Parsing issues from: {issues_file}")
    issues = parse_issues_file(issues_file)
    print(f"Found {len(issues)} issues to create\n")

    if dry_run:
        print("=" * 70)
        print("DRY RUN MODE - No issues will be created")
        print("=" * 70)

    # Create issues
    success_count = 0
    for issue in issues:
        if create_github_issue(issue, dry_run=dry_run):
            success_count += 1

    print(f"\n{'=' * 70}")
    if dry_run:
        print(f"DRY RUN: Would create {success_count}/{len(issues)} issues")
        print("\nTo actually create issues, run without --dry-run:")
        print("  python scripts/create_issues.py")
    else:
        print(f"Created {success_count}/{len(issues)} issues successfully")
        if success_count < len(issues):
            print(f"\n{len(issues) - success_count} issues failed to create")
            return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
