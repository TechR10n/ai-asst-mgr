#!/usr/bin/env python3
"""Complete GitHub setup automation

This master script runs all setup scripts in the correct order:
1. Create labels
2. Create milestones
3. Create issues

Prerequisites:
- GitHub CLI installed: brew install gh
- Authenticated: gh auth login
- Repository: https://github.com/TechR10n/ai-asst-mgr

Usage:
    python scripts/setup_github.py [--dry-run]

    --dry-run: Preview what would be created without making changes
"""

import subprocess
import sys
from pathlib import Path


def run_script(script_name: str, dry_run: bool = False) -> bool:
    """Run a setup script."""
    script_path = Path(__file__).parent / script_name

    cmd = [sys.executable, str(script_path)]
    if dry_run:
        cmd.append("--dry-run")

    print(f"\n{'=' * 70}")
    print(f"Running: {script_name}")
    print(f"{'=' * 70}\n")

    try:
        result = subprocess.run(cmd, check=True)
    except subprocess.CalledProcessError:
        print(f"\n✗ {script_name} failed")
        return False
    else:
        return result.returncode == 0


def main() -> int:
    """Main entry point."""
    # Parse arguments
    dry_run = "--dry-run" in sys.argv

    if dry_run:
        print("\n" + "=" * 70)
        print("DRY RUN MODE - Preview only, no changes will be made")
        print("=" * 70)

    print("\nStarting complete GitHub setup...")
    print("Repository: https://github.com/TechR10n/ai-asst-mgr")

    # Run scripts in order
    scripts = [
        "create_labels.py",
        "create_milestones.py",
        "create_issues.py",
    ]

    for script in scripts:
        if not run_script(script, dry_run=dry_run):
            print(f"\n✗ Setup failed at {script}")
            return 1

    # Success!
    print("\n" + "=" * 70)
    print("✓ GitHub setup complete!")
    print("=" * 70)

    if dry_run:
        print("\nThis was a dry run. To actually create everything, run:")
        print("  python scripts/setup_github.py")
    else:
        print("\nNext steps:")
        print("1. Visit: https://github.com/TechR10n/ai-asst-mgr/issues")
        print("2. Add issues to project board: https://github.com/users/TechR10n/projects/5")
        print("3. Start development with Issue #1")

    return 0


if __name__ == "__main__":
    sys.exit(main())
