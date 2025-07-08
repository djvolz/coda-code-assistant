#!/usr/bin/env python3
"""Setup script to configure OCI compartment ID for Coda."""

import os
import subprocess
import sys
from pathlib import Path

from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

try:
    import tomlkit
except ImportError:
    print("Error: tomlkit not installed. Run: uv sync")
    sys.exit(1)

# Add parent dir to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coda.themes import get_themed_console

console = get_themed_console()


def get_compartments():
    """Get list of compartments using OCI CLI."""
    try:
        # Run OCI CLI command
        result = subprocess.run(
            ["oci", "iam", "compartment", "list", "--all", "--compartment-id-in-subtree", "true"],
            capture_output=True,
            text=True,
            check=True,
        )

        import json

        data = json.loads(result.stdout)
        compartments = data.get("data", [])

        # Filter active compartments
        active_compartments = [c for c in compartments if c.get("lifecycle-state") == "ACTIVE"]

        return active_compartments

    except subprocess.CalledProcessError as e:
        console.print(f"[red]Error running OCI CLI:[/red] {e}")
        console.print("\nMake sure you have OCI CLI installed and configured.")
        console.print(
            "Install: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm"
        )
        return None
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        return None


def update_config_file(compartment_id: str):
    """Update Coda config file with compartment ID."""
    config_path = Path.home() / ".config" / "coda" / "config.toml"

    # Read existing config
    with open(config_path) as f:
        config = tomlkit.load(f)

    # Update compartment ID
    if "providers" not in config:
        config["providers"] = {}
    if "oci_genai" not in config["providers"]:
        config["providers"]["oci_genai"] = {}

    config["providers"]["oci_genai"]["compartment_id"] = compartment_id

    # Write back
    with open(config_path, "w") as f:
        tomlkit.dump(config, f)

    console.print(f"[green]✓[/green] Updated {config_path}")


def update_shell_config(compartment_id: str):
    """Add OCI_COMPARTMENT_ID to shell configuration."""
    shell = os.environ.get("SHELL", "/bin/bash")

    if "zsh" in shell:
        config_file = Path.home() / ".zshrc"
    else:
        config_file = Path.home() / ".bashrc"

    # Check if already set
    if config_file.exists():
        content = config_file.read_text()
        if "OCI_COMPARTMENT_ID" in content:
            console.print(f"[yellow]![/yellow] OCI_COMPARTMENT_ID already set in {config_file}")
            return

    # Add export
    export_line = f'\n# Coda OCI configuration\nexport OCI_COMPARTMENT_ID="{compartment_id}"\n'

    with open(config_file, "a") as f:
        f.write(export_line)

    console.print(f"[green]✓[/green] Added OCI_COMPARTMENT_ID to {config_file}")
    console.print(
        f"[yellow]![/yellow] Run 'source {config_file}' to apply changes to current shell"
    )


def main():
    """Main setup function."""
    console.print(
        Panel.fit(
            "[bold cyan]Coda OCI Setup[/bold cyan]\nConfigure Oracle Cloud Infrastructure for Coda",
            border_style="cyan",
        )
    )

    # Check for existing compartment ID
    current_id = os.environ.get("OCI_COMPARTMENT_ID")
    if current_id:
        console.print(f"\n[green]Current compartment ID:[/green] {current_id}")
        if not Prompt.ask("Change compartment ID?", choices=["y", "n"], default="n") == "y":
            return

    # Get compartments
    console.print("\n[yellow]Fetching OCI compartments...[/yellow]")
    compartments = get_compartments()

    if not compartments:
        # Manual entry
        console.print("\n[yellow]Unable to fetch compartments automatically.[/yellow]")
        compartment_id = Prompt.ask("Enter your OCI compartment ID (ocid1.compartment...)")
    else:
        # Show table
        table = Table(title="Available Compartments")
        table.add_column("#", style="cyan", width=3)
        table.add_column("Name", style="green")
        table.add_column("Description", style="yellow")
        table.add_column("ID", style="dim", overflow="fold")

        for i, comp in enumerate(compartments, 1):
            table.add_row(
                str(i), comp.get("name", ""), comp.get("description", "")[:50], comp.get("id", "")
            )

        console.print(table)

        # Select compartment
        choice = Prompt.ask(
            "\nSelect compartment number", choices=[str(i) for i in range(1, len(compartments) + 1)]
        )

        compartment_id = compartments[int(choice) - 1]["id"]

    # Update configurations
    console.print(f"\n[green]Selected compartment:[/green] {compartment_id}")

    # Update Coda config
    update_config_file(compartment_id)

    # Ask about shell config
    if Prompt.ask("\nAdd to shell configuration?", choices=["y", "n"], default="y") == "y":
        update_shell_config(compartment_id)

    # Set for current session
    os.environ["OCI_COMPARTMENT_ID"] = compartment_id

    console.print("\n[bold green]✨ OCI setup complete![/bold green]")
    console.print("\nYou can now use: ./demo_oci.py or uv run coda")


if __name__ == "__main__":
    main()
