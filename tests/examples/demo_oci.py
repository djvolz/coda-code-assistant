#!/usr/bin/env python3
"""Simple demo of OCI GenAI provider."""

import os
import sys

from rich.panel import Panel
from rich.prompt import Prompt

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coda.base.providers import Message, OCIGenAIProvider, Role
from coda.themes import get_themed_console

console = get_themed_console()


def main():
    """Run interactive demo."""
    console.print(
        Panel.fit(
            "[bold cyan]Coda OCI GenAI Demo[/bold cyan]\n"
            "Chat with Oracle Cloud Infrastructure Generative AI",
            border_style="cyan",
        )
    )

    # Check environment
    if not os.getenv("OCI_COMPARTMENT_ID"):
        console.print("\n[red]Error:[/red] OCI_COMPARTMENT_ID not set")
        console.print("Please run: export OCI_COMPARTMENT_ID='your-compartment-id'")
        return

    try:
        # Initialize provider
        console.print("\n[yellow]Initializing OCI GenAI provider...[/yellow]")
        provider = OCIGenAIProvider()
        console.print("[green]✓ Provider ready[/green]")

        # Show available models
        models = provider.list_models()
        console.print("\n[bold]Available models:[/bold]")
        for i, model in enumerate(models, 1):
            console.print(f"{i}. {model.id}")

        # Select model
        model_choice = Prompt.ask(
            "\nSelect model number",
            default="1",
            choices=[str(i) for i in range(1, len(models) + 1)],
        )
        selected_model = models[int(model_choice) - 1]
        console.print(f"[green]Using {selected_model.id}[/green]")

        # Chat loop
        console.print("\n[dim]Type 'exit' to quit, 'clear' to reset conversation[/dim]\n")
        messages = []

        while True:
            # Get user input
            user_input = Prompt.ask("[bold]You[/bold]")

            if user_input.lower() == "exit":
                break
            elif user_input.lower() == "clear":
                messages = []
                console.print("[yellow]Conversation cleared[/yellow]\n")
                continue

            # Add user message
            messages.append(Message(role=Role.USER, content=user_input))

            # Get AI response
            console.print("\n[bold cyan]Assistant:[/bold cyan] ", end="")

            try:
                # Stream response
                full_response = ""
                for chunk in provider.chat_stream(
                    messages=messages, model=selected_model.id, temperature=0.7, max_tokens=500
                ):
                    console.print(chunk.content, end="")
                    full_response += chunk.content

                # Add assistant message to history
                messages.append(Message(role=Role.ASSISTANT, content=full_response))
                console.print("\n")

            except Exception as e:
                console.print(f"\n[red]Error: {e}[/red]\n")
                messages.pop()  # Remove failed user message

    except Exception as e:
        console.print(f"\n[red]Failed to initialize provider: {e}[/red]")
        console.print("\nMake sure you have:")
        console.print("1. Set OCI_COMPARTMENT_ID environment variable")
        console.print("2. Configured ~/.oci/config with valid credentials")
        console.print("3. Have access to OCI GenAI service in your region")


if __name__ == "__main__":
    main()
