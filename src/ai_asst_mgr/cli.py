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
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ai_asst_mgr.adapters.base import VendorStatus
from ai_asst_mgr.capabilities import AgentType, UniversalAgentManager
from ai_asst_mgr.coaches import ClaudeCoach, CodexCoach, GeminiCoach, Priority
from ai_asst_mgr.operations import (
    BackupManager,
    MergeStrategy,
    RestoreManager,
    SyncManager,
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
def sync(  # noqa: PLR0913 - Typer CLI requires individual parameters for proper flag generation
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


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
