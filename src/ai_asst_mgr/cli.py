"""Command-line interface for AI Assistant Manager.

This module provides the main CLI entry point using Typer for command execution.
"""

from __future__ import annotations

import json
import platform
import shutil
import sys
from pathlib import Path
from typing import TYPE_CHECKING, Annotated, Any

import typer
import uvicorn
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ai_asst_mgr.adapters.base import VendorStatus
from ai_asst_mgr.audit import ClaudeAuditor, CodexAuditor, GeminiAuditor
from ai_asst_mgr.capabilities import AgentType, UniversalAgentManager
from ai_asst_mgr.coaches import ClaudeCoach, CodexCoach, GeminiCoach, Priority
from ai_asst_mgr.database import DatabaseManager
from ai_asst_mgr.database.sync import get_sync_status, sync_history_to_db
from ai_asst_mgr.operations import (
    BackupManager,
    MergeStrategy,
    RestoreManager,
    SyncManager,
)
from ai_asst_mgr.operations.github_parser import (
    GitLogParser,
    find_git_repos,
)
from ai_asst_mgr.platform import (
    IntervalType,
    ScheduleInfo,
    UnsupportedPlatformError,
    get_platform_info,
    get_scheduler,
)
from ai_asst_mgr.vendors import VendorRegistry

if TYPE_CHECKING:
    from collections.abc import Callable

    from ai_asst_mgr.adapters.base import VendorAdapter
    from ai_asst_mgr.coaches.base import CoachBase

app = typer.Typer(
    name="ai-asst-mgr",
    help="Universal AI assistant configuration manager",
    add_completion=False,
)
console = Console()


def _get_status_display(status: VendorStatus) -> str:
    """Get display string for vendor status with emoji and color.

    Args:
        status: VendorStatus enum value.

    Returns:
        Formatted string with emoji and color markup.
    """
    if status == VendorStatus.CONFIGURED:
        return "[green]✅ Configured[/green]"
    if status == VendorStatus.INSTALLED:
        return "[yellow]⚠️  Installed[/yellow]"
    if status == VendorStatus.NOT_INSTALLED:
        return "[red]❌ Not Installed[/red]"
    if status == VendorStatus.RUNNING:
        return "[green]🟢 Running[/green]"
    return "[red]❗ Error[/red]"


def _get_notes_for_status(status: VendorStatus) -> str:
    """Get helpful notes based on vendor status.

    Args:
        status: VendorStatus enum value.

    Returns:
        Helpful notes string.
    """
    if status == VendorStatus.CONFIGURED:
        return "Ready to use"
    if status == VendorStatus.INSTALLED:
        return "Needs configuration"
    if status == VendorStatus.NOT_INSTALLED:
        return "Not detected on system"
    if status == VendorStatus.RUNNING:
        return "Currently active"
    return "Configuration error detected"


def _format_health_status(is_healthy: bool, warnings: list[object]) -> str:
    """Format the health status with color coding.

    Args:
        is_healthy: Whether the vendor is healthy.
        warnings: List of warning messages.

    Returns:
        Color-coded status string for Rich.
    """
    if is_healthy and not warnings:
        return "[green]Healthy[/green]"
    if is_healthy and warnings:
        return "[yellow]Warning[/yellow]"
    return "[red]Issues[/red]"


def _format_issues(errors: list[object], warnings: list[object]) -> str:
    """Format issues text for display.

    Args:
        errors: List of error messages.
        warnings: List of warning messages.

    Returns:
        Formatted issues text.
    """
    if errors:
        return "\n".join(f"• {err}" for err in errors)
    if warnings:
        return "\n".join(f"⚠ {warn}" for warn in warnings)
    return "[green]No issues[/green]"


def _format_recommendations(recommendations: list[object]) -> str:
    """Format recommendations text for display.

    Args:
        recommendations: List of recommendation messages.

    Returns:
        Formatted recommendations text.
    """
    if recommendations:
        return "\n".join(f"→ {rec}" for rec in recommendations)
    return "[dim]None[/dim]"


@app.command()
def status(
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Show status for specific vendor"),
    ] = None,
) -> None:
    """Show status of all AI assistant vendors.

    Displays a table showing the installation and configuration status
    of all detected AI vendors (Claude, Gemini, OpenAI).

    Args:
        vendor: Optional vendor name to show status for a single vendor.
    """
    registry = VendorRegistry()

    # Get vendors to display
    if vendor:
        try:
            vendors_to_show = {vendor: registry.get_vendor(vendor)}
        except KeyError:
            console.print(f"[red]Error: Unknown vendor '{vendor}'[/red]")
            available = ", ".join(registry.get_all_vendors().keys())
            console.print(f"[yellow]Available vendors: {available}[/yellow]")
            raise typer.Exit(code=1) from None
    else:
        vendors_to_show = registry.get_all_vendors()

    # Create Rich table
    table = Table(title="AI Assistant Vendor Status", show_header=True, header_style="bold cyan")
    table.add_column("Vendor", style="bold", width=15)
    table.add_column("Status", width=20)
    table.add_column("Config Location", style="dim", width=40)
    table.add_column("Notes", width=25)

    # Add rows for each vendor
    for _vendor_name, adapter in vendors_to_show.items():
        vendor_info = adapter.info
        vendor_status = adapter.get_status()
        status_display = _get_status_display(vendor_status)
        config_location = str(vendor_info.config_dir)
        notes = _get_notes_for_status(vendor_status)

        table.add_row(
            vendor_info.name,
            status_display,
            config_location,
            notes,
        )

    # Display the table
    console.print(table)

    # Add summary if showing all vendors
    if not vendor:
        configured_count = len(registry.get_configured_vendors())
        installed_count = len(registry.get_installed_vendors())
        total_count = len(vendors_to_show)

        console.print(
            f"\n[bold]Summary:[/bold] {configured_count}/{total_count} configured, "
            f"{installed_count}/{total_count} installed"
        )


@app.command()
def config(
    key: Annotated[
        str | None,
        typer.Argument(help="Configuration key to get or set"),
    ] = None,
    value: Annotated[
        str | None,
        typer.Argument(help="Value to set for the configuration key"),
    ] = None,
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Vendor to configure"),
    ] = None,
    list_all: Annotated[
        bool,
        typer.Option("--list", "-l", help="List all configuration values"),
    ] = False,
) -> None:
    """Get or set configuration values for AI assistant vendors.

    Examples:
        ai-asst-mgr config --list                         # List all config
        ai-asst-mgr config --vendor claude --list         # List Claude config
        ai-asst-mgr config theme                          # Get value for 'theme'
        ai-asst-mgr config theme "light"                  # Set theme to "light"
        ai-asst-mgr config --vendor claude version        # Get Claude version
        ai-asst-mgr config mcp.servers.brave.url "https://..." # Set nested value
    """
    registry = VendorRegistry()

    # Determine which vendors to operate on
    if vendor:
        try:
            vendors_to_use = {vendor: registry.get_vendor(vendor)}
        except KeyError:
            console.print(f"[red]Error: Unknown vendor '{vendor}'[/red]")
            available = ", ".join(registry.get_all_vendors().keys())
            console.print(f"[yellow]Available vendors: {available}[/yellow]")
            raise typer.Exit(code=1) from None
    else:
        vendors_to_use = registry.get_all_vendors()

    # Handle --list flag
    if list_all:
        _config_list_all(vendors_to_use)
        return

    # Handle get/set operations
    if key is None:
        console.print("[red]Error: Please provide a configuration key or use --list[/red]")
        console.print("[yellow]Usage: ai-asst-mgr config KEY [VALUE][/yellow]")
        raise typer.Exit(code=1)

    # If value is provided, set the config
    if value is not None:
        _config_set_value(vendors_to_use, key, value)
    else:
        # Get the config value
        _config_get_value(vendors_to_use, key, vendor)


@app.command()
def health(
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Check health for specific vendor"),
    ] = None,
) -> None:
    """Run health checks on vendor configurations.

    Performs diagnostic checks on AI vendor configurations and displays results
    in a table showing health status, issues, and recommendations.

    Args:
        vendor: Optional vendor name to check. If not provided, checks all vendors.
    """
    registry = VendorRegistry()

    # Determine which vendors to check
    if vendor:
        try:
            vendors_to_check = {vendor: registry.get_vendor(vendor)}
        except KeyError as e:
            console.print(f"[red]Error:[/red] Unknown vendor '{vendor}'")
            console.print("\nAvailable vendors:")
            for name in registry.get_all_vendors():
                console.print(f"  - {name}")
            raise typer.Exit(1) from e
    else:
        vendors_to_check = registry.get_all_vendors()

    # Create Rich table
    table = Table(title="Vendor Health Status", show_header=True, header_style="bold")
    table.add_column("Vendor", style="cyan", width=12)
    table.add_column("Status", width=10)
    table.add_column("Issues Found", width=40)
    table.add_column("Recommendations", width=40)

    # Run health checks and populate table
    for vendor_name, adapter in vendors_to_check.items():
        try:
            health_result = adapter.health_check()
            audit_result = adapter.audit_config()

            # Determine health status and color
            is_healthy = bool(health_result.get("healthy", False))
            errors_raw = health_result.get("errors", [])
            warnings_raw = audit_result.get("warnings", [])
            recommendations_raw = audit_result.get("recommendations", [])

            # Type narrow to lists of strings
            errors = errors_raw if isinstance(errors_raw, list) else []
            warnings = warnings_raw if isinstance(warnings_raw, list) else []
            recommendations = recommendations_raw if isinstance(recommendations_raw, list) else []

            # Format output using helper functions
            status = _format_health_status(is_healthy, warnings)
            issues_text = _format_issues(errors, warnings)
            recommendations_text = _format_recommendations(recommendations)

            table.add_row(
                vendor_name.capitalize(),
                status,
                issues_text,
                recommendations_text,
            )

        except Exception as e:
            # Handle any errors gracefully
            table.add_row(
                vendor_name.capitalize(),
                "[red]Error[/red]",
                f"Failed to run health check: {e!s}",
                "",
            )

    # Display the table
    console.print(table)


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


@app.command()
def init(
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Initialize specific vendor"),
    ] = None,
    dry_run: Annotated[
        bool,
        typer.Option("--dry-run", help="Show what would be initialized without making changes"),
    ] = False,
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Force reinitialization even if already configured"),
    ] = False,
) -> None:
    """Initialize AI assistant vendor configurations.

    Creates necessary directory structures and default configuration files
    for AI assistant vendors. By default, initializes all installed vendors,
    or you can specify a single vendor with --vendor.

    Examples:
        ai-asst-mgr init                  # Initialize all vendors
        ai-asst-mgr init --vendor gemini  # Initialize specific vendor
        ai-asst-mgr init --dry-run        # Preview what would be initialized
        ai-asst-mgr init --force          # Force reinitialize all vendors

    Args:
        vendor: Optional vendor name to initialize. If not provided, initializes all.
        dry_run: If True, shows what would be initialized without making changes.
        force: If True, reinitializes even if already configured.
    """
    registry = VendorRegistry()

    # Get vendors to initialize
    vendors_to_init = _get_vendors_to_init(registry, vendor)

    # Display header
    _display_init_header(dry_run)

    # Process vendors and collect results
    results_table, counts = _process_vendor_initializations(
        vendors_to_init,
        dry_run=dry_run,
        force=force,
    )

    # Display results and summary
    console.print(results_table)
    _display_init_summary(counts, dry_run)

    # Exit with appropriate code
    if counts["failed"] > 0:
        raise typer.Exit(code=1)


# init command helpers
def _get_vendors_to_init(registry: VendorRegistry, vendor: str | None) -> dict[str, VendorAdapter]:
    """Get the vendors that should be initialized.

    Args:
        registry: VendorRegistry instance.
        vendor: Optional specific vendor name.

    Returns:
        Dictionary of vendors to initialize.

    Raises:
        typer.Exit: If vendor is invalid.
    """
    if vendor:
        try:
            return {vendor: registry.get_vendor(vendor)}
        except KeyError:
            console.print(f"[red]Error: Unknown vendor '{vendor}'[/red]")
            available = ", ".join(registry.get_all_vendors().keys())
            console.print(f"[yellow]Available vendors: {available}[/yellow]")
            raise typer.Exit(code=1) from None
    return registry.get_all_vendors()


def _display_init_header(dry_run: bool) -> None:
    """Display initialization header.

    Args:
        dry_run: Whether this is a dry run.
    """
    if dry_run:
        console.print(
            Panel.fit(
                "[bold blue]Initialization Preview (Dry Run)[/bold blue]",
                border_style="blue",
            )
        )
    else:
        console.print(
            Panel.fit(
                "[bold green]Initializing Vendor Configurations[/bold green]",
                border_style="green",
            )
        )


def _process_vendor_initializations(
    vendors_to_init: dict[str, VendorAdapter],
    dry_run: bool,
    force: bool,
) -> tuple[Table, dict[str, int]]:
    """Process vendor initializations and build results table.

    Args:
        vendors_to_init: Dictionary of vendors to initialize.
        dry_run: Whether this is a dry run.
        force: Whether to force reinitialize.

    Returns:
        Tuple of (results_table, counts_dict).
    """
    # Create results table
    results_table = Table(show_header=True, header_style="bold cyan")
    results_table.add_column("Vendor", style="bold", width=15)
    results_table.add_column("Status", width=20)
    results_table.add_column("Action", width=40)

    # Track results
    counts = {"initialized": 0, "skipped": 0, "failed": 0}

    # Initialize each vendor
    for vendor_name, adapter in vendors_to_init.items():
        try:
            status, action = _initialize_vendor(
                adapter,
                dry_run=dry_run,
                force=force,
            )

            # Categorize result and update display
            status_display, count_category = _categorize_init_result(status)
            counts[count_category] += 1

            results_table.add_row(
                adapter.info.name,
                status_display,
                action,
            )

        except Exception as e:
            counts["failed"] += 1
            results_table.add_row(
                adapter.info.name if hasattr(adapter, "info") else vendor_name,
                "[red]Failed[/red]",
                f"Error: {e!s}",
            )

    return results_table, counts


def _display_init_summary(counts: dict[str, int], dry_run: bool) -> None:
    """Display initialization summary.

    Args:
        counts: Dictionary with count of initialized, skipped, and failed.
        dry_run: Whether this is a dry run.
    """
    console.print("\n[bold]Summary:[/bold]")
    if dry_run:
        console.print(f"  Would initialize: {counts['initialized']}")
        console.print(f"  Would skip: {counts['skipped']}")
    else:
        console.print(f"  Initialized: {counts['initialized']}")
        console.print(f"  Skipped: {counts['skipped']}")
        console.print(f"  Failed: {counts['failed']}")


def _initialize_vendor(
    adapter: VendorAdapter,
    dry_run: bool = False,
    force: bool = False,
) -> tuple[str, str]:
    """Initialize a single vendor's configuration.

    Args:
        adapter: VendorAdapter instance for the vendor.
        dry_run: If True, only check what would be done.
        force: If True, reinitialize even if already configured.

    Returns:
        Tuple of (status, action) strings describing the result.

    Raises:
        RuntimeError: If initialization fails (propagates from adapter.initialize()).
    """
    # Check current status
    is_configured = adapter.is_configured()

    # Determine if we should initialize
    if is_configured and not force:
        return ("Skipped", "Already configured (use --force to reinitialize)")

    # Dry run - just report what would happen
    if dry_run:
        if is_configured:
            return ("Would initialize", "Force reinitialize configuration")
        return ("Would initialize", "Create configuration directory and defaults")

    # Actually initialize
    adapter.initialize()

    if is_configured:
        return ("Initialized", "Reinitialized configuration")
    return ("Initialized", "Created configuration directory and defaults")


def _categorize_init_result(status: str) -> tuple[str, str]:
    """Categorize initialization result for display and counting.

    Args:
        status: Status string from _initialize_vendor.

    Returns:
        Tuple of (status_display, count_category) where count_category is one of:
        "initialized", "skipped", or "failed".
    """
    if "Initialized" in status or "Would initialize" in status:
        return (f"[green]{status}[/green]", "initialized")
    if "Skipped" in status:
        return (f"[yellow]{status}[/yellow]", "skipped")
    return (f"[red]{status}[/red]", "failed")


# config command helpers
def _config_list_all(vendors: dict[str, VendorAdapter]) -> None:
    """List all configuration values for vendors.

    Args:
        vendors: Dictionary of vendor name to adapter mappings.
    """
    for vendor_name, adapter in vendors.items():
        try:
            # Check if vendor is configured
            if not adapter.is_configured():
                console.print(f"\n[yellow]{vendor_name.capitalize()}: Not configured[/yellow]")
                continue

            # Load the full settings
            if hasattr(adapter, "_load_settings"):
                settings = adapter._load_settings()
            else:
                console.print(
                    f"\n[yellow]{vendor_name.capitalize()}: Unable to load settings[/yellow]"
                )
                continue

            # Display vendor config table
            console.print(f"\n[bold cyan]{vendor_name.capitalize()} Configuration:[/bold cyan]")
            table = Table(show_header=True, header_style="bold magenta")
            table.add_column("Key", style="cyan", width=30)
            table.add_column("Value", style="green", width=50)

            # Flatten nested dict for display
            for config_key, config_value in _flatten_dict(settings).items():
                value_str = _format_config_value(config_value)
                table.add_row(config_key, value_str)

            console.print(table)

        except Exception as e:
            console.print(f"\n[red]Error listing config for {vendor_name}: {e}[/red]")


def _config_get_value(vendors: dict[str, VendorAdapter], key: str, vendor_name: str | None) -> None:
    """Get a configuration value.

    Args:
        vendors: Dictionary of vendor name to adapter mappings.
        key: Configuration key to retrieve.
        vendor_name: Optional vendor name (if specified, only get from that vendor).
    """
    found = False

    for name, adapter in vendors.items():
        try:
            value = adapter.get_config(key)
            found = True

            # If specific vendor was requested, just show the value
            if vendor_name:
                console.print(_format_config_value(value))
            else:
                # Show vendor name with the value
                console.print(f"[cyan]{name.capitalize()}:[/cyan] {_format_config_value(value)}")

        except KeyError:
            if vendor_name:
                # If specific vendor was requested and key not found, show error
                console.print(f"[red]Configuration key '{key}' not found in {name}[/red]")
                raise typer.Exit(code=1) from None
            # If querying all vendors, skip those that don't have the key
            continue
        except Exception as e:
            console.print(f"[red]Error reading config from {name}: {e}[/red]")
            if vendor_name:
                raise typer.Exit(code=1) from e

    if not found and not vendor_name:
        console.print(f"[red]Configuration key '{key}' not found in any vendor[/red]")
        raise typer.Exit(code=1)


def _config_set_value(
    vendors: dict[str, VendorAdapter],
    key: str,
    value: str,
) -> None:
    """Set a configuration value.

    Args:
        vendors: Dictionary of vendor name to adapter mappings (pre-filtered by caller).
        key: Configuration key to set.
        value: Value to set.
    """
    # Parse value - try to convert to appropriate type
    parsed_value = _parse_config_value(value)

    for name, adapter in vendors.items():
        try:
            adapter.set_config(key, parsed_value)
            console.print(
                f"[green]Set {key} = {_format_config_value(parsed_value)} for {name}[/green]"
            )

        except ValueError as e:
            console.print(f"[red]Invalid value for {name}: {e}[/red]")
            raise typer.Exit(code=1) from e
        except Exception as e:
            console.print(f"[red]Error setting config for {name}: {e}[/red]")
            raise typer.Exit(code=1) from e


def _flatten_dict(d: dict[str, Any], parent_key: str = "", sep: str = ".") -> dict[str, Any]:
    """Flatten a nested dictionary using dot notation.

    Args:
        d: Dictionary to flatten.
        parent_key: Parent key prefix.
        sep: Separator for nested keys.

    Returns:
        Flattened dictionary with dot-notation keys.
    """
    items: list[tuple[str, Any]] = []
    for k, v in d.items():
        new_key = f"{parent_key}{sep}{k}" if parent_key else k
        if isinstance(v, dict):
            items.extend(_flatten_dict(v, new_key, sep=sep).items())
        else:
            items.append((new_key, v))
    return dict(items)


def _format_config_value(value: object) -> str:
    """Format a configuration value for display.

    Args:
        value: Value to format.

    Returns:
        Formatted string representation.
    """
    if isinstance(value, (dict, list)):
        return json.dumps(value, indent=2)
    if isinstance(value, bool):
        return "[green]true[/green]" if value else "[red]false[/red]"
    if value is None:
        return "[dim]null[/dim]"
    return str(value)


def _parse_config_value(value: str) -> object:
    """Parse a string value to appropriate type.

    Args:
        value: String value to parse.

    Returns:
        Parsed value (bool, int, float, dict, list, or str).
    """
    # Try to parse as JSON first (handles objects, arrays, booleans, numbers)
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        # Return as string if not valid JSON
        return value


# Coach command helpers
def _get_coach_for_vendor(vendor_id: str) -> CoachBase:
    """Get the coach instance for a vendor.

    Args:
        vendor_id: Vendor identifier (claude, gemini, openai).

    Returns:
        CoachBase instance for the vendor.

    Raises:
        typer.Exit: If vendor is unknown.
    """
    coaches: dict[str, CoachBase] = {
        "claude": ClaudeCoach(),
        "gemini": GeminiCoach(),
        "openai": CodexCoach(),
    }

    if vendor_id not in coaches:
        console.print(f"[red]Error: Unknown vendor '{vendor_id}'[/red]")
        console.print(f"[yellow]Available vendors: {', '.join(coaches.keys())}[/yellow]")
        raise typer.Exit(code=1)

    return coaches[vendor_id]


def _get_all_coaches() -> dict[str, CoachBase]:
    """Get all available coaches.

    Returns:
        Dictionary mapping vendor IDs to coach instances.
    """
    return {
        "claude": ClaudeCoach(),
        "gemini": GeminiCoach(),
        "openai": CodexCoach(),
    }


def _display_coach_insights(coach: CoachBase) -> None:
    """Display insights from a coach in a Rich panel.

    Args:
        coach: CoachBase instance with analysis results.
    """
    insights = coach.get_insights()

    if not insights:
        console.print(f"[dim]No insights available for {coach.vendor_name}[/dim]")
        return

    # Create insights table
    table = Table(show_header=True, header_style="bold cyan", title=f"{coach.vendor_name} Insights")
    table.add_column("Category", style="dim", width=15)
    table.add_column("Insight", width=40)
    table.add_column("Metric", width=25)

    for insight in insights:
        metric_display = f"{insight.metric_value}"
        if insight.metric_unit:
            metric_display += f" {insight.metric_unit}"

        table.add_row(
            insight.category,
            f"[bold]{insight.title}[/bold]\n{insight.description}",
            metric_display,
        )

    console.print(table)


def _display_coach_recommendations(coach: CoachBase) -> None:
    """Display recommendations from a coach with priority coloring.

    Args:
        coach: CoachBase instance with analysis results.
    """
    recommendations = coach.get_recommendations()

    if not recommendations:
        msg = f"\n[green]No recommendations for {coach.vendor_name} - looks good![/green]"
        console.print(msg)
        return

    console.print(f"\n[bold]{coach.vendor_name} Recommendations:[/bold]\n")

    # Priority colors and emojis
    priority_styles = {
        Priority.CRITICAL: ("[red]", "🔴"),
        Priority.HIGH: ("[yellow]", "🟠"),
        Priority.MEDIUM: ("[blue]", "🟡"),
        Priority.LOW: ("[dim]", "🟢"),
    }

    for rec in recommendations:
        style, emoji = priority_styles.get(rec.priority, ("[white]", "⚪"))
        close_style = style.replace("[", "[/")

        panel_content = (
            f"{rec.description}\n\n"
            f"[bold]Action:[/bold] {rec.action}\n"
            f"[bold]Expected Benefit:[/bold] {rec.expected_benefit}"
        )

        console.print(
            Panel(
                panel_content,
                title=f"{emoji} {style}{rec.title}{close_style}",
                subtitle=f"[dim]{rec.category} | {rec.priority.value.upper()}[/dim]",
                border_style=style.strip("[]"),
            )
        )


def _display_coach_stats(coach: CoachBase) -> None:
    """Display raw statistics from a coach.

    Args:
        coach: CoachBase instance with analysis results.
    """
    stats = coach.get_stats()

    if not stats:
        return

    console.print(f"\n[bold]{coach.vendor_name} Statistics:[/bold]")

    table = Table.grid(padding=(0, 2))
    for key, value in stats.items():
        # Format booleans nicely
        if isinstance(value, bool):
            value_str = "[green]Yes[/green]" if value else "[red]No[/red]"
        else:
            value_str = str(value)

        table.add_row(f"[cyan]{key}:[/cyan]", value_str)

    console.print(table)


def _compare_vendors(coaches: dict[str, CoachBase]) -> None:
    """Display cross-vendor comparison.

    Args:
        coaches: Dictionary of vendor IDs to coach instances.
    """
    console.print(Panel.fit("[bold blue]Cross-Vendor Comparison[/bold blue]", border_style="blue"))

    # Create comparison table
    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Metric", style="cyan", width=25)

    for _vendor_id, coach in coaches.items():
        table.add_column(coach.vendor_name, width=20)

    # Collect stats from all coaches
    all_stats: dict[str, dict[str, object]] = {}
    for vendor_id, coach in coaches.items():
        coach.analyze()
        all_stats[vendor_id] = coach.get_stats()

    # Find common stat keys
    all_keys: set[str] = set()
    for stats in all_stats.values():
        all_keys.update(stats.keys())

    # Add rows for each stat
    for key in sorted(all_keys):
        row = [key]
        for vendor_id in coaches:
            value = all_stats[vendor_id].get(key, "-")
            if isinstance(value, bool):
                row.append("[green]Yes[/green]" if value else "[red]No[/red]")
            else:
                row.append(str(value))
        table.add_row(*row)

    console.print(table)

    # Recommendation summary
    console.print("\n[bold]Recommendation Summary:[/bold]")
    rec_table = Table(show_header=True, header_style="bold")
    rec_table.add_column("Vendor", width=15)
    rec_table.add_column("Critical", width=10)
    rec_table.add_column("High", width=10)
    rec_table.add_column("Medium", width=10)
    rec_table.add_column("Low", width=10)
    rec_table.add_column("Total", width=10)

    for _vendor_id, coach in coaches.items():
        recs = coach.get_recommendations()
        counts = dict.fromkeys(Priority, 0)
        for rec in recs:
            counts[rec.priority] += 1

        rec_table.add_row(
            coach.vendor_name,
            f"[red]{counts[Priority.CRITICAL]}[/red]",
            f"[yellow]{counts[Priority.HIGH]}[/yellow]",
            f"[blue]{counts[Priority.MEDIUM]}[/blue]",
            f"[dim]{counts[Priority.LOW]}[/dim]",
            str(len(recs)),
        )

    console.print(rec_table)


@app.command()
def coach(
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Analyze specific vendor (claude, gemini, openai)"),
    ] = None,
    report: Annotated[
        str | None,
        typer.Option("--report", "-r", help="Report period: weekly or monthly"),
    ] = None,
    compare: Annotated[
        bool,
        typer.Option("--compare", "-c", help="Show cross-vendor comparison"),
    ] = False,
    export: Annotated[
        str | None,
        typer.Option("--export", "-e", help="Export report to file (json or markdown)"),
    ] = None,
    export_path: Annotated[
        Path | None,
        typer.Option("--output", "-o", help="Output path for exported report"),
    ] = None,
) -> None:
    """Analyze AI assistant usage and get optimization recommendations.

    The coach command analyzes your AI assistant configurations and usage
    patterns to provide data-driven insights and actionable recommendations.

    Examples:
        ai-asst-mgr coach                      # Analyze all vendors
        ai-asst-mgr coach --vendor claude      # Analyze Claude only
        ai-asst-mgr coach --compare            # Cross-vendor comparison
        ai-asst-mgr coach --export json        # Export report as JSON
        ai-asst-mgr coach -v claude -e markdown -o report  # Export Claude report

    Args:
        vendor: Optional vendor to analyze. If not provided, analyzes all.
        report: Report period (weekly/monthly). Currently informational.
        compare: If True, shows cross-vendor comparison.
        export: Export format (json or markdown).
        export_path: Output path for exported report.
    """
    # Get period days from report option
    period_days = 7  # Default to weekly
    if report == "monthly":
        period_days = 30

    # Handle comparison mode
    if compare:
        coaches = _get_all_coaches()
        _compare_vendors(coaches)
        return

    # Get coaches to analyze
    coaches_to_analyze = {vendor: _get_coach_for_vendor(vendor)} if vendor else _get_all_coaches()

    # Analyze each vendor
    for vendor_id, coach_instance in coaches_to_analyze.items():
        # Run analysis
        coach_instance.analyze(period_days=period_days)

        # Display header
        console.print(
            Panel.fit(
                f"[bold blue]{coach_instance.vendor_name} Analysis[/bold blue]",
                border_style="blue",
            )
        )

        # Display insights
        _display_coach_insights(coach_instance)

        # Display recommendations
        _display_coach_recommendations(coach_instance)

        # Display stats
        _display_coach_stats(coach_instance)

        # Export if requested
        if export:
            output_path = export_path or Path(f"{vendor_id}_report")
            try:
                exported_path = coach_instance.export_report(output_path, format=export)
                console.print(f"\n[green]Report exported to: {exported_path}[/green]")
            except (ValueError, RuntimeError) as e:
                console.print(f"\n[red]Export failed: {e}[/red]")

        # Add spacing between vendors
        if len(coaches_to_analyze) > 1:
            console.print("\n" + "=" * 60 + "\n")


# ============================================================================
# Backup/Restore/Sync Commands
# ============================================================================

DEFAULT_BACKUP_DIR = Path.home() / ".config" / "ai-asst-mgr" / "backups"


def _get_backup_manager(backup_dir: Path | None = None) -> BackupManager:
    """Get backup manager instance.

    Args:
        backup_dir: Optional backup directory. Uses default if not provided.

    Returns:
        BackupManager instance.
    """
    return BackupManager(backup_dir or DEFAULT_BACKUP_DIR)


def _get_restore_manager(backup_dir: Path | None = None) -> RestoreManager:
    """Get restore manager instance.

    Args:
        backup_dir: Optional backup directory. Uses default if not provided.

    Returns:
        RestoreManager instance.
    """
    backup_manager = _get_backup_manager(backup_dir)
    return RestoreManager(backup_manager)


def _get_sync_manager(backup_dir: Path | None = None) -> SyncManager:
    """Get sync manager instance.

    Args:
        backup_dir: Optional backup directory for pre-sync backups.

    Returns:
        SyncManager instance.
    """
    backup_manager = _get_backup_manager(backup_dir)
    return SyncManager(backup_manager)


_BYTES_PER_UNIT = 1024
_MAX_PREVIEW_FILES = 5
_MAX_SYNC_PREVIEW_FILES = 3


def _format_size_bytes(size_bytes: int) -> str:
    """Format size in bytes to human-readable string.

    Args:
        size_bytes: Size in bytes.

    Returns:
        Human-readable size string.
    """
    size: float = float(size_bytes)
    for unit in ["B", "KB", "MB", "GB"]:
        if size < _BYTES_PER_UNIT:
            return f"{size:.1f} {unit}"
        size /= _BYTES_PER_UNIT
    return f"{size:.1f} TB"


@app.command()
def backup(
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Backup specific vendor only"),
    ] = None,
    backup_dir: Annotated[
        Path | None,
        typer.Option("--backup-dir", "-d", help="Directory to store backups"),
    ] = None,
    list_backups: Annotated[
        bool,
        typer.Option("--list", "-l", help="List existing backups"),
    ] = False,
    verify: Annotated[
        Path | None,
        typer.Option("--verify", help="Verify integrity of a backup file"),
    ] = None,
) -> None:
    """Backup AI assistant vendor configurations.

    Creates compressed archives of vendor configuration directories with
    checksum verification and retention policies.

    Examples:
        ai-asst-mgr backup                    # Backup all vendors
        ai-asst-mgr backup --vendor claude    # Backup Claude only
        ai-asst-mgr backup --list             # List all backups
        ai-asst-mgr backup --verify path.tar.gz  # Verify backup integrity

    Args:
        vendor: Optional vendor name to backup. If not provided, backs up all.
        backup_dir: Directory to store backups. Uses default if not provided.
        list_backups: If True, lists existing backups instead of creating new ones.
        verify: Path to backup file to verify.
    """
    registry = VendorRegistry()
    backup_manager = _get_backup_manager(backup_dir)

    # Handle --verify
    if verify:
        _backup_verify(backup_manager, verify)
        return

    # Handle --list
    if list_backups:
        _backup_list(backup_manager, vendor)
        return

    # Create backup(s)
    _backup_create(registry, backup_manager, vendor)


def _backup_verify(backup_manager: BackupManager, backup_path: Path) -> None:
    """Verify backup integrity.

    Args:
        backup_manager: BackupManager instance.
        backup_path: Path to backup file.
    """
    console.print(f"Verifying backup: {backup_path}")

    is_valid, message = backup_manager.verify_backup(backup_path)

    if is_valid:
        console.print(f"[green]✓ {message}[/green]")
    else:
        console.print(f"[red]✗ {message}[/red]")
        raise typer.Exit(code=1)


def _backup_list(backup_manager: BackupManager, vendor: str | None) -> None:
    """List existing backups.

    Args:
        backup_manager: BackupManager instance.
        vendor: Optional vendor to filter by.
    """
    backups = backup_manager.list_backups(vendor)

    if not backups:
        console.print("[yellow]No backups found[/yellow]")
        return

    table = Table(title="Available Backups", show_header=True, header_style="bold cyan")
    table.add_column("Vendor", style="bold", width=12)
    table.add_column("Timestamp", width=20)
    table.add_column("Size", width=10)
    table.add_column("Files", width=8)
    table.add_column("Path", style="dim", width=40)

    for bkp in backups:
        table.add_row(
            bkp.vendor_id.capitalize(),
            bkp.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
            _format_size_bytes(bkp.size_bytes),
            str(bkp.file_count),
            str(bkp.backup_path),
        )

    console.print(table)
    console.print(f"\n[bold]Total:[/bold] {len(backups)} backup(s)")


def _backup_create(
    registry: VendorRegistry,
    backup_manager: BackupManager,
    vendor: str | None,
) -> None:
    """Create backup(s).

    Args:
        registry: VendorRegistry instance.
        backup_manager: BackupManager instance.
        vendor: Optional vendor to backup.
    """

    def progress_callback(msg: str) -> None:
        console.print(f"  {msg}")

    if vendor:
        # Single vendor backup
        try:
            adapter = registry.get_vendor(vendor)
        except KeyError:
            console.print(f"[red]Error: Unknown vendor '{vendor}'[/red]")
            available = ", ".join(registry.get_all_vendors().keys())
            console.print(f"[yellow]Available vendors: {available}[/yellow]")
            raise typer.Exit(code=1) from None

        console.print(f"\n[bold]Backing up {adapter.info.name}...[/bold]")
        result = backup_manager.backup_vendor(adapter, progress_callback)

        if result.success and result.metadata:
            console.print("\n[green]✓ Backup created successfully[/green]")
            console.print(f"  Path: {result.metadata.backup_path}")
            console.print(f"  Size: {_format_size_bytes(result.metadata.size_bytes)}")
            console.print(f"  Files: {result.metadata.file_count}")
        else:
            console.print(f"\n[red]✗ Backup failed: {result.error}[/red]")
            raise typer.Exit(code=1)
    else:
        # All vendors backup
        console.print(
            Panel.fit("[bold blue]Backing Up All Vendors[/bold blue]", border_style="blue")
        )

        installed = registry.get_installed_vendors()
        if not installed:
            console.print("[yellow]No installed vendors found to backup[/yellow]")
            return

        summary = backup_manager.backup_all_vendors(installed, progress_callback)

        # Display summary table
        table = Table(title="Backup Summary", show_header=True, header_style="bold")
        table.add_column("Vendor", width=15)
        table.add_column("Status", width=12)
        table.add_column("Size", width=12)
        table.add_column("Details", width=40)

        for vendor_id, result in summary.results.items():
            if result.success and result.metadata:
                table.add_row(
                    vendor_id.capitalize(),
                    "[green]Success[/green]",
                    _format_size_bytes(result.metadata.size_bytes),
                    str(result.metadata.backup_path.name),
                )
            else:
                table.add_row(
                    vendor_id.capitalize(),
                    "[red]Failed[/red]",
                    "-",
                    result.error or "Unknown error",
                )

        console.print(table)
        console.print(
            f"\n[bold]Summary:[/bold] {summary.successful}/{summary.total_vendors} succeeded, "
            f"{_format_size_bytes(summary.total_size_bytes)} total"
        )


@app.command()
def restore(
    backup_path: Annotated[
        Path | None,
        typer.Argument(help="Path to backup file to restore"),
    ] = None,
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Restore specific vendor (uses latest backup)"),
    ] = None,
    backup_dir: Annotated[
        Path | None,
        typer.Option("--backup-dir", "-d", help="Directory containing backups"),
    ] = None,
    preview: Annotated[
        bool,
        typer.Option("--preview", "-p", help="Preview restore without making changes"),
    ] = False,
    selective: Annotated[
        str | None,
        typer.Option(
            "--selective", "-s", help="Restore only specific directories (comma-separated)"
        ),
    ] = None,
    no_backup: Annotated[
        bool,
        typer.Option("--no-backup", help="Skip creating pre-restore backup"),
    ] = False,
) -> None:
    """Restore AI assistant configurations from backup.

    Restores vendor configuration directories from backup archives with
    optional pre-restore backup for rollback capability.

    Examples:
        ai-asst-mgr restore backup.tar.gz           # Restore from specific file
        ai-asst-mgr restore --vendor claude         # Restore latest Claude backup
        ai-asst-mgr restore backup.tar.gz --preview # Preview what would be restored
        ai-asst-mgr restore backup.tar.gz --selective agents,skills  # Restore specific dirs

    Args:
        backup_path: Path to backup file. Optional if --vendor is used.
        vendor: Vendor to restore latest backup for.
        backup_dir: Directory containing backups.
        preview: If True, shows preview without restoring.
        selective: Comma-separated list of directories to restore.
        no_backup: If True, skips creating pre-restore backup.
    """
    registry = VendorRegistry()
    backup_manager = _get_backup_manager(backup_dir)
    restore_manager = _get_restore_manager(backup_dir)

    # Determine backup path
    actual_backup_path = _resolve_backup_path(backup_path, vendor, backup_manager)
    if actual_backup_path is None:
        return

    # Determine vendor adapter
    adapter = _resolve_restore_adapter(registry, vendor, actual_backup_path, backup_manager)
    if adapter is None:
        return

    def progress_callback(msg: str) -> None:
        console.print(f"  {msg}")

    # Handle preview
    if preview:
        _restore_preview(restore_manager, actual_backup_path, adapter)
        return

    # Handle selective restore
    if selective:
        directories = [d.strip() for d in selective.split(",")]
        _restore_selective(
            restore_manager, actual_backup_path, adapter, directories, progress_callback
        )
        return

    # Full restore
    _restore_full(restore_manager, actual_backup_path, adapter, not no_backup, progress_callback)


def _resolve_backup_path(
    backup_path: Path | None,
    vendor: str | None,
    backup_manager: BackupManager,
) -> Path | None:
    """Resolve the backup path to use.

    Args:
        backup_path: Explicit backup path if provided.
        vendor: Vendor name to find latest backup for.
        backup_manager: BackupManager instance.

    Returns:
        Resolved backup path or None if not found.
    """
    if backup_path:
        if not backup_path.exists():
            console.print(f"[red]Error: Backup file not found: {backup_path}[/red]")
            raise typer.Exit(code=1)
        return backup_path

    if vendor:
        latest = backup_manager.get_latest_backup(vendor)
        if latest:
            return latest.backup_path
        console.print(f"[red]Error: No backups found for vendor '{vendor}'[/red]")
        raise typer.Exit(code=1)

    console.print("[red]Error: Please provide a backup path or use --vendor[/red]")
    raise typer.Exit(code=1)


def _resolve_restore_adapter(
    registry: VendorRegistry,
    vendor: str | None,
    backup_path: Path,
    backup_manager: BackupManager,
) -> VendorAdapter | None:
    """Resolve the vendor adapter for restore.

    Args:
        registry: VendorRegistry instance.
        vendor: Vendor name if provided.
        backup_path: Backup path to infer vendor from.
        backup_manager: BackupManager instance.

    Returns:
        VendorAdapter or None if not found.
    """
    if vendor:
        try:
            return registry.get_vendor(vendor)
        except KeyError:
            console.print(f"[red]Error: Unknown vendor '{vendor}'[/red]")
            raise typer.Exit(code=1) from None

    # Try to infer vendor from backup metadata
    backups = backup_manager.list_backups()
    for bkp in backups:
        if bkp.backup_path == backup_path:
            try:
                return registry.get_vendor(bkp.vendor_id)
            except KeyError:
                console.print(f"[red]Error: Unknown vendor '{bkp.vendor_id}'[/red]")
                raise typer.Exit(code=1) from None

    # Try to infer from backup filename
    filename = backup_path.name.lower()
    for vendor_id in ["claude", "gemini", "openai"]:
        if vendor_id in filename:
            try:
                return registry.get_vendor(vendor_id)
            except KeyError:
                continue

    console.print("[red]Error: Cannot determine vendor from backup. Use --vendor option.[/red]")
    raise typer.Exit(code=1)


def _restore_preview(
    restore_manager: RestoreManager,
    backup_path: Path,
    adapter: VendorAdapter,
) -> None:
    """Preview restore operation.

    Args:
        restore_manager: RestoreManager instance.
        backup_path: Path to backup file.
        adapter: VendorAdapter instance.
    """
    preview_result = restore_manager.preview_restore(backup_path, adapter)

    if preview_result is None:
        console.print("[red]Error: Failed to read backup file[/red]")
        raise typer.Exit(code=1)

    console.print(Panel.fit("[bold blue]Restore Preview[/bold blue]", border_style="blue"))

    console.print(f"\n[bold]Vendor:[/bold] {adapter.info.name}")
    console.print(
        f"[bold]Backup Date:[/bold] {preview_result.backup_timestamp.strftime('%Y-%m-%d %H:%M:%S')}"
    )
    console.print(
        f"[bold]Estimated Size:[/bold] {_format_size_bytes(preview_result.estimated_size_bytes)}"
    )

    console.print(f"\n[bold]Files to restore:[/bold] {len(preview_result.files_to_restore)}")
    if preview_result.files_to_overwrite:
        console.print(
            f"[yellow]Files to overwrite:[/yellow] {len(preview_result.files_to_overwrite)}"
        )
        for f in preview_result.files_to_overwrite[:_MAX_PREVIEW_FILES]:
            console.print(f"  - {f}")
        if len(preview_result.files_to_overwrite) > _MAX_PREVIEW_FILES:
            remaining = len(preview_result.files_to_overwrite) - _MAX_PREVIEW_FILES
            console.print(f"  ... and {remaining} more")

    if preview_result.directories_to_create:
        console.print("\n[bold]Directories to create:[/bold]")
        for d in preview_result.directories_to_create:
            console.print(f"  + {d}")

    console.print("\n[dim]Use without --preview to perform the restore[/dim]")


def _restore_selective(
    restore_manager: RestoreManager,
    backup_path: Path,
    adapter: VendorAdapter,
    directories: list[str],
    progress_callback: Callable[[str], None],
) -> None:
    """Perform selective restore.

    Args:
        restore_manager: RestoreManager instance.
        backup_path: Path to backup file.
        adapter: VendorAdapter instance.
        directories: List of directories to restore.
        progress_callback: Progress callback function.
    """
    # Show available directories first
    available = restore_manager.get_restorable_directories(backup_path)
    invalid_dirs = [d for d in directories if d not in available]

    if invalid_dirs:
        console.print(f"[red]Error: Invalid directories: {', '.join(invalid_dirs)}[/red]")
        console.print(f"[yellow]Available directories: {', '.join(available)}[/yellow]")
        raise typer.Exit(code=1)

    console.print(f"\n[bold]Selectively restoring {adapter.info.name}...[/bold]")
    console.print(f"Directories: {', '.join(directories)}")

    result = restore_manager.restore_selective(backup_path, adapter, directories, progress_callback)

    if result.success:
        console.print("\n[green]✓ Restore completed successfully[/green]")
        console.print(f"  Files restored: {result.restored_files}")
    else:
        console.print(f"\n[red]✗ Restore failed: {result.error}[/red]")
        raise typer.Exit(code=1)


def _restore_full(
    restore_manager: RestoreManager,
    backup_path: Path,
    adapter: VendorAdapter,
    create_backup: bool,
    progress_callback: Callable[[str], None],
) -> None:
    """Perform full restore.

    Args:
        restore_manager: RestoreManager instance.
        backup_path: Path to backup file.
        adapter: VendorAdapter instance.
        create_backup: Whether to create pre-restore backup.
        progress_callback: Progress callback function.
    """
    console.print(f"\n[bold]Restoring {adapter.info.name}...[/bold]")

    result = restore_manager.restore_vendor(
        backup_path,
        adapter,
        create_pre_restore_backup=create_backup,
        progress_callback=progress_callback,
    )

    if result.success:
        console.print("\n[green]✓ Restore completed successfully[/green]")
        console.print(f"  Files restored: {result.restored_files}")
        if result.pre_restore_backup:
            console.print(f"  Pre-restore backup: {result.pre_restore_backup}")
    else:
        console.print(f"\n[red]✗ Restore failed: {result.error}[/red]")
        if result.pre_restore_backup:
            console.print(f"[yellow]Rollback available: {result.pre_restore_backup}[/yellow]")
        raise typer.Exit(code=1)


@app.command()
def sync(
    repo_url: Annotated[
        str,
        typer.Argument(help="Git repository URL to sync from"),
    ],
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Sync specific vendor only"),
    ] = None,
    branch: Annotated[
        str,
        typer.Option("--branch", "-b", help="Git branch to sync from"),
    ] = "main",
    strategy: Annotated[
        str,
        typer.Option(
            "--strategy", "-s", help="Merge strategy: replace, merge, keep_local, keep_remote"
        ),
    ] = "keep_remote",
    preview: Annotated[
        bool,
        typer.Option("--preview", "-p", help="Preview sync without making changes"),
    ] = False,
    no_backup: Annotated[
        bool,
        typer.Option("--no-backup", help="Skip creating pre-sync backup"),
    ] = False,
    backup_dir: Annotated[
        Path | None,
        typer.Option("--backup-dir", "-d", help="Directory to store pre-sync backups"),
    ] = None,
) -> None:
    """Synchronize AI assistant configurations from a Git repository.

    Clones configuration from a Git repository and syncs it to local
    vendor configuration directories with various merge strategies.

    Merge Strategies:
        replace    - Replace all local files with remote
        merge      - Keep both versions (creates .remote files for conflicts)
        keep_local - Keep local files if they exist
        keep_remote - Use remote files (default)

    Examples:
        ai-asst-mgr sync https://github.com/user/configs.git
        ai-asst-mgr sync https://github.com/user/configs.git --vendor claude
        ai-asst-mgr sync https://github.com/user/configs.git --preview
        ai-asst-mgr sync https://github.com/user/configs.git --strategy merge

    Args:
        repo_url: Git repository URL to sync from.
        vendor: Optional vendor to sync. If not provided, syncs all.
        branch: Git branch to sync from.
        strategy: Merge strategy to use.
        preview: If True, shows preview without syncing.
        no_backup: If True, skips creating pre-sync backup.
        backup_dir: Directory for pre-sync backups.
    """
    registry = VendorRegistry()
    sync_manager = _get_sync_manager(backup_dir)

    # Parse merge strategy
    try:
        merge_strategy = MergeStrategy(strategy)
    except ValueError:
        valid_strategies = ", ".join(s.value for s in MergeStrategy)
        console.print(f"[red]Error: Invalid strategy '{strategy}'[/red]")
        console.print(f"[yellow]Valid strategies: {valid_strategies}[/yellow]")
        raise typer.Exit(code=1) from None

    # Get vendors to sync
    if vendor:
        try:
            vendors_to_sync = {vendor: registry.get_vendor(vendor)}
        except KeyError:
            console.print(f"[red]Error: Unknown vendor '{vendor}'[/red]")
            available = ", ".join(registry.get_all_vendors().keys())
            console.print(f"[yellow]Available vendors: {available}[/yellow]")
            raise typer.Exit(code=1) from None
    else:
        vendors_to_sync = registry.get_all_vendors()

    # Handle preview
    if preview:
        _sync_preview(sync_manager, repo_url, vendors_to_sync, branch)
        return

    # Perform sync
    _sync_execute(
        sync_manager,
        repo_url,
        vendors_to_sync,
        branch,
        merge_strategy,
        not no_backup,
    )


def _sync_preview(
    sync_manager: SyncManager,
    repo_url: str,
    vendors: dict[str, VendorAdapter],
    branch: str,
) -> None:
    """Preview sync operation.

    Args:
        sync_manager: SyncManager instance.
        repo_url: Git repository URL.
        vendors: Dictionary of vendors to sync.
        branch: Git branch.
    """
    console.print(Panel.fit("[bold blue]Sync Preview[/bold blue]", border_style="blue"))
    console.print(f"\n[bold]Repository:[/bold] {repo_url}")
    console.print(f"[bold]Branch:[/bold] {branch}\n")

    for _vendor_id, adapter in vendors.items():
        console.print(f"[bold cyan]{adapter.info.name}:[/bold cyan]")

        preview_result = sync_manager.preview_sync(repo_url, adapter, branch)

        if preview_result is None:
            console.print("  [red]Failed to preview (check repository URL)[/red]")
            continue

        if preview_result.files_to_add:
            console.print(f"  [green]Files to add:[/green] {len(preview_result.files_to_add)}")
            for f in preview_result.files_to_add[:_MAX_SYNC_PREVIEW_FILES]:
                console.print(f"    + {f}")
            if len(preview_result.files_to_add) > _MAX_SYNC_PREVIEW_FILES:
                remaining = len(preview_result.files_to_add) - _MAX_SYNC_PREVIEW_FILES
                console.print(f"    ... and {remaining} more")

        if preview_result.files_to_modify:
            console.print(
                f"  [yellow]Files to modify:[/yellow] {len(preview_result.files_to_modify)}"
            )
            for f in preview_result.files_to_modify[:_MAX_SYNC_PREVIEW_FILES]:
                console.print(f"    ~ {f}")
            if len(preview_result.files_to_modify) > _MAX_SYNC_PREVIEW_FILES:
                remaining = len(preview_result.files_to_modify) - _MAX_SYNC_PREVIEW_FILES
                console.print(f"    ... and {remaining} more")

        if preview_result.files_to_delete:
            delete_count = len(preview_result.files_to_delete)
            console.print(f"  [red]Files to delete (REPLACE mode):[/red] {delete_count}")

        if preview_result.conflicts:
            console.print(
                f"  [yellow]Potential conflicts:[/yellow] {len(preview_result.conflicts)}"
            )

        if not (preview_result.files_to_add or preview_result.files_to_modify):
            console.print("  [dim]No changes detected[/dim]")

        console.print()

    console.print("[dim]Use without --preview to perform the sync[/dim]")


def _sync_execute(
    sync_manager: SyncManager,
    repo_url: str,
    vendors: dict[str, VendorAdapter],
    branch: str,
    strategy: MergeStrategy,
    create_backup: bool,
) -> None:
    """Execute sync operation.

    Args:
        sync_manager: SyncManager instance.
        repo_url: Git repository URL.
        vendors: Dictionary of vendors to sync.
        branch: Git branch.
        strategy: Merge strategy.
        create_backup: Whether to create pre-sync backup.
    """
    console.print(
        Panel.fit("[bold blue]Syncing from Git Repository[/bold blue]", border_style="blue")
    )
    console.print(f"\n[bold]Repository:[/bold] {repo_url}")
    console.print(f"[bold]Branch:[/bold] {branch}")
    console.print(f"[bold]Strategy:[/bold] {strategy.value}\n")

    def progress_callback(msg: str) -> None:
        console.print(f"  {msg}")

    results = sync_manager.sync_all_vendors(
        repo_url,
        vendors,
        branch,
        strategy,
        progress_callback,
        create_backup=create_backup,
    )

    # Display results table
    table = Table(title="Sync Results", show_header=True, header_style="bold")
    table.add_column("Vendor", width=15)
    table.add_column("Status", width=12)
    table.add_column("Added", width=8)
    table.add_column("Modified", width=10)
    table.add_column("Deleted", width=8)
    table.add_column("Duration", width=10)

    total_added = 0
    total_modified = 0
    total_deleted = 0
    successful = 0

    for vendor_id, result in results.items():
        if result.success:
            successful += 1
            total_added += result.files_added
            total_modified += result.files_modified
            total_deleted += result.files_deleted

            table.add_row(
                vendor_id.capitalize(),
                "[green]Success[/green]",
                str(result.files_added),
                str(result.files_modified),
                str(result.files_deleted),
                f"{result.duration_seconds:.1f}s",
            )

            if result.pre_sync_backup:
                console.print(f"  [dim]Pre-sync backup: {result.pre_sync_backup}[/dim]")
        else:
            table.add_row(
                vendor_id.capitalize(),
                "[red]Failed[/red]",
                "-",
                "-",
                "-",
                "-",
            )
            console.print(f"  [red]{vendor_id}: {result.error}[/red]")

    console.print(table)
    console.print(
        f"\n[bold]Summary:[/bold] {successful}/{len(results)} succeeded, "
        f"+{total_added} ~{total_modified} -{total_deleted} files"
    )


# ============================================================================
# Audit Command
# ============================================================================

# Score thresholds for audit display
AUDIT_SCORE_GOOD = 80
AUDIT_SCORE_WARNING = 60

# Severity and category filter values
VALID_SEVERITIES = ["info", "warning", "error", "critical"]
VALID_CATEGORIES = ["security", "config", "quality", "usage"]
SEVERITY_ORDER = {"info": 0, "warning": 1, "error": 2, "critical": 3}


def _get_severity_style(severity_value: str) -> str:
    """Get Rich style for severity level.

    Args:
        severity_value: The severity value string.

    Returns:
        Rich style string with color.
    """
    styles = {
        "critical": "[bold red]CRITICAL[/bold red]",
        "error": "[red]ERROR[/red]",
        "warning": "[yellow]WARNING[/yellow]",
        "info": "[dim]INFO[/dim]",
    }
    return styles.get(severity_value, severity_value)


def _get_category_style(category_value: str) -> str:
    """Get Rich style for category.

    Args:
        category_value: The category value string.

    Returns:
        Rich style string with color.
    """
    styles = {
        "security": "[cyan]security[/cyan]",
        "config": "[blue]config[/blue]",
        "quality": "[magenta]quality[/magenta]",
        "usage": "[green]usage[/green]",
    }
    return styles.get(category_value, category_value)


def _run_vendor_audit(vendor_id: str, config_dir: Path) -> dict[str, Any]:
    """Run audit for a specific vendor.

    Args:
        vendor_id: The vendor identifier.
        config_dir: Path to vendor config directory.

    Returns:
        Audit report as dictionary.
    """
    auditor_classes: dict[str, type[ClaudeAuditor] | type[GeminiAuditor] | type[CodexAuditor]] = {
        "claude": ClaudeAuditor,
        "gemini": GeminiAuditor,
        "openai": CodexAuditor,
    }

    auditor_class = auditor_classes.get(vendor_id)
    if not auditor_class:
        return {"vendor_id": vendor_id, "error": f"Unknown vendor: {vendor_id}"}

    auditor = auditor_class(config_dir)
    report = auditor.run_audit()
    return report.to_dict()


def _validate_audit_filter(value: str | None, valid_options: list[str], filter_name: str) -> None:
    """Validate an audit filter value.

    Args:
        value: The filter value to validate.
        valid_options: List of valid option values.
        filter_name: Name of the filter for error messages.

    Raises:
        typer.Exit: If the value is invalid.
    """
    if value and value.lower() not in valid_options:
        console.print(f"[red]Error: Invalid {filter_name} '{value}'[/red]")
        console.print(f"[yellow]Valid {filter_name} values: {', '.join(valid_options)}[/yellow]")
        raise typer.Exit(code=1)


def _get_vendors_to_audit(registry: VendorRegistry, vendor: str | None) -> dict[str, VendorAdapter]:
    """Get the vendors to audit.

    Args:
        registry: The vendor registry.
        vendor: Optional specific vendor to audit.

    Returns:
        Dictionary of vendor_id to VendorAdapter.

    Raises:
        typer.Exit: If the specified vendor is not found.
    """
    if vendor:
        try:
            return {vendor: registry.get_vendor(vendor)}
        except KeyError:
            console.print(f"[red]Error: Unknown vendor '{vendor}'[/red]")
            available = ", ".join(registry.get_all_vendors().keys())
            console.print(f"[yellow]Available vendors: {available}[/yellow]")
            raise typer.Exit(code=1) from None
    return registry.get_all_vendors()


def _filter_audit_checks(
    checks: list[dict[str, Any]],
    min_severity: int,
    category: str | None,
    failed_only: bool,
) -> list[dict[str, Any]]:
    """Filter audit checks based on criteria.

    Args:
        checks: List of check dictionaries.
        min_severity: Minimum severity level (0-3).
        category: Optional category to filter by.
        failed_only: If True, only include failed checks.

    Returns:
        Filtered list of checks.
    """
    filtered = []
    for check in checks:
        check_severity = SEVERITY_ORDER.get(check.get("severity", "info"), 0)
        if check_severity < min_severity:
            continue
        if category and check.get("category", "") != category.lower():
            continue
        if failed_only and check.get("passed", True):
            continue
        filtered.append(check)
    return filtered


def _get_score_style(score: float) -> str:
    """Get Rich style color for audit score.

    Args:
        score: The audit score (0-100).

    Returns:
        Rich style string.
    """
    if score >= AUDIT_SCORE_GOOD:
        return "[green]"
    if score >= AUDIT_SCORE_WARNING:
        return "[yellow]"
    return "[red]"


def _display_vendor_checks(filtered_checks: list[dict[str, Any]], failed_only: bool) -> None:
    """Display filtered checks for a vendor.

    Args:
        filtered_checks: List of filtered check dictionaries.
        failed_only: Whether we're showing failed-only mode.
    """
    if not filtered_checks:
        if failed_only:
            console.print("  [green]✓ All checks passed[/green]")
        else:
            console.print("  [dim]No checks match the filter criteria[/dim]")
        return

    table = Table(show_header=True, header_style="bold", box=None, padding=(0, 1))
    table.add_column("Status", width=6)
    table.add_column("Severity", width=10)
    table.add_column("Category", width=10)
    table.add_column("Check", width=25)
    table.add_column("Message", width=40)

    for check in filtered_checks:
        status = "[green]✓[/green]" if check.get("passed") else "[red]✗[/red]"
        sev = _get_severity_style(check.get("severity", "info"))
        cat = _get_category_style(check.get("category", ""))
        name = check.get("name", "")[:25]
        message = check.get("message", "")[:40]

        table.add_row(status, sev, cat, name, message)

        if not check.get("passed") and check.get("recommendation"):
            console.print(f"      [dim]→ {check.get('recommendation')}[/dim]")

    console.print(table)


@app.command()
def audit(
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Audit specific vendor only"),
    ] = None,
    severity: Annotated[
        str | None,
        typer.Option(
            "--severity", "-s", help="Filter by minimum severity (info, warning, error, critical)"
        ),
    ] = None,
    category: Annotated[
        str | None,
        typer.Option(
            "--category", "-c", help="Filter by category (security, config, quality, usage)"
        ),
    ] = None,
    output_json: Annotated[
        bool,
        typer.Option("--json", help="Output results as JSON"),
    ] = False,
    failed_only: Annotated[
        bool,
        typer.Option("--failed", "-f", help="Show only failed checks"),
    ] = False,
) -> None:
    """Run security and configuration audits for AI assistants.

    Performs comprehensive audits including:
    - Security checks (permissions, API key exposure, sensitive files)
    - Configuration validity (JSON syntax, required files)
    - Quality assessment (documentation, completeness)
    - Usage patterns (file sizes, duplicates)

    Examples:
        ai-asst-mgr audit                        # Audit all vendors
        ai-asst-mgr audit --vendor claude        # Audit Claude only
        ai-asst-mgr audit --severity warning     # Show warnings and above
        ai-asst-mgr audit --category security    # Security checks only
        ai-asst-mgr audit --json                 # Output as JSON
        ai-asst-mgr audit --failed               # Show only failed checks
    """
    _validate_audit_filter(severity, VALID_SEVERITIES, "severity")
    _validate_audit_filter(category, VALID_CATEGORIES, "category")

    registry = VendorRegistry()
    vendors_to_audit = _get_vendors_to_audit(registry, vendor)

    all_reports = [
        _run_vendor_audit(vid, adapter.info.config_dir) for vid, adapter in vendors_to_audit.items()
    ]

    if output_json:
        console.print(json.dumps(all_reports, indent=2))
        return

    console.print(
        Panel.fit("[bold blue]AI Assistant Configuration Audit[/bold blue]", border_style="blue")
    )

    min_severity = SEVERITY_ORDER.get(severity.lower() if severity else "info", 0)
    total_passed, total_failed, has_critical = 0, 0, False

    for report in all_reports:
        summary = report.get("summary", {})
        total_passed += summary.get("passed", 0)
        total_failed += summary.get("failed", 0)
        has_critical = has_critical or summary.get("by_severity", {}).get("critical", 0) > 0

        score = summary.get("score", 0)
        score_style = _get_score_style(score)
        vid = report.get("vendor_id", "unknown")
        console.print(
            f"\n[bold cyan]{vid.capitalize()}[/bold cyan] - "
            f"Score: {score_style}{score:.1f}%[/{score_style.split('[')[1]}"
        )

        filtered = _filter_audit_checks(
            report.get("checks", []), min_severity, category, failed_only
        )
        _display_vendor_checks(filtered, failed_only)

    console.print(f"\n[bold]Summary:[/bold] {total_passed} passed, {total_failed} failed")

    if has_critical:
        console.print("[bold red]⚠ Critical issues found! Please address immediately.[/bold red]")
        raise typer.Exit(code=2)

    if total_failed > 0:
        raise typer.Exit(code=1)


# ============================================================================
# Agents Command
# ============================================================================

# Display constants for agent listing
DESCRIPTION_TRUNCATE_LENGTH = 40
CONTENT_PREVIEW_LINES = 20

agents_app = typer.Typer(help="Manage agents across AI assistant vendors")
app.add_typer(agents_app, name="agents")


def _get_agent_manager() -> UniversalAgentManager:
    """Get UniversalAgentManager instance.

    Returns:
        UniversalAgentManager instance with all vendors.
    """
    registry = VendorRegistry()
    return UniversalAgentManager(registry.get_all_vendors())


def _format_agent_type(agent_type: AgentType) -> str:
    """Format agent type for display.

    Args:
        agent_type: The agent type enum value.

    Returns:
        Formatted string with color.
    """
    type_styles = {
        AgentType.AGENT: "[cyan]agent[/cyan]",
        AgentType.SKILL: "[green]skill[/green]",
        AgentType.MCP_SERVER: "[yellow]mcp_server[/yellow]",
        AgentType.FUNCTION: "[blue]function[/blue]",
    }
    return type_styles.get(agent_type, str(agent_type.value))


@agents_app.command("list")
def agents_list(
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Filter by specific vendor"),
    ] = None,
    agent_type: Annotated[
        str | None,
        typer.Option("--type", "-t", help="Filter by type: agent, skill, mcp_server"),
    ] = None,
    search: Annotated[
        str | None,
        typer.Option("--search", "-s", help="Search query for name/description"),
    ] = None,
) -> None:
    """List agents across all AI assistant vendors.

    Displays a table of all agents, skills, MCP servers, and other capabilities
    found across Claude, Gemini, and OpenAI vendors.

    Examples:
        ai-asst-mgr agents list                    # List all agents
        ai-asst-mgr agents list --vendor claude    # List Claude agents only
        ai-asst-mgr agents list --type skill       # List skills only
        ai-asst-mgr agents list --search "code"    # Search for agents

    Args:
        vendor: Optional vendor ID to filter by.
        agent_type: Optional agent type to filter by.
        search: Optional search query.
    """
    manager = _get_agent_manager()

    # Parse agent type filter
    type_filter = None
    if agent_type:
        try:
            type_filter = AgentType(agent_type)
        except ValueError:
            valid_types = ", ".join(t.value for t in AgentType)
            console.print(f"[red]Error: Invalid agent type '{agent_type}'[/red]")
            console.print(f"[yellow]Valid types: {valid_types}[/yellow]")
            raise typer.Exit(code=1) from None

    # List agents
    result = manager.list_all_agents(
        vendor_filter=vendor,
        type_filter=type_filter,
        search_query=search,
    )

    if result.total_count == 0:
        console.print("[yellow]No agents found[/yellow]")
        if vendor or agent_type or search:
            console.print("[dim]Try removing filters to see all agents[/dim]")
        return

    # Create table
    table = Table(
        title="Agents Across Vendors",
        show_header=True,
        header_style="bold cyan",
    )
    table.add_column("Name", style="bold", width=25)
    table.add_column("Vendor", width=10)
    table.add_column("Type", width=12)
    table.add_column("Description", width=40)
    table.add_column("Size", width=10)

    for agent in result.agents:
        table.add_row(
            agent.name,
            agent.vendor_id.capitalize(),
            _format_agent_type(agent.agent_type),
            (
                agent.description[:DESCRIPTION_TRUNCATE_LENGTH] + "..."
                if len(agent.description) > DESCRIPTION_TRUNCATE_LENGTH
                else agent.description
            ),
            _format_size_bytes(agent.size_bytes),
        )

    console.print(table)

    # Summary
    console.print(f"\n[bold]Total:[/bold] {result.total_count} agent(s)")
    if result.by_vendor:
        vendor_summary = ", ".join(f"{v.capitalize()}: {c}" for v, c in result.by_vendor.items())
        console.print(f"[bold]By Vendor:[/bold] {vendor_summary}")
    if result.by_type:
        type_summary = ", ".join(f"{t}: {c}" for t, c in result.by_type.items())
        console.print(f"[bold]By Type:[/bold] {type_summary}")


@agents_app.command("show")
def agents_show(
    name: Annotated[str, typer.Argument(help="Name of the agent to show")],
    vendor: Annotated[
        str,
        typer.Option("--vendor", "-v", help="Vendor ID (claude, gemini, openai)"),
    ],
) -> None:
    """Show details of a specific agent.

    Displays detailed information about an agent including its content,
    file path, and metadata.

    Examples:
        ai-asst-mgr agents show code-review --vendor claude
        ai-asst-mgr agents show my-mcp-server -v gemini

    Args:
        name: Name of the agent.
        vendor: Vendor ID.
    """
    manager = _get_agent_manager()
    agent = manager.get_agent(name, vendor)

    if not agent:
        console.print(f"[red]Error: Agent '{name}' not found in {vendor}[/red]")
        raise typer.Exit(code=1)

    # Display agent details
    console.print(Panel.fit(f"[bold blue]{agent.name}[/bold blue]", border_style="blue"))

    details = Table.grid(padding=(0, 2))
    details.add_row("[bold]Vendor:[/bold]", agent.vendor_id.capitalize())
    details.add_row("[bold]Type:[/bold]", _format_agent_type(agent.agent_type))
    details.add_row("[bold]Description:[/bold]", agent.description or "[dim]None[/dim]")
    file_path_str = str(agent.file_path) if agent.file_path else "[dim]None[/dim]"
    details.add_row("[bold]File Path:[/bold]", file_path_str)
    details.add_row("[bold]Size:[/bold]", _format_size_bytes(agent.size_bytes))
    details.add_row("[bold]Created:[/bold]", agent.created_at.strftime("%Y-%m-%d %H:%M:%S"))
    details.add_row("[bold]Modified:[/bold]", agent.modified_at.strftime("%Y-%m-%d %H:%M:%S"))

    console.print(details)

    if agent.content:
        console.print("\n[bold]Content:[/bold]")
        content_lines = agent.content.split("\n")
        lines = content_lines[:CONTENT_PREVIEW_LINES]
        content_preview = "\n".join(lines)
        if len(content_lines) > CONTENT_PREVIEW_LINES:
            content_preview += "\n[dim]... (truncated)[/dim]"
        console.print(Panel(content_preview, border_style="dim"))


@agents_app.command("create")
def agents_create(
    name: Annotated[str, typer.Argument(help="Name of the agent to create")],
    vendor: Annotated[
        str,
        typer.Option("--vendor", "-v", help="Vendor ID (claude, gemini, openai)"),
    ],
    agent_type: Annotated[
        str,
        typer.Option("--type", "-t", help="Agent type: agent, skill, mcp_server"),
    ] = "agent",
    content: Annotated[
        str | None,
        typer.Option("--content", "-c", help="Content for the agent (or use --file)"),
    ] = None,
    file: Annotated[
        Path | None,
        typer.Option("--file", "-f", help="Read content from file"),
    ] = None,
    description: Annotated[
        str | None,
        typer.Option("--description", "-d", help="Description for the agent"),
    ] = None,
) -> None:
    """Create a new agent for a vendor.

    Creates a new agent, skill, or MCP server configuration for the
    specified vendor.

    Examples:
        ai-asst-mgr agents create my-agent -v claude -t agent -c "# My Agent"
        ai-asst-mgr agents create my-skill -v claude -t skill -f skill.md
        ai-asst-mgr agents create my-mcp -v gemini -t mcp_server -c '{"url":"..."}'

    Args:
        name: Name of the agent.
        vendor: Vendor ID.
        agent_type: Type of agent to create.
        content: Content for the agent.
        file: Path to file with content.
        description: Optional description.
    """
    # Parse agent type
    try:
        parsed_type = AgentType(agent_type)
    except ValueError:
        valid_types = ", ".join(t.value for t in AgentType)
        console.print(f"[red]Error: Invalid agent type '{agent_type}'[/red]")
        console.print(f"[yellow]Valid types: {valid_types}[/yellow]")
        raise typer.Exit(code=1) from None

    # Get content
    if file:
        if not file.exists():
            console.print(f"[red]Error: File not found: {file}[/red]")
            raise typer.Exit(code=1)
        agent_content = file.read_text(encoding="utf-8")
    elif content:
        agent_content = content
    elif parsed_type in (AgentType.AGENT, AgentType.SKILL):
        # Generate default markdown content
        agent_content = f"# {name}\n\n{description or 'Add description here.'}\n"
    else:
        # Generate default JSON content for MCP servers
        agent_content = f'{{"name": "{name}", "description": "{description or ""}"}}'

    manager = _get_agent_manager()

    def progress_callback(msg: str) -> None:
        console.print(f"  {msg}")

    result = manager.create_agent(
        name=name,
        vendor_id=vendor,
        agent_type=parsed_type,
        content=agent_content,
        progress_callback=progress_callback,
    )

    if result.success and result.agent:
        console.print(f"\n[green]✓ Created agent '{name}' for {vendor}[/green]")
        if result.agent.file_path:
            console.print(f"  Path: {result.agent.file_path}")
    else:
        console.print(f"\n[red]✗ Failed to create agent: {result.error}[/red]")
        raise typer.Exit(code=1)


@agents_app.command("delete")
def agents_delete(
    name: Annotated[str, typer.Argument(help="Name of the agent to delete")],
    vendor: Annotated[
        str,
        typer.Option("--vendor", "-v", help="Vendor ID (claude, gemini, openai)"),
    ],
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Delete an agent from a vendor.

    Removes an agent, skill, or MCP server configuration from the
    specified vendor.

    Examples:
        ai-asst-mgr agents delete old-agent -v claude
        ai-asst-mgr agents delete old-skill -v claude --force

    Args:
        name: Name of the agent to delete.
        vendor: Vendor ID.
        force: Skip confirmation prompt.
    """
    manager = _get_agent_manager()

    # Check if agent exists
    agent = manager.get_agent(name, vendor)
    if not agent:
        console.print(f"[red]Error: Agent '{name}' not found in {vendor}[/red]")
        raise typer.Exit(code=1)

    # Confirm deletion
    if not force:
        console.print("\n[yellow]About to delete:[/yellow]")
        console.print(f"  Name: {agent.name}")
        console.print(f"  Vendor: {agent.vendor_id}")
        console.print(f"  Type: {agent.agent_type.value}")
        if agent.file_path:
            console.print(f"  File: {agent.file_path}")

        confirm = typer.confirm("\nAre you sure you want to delete this agent?")
        if not confirm:
            console.print("[dim]Aborted[/dim]")
            return

    def progress_callback(msg: str) -> None:
        console.print(f"  {msg}")

    success, message = manager.delete_agent(name, vendor, progress_callback=progress_callback)

    if success:
        console.print(f"\n[green]✓ {message}[/green]")
    else:
        console.print(f"\n[red]✗ {message}[/red]")
        raise typer.Exit(code=1)


@agents_app.command("sync")
def agents_sync(
    name: Annotated[str, typer.Argument(help="Name of the agent to sync")],
    source: Annotated[
        str,
        typer.Option("--source", "-s", help="Source vendor ID"),
    ],
    target: Annotated[
        list[str] | None,
        typer.Option("--target", "-t", help="Target vendor ID(s) (repeatable)"),
    ] = None,
) -> None:
    """Sync an agent from one vendor to others.

    Copies an agent from a source vendor to one or more target vendors,
    converting the format as needed for compatibility.

    Examples:
        ai-asst-mgr agents sync my-agent --source claude --target gemini
        ai-asst-mgr agents sync my-agent -s claude -t gemini -t openai
        ai-asst-mgr agents sync my-agent -s claude  # Sync to all other vendors

    Args:
        name: Name of the agent to sync.
        source: Source vendor ID.
        target: Target vendor ID(s). If not specified, syncs to all others.
    """
    manager = _get_agent_manager()

    def progress_callback(msg: str) -> None:
        console.print(f"  {msg}")

    console.print(f"\n[bold]Syncing agent '{name}' from {source}...[/bold]")

    result = manager.sync_agent(
        agent_name=name,
        source_vendor=source,
        target_vendors=target,
        progress_callback=progress_callback,
    )

    if result.success:
        console.print(f"\n[green]✓ Synced to {result.synced_count} vendor(s)[/green]")
        if result.target_vendors:
            console.print(f"  Vendors: {', '.join(result.target_vendors)}")
    else:
        console.print("\n[red]✗ Sync failed[/red]")

    if result.errors:
        console.print("\n[yellow]Errors:[/yellow]")
        for error in result.errors:
            console.print(f"  • {error}")

    if not result.success:
        raise typer.Exit(code=1)


# ============================================================================
# Schedule Command
# ============================================================================

# Time validation constants
MAX_HOUR = 23
MAX_MINUTE = 59
MAX_DAY_OF_WEEK = 6
MIN_DAY_OF_MONTH = 1
MAX_DAY_OF_MONTH = 31

schedule_app = typer.Typer(help="Manage scheduled backup tasks")
app.add_typer(schedule_app, name="schedule")


def _get_interval_display(interval: IntervalType | None) -> str:
    """Get display string for interval type.

    Args:
        interval: IntervalType enum value.

    Returns:
        Formatted interval string.
    """
    if interval is None:
        return "[dim]Not set[/dim]"
    displays = {
        IntervalType.HOURLY: "[cyan]Hourly[/cyan]",
        IntervalType.DAILY: "[green]Daily[/green]",
        IntervalType.WEEKLY: "[blue]Weekly[/blue]",
        IntervalType.MONTHLY: "[magenta]Monthly[/magenta]",
    }
    return displays.get(interval, interval.value)


def _display_schedule_info(info: ScheduleInfo) -> None:
    """Display schedule information in a formatted table.

    Args:
        info: ScheduleInfo instance with schedule details.
    """
    table = Table(title="Schedule Details", show_header=False, box=None)
    table.add_column("Property", style="bold")
    table.add_column("Value")

    status = "[green]Active[/green]" if info.is_active else "[red]Inactive[/red]"
    table.add_row("Status", status)

    if info.interval:
        table.add_row("Interval", _get_interval_display(info.interval))

    if info.next_run:
        table.add_row("Next Run", info.next_run)

    if info.script_path:
        table.add_row("Script", str(info.script_path))

    if info.platform_details:
        for key, value in info.platform_details.items():
            table.add_row(key.replace("_", " ").title(), value)

    console.print(table)


@schedule_app.command("status")
def schedule_status() -> None:
    """Show the current backup schedule status.

    Displays whether a backup schedule is active and its configuration
    details for the current platform.

    Examples:
        ai-asst-mgr schedule status
    """
    try:
        scheduler = get_scheduler()
    except UnsupportedPlatformError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from None

    platform_info = get_platform_info()
    console.print(
        Panel.fit(
            f"[bold blue]Backup Schedule Status[/bold blue]\n"
            f"[dim]Platform: {scheduler.platform_name} ({platform_info['machine']})[/dim]",
            border_style="blue",
        )
    )

    info = scheduler.get_schedule_info()
    _display_schedule_info(info)


@schedule_app.command("setup")
def schedule_setup(
    script: Annotated[
        Path,
        typer.Argument(help="Path to the backup script to schedule"),
    ],
    interval: Annotated[
        str,
        typer.Option("--interval", "-i", help="Interval: hourly, daily, weekly, monthly"),
    ] = "daily",
    hour: Annotated[
        int,
        typer.Option("--hour", "-H", help="Hour to run (0-23)"),
    ] = 2,
    minute: Annotated[
        int,
        typer.Option("--minute", "-m", help="Minute to run (0-59)"),
    ] = 0,
    day_of_week: Annotated[
        int,
        typer.Option("--day-of-week", "-w", help="Day of week for weekly (0=Sunday)"),
    ] = 0,
    day_of_month: Annotated[
        int,
        typer.Option("--day-of-month", "-d", help="Day of month for monthly (1-31)"),
    ] = 1,
) -> None:
    """Set up a scheduled backup task.

    Creates a platform-specific scheduled task (LaunchAgent on macOS,
    cron on Linux) to run backups at the specified interval.

    Examples:
        ai-asst-mgr schedule setup ./backup.sh                  # Daily at 2 AM
        ai-asst-mgr schedule setup ./backup.sh -i hourly        # Every hour
        ai-asst-mgr schedule setup ./backup.sh -i weekly -w 0   # Sundays at 2 AM
        ai-asst-mgr schedule setup ./backup.sh -i daily -H 3    # Daily at 3 AM

    Args:
        script: Path to the backup script to schedule.
        interval: How often to run (hourly, daily, weekly, monthly).
        hour: Hour to run (0-23), default 2.
        minute: Minute to run (0-59), default 0.
        day_of_week: Day of week for weekly (0=Sunday), default 0.
        day_of_month: Day of month for monthly (1-31), default 1.
    """
    # Validate script exists
    if not script.exists():
        console.print(f"[red]Error: Script not found: {script}[/red]")
        raise typer.Exit(code=1)

    # Validate script is executable
    if not script.stat().st_mode & 0o111:
        console.print(f"[yellow]Warning: Script may not be executable: {script}[/yellow]")

    # Parse interval
    try:
        interval_type = IntervalType(interval.lower())
    except ValueError:
        valid = ", ".join(i.value for i in IntervalType)
        console.print(f"[red]Error: Invalid interval '{interval}'[/red]")
        console.print(f"[yellow]Valid intervals: {valid}[/yellow]")
        raise typer.Exit(code=1) from None

    # Validate time parameters
    if not (0 <= hour <= MAX_HOUR):
        console.print(f"[red]Error: Hour must be 0-{MAX_HOUR}, got {hour}[/red]")
        raise typer.Exit(code=1)
    if not (0 <= minute <= MAX_MINUTE):
        console.print(f"[red]Error: Minute must be 0-{MAX_MINUTE}, got {minute}[/red]")
        raise typer.Exit(code=1)
    if not (0 <= day_of_week <= MAX_DAY_OF_WEEK):
        console.print(
            f"[red]Error: Day of week must be 0-{MAX_DAY_OF_WEEK}, got {day_of_week}[/red]"
        )
        raise typer.Exit(code=1)
    if not (MIN_DAY_OF_MONTH <= day_of_month <= MAX_DAY_OF_MONTH):
        console.print(
            f"[red]Error: Day of month must be {MIN_DAY_OF_MONTH}-{MAX_DAY_OF_MONTH}, "
            f"got {day_of_month}[/red]"
        )
        raise typer.Exit(code=1)

    try:
        scheduler = get_scheduler()
    except UnsupportedPlatformError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from None

    console.print(
        Panel.fit(
            f"[bold blue]Setting Up Backup Schedule[/bold blue]\n"
            f"[dim]Platform: {scheduler.platform_name}[/dim]",
            border_style="blue",
        )
    )

    script_path = script.resolve()
    console.print(f"  Script: {script_path}")
    console.print(f"  Interval: {interval_type.description}")

    success = scheduler.setup_schedule(
        script_path=script_path,
        interval=interval_type,
        hour=hour,
        minute=minute,
        day_of_week=day_of_week,
        day_of_month=day_of_month,
    )

    if success:
        console.print("\n[green]✓ Backup schedule created successfully[/green]")
        info = scheduler.get_schedule_info()
        if info.next_run:
            console.print(f"  Next run: {info.next_run}")
    else:
        console.print("\n[red]✗ Failed to create backup schedule[/red]")
        raise typer.Exit(code=1)


@schedule_app.command("remove")
def schedule_remove(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Skip confirmation prompt"),
    ] = False,
) -> None:
    """Remove the backup schedule.

    Removes the platform-specific scheduled task (LaunchAgent on macOS,
    cron on Linux).

    Examples:
        ai-asst-mgr schedule remove          # With confirmation
        ai-asst-mgr schedule remove --force  # Skip confirmation

    Args:
        force: Skip confirmation prompt.
    """
    try:
        scheduler = get_scheduler()
    except UnsupportedPlatformError as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(code=1) from None

    if not scheduler.is_scheduled():
        console.print("[yellow]No backup schedule is currently active[/yellow]")
        return

    info = scheduler.get_schedule_info()

    if not force:
        console.print("\n[yellow]About to remove schedule:[/yellow]")
        _display_schedule_info(info)
        confirm = typer.confirm("\nAre you sure you want to remove this schedule?")
        if not confirm:
            console.print("[dim]Aborted[/dim]")
            return

    success = scheduler.remove_schedule()

    if success:
        console.print("\n[green]✓ Backup schedule removed successfully[/green]")
    else:
        console.print("\n[red]✗ Failed to remove backup schedule[/red]")
        raise typer.Exit(code=1)


# =============================================================================
# Database Management Commands
# =============================================================================

db_app = typer.Typer(help="Manage the session tracking database")
app.add_typer(db_app, name="db")

DEFAULT_DB_PATH = Path.home() / "Data" / "claude-sessions" / "sessions.db"


@db_app.command("init")
def db_init(
    force: Annotated[
        bool,
        typer.Option("--force", "-f", help="Overwrite existing database"),
    ] = False,
) -> None:
    """Initialize a fresh session tracking database.

    Creates a new SQLite database with the full schema for tracking
    Claude Code sessions, events, and analytics.

    Examples:
        ai-asst-mgr db init           # Initialize database
        ai-asst-mgr db init --force   # Overwrite existing database
    """
    if DEFAULT_DB_PATH.exists() and not force:
        console.print(
            f"[yellow]Database already exists at {DEFAULT_DB_PATH}[/yellow]\n"
            "Use --force to overwrite."
        )
        raise typer.Exit(1)

    # Ensure parent directory exists
    DEFAULT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    # Delete existing if force
    if DEFAULT_DB_PATH.exists():
        DEFAULT_DB_PATH.unlink()
        console.print("[dim]Deleted existing database[/dim]")

    # Initialize new database
    db = DatabaseManager(DEFAULT_DB_PATH)
    db.initialize()

    console.print(
        Panel.fit(
            f"[bold green]Database initialized successfully![/bold green]\n\n"
            f"Location: [cyan]{DEFAULT_DB_PATH}[/cyan]\n\n"
            "Run [bold]ai-asst-mgr db sync[/bold] to import Claude history.",
            title="Database Ready",
            border_style="green",
        )
    )


@db_app.command("sync")
def db_sync(
    full: Annotated[
        bool,
        typer.Option("--full", "-f", help="Full sync (ignore last sync state)"),
    ] = False,
) -> None:
    """Sync Claude Code history to the database.

    Imports session data from ~/.claude/history.jsonl into the database.
    By default, only imports entries since the last sync.

    Examples:
        ai-asst-mgr db sync         # Sync new entries only
        ai-asst-mgr db sync --full  # Full sync (re-import all)
    """
    if not DEFAULT_DB_PATH.exists():
        console.print("[red]Database not found![/red]\nRun [bold]ai-asst-mgr db init[/bold] first.")
        raise typer.Exit(1)

    db = DatabaseManager(DEFAULT_DB_PATH)

    console.print("[dim]Syncing Claude history to database...[/dim]")
    result = sync_history_to_db(db, full_sync=full)

    if result.errors:
        console.print(f"[yellow]Completed with {len(result.errors)} errors[/yellow]")
        for error in result.errors[:5]:
            console.print(f"  [red]• {error}[/red]")
    else:
        console.print(
            Panel.fit(
                f"[bold green]Sync completed![/bold green]\n\n"
                f"Sessions imported: [cyan]{result.sessions_imported}[/cyan]\n"
                f"Messages imported: [cyan]{result.messages_imported}[/cyan]\n"
                f"Sessions skipped:  [dim]{result.sessions_skipped}[/dim]",
                title="Sync Results",
                border_style="green",
            )
        )


@db_app.command("status")
def db_status() -> None:
    """Show database sync status and statistics.

    Displays information about the database, last sync time,
    and record counts.

    Examples:
        ai-asst-mgr db status
    """
    if not DEFAULT_DB_PATH.exists():
        console.print("[red]Database not found![/red]\nRun [bold]ai-asst-mgr db init[/bold] first.")
        raise typer.Exit(1)

    db = DatabaseManager(DEFAULT_DB_PATH)
    status = get_sync_status(db)

    table = Table(title="Database Status", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Database Path", str(DEFAULT_DB_PATH))
    table.add_row("Sessions in DB", str(status["database_sessions"]))
    table.add_row("Events in DB", str(status["database_events"]))
    table.add_row("History File", status["history_file_path"])
    table.add_row("History Entries", str(status["history_file_entries"]))
    table.add_row(
        "Last Synced",
        status["last_synced_datetime"] or "[dim]Never[/dim]",
    )

    console.print(table)


# =============================================================================
# GitHub Activity Tracking Commands
# =============================================================================

github_app = typer.Typer(help="GitHub activity tracking and AI vendor attribution")
app.add_typer(github_app, name="github")

# Display truncation constants
_COMMIT_MSG_MAX_LEN = 42
_REPO_NAME_MAX_LEN = 18
_REPO_LIST_MAX_LEN = 28


def _resolve_github_repos(
    repo: Path | None,
    base_path: Path | None,
) -> list[Path]:
    """Resolve which repositories to scan for GitHub sync."""
    if repo:
        if not repo.exists():
            console.print(f"[red]Repository not found: {repo}[/red]")
            raise typer.Exit(1)
        return [repo]

    if base_path:
        if not base_path.exists():
            console.print(f"[red]Path not found: {base_path}[/red]")
            raise typer.Exit(1)
        console.print(f"[dim]Searching for git repositories in {base_path}...[/dim]")
        repos = find_git_repos(base_path)
        if not repos:
            console.print("[yellow]No git repositories found[/yellow]")
            raise typer.Exit(0)
        console.print(f"[dim]Found {len(repos)} repositories[/dim]")
        return repos

    return [Path.cwd()]


@github_app.command("sync")
def github_sync(
    repo: Annotated[
        Path | None,
        typer.Option("--repo", "-r", help="Path to a specific git repository"),
    ] = None,
    base_path: Annotated[
        Path | None,
        typer.Option("--base", "-b", help="Base path to search for git repositories"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-n", help="Maximum commits per repository"),
    ] = 100,
) -> None:
    """Sync GitHub commits and detect AI vendor attribution.

    Parses git repositories to find commits and detect AI-generated code
    based on commit message signatures (Claude, Gemini, OpenAI).

    Examples:
        ai-asst-mgr github sync                           # Scan current directory
        ai-asst-mgr github sync --repo /path/to/project   # Specific repo
        ai-asst-mgr github sync --base ~/Developer        # Scan directory for repos
    """
    if not DEFAULT_DB_PATH.exists():
        console.print("[red]Database not found![/red]\nRun [bold]ai-asst-mgr db init[/bold] first.")
        raise typer.Exit(1)

    db = DatabaseManager(DEFAULT_DB_PATH)
    parser = GitLogParser()
    repos = _resolve_github_repos(repo, base_path)

    # Sync each repository
    total_commits = 0
    ai_commits = 0
    errors: list[str] = []

    for repo_path in repos:
        try:
            commits = parser.parse_repo(repo_path, limit=limit)
            for commit in commits:
                if db.record_github_commit(commit):
                    total_commits += 1
                    if commit.vendor_id:
                        ai_commits += 1
        except (ValueError, OSError) as e:
            errors.append(f"{repo_path.name}: {e}")

    # Display results
    if errors:
        console.print(f"[yellow]Completed with {len(errors)} errors[/yellow]")
        for error in errors[:5]:
            console.print(f"  [red]• {error}[/red]")
    else:
        console.print(
            Panel.fit(
                f"[bold green]GitHub sync completed![/bold green]\n\n"
                f"Commits synced: [cyan]{total_commits}[/cyan]\n"
                f"AI-attributed:  [cyan]{ai_commits}[/cyan]\n"
                f"Repositories:   [cyan]{len(repos)}[/cyan]",
                title="Sync Results",
                border_style="green",
            )
        )


@github_app.command("stats")
def github_stats() -> None:
    """Show GitHub contribution statistics by AI vendor.

    Displays a summary of commits tracked in the database,
    broken down by AI vendor attribution.

    Examples:
        ai-asst-mgr github stats
    """
    if not DEFAULT_DB_PATH.exists():
        console.print("[red]Database not found![/red]\nRun [bold]ai-asst-mgr db init[/bold] first.")
        raise typer.Exit(1)

    db = DatabaseManager(DEFAULT_DB_PATH)
    stats = db.get_github_stats()

    if stats.total_commits == 0:
        console.print("[yellow]No commits tracked yet.[/yellow]")
        console.print("Run [bold]ai-asst-mgr github sync[/bold] to import commits.")
        raise typer.Exit(0)

    # Create stats table
    table = Table(title="GitHub Activity Statistics", show_header=False)
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="white")

    table.add_row("Total Commits", str(stats.total_commits))
    table.add_row("Repositories", str(stats.repos_tracked))
    table.add_row("", "")  # Spacer
    table.add_row("[bold]AI Attribution[/bold]", "")

    # Format vendor rows with percentages
    def _fmt_vendor(count: int, total: int) -> str:
        if total == 0:
            return "0"
        pct = count / total * 100
        return f"{count} ({pct:.1f}%)"

    table.add_row("  Claude", _fmt_vendor(stats.claude_commits, stats.total_commits))
    table.add_row("  Gemini", _fmt_vendor(stats.gemini_commits, stats.total_commits))
    table.add_row("  OpenAI", _fmt_vendor(stats.openai_commits, stats.total_commits))
    table.add_row("", "")  # Spacer
    table.add_row(
        "[bold]AI Total[/bold]",
        f"[green]{stats.ai_attributed_commits}[/green] ({stats.ai_percentage:.1f}%)",
    )

    if stats.first_commit:
        table.add_row("", "")  # Spacer
        table.add_row("First Commit", stats.first_commit[:19])
        table.add_row("Last Commit", stats.last_commit[:19] if stats.last_commit else "N/A")

    console.print(table)


@github_app.command("list")
def github_list(
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Filter by vendor (claude, gemini, openai, none)"),
    ] = None,
    repo_filter: Annotated[
        str | None,
        typer.Option("--repo", "-r", help="Filter by repository name"),
    ] = None,
    limit_count: Annotated[
        int,
        typer.Option("--limit", "-n", help="Number of commits to show"),
    ] = 20,
) -> None:
    """List recent GitHub commits with vendor attribution.

    Displays commits from the database with optional filtering
    by vendor or repository.

    Examples:
        ai-asst-mgr github list                    # Recent 20 commits
        ai-asst-mgr github list --vendor claude    # Claude-attributed only
        ai-asst-mgr github list --vendor none      # Non-AI commits
        ai-asst-mgr github list -n 50              # Show 50 commits
    """
    if not DEFAULT_DB_PATH.exists():
        console.print("[red]Database not found![/red]\nRun [bold]ai-asst-mgr db init[/bold] first.")
        raise typer.Exit(1)

    db = DatabaseManager(DEFAULT_DB_PATH)
    commits = db.get_github_commits(vendor_id=vendor, repo=repo_filter, limit=limit_count)

    if not commits:
        console.print("[yellow]No commits found matching filters.[/yellow]")
        raise typer.Exit(0)

    # Create commits table
    table = Table(title=f"GitHub Commits (showing {len(commits)})", show_header=True)
    table.add_column("SHA", style="cyan", width=7)
    table.add_column("Repo", style="dim", width=20)
    table.add_column("Message", width=45)
    table.add_column("Vendor", width=8)
    table.add_column("Date", style="dim", width=16)

    for commit in commits:
        # Format vendor badge
        if commit.vendor_id == "claude":
            vendor_badge = "[magenta]Claude[/magenta]"
        elif commit.vendor_id == "gemini":
            vendor_badge = "[blue]Gemini[/blue]"
        elif commit.vendor_id == "openai":
            vendor_badge = "[green]OpenAI[/green]"
        else:
            vendor_badge = "[dim]-[/dim]"

        # Truncate message to first line
        first_line = commit.message.split("\n")[0]
        message = first_line[:_COMMIT_MSG_MAX_LEN]
        if len(first_line) > _COMMIT_MSG_MAX_LEN:
            message += "..."

        # Truncate repo name
        repo_display = commit.repo[:_REPO_NAME_MAX_LEN]
        if len(commit.repo) > _REPO_NAME_MAX_LEN:
            repo_display += "..."

        table.add_row(
            commit.sha[:7],
            repo_display,
            message,
            vendor_badge,
            commit.committed_at[:16],
        )

    console.print(table)


@github_app.command("repos")
def github_repos() -> None:
    """List tracked repositories with commit counts.

    Shows all repositories that have been synced to the database
    with their commit counts and AI attribution statistics.

    Examples:
        ai-asst-mgr github repos
    """
    if not DEFAULT_DB_PATH.exists():
        console.print("[red]Database not found![/red]\nRun [bold]ai-asst-mgr db init[/bold] first.")
        raise typer.Exit(1)

    db = DatabaseManager(DEFAULT_DB_PATH)
    repos = db.get_github_repo_stats()

    if not repos:
        console.print("[yellow]No repositories tracked yet.[/yellow]")
        console.print("Run [bold]ai-asst-mgr github sync[/bold] to import commits.")
        raise typer.Exit(0)

    table = Table(title="Tracked Repositories", show_header=True)
    table.add_column("Repository", style="cyan", width=30)
    table.add_column("Total", justify="right", width=8)
    table.add_column("AI", justify="right", width=8)
    table.add_column("AI %", justify="right", width=8)
    table.add_column("Last Commit", style="dim", width=16)

    for repo_info in repos:
        total = int(repo_info["total_commits"] or 0)
        ai_count = int(repo_info["ai_commits"] or 0)
        ai_pct = (ai_count / total * 100) if total > 0 else 0

        # Truncate repo name
        repo_name = str(repo_info["repo"])
        repo_display = repo_name[:_REPO_LIST_MAX_LEN]
        if len(repo_name) > _REPO_LIST_MAX_LEN:
            repo_display += "..."

        last_commit = repo_info["last_commit"]
        last_commit_str = str(last_commit)[:16] if last_commit else "N/A"

        table.add_row(
            repo_display,
            str(total),
            str(ai_count),
            f"{ai_pct:.1f}%",
            last_commit_str,
        )

    console.print(table)


@github_app.command("attribution")
def github_attribution(
    repo: Annotated[
        str | None,
        typer.Argument(help="Repository (owner/repo format)"),
    ] = None,
    pr: Annotated[
        int | None,
        typer.Option("--pr", "-p", help="PR number to analyze"),
    ] = None,
    issue: Annotated[
        int | None,
        typer.Option("--issue", "-i", help="Issue number to analyze"),
    ] = None,
    summary: Annotated[
        bool,
        typer.Option("--summary", "-s", help="Show summary by vendor"),
    ] = False,
) -> None:
    """Show AI vendor attribution for repository resources.

    Analyzes commits, PRs, and issues to identify AI-generated content
    and attribute it to specific AI vendors (Claude, Gemini, OpenAI).

    Examples:
        ai-asst-mgr github attribution owner/repo
        ai-asst-mgr github attribution owner/repo --pr 123
        ai-asst-mgr github attribution owner/repo --summary
    """
    if not DEFAULT_DB_PATH.exists():
        console.print("[red]Database not found![/red]\nRun [bold]ai-asst-mgr db init[/bold] first.")
        raise typer.Exit(1)

    # Determine repository to query
    if repo:
        repo_name = repo
    else:
        # Try to get repo from current directory
        parser = GitLogParser()
        try:
            repo_path = Path.cwd()
            repo_name = parser._get_repo_name(repo_path)
        except Exception:
            console.print("[red]Not in a git repo. Specify repository: owner/repo[/red]")
            raise typer.Exit(1) from None

    db = DatabaseManager(DEFAULT_DB_PATH)

    # Query commits for this repository
    commits = db.get_github_commits(repo=repo_name, limit=1000)

    if not commits:
        console.print(f"[yellow]No commits found for repository: {repo_name}[/yellow]")
        console.print("Run [bold]ai-asst-mgr github sync[/bold] to import commits.")
        raise typer.Exit(0)

    # Filter by PR or issue if specified
    if pr is not None:
        # Filter commits that mention the PR number
        pr_pattern = f"#{pr}"
        commits = [c for c in commits if pr_pattern in c.message or f"PR {pr}" in c.message]
        if not commits:
            console.print(f"[yellow]No commits found for PR #{pr} in {repo_name}[/yellow]")
            raise typer.Exit(0)

    if issue is not None:
        # Filter commits that mention the issue number
        issue_pattern = f"#{issue}"
        commits = [
            c for c in commits if issue_pattern in c.message or f"Issue {issue}" in c.message
        ]
        if not commits:
            console.print(f"[yellow]No commits found for issue #{issue} in {repo_name}[/yellow]")
            raise typer.Exit(0)

    # Show summary or detailed list
    if summary:
        # Calculate vendor breakdown
        total = len(commits)
        vendor_counts: dict[str, int] = {}
        for commit in commits:
            if commit.vendor_id:
                vendor_counts[commit.vendor_id] = vendor_counts.get(commit.vendor_id, 0) + 1
            else:
                vendor_counts["manual"] = vendor_counts.get("manual", 0) + 1

        # Create summary table
        table = Table(title=f"Attribution Summary: {repo_name}", show_header=True)
        table.add_column("Vendor", style="cyan", width=15)
        table.add_column("Commits", justify="right", width=10)
        table.add_column("Percentage", justify="right", width=12)

        # Sort by count descending
        for vendor, count in sorted(vendor_counts.items(), key=lambda x: x[1], reverse=True):
            pct = count / total * 100
            if vendor == "claude":
                vendor_display = "[magenta]Claude[/magenta]"
            elif vendor == "gemini":
                vendor_display = "[blue]Gemini[/blue]"
            elif vendor == "openai":
                vendor_display = "[green]OpenAI[/green]"
            else:
                vendor_display = "[dim]Manual[/dim]"

            table.add_row(vendor_display, str(count), f"{pct:.1f}%")

        # Add total row
        table.add_row("[bold]Total[/bold]", f"[bold]{total}[/bold]", "[bold]100.0%[/bold]")
        console.print(table)
    else:
        # Show detailed commit list
        title = f"Commits: {repo_name}"
        if pr is not None:
            title += f" (PR #{pr})"
        if issue is not None:
            title += f" (Issue #{issue})"

        table = Table(title=title, show_header=True)
        table.add_column("SHA", style="cyan", width=7)
        table.add_column("Message", width=50)
        table.add_column("Vendor", width=10)
        table.add_column("Date", style="dim", width=16)

        for commit in commits[:50]:  # Limit to 50 for display
            # Format vendor badge
            if commit.vendor_id == "claude":
                vendor_badge = "[magenta]Claude[/magenta]"
            elif commit.vendor_id == "gemini":
                vendor_badge = "[blue]Gemini[/blue]"
            elif commit.vendor_id == "openai":
                vendor_badge = "[green]OpenAI[/green]"
            else:
                vendor_badge = "[dim]Manual[/dim]"

            # Truncate message to first line
            first_line = commit.message.split("\n")[0]
            message = first_line[:48]
            if len(first_line) > 48:
                message += "..."

            table.add_row(
                commit.sha[:7],
                message,
                vendor_badge,
                commit.committed_at[:16],
            )

        console.print(table)
        if len(commits) > 50:
            console.print(f"[dim]Showing 50 of {len(commits)} commits. Use --summary.[/dim]")


@github_app.command("activity")
def github_activity(
    session: Annotated[
        str | None,
        typer.Option("--session", "-s", help="Filter by session ID"),
    ] = None,
    vendor: Annotated[
        str | None,
        typer.Option("--vendor", "-v", help="Filter by vendor"),
    ] = None,
    limit: Annotated[
        int,
        typer.Option("--limit", "-l", help="Maximum activities to show"),
    ] = 50,
) -> None:
    """Show GitHub activity log.

    Lists GitHub operations performed during AI assistant sessions,
    including PR creation, issue creation, comments, and commits.

    Examples:
        ai-asst-mgr github activity
        ai-asst-mgr github activity --session abc123
        ai-asst-mgr github activity --vendor claude --limit 20
    """
    if not DEFAULT_DB_PATH.exists():
        console.print("[red]Database not found![/red]\nRun [bold]ai-asst-mgr db init[/bold] first.")
        raise typer.Exit(1)

    db = DatabaseManager(DEFAULT_DB_PATH)

    # Build query
    query = "SELECT * FROM github_activity WHERE 1=1"
    params: list[Any] = []

    if session:
        query += " AND session_id = ?"
        params.append(session)

    if vendor:
        query += " AND vendor_id = ?"
        params.append(vendor)

    query += " ORDER BY timestamp DESC LIMIT ?"
    params.append(limit)

    # Execute query
    try:
        with db._connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
    except Exception as e:
        console.print(f"[red]Error querying github_activity: {e}[/red]")
        console.print("[yellow]The github_activity table may not exist yet.[/yellow]")
        raise typer.Exit(1) from None

    if not rows:
        console.print("[yellow]No GitHub activity found matching filters.[/yellow]")
        if not session and not vendor:
            console.print(
                "[dim]This table tracks GitHub operations during AI assistant sessions.[/dim]"
            )
        raise typer.Exit(0)

    # Create activity table
    table = Table(title=f"GitHub Activity (showing {len(rows)})", show_header=True)
    table.add_column("Time", style="dim", width=16)
    table.add_column("Vendor", width=10)
    table.add_column("Operation", width=15)
    table.add_column("Repository", width=25)
    table.add_column("Resource", width=12)
    table.add_column("Session", style="dim", width=12)

    for row in rows:
        # Format vendor badge
        vendor_id = row["vendor_id"]
        if vendor_id == "claude":
            vendor_badge = "[magenta]Claude[/magenta]"
        elif vendor_id == "gemini":
            vendor_badge = "[blue]Gemini[/blue]"
        elif vendor_id == "openai":
            vendor_badge = "[green]OpenAI[/green]"
        else:
            vendor_badge = str(vendor_id)

        # Format operation type with color
        op_type = row["operation_type"]
        if op_type in ("pr_created", "issue_created"):
            op_display = f"[green]{op_type}[/green]"
        elif op_type in ("comment_added", "commit_pushed"):
            op_display = f"[cyan]{op_type}[/cyan]"
        else:
            op_display = op_type

        # Format repository
        repo_owner = row["repo_owner"]
        repo_name = row["repo_name"]
        repo_full = f"{repo_owner}/{repo_name}"
        if len(repo_full) > 23:
            repo_full = repo_full[:20] + "..."

        # Format resource
        resource_id = row["resource_id"]
        resource_display = f"#{resource_id}" if resource_id else "-"

        # Format session ID
        session_id = row["session_id"]
        session_display = session_id[:10] if session_id else "-"

        # Format timestamp
        timestamp = row["timestamp"]
        time_display = timestamp[:16] if timestamp else "-"

        table.add_row(
            time_display,
            vendor_badge,
            op_display,
            repo_full,
            resource_display,
            session_display,
        )

    console.print(table)


# =============================================================================
# Web Dashboard Command
# =============================================================================


@app.command()
def serve(
    host: Annotated[
        str,
        typer.Option("--host", "-h", help="Host to bind to"),
    ] = "127.0.0.1",
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port to bind to"),
    ] = 8080,
    reload: Annotated[
        bool,
        typer.Option("--reload", "-r", help="Enable auto-reload for development"),
    ] = False,
) -> None:
    """Start the web dashboard server.

    Starts a FastAPI server that provides a web interface for viewing
    AI assistant statistics, coaching insights, and agent management.

    Examples:
        ai-asst-mgr serve                    # Start on localhost:8080
        ai-asst-mgr serve --port 3000        # Use custom port
        ai-asst-mgr serve --host 0.0.0.0     # Bind to all interfaces
        ai-asst-mgr serve --reload           # Enable auto-reload

    Args:
        host: Host address to bind to.
        port: Port number to bind to.
        reload: Enable auto-reload for development.
    """
    console.print(
        Panel.fit(
            f"[bold blue]AI Assistant Manager - Web Dashboard[/bold blue]\n\n"
            f"Starting server at [green]http://{host}:{port}[/green]\n\n"
            f"Press [bold]Ctrl+C[/bold] to stop",
            border_style="blue",
        )
    )

    try:
        uvicorn.run(
            "ai_asst_mgr.web:create_app",
            host=host,
            port=port,
            reload=reload,
            factory=True,
            log_level="info",
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Server stopped[/yellow]")


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
