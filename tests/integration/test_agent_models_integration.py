#!/usr/bin/env python3
"""Test agent functionality with different OCI models."""

import asyncio
import sys

from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from coda.agents import Agent, tool
from coda.configuration import get_config
from coda.providers import ProviderFactory


# Define test tools
@tool(description="Add two numbers together")
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


@tool(description="Get the current date and time")
def get_time() -> str:
    """Get current timestamp."""
    from datetime import datetime

    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


@tool(description="Calculate the length of a string")
def string_length(text: str) -> int:
    """Get the length of a string."""
    return len(text)


async def test_model(provider, model: str, console: Console) -> dict:
    """Test a specific model with agent functionality."""
    results = {"model": model, "supports_tools": False, "tool_test": "N/A", "error": None}

    try:
        # Check if model supports tools
        model_info = next((m for m in provider.list_models() if m.id == model), None)
        if not model_info:
            results["error"] = "Model not found"
            return results

        results["supports_tools"] = model_info.supports_functions

        if not model_info.supports_functions:
            console.print(f"[yellow]Model {model} does not support function calling[/yellow]")
            return results

        # Create agent
        console.print(f"\n[cyan]Testing {model}...[/cyan]")
        agent = Agent(
            provider=provider,
            model=model,
            instructions="You are a helpful assistant that can use tools to answer questions.",
            tools=[add, get_time, string_length],
            name=f"Test Agent ({model})",
            temperature=0.3,
            console=console,
        )

        # Test 1: Simple calculation
        console.print("\n[bold]Test 1: Simple calculation[/bold]")
        response = await agent.run_async("What is 42 + 58?", max_steps=3)
        console.print(f"Response: {response.content}")

        # Test 2: Current time
        console.print("\n[bold]Test 2: Get current time[/bold]")
        response = await agent.run_async("What time is it right now?", max_steps=3)
        console.print(f"Response: {response.content}")

        # Test 3: String length
        console.print("\n[bold]Test 3: String operation[/bold]")
        response = await agent.run_async(
            "How many characters are in the word 'OpenAI'?", max_steps=3
        )
        console.print(f"Response: {response.content}")

        # Test 4: Multiple tools
        console.print("\n[bold]Test 4: Multiple tool usage[/bold]")
        response = await agent.run_async(
            "Calculate 15 + 25, then tell me how many characters are in the result when written as a word.",
            max_steps=3,
        )
        console.print(f"Response: {response.content}")

        results["tool_test"] = "PASSED"

    except Exception as e:
        results["error"] = str(e)
        console.print(f"[red]Error testing {model}: {e}[/red]")

    return results


async def main():
    """Test agent functionality across different models."""
    console = Console()

    # Header
    console.print(
        Panel.fit(
            "[bold cyan]Coda Agent Model Testing[/bold cyan]\n"
            "Testing tool calling capabilities across OCI models",
            border_style="cyan",
        )
    )

    # Load configuration
    config = get_config()
    factory = ProviderFactory(config.to_dict())

    try:
        # Create OCI provider
        provider = factory.create("oci_genai")

        # Get all available models
        models = provider.list_models()
        console.print(f"\nFound {len(models)} models")

        # Test models from each provider
        test_models = [
            # Cohere models (should support tools)
            "cohere.command-r-plus",
            "cohere.command-r",
            "cohere.command-r-08-2024",
            # Meta models (no tool support expected)
            "meta.llama-3.1-70b-instruct",
            "meta.llama-3.3-70b-instruct",
            # xAI models (no tool support expected)
            "xai.grok-3",
            "xai.grok-3-mini",
        ]

        results = []

        for model in test_models:
            if model in [m.id for m in models]:
                result = await test_model(provider, model, console)
                results.append(result)
                console.print("\n" + "=" * 60 + "\n")
            else:
                console.print(f"[yellow]Model {model} not available[/yellow]")

        # Summary table
        console.print("\n[bold cyan]Test Summary[/bold cyan]")
        table = Table(show_header=True, header_style="bold magenta")
        table.add_column("Model", style="cyan")
        table.add_column("Supports Tools", justify="center")
        table.add_column("Tool Test", justify="center")
        table.add_column("Notes")

        for result in results:
            supports = "✓" if result["supports_tools"] else "✗"
            test_status = result["tool_test"]
            if test_status == "PASSED":
                test_status = "[green]PASSED[/green]"
            elif test_status == "N/A":
                test_status = "[dim]N/A[/dim]"
            else:
                test_status = "[red]FAILED[/red]"

            notes = result["error"] or ""
            table.add_row(result["model"], supports, test_status, notes)

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
