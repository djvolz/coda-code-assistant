#!/usr/bin/env python3
"""Script to show all available OCI GenAI models with dynamic discovery."""

import os
import sys

from rich.panel import Panel
from rich.table import Table

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coda.base.providers import OCIGenAIProvider
from coda.themes import get_themed_console

console = get_themed_console()


def main():
    """Show all available OCI GenAI models."""
    console.print(
        Panel.fit(
            "[bold cyan]OCI GenAI Available Models[/bold cyan]\n"
            "Dynamically discovered from Oracle Cloud Infrastructure",
            border_style="cyan",
        )
    )

    if not os.getenv("OCI_COMPARTMENT_ID"):
        console.print("\n[red]Error:[/red] OCI_COMPARTMENT_ID not set")
        console.print("Please run: export OCI_COMPARTMENT_ID='your-compartment-id'")
        return

    try:
        # Initialize provider
        console.print("\n[yellow]Discovering models from OCI GenAI service...[/yellow]")
        provider = OCIGenAIProvider()

        # Get models
        models = provider.list_models()
        console.print(f"[green]✓ Found {len(models)} models[/green]")

        # Group models by provider
        providers = {}
        for model in models:
            if model.provider not in providers:
                providers[model.provider] = []
            providers[model.provider].append(model)

        # Create table for each provider
        for provider_name, provider_models in providers.items():
            table = Table(title=f"{provider_name.upper()} Models ({len(provider_models)} models)")
            table.add_column("Model ID", style="cyan", width=40)
            table.add_column("Name", style="green", width=40)
            table.add_column("Capabilities", style="yellow", width=20)
            table.add_column("LTS", style="magenta", width=8)
            table.add_column("Streaming", style="blue", width=10)
            table.add_column("Functions", style="red", width=10)

            for model in provider_models:
                capabilities = model.metadata.get("capabilities", [])
                cap_str = ", ".join(capabilities) if capabilities else "N/A"
                if len(cap_str) > 18:
                    cap_str = cap_str[:15] + "..."

                lts = "✓" if model.metadata.get("is_long_term_supported") else "✗"
                streaming = "✓" if model.supports_streaming else "✗"
                functions = "✓" if model.supports_functions else "✗"

                table.add_row(model.id, model.name, cap_str, lts, streaming, functions)

            console.print(table)

        # Summary
        console.print("\n[bold]Summary:[/bold]")
        console.print(f"• Total models: {len(models)}")
        console.print(f"• Providers: {', '.join(providers.keys())}")

        # Show cache info
        if provider._cache_timestamp:
            console.print(
                f"• Cache age: {(provider._cache_timestamp.now() - provider._cache_timestamp).seconds // 60} minutes"
            )

        chat_models = [m for m in models if "CHAT" in m.metadata.get("capabilities", [])]
        console.print(f"• Chat-capable models: {len(chat_models)}")

        lts_models = [m for m in models if m.metadata.get("is_long_term_supported")]
        console.print(f"• Long-term supported: {len(lts_models)}")

    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        console.print("\nMake sure you have:")
        console.print("1. Set OCI_COMPARTMENT_ID environment variable")
        console.print("2. Configured ~/.oci/config with valid credentials")
        console.print("3. Have access to OCI GenAI service in your region")


if __name__ == "__main__":
    main()
