"""Command-line interface for AI Assistant Manager.

This module provides the main CLI entry point using Typer for command execution.
"""

from __future__ import annotations

import json
import platform
import shutil
import sys
from pathlib import Path
from typing import Annotated, Any

import typer
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from ai_asst_mgr.adapters.base import VendorAdapter, VendorStatus
from ai_asst_mgr.vendors import VendorRegistry

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
        _config_set_value(vendors_to_use, key, value, vendor)
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
    vendor_name: str | None,  # noqa: ARG001
) -> None:
    """Set a configuration value.

    Args:
        vendors: Dictionary of vendor name to adapter mappings.
        key: Configuration key to set.
        value: Value to set.
        vendor_name: Optional vendor name (if specified, only set for that vendor).
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


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
