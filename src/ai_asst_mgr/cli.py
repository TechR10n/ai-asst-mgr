"""Command-line interface for AI Assistant Manager.

This module provides the main CLI entry point using Typer for command execution.
"""

from __future__ import annotations

import platform
import shutil
import sys
from pathlib import Path
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ai_asst_mgr.vendors import VendorRegistry

app = typer.Typer(
    name="ai-asst-mgr",
    help="Universal AI assistant configuration manager",
    add_completion=False,
)
console = Console()


@app.command()
def status(
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Show status for specific vendor"),
    ] = None,
) -> None:
    """Show status of all AI assistant vendors."""
    if vendor:
        console.print(f"[blue]Status for {vendor}:[/blue] Not implemented yet")
    else:
        console.print("[blue]Vendor Status:[/blue] Not implemented yet")


@app.command()
def init(
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Initialize specific vendor"),
    ] = None,
) -> None:
    """Initialize AI assistant vendor configurations."""
    if vendor:
        console.print(f"[green]Initializing {vendor}...[/green]")
    else:
        console.print("[green]Initializing all vendors...[/green]")


@app.command()
def health(
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Check health for specific vendor"),
    ] = None,
) -> None:
    """Run health checks on vendor configurations."""
    if vendor:
        console.print(f"[yellow]Health check for {vendor}:[/yellow] Not implemented yet")
    else:
        console.print("[yellow]Health check:[/yellow] Not implemented yet")


def _check_python_version(issues: list[dict[str, str]]) -> tuple[int, int]:
    """Check Python version against minimum requirement.

    Args:
        issues: List to append issues to.

    Returns:
        Tuple of (passed_count, failed_count).
    """
    python_version = sys.version_info
    min_version = (3, 14)

    if python_version >= min_version:
        console.print(
            f"  [green]✓[/green] Python "
            f"{python_version.major}.{python_version.minor}"
            f".{python_version.micro}"
        )
        return (1, 0)

    console.print(
        f"  [red]✗[/red] Python "
        f"{python_version.major}.{python_version.minor}"
        f".{python_version.micro} "
        f"(requires {min_version[0]}.{min_version[1]}+)"
    )
    issues.append(
        {
            "category": "Python",
            "issue": (
                f"Python version {python_version.major}"
                f".{python_version.minor} is below minimum requirement"
            ),
            "remediation": f"Install Python {min_version[0]}.{min_version[1]} or higher",
        }
    )
    return (0, 1)


def _check_dependencies(issues: list[dict[str, str]]) -> tuple[int, int]:
    """Check required Python dependencies.

    Args:
        issues: List to append issues to.

    Returns:
        Tuple of (passed_count, failed_count).
    """
    required_packages = ["typer", "rich", "sqlalchemy", "pydantic", "httpx"]
    passed = 0
    failed = 0

    for package in required_packages:
        try:
            __import__(package)
            console.print(f"  [green]✓[/green] {package} installed")
            passed += 1
        except ImportError:
            console.print(f"  [red]✗[/red] {package} not found")
            issues.append(
                {
                    "category": "Dependencies",
                    "issue": f"Required package '{package}' is not installed",
                    "remediation": "Run: uv pip install -e .",
                }
            )
            failed += 1

    return (passed, failed)


def _check_vendors(issues: list[dict[str, str]]) -> tuple[int, int]:
    """Check vendor installations.

    Args:
        issues: List to append issues to.

    Returns:
        Tuple of (passed_count, failed_count).
    """
    registry = VendorRegistry()
    vendors = registry.get_all_vendors()
    passed = 0

    for name, adapter in vendors.items():
        is_installed = adapter.is_installed()
        is_configured = adapter.is_configured()

        if is_installed:
            console.print(f"  [green]✓[/green] {adapter.info.name}: Installed")
            passed += 1

            if is_configured:
                console.print("    [green]✓[/green] Configuration found")
                passed += 1
            else:
                console.print("    [yellow]⚠[/yellow] Not configured")
                issues.append(
                    {
                        "category": "Configuration",
                        "issue": f"{adapter.info.name} is installed but not configured",
                        "remediation": f"Run: ai-asst-mgr init --vendor {name}",
                    }
                )
        else:
            console.print(f"  [dim]○[/dim] {adapter.info.name}: Not installed")

    return (passed, 0)


def _check_config_files() -> int:
    """Check for configuration files.

    Returns:
        Number of config files found.
    """
    config_checks = [
        (Path.home() / ".claude", "Claude configuration directory"),
        (Path.home() / ".config" / "ai-asst-mgr", "AI Assistant Manager config"),
    ]

    passed = 0
    for config_path, description in config_checks:
        if config_path.exists():
            console.print(f"  [green]✓[/green] {description}: {config_path}")
            passed += 1
        else:
            console.print(f"  [dim]○[/dim] {description}: Not found")

    return passed


def _check_permissions(issues: list[dict[str, str]]) -> tuple[int, int]:
    """Check file permissions for config directories.

    Args:
        issues: List to append issues to.

    Returns:
        Tuple of (passed_count, failed_count).
    """
    test_dirs = [
        Path.home() / ".config",
        Path.home(),
    ]

    passed = 0
    failed = 0

    for test_dir in test_dirs:
        if test_dir.exists() and test_dir.is_dir():
            if _check_write_permission(test_dir):
                console.print(f"  [green]✓[/green] Write access to {test_dir}")
                passed += 1
            else:
                console.print(f"  [red]✗[/red] No write access to {test_dir}")
                issues.append(
                    {
                        "category": "Permissions",
                        "issue": f"No write permission for {test_dir}",
                        "remediation": f"Fix permissions: chmod u+w {test_dir}",
                    }
                )
                failed += 1

    return (passed, failed)


def _check_database_health(issues: list[dict[str, str]]) -> tuple[int, int]:
    """Check database health.

    Args:
        issues: List to append issues to.

    Returns:
        Tuple of (passed_count, failed_count).
    """
    db_path = Path.home() / ".config" / "ai-asst-mgr" / "database.db"

    if not db_path.exists():
        console.print("  [dim]○[/dim] Database not yet initialized")
        return (0, 0)

    if not db_path.is_file():
        console.print("  [red]✗[/red] Database path is not a file")
        issues.append(
            {
                "category": "Database",
                "issue": "Database path exists but is not a file",
                "remediation": f"Remove invalid path and reinitialize: rm -rf {db_path}",
            }
        )
        return (0, 1)

    console.print(f"  [green]✓[/green] Database file exists: {db_path}")
    passed = 1

    if _check_read_permission(db_path):
        console.print("  [green]✓[/green] Database is readable")
        return (passed + 1, 0)

    console.print("  [red]✗[/red] Database is not readable")
    issues.append(
        {
            "category": "Database",
            "issue": "Database file exists but is not readable",
            "remediation": f"Fix permissions: chmod u+r {db_path}",
        }
    )
    return (passed, 1)


def _check_system_tools() -> int:
    """Check for system tools.

    Returns:
        Number of tools found.
    """
    system_tools = ["git"]
    passed = 0

    for tool in system_tools:
        if shutil.which(tool):
            console.print(f"  [green]✓[/green] {tool} is available")
            passed += 1
        else:
            console.print(f"  [yellow]⚠[/yellow] {tool} not found (optional)")

    return passed


def _display_summary(
    checks_passed: int,
    checks_failed: int,
    issues: list[dict[str, str]],
    fix: bool,
) -> None:
    """Display diagnostic summary and issue remediation table.

    Args:
        checks_passed: Number of checks that passed.
        checks_failed: Number of checks that failed.
        issues: List of issues found.
        fix: Whether to attempt automatic fixes.
    """
    console.print("\n" + "=" * 60)
    total_checks = checks_passed + checks_failed

    summary = Table.grid(padding=(0, 2))
    summary.add_row(
        Text("Total Checks:", style="bold"),
        Text(str(total_checks)),
    )
    summary.add_row(
        Text("Passed:", style="bold green"),
        Text(str(checks_passed), style="green"),
    )
    summary.add_row(
        Text("Failed:", style="bold red"),
        Text(str(checks_failed), style="red"),
    )

    console.print(Panel(summary, title="[bold]Summary[/bold]", border_style="blue"))

    if not issues:
        return

    console.print("\n[bold red]Issues Found:[/bold red]")

    issue_table = Table(show_header=True, header_style="bold magenta")
    issue_table.add_column("Category", style="cyan")
    issue_table.add_column("Issue", style="yellow")
    issue_table.add_column("Remediation", style="green")

    for issue in issues:
        issue_table.add_row(
            issue["category"],
            issue["issue"],
            issue["remediation"],
        )

    console.print(issue_table)

    if not fix:
        return

    console.print("\n[bold yellow]Attempting automatic fixes...[/bold yellow]")
    fixed_count = _attempt_fixes(issues)
    console.print(f"[green]Fixed {fixed_count}/{len(issues)} issues[/green]")

    if fixed_count < len(issues):
        console.print(
            "\n[yellow]Some issues require manual intervention.[/yellow]",
        )


@app.command()
def doctor(
    fix: Annotated[
        bool,
        typer.Option("--fix", help="Automatically fix common issues"),
    ] = False,
) -> None:
    """Run comprehensive system diagnostics and health checks.

    This command performs a thorough analysis of your AI assistant manager
    installation, checking:
    - Python version and environment
    - Required and optional dependencies
    - Vendor installations and configurations
    - File permissions
    - Database health
    - Configuration validity

    Use --fix to automatically resolve common issues where possible.
    """
    console.print(
        Panel.fit(
            "[bold blue]AI Assistant Manager - System Diagnostics[/bold blue]",
            border_style="blue",
        )
    )

    issues: list[dict[str, str]] = []
    checks_passed = 0
    checks_failed = 0

    # 1. Python Version Check
    console.print("\n[bold cyan]1. Python Environment[/bold cyan]")
    py_passed, py_failed = _check_python_version(issues)
    checks_passed += py_passed
    checks_failed += py_failed

    console.print(f"  [green]✓[/green] Platform: {platform.system()} {platform.release()}")
    console.print(f"  [green]✓[/green] Architecture: {platform.machine()}")
    checks_passed += 2

    # 2. Dependencies Check
    console.print("\n[bold cyan]2. Dependencies[/bold cyan]")
    dep_passed, dep_failed = _check_dependencies(issues)
    checks_passed += dep_passed
    checks_failed += dep_failed

    # 3. Vendor Installations Check
    console.print("\n[bold cyan]3. Vendor Installations[/bold cyan]")
    vendor_passed, vendor_failed = _check_vendors(issues)
    checks_passed += vendor_passed
    checks_failed += vendor_failed

    # 4. Configuration Files Check
    console.print("\n[bold cyan]4. Configuration Files[/bold cyan]")
    checks_passed += _check_config_files()

    # 5. File Permissions Check
    console.print("\n[bold cyan]5. File Permissions[/bold cyan]")
    perm_passed, perm_failed = _check_permissions(issues)
    checks_passed += perm_passed
    checks_failed += perm_failed

    # 6. Database Health Check
    console.print("\n[bold cyan]6. Database Health[/bold cyan]")
    db_passed, db_failed = _check_database_health(issues)
    checks_passed += db_passed
    checks_failed += db_failed

    # 7. System Tools Check
    console.print("\n[bold cyan]7. System Tools[/bold cyan]")
    checks_passed += _check_system_tools()

    # Display summary and handle results
    _display_summary(checks_passed, checks_failed, issues, fix)

    # Exit with appropriate code
    if checks_failed > 0:
        console.print(
            "\n[red]System diagnostics completed with issues.[/red]",
        )
        raise typer.Exit(code=1)

    console.print(
        "\n[green]All system checks passed successfully![/green]",
    )
    raise typer.Exit(code=0)


def _check_write_permission(path: Path) -> bool:
    """Check if a directory has write permission.

    Args:
        path: Directory path to check.

    Returns:
        True if directory is writable, False otherwise.
    """
    return path.exists() and path.is_dir() and _has_write_access(path)


def _check_read_permission(path: Path) -> bool:
    """Check if a file has read permission.

    Args:
        path: File path to check.

    Returns:
        True if file is readable, False otherwise.
    """
    return path.exists() and path.is_file() and _has_read_access(path)


def _has_write_access(path: Path) -> bool:
    """Test if path has write access by attempting to create a temp file.

    Args:
        path: Path to test for write access.

    Returns:
        True if write access is available, False otherwise.
    """
    try:
        test_file = path / ".doctor_test_write"
        test_file.touch()
        test_file.unlink()
    except (OSError, PermissionError):
        return False
    else:
        return True


def _has_read_access(path: Path) -> bool:
    """Test if file has read access.

    Args:
        path: File path to test.

    Returns:
        True if file is readable, False otherwise.
    """
    try:
        path.read_bytes()
    except (OSError, PermissionError):
        return False
    else:
        return True


def _attempt_fixes(issues: list[dict[str, str]]) -> int:
    """Attempt to automatically fix common issues.

    Args:
        issues: List of issue dictionaries to attempt to fix.

    Returns:
        Number of issues successfully fixed.
    """
    fixed = 0

    for issue in issues:
        category = issue["category"]

        # Auto-fix: Create missing configuration directories
        if category == "Configuration" and "not configured" in issue["issue"]:
            # This would require vendor-specific initialization
            # For now, we'll count it as not auto-fixable
            continue

        # Auto-fix: Create missing directories
        if "directory" in issue["issue"].lower() and "not found" in issue["issue"].lower():
            # Extract path from remediation if possible
            # For now, mark as not auto-fixable
            continue

        # Other fixes would be implemented here
        # For safety, we don't auto-fix permission issues

    return fixed


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
