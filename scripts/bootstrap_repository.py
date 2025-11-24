#!/usr/bin/env python3
"""
Complete repository bootstrap

Runs all setup and configuration scripts in the correct order:
1. Configure repository (visibility, features, security, branch protection)
2. Create labels (29 total)
3. Create milestones (2 total)
4. Create issues (57 total)
5. Verify configuration

Prerequisites:
- GitHub CLI installed and authenticated: gh auth login
- Repository exists: https://github.com/TechR10n/ai-asst-mgr
- You are the repository owner

Usage:
    python scripts/bootstrap_repository.py [--dry-run] [--skip-config] [--skip-issues]

Options:
    --dry-run: Preview all changes without applying them
    --skip-config: Skip repository configuration (only create labels/milestones/issues)
    --skip-issues: Skip issue creation (only configure repository and create labels/milestones)
    --verify-only: Only verify current configuration, don't make changes
"""

import subprocess
import sys
from pathlib import Path


class RepositoryBootstrap:
    """Bootstrap GitHub repository with complete setup."""

    def __init__(
        self,
        dry_run: bool = False,
        skip_config: bool = False,
        skip_issues: bool = False,
        verify_only: bool = False
    ):
        self.dry_run = dry_run
        self.skip_config = skip_config
        self.skip_issues = skip_issues
        self.verify_only = verify_only
        self.scripts_dir = Path(__file__).parent

    def run(self) -> bool:
        """Run complete bootstrap process."""
        print("=" * 70)
        print("AI ASSISTANT MANAGER - REPOSITORY BOOTSTRAP")
        print("=" * 70)
        print()

        if self.dry_run:
            print("⚠️  DRY RUN MODE - No changes will be made")
            print()

        if self.verify_only:
            print("🔍 VERIFICATION MODE - Checking current configuration")
            print()
            return self.verify_configuration()

        steps = []

        # Add configuration step
        if not self.skip_config:
            steps.append(("Repository Configuration", self.configure_repository))

        # Add setup steps
        steps.extend([
            ("Create Labels", self.create_labels),
            ("Create Milestones", self.create_milestones),
        ])

        # Add issue creation step
        if not self.skip_issues:
            steps.append(("Create Issues", self.create_issues))

        # Add verification step
        steps.append(("Verify Configuration", self.verify_configuration))

        # Run all steps
        results = []
        for name, func in steps:
            print(f"\n{'=' * 70}")
            print(f"Step: {name}")
            print(f"{'=' * 70}\n")

            try:
                success = func()
                results.append((name, success))

                status = "✓" if success else "✗"
                print(f"\n{status} {name}: {'Success' if success else 'Failed'}")
            except Exception as e:
                print(f"\n✗ {name}: Error - {e}")
                results.append((name, False))

            # Stop on failure for critical steps
            if not success and name in ["Repository Configuration", "Create Labels"]:
                print(f"\n⚠️  Critical step failed: {name}")
                print("Fix the error and run again.")
                break

        # Final summary
        self.print_summary(results)

        success_count = sum(1 for _, success in results if success)
        total_count = len(results)

        return success_count == total_count

    def configure_repository(self) -> bool:
        """Configure repository settings."""
        script = self.scripts_dir / "configure_repository.py"

        cmd = [sys.executable, str(script)]
        if self.dry_run:
            cmd.append("--dry-run")

        result = subprocess.run(cmd)
        return result.returncode == 0

    def create_labels(self) -> bool:
        """Create GitHub labels."""
        script = self.scripts_dir / "create_labels.py"

        cmd = [sys.executable, str(script)]
        if self.dry_run:
            cmd.append("--dry-run")

        result = subprocess.run(cmd)
        return result.returncode == 0

    def create_milestones(self) -> bool:
        """Create GitHub milestones."""
        script = self.scripts_dir / "create_milestones.py"

        cmd = [sys.executable, str(script)]
        if self.dry_run:
            cmd.append("--dry-run")

        result = subprocess.run(cmd)
        return result.returncode == 0

    def create_issues(self) -> bool:
        """Create GitHub issues."""
        script = self.scripts_dir / "create_issues.py"

        cmd = [sys.executable, str(script)]
        if self.dry_run:
            cmd.append("--dry-run")

        result = subprocess.run(cmd)
        return result.returncode == 0

    def verify_configuration(self) -> bool:
        """Verify repository configuration."""
        script = self.scripts_dir / "configure_repository.py"

        cmd = [sys.executable, str(script), "--verify-only"]

        result = subprocess.run(cmd)
        return result.returncode == 0

    def print_summary(self, results: list[tuple[str, bool]]) -> None:
        """Print final summary."""
        print(f"\n{'=' * 70}")
        print("BOOTSTRAP SUMMARY")
        print(f"{'=' * 70}\n")

        for name, success in results:
            status = "✓" if success else "✗"
            print(f"{status} {name}")

        success_count = sum(1 for _, success in results if success)
        total_count = len(results)

        print(f"\n{success_count}/{total_count} steps completed successfully")

        if self.dry_run:
            print("\n" + "=" * 70)
            print("This was a DRY RUN - no changes were made")
            print("=" * 70)
            print("\nTo apply these changes, run:")
            print("  python scripts/bootstrap_repository.py")
        elif success_count == total_count:
            print("\n" + "=" * 70)
            print("✓ BOOTSTRAP COMPLETE!")
            print("=" * 70)
            print("\nYour repository is now fully configured:")
            print("  ✓ Public and findable")
            print("  ✓ Single-maintainer control")
            print("  ✓ Labels, milestones, and issues created")
            print("  ✓ Branch protection enabled")
            print("  ✓ Security features enabled")
            print("\nNext steps:")
            print("  1. Visit: https://github.com/TechR10n/ai-asst-mgr")
            print("  2. Add issues to project board")
            print("  3. Start development!")
        else:
            print("\n" + "=" * 70)
            print("⚠️  BOOTSTRAP INCOMPLETE")
            print("=" * 70)
            print(f"\n{total_count - success_count} steps failed")
            print("Review the errors above and run again.")


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Bootstrap GitHub repository with complete setup"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview all changes without applying them"
    )
    parser.add_argument(
        "--skip-config",
        action="store_true",
        help="Skip repository configuration (only create labels/milestones/issues)"
    )
    parser.add_argument(
        "--skip-issues",
        action="store_true",
        help="Skip issue creation (only configure repository and create labels/milestones)"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify current configuration, don't make changes"
    )

    args = parser.parse_args()

    bootstrap = RepositoryBootstrap(
        dry_run=args.dry_run,
        skip_config=args.skip_config,
        skip_issues=args.skip_issues,
        verify_only=args.verify_only
    )

    success = bootstrap.run()
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
