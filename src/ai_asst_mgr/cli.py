"""Command-line interface for AI Assistant Manager.

This module provides the main CLI entry point using Typer for command execution.
"""

from __future__ import annotations

from typing import Annotated

import typer
from rich.console import Console
from rich.table import Table

from ai_asst_mgr.adapters.base import VendorStatus
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


def main() -> None:
    """Entry point for the CLI application."""
    app()


if __name__ == "__main__":
    main()
