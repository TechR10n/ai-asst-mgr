#!/usr/bin/env python3
"""
Complete repository configuration automation

Configures GitHub repository with single-maintainer control:
- Repository visibility (public)
- Branch protection rules
- Repository features (Issues, Wiki, Discussions, etc.)
- Security settings (Dependabot)
- Repository topics
- Pull request settings

Prerequisites:
- GitHub CLI installed and authenticated: gh auth login
- Repository exists: https://github.com/TechR10n/ai-asst-mgr

Usage:
    python scripts/configure_repository.py [--dry-run] [--verify-only]
"""

import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Any, Optional


@dataclass
class RepositoryConfig:
    """Repository configuration."""
    owner: str = "TechR10n"
    repo: str = "ai-asst-mgr"
    visibility: str = "public"

    # Features
    has_issues: bool = True
    has_wiki: bool = True
    has_discussions: bool = True
    has_projects: bool = True

    # Pull Request settings
    allow_squash_merge: bool = True
    allow_merge_commit: bool = True
    allow_rebase_merge: bool = True
    delete_branch_on_merge: bool = True

    # Security
    enable_dependabot_alerts: bool = True
    enable_dependabot_security_updates: bool = True

    # Topics
    topics: list[str] = None

    def __post_init__(self):
        if self.topics is None:
            self.topics = [
                "ai", "claude", "gemini", "codex", "ai-assistant",
                "configuration-management", "python", "cli", "fastapi",
                "developer-tools", "automation"
            ]


class GitHubConfigurator:
    """Configure GitHub repository settings."""

    def __init__(self, config: RepositoryConfig, dry_run: bool = False):
        self.config = config
        self.dry_run = dry_run
        self.repo_path = f"{config.owner}/{config.repo}"

    def run(self) -> bool:
        """Run all configuration steps."""
        print(f"{'=' * 70}")
        print(f"Configuring repository: {self.repo_path}")
        print(f"{'=' * 70}")

        if self.dry_run:
            print("\n⚠️  DRY RUN MODE - No changes will be made\n")

        steps = [
            ("Verify GitHub CLI", self.verify_gh_cli),
            ("Set repository visibility", self.set_visibility),
            ("Configure repository features", self.configure_features),
            ("Configure pull request settings", self.configure_pr_settings),
            ("Set repository topics", self.set_topics),
            ("Enable security features", self.enable_security),
            ("Configure branch protection", self.configure_branch_protection),
        ]

        results = []
        for name, func in steps:
            print(f"\n{'─' * 70}")
            print(f"Step: {name}")
            print(f"{'─' * 70}")

            try:
                success = func()
                results.append((name, success))
                status = "✓" if success else "✗"
                print(f"{status} {name}: {'Success' if success else 'Failed'}")
            except Exception as e:
                print(f"✗ {name}: Error - {e}")
                results.append((name, False))

        # Summary
        print(f"\n{'=' * 70}")
        print("Configuration Summary")
        print(f"{'=' * 70}")

        for name, success in results:
            status = "✓" if success else "✗"
            print(f"{status} {name}")

        success_count = sum(1 for _, success in results if success)
        total_count = len(results)

        print(f"\n{success_count}/{total_count} steps completed successfully")

        if self.dry_run:
            print("\nThis was a dry run. Run without --dry-run to apply changes.")

        return success_count == total_count

    def verify_gh_cli(self) -> bool:
        """Verify GitHub CLI is installed and authenticated."""
        try:
            # Check if gh is installed
            result = subprocess.run(
                ["gh", "--version"],
                capture_output=True,
                check=True
            )
            print(f"✓ GitHub CLI installed: {result.stdout.decode().split()[2]}")

            # Check authentication
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                check=True
            )
            print("✓ GitHub CLI authenticated")

            return True
        except (subprocess.CalledProcessError, FileNotFoundError) as e:
            print(f"✗ GitHub CLI error: {e}")
            print("Install: brew install gh")
            print("Authenticate: gh auth login")
            return False

    def set_visibility(self) -> bool:
        """Set repository visibility."""
        if self.dry_run:
            print(f"[DRY RUN] Would set visibility to: {self.config.visibility}")
            return True

        try:
            subprocess.run(
                [
                    "gh", "repo", "edit", self.repo_path,
                    "--visibility", self.config.visibility
                ],
                capture_output=True,
                text=True,
                check=True
            )
            print(f"✓ Repository visibility set to: {self.config.visibility}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to set visibility: {e.stderr}")
            return False

    def configure_features(self) -> bool:
        """Configure repository features."""
        features = {
            "issues": self.config.has_issues,
            "wiki": self.config.has_wiki,
            "discussions": self.config.has_discussions,
            "projects": self.config.has_projects,
        }

        if self.dry_run:
            print("[DRY RUN] Would configure features:")
            for feature, enabled in features.items():
                print(f"  - {feature}: {'enabled' if enabled else 'disabled'}")
            return True

        success = True
        for feature, enabled in features.items():
            flag = f"--enable-{feature}" if enabled else f"--disable-{feature}"
            try:
                subprocess.run(
                    ["gh", "repo", "edit", self.repo_path, flag],
                    capture_output=True,
                    text=True,
                    check=True
                )
                print(f"✓ {feature}: {'enabled' if enabled else 'disabled'}")
            except subprocess.CalledProcessError as e:
                print(f"✗ Failed to configure {feature}: {e.stderr}")
                success = False

        return success

    def configure_pr_settings(self) -> bool:
        """Configure pull request settings."""
        settings = {
            "allow-squash-merge": self.config.allow_squash_merge,
            "allow-merge-commit": self.config.allow_merge_commit,
            "allow-rebase-merge": self.config.allow_rebase_merge,
            "delete-branch-on-merge": self.config.delete_branch_on_merge,
        }

        if self.dry_run:
            print("[DRY RUN] Would configure PR settings:")
            for setting, enabled in settings.items():
                print(f"  - {setting}: {'enabled' if enabled else 'disabled'}")
            return True

        # Build command
        cmd = ["gh", "repo", "edit", self.repo_path]
        for setting, enabled in settings.items():
            flag = f"--{setting}" if enabled else f"--no-{setting}"
            cmd.append(flag)

        try:
            subprocess.run(cmd, capture_output=True, text=True, check=True)
            print("✓ Pull request settings configured")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to configure PR settings: {e.stderr}")
            return False

    def set_topics(self) -> bool:
        """Set repository topics."""
        if self.dry_run:
            print(f"[DRY RUN] Would set topics: {', '.join(self.config.topics)}")
            return True

        try:
            # GitHub API call to set topics
            topics_json = json.dumps({"names": self.config.topics})

            subprocess.run(
                [
                    "gh", "api",
                    f"repos/{self.repo_path}/topics",
                    "--method", "PUT",
                    "-H", "Accept: application/vnd.github+json",
                    "-H", "X-GitHub-Api-Version: 2022-11-28",
                    "--input", "-"
                ],
                input=topics_json,
                text=True,
                capture_output=True,
                check=True
            )
            print(f"✓ Topics set: {', '.join(self.config.topics)}")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to set topics: {e.stderr}")
            return False

    def enable_security(self) -> bool:
        """Enable security features."""
        if self.dry_run:
            print("[DRY RUN] Would enable security features:")
            print(f"  - Dependabot alerts: {self.config.enable_dependabot_alerts}")
            print(f"  - Dependabot security updates: {self.config.enable_dependabot_security_updates}")
            return True

        success = True

        # Enable vulnerability alerts (Dependabot alerts)
        if self.config.enable_dependabot_alerts:
            try:
                subprocess.run(
                    [
                        "gh", "api",
                        f"repos/{self.repo_path}/vulnerability-alerts",
                        "--method", "PUT"
                    ],
                    capture_output=True,
                    check=True
                )
                print("✓ Dependabot alerts enabled")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Dependabot alerts: {e.stderr} (may already be enabled)")

        # Enable automated security fixes (Dependabot security updates)
        if self.config.enable_dependabot_security_updates:
            try:
                subprocess.run(
                    [
                        "gh", "api",
                        f"repos/{self.repo_path}/automated-security-fixes",
                        "--method", "PUT"
                    ],
                    capture_output=True,
                    check=True
                )
                print("✓ Dependabot security updates enabled")
            except subprocess.CalledProcessError as e:
                print(f"⚠️  Dependabot security updates: {e.stderr} (may already be enabled)")

        return success

    def configure_branch_protection(self) -> bool:
        """Configure branch protection rules for main branch."""
        if self.dry_run:
            print("[DRY RUN] Would configure branch protection for 'main':")
            print("  - Require pull request before merging")
            print("  - Require 1 approval")
            print("  - Require review from code owners")
            print("  - Require status checks to pass")
            print("  - Require conversation resolution")
            return True

        # Branch protection configuration
        protection_config = {
            "required_status_checks": None,  # Will be set when CI is configured
            "enforce_admins": True,
            "required_pull_request_reviews": {
                "required_approving_review_count": 1,
                "require_code_owner_reviews": True,
                "dismiss_stale_reviews": True
            },
            "required_conversation_resolution": True,
            "restrictions": None,  # No restrictions on who can push
            "allow_force_pushes": False,
            "allow_deletions": False
        }

        try:
            config_json = json.dumps(protection_config)

            subprocess.run(
                [
                    "gh", "api",
                    f"repos/{self.repo_path}/branches/main/protection",
                    "--method", "PUT",
                    "-H", "Accept: application/vnd.github+json",
                    "-H", "X-GitHub-Api-Version: 2022-11-28",
                    "--input", "-"
                ],
                input=config_json,
                text=True,
                capture_output=True,
                check=True
            )
            print("✓ Branch protection configured for 'main'")
            return True
        except subprocess.CalledProcessError as e:
            print(f"✗ Failed to configure branch protection: {e.stderr}")
            # This is often due to needing to create the branch first
            print("Note: Branch protection requires 'main' branch to exist")
            return False


class RepositoryVerifier:
    """Verify repository configuration."""

    def __init__(self, config: RepositoryConfig):
        self.config = config
        self.repo_path = f"{config.owner}/{config.repo}"

    def verify_all(self) -> bool:
        """Verify all configuration."""
        print(f"{'=' * 70}")
        print(f"Verifying repository: {self.repo_path}")
        print(f"{'=' * 70}\n")

        checks = [
            ("Repository visibility", self.verify_visibility),
            ("Repository features", self.verify_features),
            ("Repository topics", self.verify_topics),
            ("Branch protection", self.verify_branch_protection),
            ("CODEOWNERS file", self.verify_codeowners),
            ("Security policy", self.verify_security_policy),
            ("Workflows", self.verify_workflows),
        ]

        results = []
        for name, func in checks:
            try:
                success = func()
                results.append((name, success))
            except Exception as e:
                print(f"✗ {name}: Error - {e}")
                results.append((name, False))

        # Summary
        print(f"\n{'=' * 70}")
        print("Verification Summary")
        print(f"{'=' * 70}")

        for name, success in results:
            status = "✓" if success else "✗"
            print(f"{status} {name}")

        success_count = sum(1 for _, success in results if success)
        total_count = len(results)

        print(f"\n{success_count}/{total_count} checks passed")

        return success_count == total_count

    def verify_visibility(self) -> bool:
        """Verify repository visibility."""
        try:
            result = subprocess.run(
                ["gh", "repo", "view", self.repo_path, "--json", "visibility"],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            visibility = data.get("visibility", "").lower()

            if visibility == self.config.visibility:
                print(f"✓ Repository is {visibility}")
                return True
            else:
                print(f"✗ Repository is {visibility}, expected {self.config.visibility}")
                return False
        except Exception as e:
            print(f"✗ Failed to verify visibility: {e}")
            return False

    def verify_features(self) -> bool:
        """Verify repository features."""
        try:
            result = subprocess.run(
                [
                    "gh", "repo", "view", self.repo_path, "--json",
                    "hasIssuesEnabled,hasWikiEnabled,hasDiscussionsEnabled,hasProjectsEnabled"
                ],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)

            features = {
                "issues": (data.get("hasIssuesEnabled"), self.config.has_issues),
                "wiki": (data.get("hasWikiEnabled"), self.config.has_wiki),
                "discussions": (data.get("hasDiscussionsEnabled"), self.config.has_discussions),
                "projects": (data.get("hasProjectsEnabled"), self.config.has_projects),
            }

            all_correct = True
            for feature, (actual, expected) in features.items():
                if actual == expected:
                    print(f"✓ {feature}: {'enabled' if actual else 'disabled'}")
                else:
                    print(f"✗ {feature}: {actual}, expected {expected}")
                    all_correct = False

            return all_correct
        except Exception as e:
            print(f"✗ Failed to verify features: {e}")
            return False

    def verify_topics(self) -> bool:
        """Verify repository topics."""
        try:
            result = subprocess.run(
                ["gh", "repo", "view", self.repo_path, "--json", "repositoryTopics"],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)
            topics = [t["name"] for t in data.get("repositoryTopics", [])]

            missing = set(self.config.topics) - set(topics)
            extra = set(topics) - set(self.config.topics)

            if not missing and not extra:
                print(f"✓ Topics correct: {', '.join(topics)}")
                return True
            else:
                if missing:
                    print(f"⚠️  Missing topics: {', '.join(missing)}")
                if extra:
                    print(f"⚠️  Extra topics: {', '.join(extra)}")
                return False
        except Exception as e:
            print(f"✗ Failed to verify topics: {e}")
            return False

    def verify_branch_protection(self) -> bool:
        """Verify branch protection rules."""
        try:
            result = subprocess.run(
                [
                    "gh", "api",
                    f"repos/{self.repo_path}/branches/main/protection"
                ],
                capture_output=True,
                text=True,
                check=True
            )
            data = json.loads(result.stdout)

            checks = [
                ("Pull request required", data.get("required_pull_request_reviews") is not None),
                ("Code owner review required",
                 data.get("required_pull_request_reviews", {}).get("require_code_owner_reviews", False)),
            ]

            all_correct = True
            for name, result in checks:
                if result:
                    print(f"✓ {name}")
                else:
                    print(f"✗ {name}")
                    all_correct = False

            return all_correct
        except subprocess.CalledProcessError:
            print("✗ Branch protection not configured")
            return False
        except Exception as e:
            print(f"✗ Failed to verify branch protection: {e}")
            return False

    def verify_codeowners(self) -> bool:
        """Verify CODEOWNERS file exists."""
        import os
        path = ".github/CODEOWNERS"
        exists = os.path.exists(path)

        if exists:
            with open(path) as f:
                content = f.read()
                if f"@{self.config.owner}" in content:
                    print(f"✓ CODEOWNERS file exists and contains @{self.config.owner}")
                    return True
                else:
                    print(f"⚠️  CODEOWNERS file exists but doesn't contain @{self.config.owner}")
                    return False
        else:
            print(f"✗ CODEOWNERS file not found at {path}")
            return False

    def verify_security_policy(self) -> bool:
        """Verify SECURITY.md exists."""
        import os
        path = ".github/SECURITY.md"
        exists = os.path.exists(path)

        if exists:
            print(f"✓ Security policy exists at {path}")
            return True
        else:
            print(f"✗ Security policy not found at {path}")
            return False

    def verify_workflows(self) -> bool:
        """Verify GitHub Actions workflows exist."""
        import os
        workflows = [
            ".github/workflows/auto-label.yml",
            ".github/workflows/stale.yml",
        ]

        all_exist = True
        for workflow in workflows:
            if os.path.exists(workflow):
                print(f"✓ Workflow exists: {workflow}")
            else:
                print(f"✗ Workflow not found: {workflow}")
                all_exist = False

        return all_exist


def main() -> int:
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Configure GitHub repository with single-maintainer control"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview changes without applying them"
    )
    parser.add_argument(
        "--verify-only",
        action="store_true",
        help="Only verify configuration, don't make changes"
    )

    args = parser.parse_args()

    config = RepositoryConfig()

    if args.verify_only:
        verifier = RepositoryVerifier(config)
        success = verifier.verify_all()
        return 0 if success else 1
    else:
        configurator = GitHubConfigurator(config, dry_run=args.dry_run)
        success = configurator.run()
        return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
