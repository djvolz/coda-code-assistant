#!/usr/bin/env python3
"""Test script for OCI GenAI provider."""

import asyncio
import os
import sys

from rich.panel import Panel

from coda.themes import get_themed_console

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from coda.base.providers import Message, OCIGenAIProvider, Role

console = get_themed_console()


def test_basic_chat():
    """Test basic chat completion."""
    console.print("\n[bold cyan]Testing Basic Chat Completion[/bold cyan]")

    try:
        # Initialize provider
        provider = OCIGenAIProvider()
        console.print("[green]✓[/green] Provider initialized")

        # List models
        models = provider.list_models()
        console.print(f"[green]✓[/green] Found {len(models)} models:")
        for model in models:
            console.print(f"  - {model.id}: {model.name}")

        # Test chat
        messages = [Message(role=Role.USER, content="Hello! Can you tell me a short joke?")]

        model = "cohere.command-r-plus-08-2024"
        console.print(f"\n[yellow]Testing chat with {model}...[/yellow]")

        response = provider.chat(messages=messages, model=model, temperature=0.7, max_tokens=100)

        console.print("[green]✓[/green] Chat completed")
        console.print(Panel(response.content, title="Response", border_style="green"))

        if response.usage:
            console.print(f"Tokens used: {response.usage}")

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        return False

    return True


def test_streaming():
    """Test streaming chat completion."""
    console.print("\n[bold cyan]Testing Streaming Chat[/bold cyan]")

    try:
        provider = OCIGenAIProvider()

        messages = [
            Message(
                role=Role.USER, content="Count from 1 to 5 slowly, with a word between each number."
            )
        ]

        model = "cohere.command-r-08-2024"
        console.print(f"[yellow]Testing streaming with {model}...[/yellow]")

        console.print("[dim]Response:[/dim] ", end="")
        full_response = ""

        for chunk in provider.chat_stream(
            messages=messages, model=model, temperature=0.7, max_tokens=150
        ):
            console.print(chunk.content, end="")
            full_response += chunk.content

        console.print("\n[green]✓[/green] Streaming completed")

    except Exception as e:
        console.print(f"\n[red]✗ Error:[/red] {e}")
        return False

    return True


async def test_async_chat():
    """Test async chat completion."""
    console.print("\n[bold cyan]Testing Async Chat[/bold cyan]")

    try:
        provider = OCIGenAIProvider()

        messages = [Message(role=Role.USER, content="What is 2+2? Reply with just the number.")]

        model = "meta.llama-3.1-70b-instruct"
        console.print(f"[yellow]Testing async chat with {model}...[/yellow]")

        response = await provider.achat(
            messages=messages, model=model, temperature=0.1, max_tokens=10
        )

        console.print("[green]✓[/green] Async chat completed")
        console.print(f"Response: {response.content}")

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        return False

    return True


async def test_async_streaming():
    """Test async streaming chat completion."""
    console.print("\n[bold cyan]Testing Async Streaming[/bold cyan]")

    try:
        provider = OCIGenAIProvider()

        messages = [
            Message(role=Role.SYSTEM, content="You are a helpful assistant. Be concise."),
            Message(role=Role.USER, content="List 3 colors, one per line."),
        ]

        model = "meta.llama-3.1-70b-instruct"
        console.print(f"[yellow]Testing async streaming with {model}...[/yellow]")

        console.print("[dim]Response:[/dim]\n", end="")
        full_response = ""

        async for chunk in provider.achat_stream(
            messages=messages, model=model, temperature=0.5, max_tokens=50
        ):
            console.print(chunk.content, end="")
            full_response += chunk.content

        console.print("\n[green]✓[/green] Async streaming completed")

    except Exception as e:
        console.print(f"\n[red]✗ Error:[/red] {e}")
        return False

    return True


def test_error_handling():
    """Test error handling."""
    console.print("\n[bold cyan]Testing Error Handling[/bold cyan]")

    try:
        provider = OCIGenAIProvider()

        # Test invalid model
        console.print("[yellow]Testing invalid model...[/yellow]")
        try:
            provider.chat(
                messages=[Message(role=Role.USER, content="test")],
                model="invalid.model",
            )
            console.print("[red]✗[/red] Should have raised error for invalid model")
        except ValueError as e:
            console.print(f"[green]✓[/green] Correctly caught invalid model: {e}")

        # Test empty messages
        console.print("\n[yellow]Testing empty messages...[/yellow]")
        try:
            provider.chat(
                messages=[],
                model="cohere.command-r-08-2024",
            )
            console.print("[red]✗[/red] Should have raised error for empty messages")
        except Exception as e:
            console.print(f"[green]✓[/green] Correctly caught error: {type(e).__name__}")

    except Exception as e:
        console.print(f"[red]✗ Error in error handling test:[/red] {e}")
        return False

    return True


def main():
    """Run all tests."""
    console.print(
        Panel.fit(
            "[bold]OCI GenAI Provider Test Suite[/bold]\n"
            "Testing the Oracle Cloud Infrastructure Generative AI provider",
            border_style="blue",
        )
    )

    # Check for required environment variables
    if not os.getenv("OCI_COMPARTMENT_ID"):
        console.print("\n[red]Error:[/red] OCI_COMPARTMENT_ID environment variable not set")
        console.print("Please set: export OCI_COMPARTMENT_ID='your-compartment-id'")
        sys.exit(1)

    # Check for OCI config
    oci_config_path = os.path.expanduser("~/.oci/config")
    if not os.path.exists(oci_config_path):
        console.print(f"\n[red]Error:[/red] OCI config not found at {oci_config_path}")
        console.print(
            "Please configure OCI CLI: https://docs.oracle.com/en-us/iaas/Content/API/SDKDocs/cliinstall.htm"
        )
        sys.exit(1)

    # Run tests
    tests_passed = 0
    total_tests = 5

    if test_basic_chat():
        tests_passed += 1

    if test_streaming():
        tests_passed += 1

    if asyncio.run(test_async_chat()):
        tests_passed += 1

    if asyncio.run(test_async_streaming()):
        tests_passed += 1

    if test_error_handling():
        tests_passed += 1

    # Summary
    console.print(f"\n[bold]Test Summary:[/bold] {tests_passed}/{total_tests} passed")

    if tests_passed == total_tests:
        console.print("[bold green]All tests passed! ✨[/bold green]")
    else:
        console.print(f"[bold red]{total_tests - tests_passed} tests failed[/bold red]")
        sys.exit(1)


if __name__ == "__main__":
    main()
