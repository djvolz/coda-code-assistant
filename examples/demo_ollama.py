#!/usr/bin/env python3
"""
Demo script for Ollama provider with Coda.

This example shows how to use the Ollama provider for local LLM inference.
Make sure Ollama is running: https://ollama.ai/
"""

import asyncio

from rich.panel import Panel
from rich.text import Text

from coda.base.providers import Message, OllamaProvider, Role
from coda.themes import get_themed_console

console = get_themed_console()


def demo_basic_chat():
    """Demo basic chat functionality."""
    console.print(Panel("Basic Chat Example", style="bold green"))

    # Create provider
    provider = OllamaProvider(host="http://localhost:11434")

    # List available models
    console.print("\n[bold]Available Ollama models:[/bold]")
    models = provider.list_models()
    for model in models:
        console.print(f"  • {model.id} - {model.metadata.get('parameter_size', 'N/A')} params")

    if not models:
        console.print("[red]No models found! Pull a model first:[/red]")
        console.print("  ollama pull llama3.1")
        return

    # Use the smallest/fastest model
    model_id = models[-1].id if models else "qwen2.5:0.5b"
    console.print(f"\n[green]Using model:[/green] {model_id}")

    # Create a conversation
    messages = [
        Message(role=Role.SYSTEM, content="You are a helpful coding assistant."),
        Message(role=Role.USER, content="Write a Python function to calculate factorial."),
    ]

    # Get response
    console.print("\n[bold cyan]Assistant:[/bold cyan]")
    response = provider.chat(messages, model=model_id)
    console.print(response.content)

    # Show token usage
    if response.usage:
        console.print(
            f"\n[dim]Tokens used: {response.usage['total_tokens']} "
            f"(prompt: {response.usage['prompt_tokens']}, "
            f"completion: {response.usage['completion_tokens']})[/dim]"
        )


def demo_streaming():
    """Demo streaming functionality."""
    console.print(Panel("Streaming Example", style="bold blue"))

    provider = OllamaProvider()
    models = provider.list_models()

    if not models:
        return

    model_id = models[-1].id  # Use fastest model

    messages = [Message(role=Role.USER, content="Explain Python decorators in 3 sentences.")]

    console.print(f"\n[green]Streaming from {model_id}:[/green]\n")

    full_response = ""
    for chunk in provider.chat_stream(messages, model=model_id):
        console.print(chunk.content, end="")
        full_response += chunk.content
        if chunk.finish_reason:
            console.print(f"\n\n[dim]Finish reason: {chunk.finish_reason}[/dim]")


async def demo_async():
    """Demo async functionality."""
    console.print(Panel("Async Example", style="bold magenta"))

    provider = OllamaProvider()
    models = provider.list_models()

    if not models:
        return

    model_id = models[-1].id

    messages = [Message(role=Role.USER, content="What are the benefits of async programming?")]

    console.print(f"\n[green]Async request to {model_id}:[/green]\n")

    # Async chat
    response = await provider.achat(messages, model=model_id, max_tokens=100)
    console.print(response.content)

    # Async streaming
    console.print("\n[green]Async streaming:[/green]\n")
    async for chunk in provider.achat_stream(
        [Message(role=Role.USER, content="List 3 Python async best practices.")], model=model_id
    ):
        console.print(chunk.content, end="")


def demo_model_management():
    """Demo model management features."""
    console.print(Panel("Model Management", style="bold yellow"))

    provider = OllamaProvider()

    # Show how to pull a model (commented out to avoid actually pulling)
    console.print("\n[bold]To pull a new model:[/bold]")
    console.print("  provider.pull_model('llama3.1:8b')")
    console.print("\n[bold]To delete a model:[/bold]")
    console.print("  provider.delete_model('llama3.1:8b')")

    # Show model details
    console.print("\n[bold]Current model details:[/bold]")
    models = provider.list_models()
    if models:
        model = models[0]
        console.print(f"\nModel: {model.id}")
        console.print(f"  Context length: {model.context_length}")
        console.print(f"  Max tokens: {model.max_tokens}")
        console.print(f"  Metadata: {model.metadata}")


def main():
    """Run all demos."""
    console.print(Text("Ollama Provider Demo", style="bold white on blue"))
    console.print()

    try:
        # Basic chat
        demo_basic_chat()
        console.print()

        # Streaming
        demo_streaming()
        console.print()

        # Async
        asyncio.run(demo_async())
        console.print()

        # Model management
        demo_model_management()

    except Exception as e:
        console.print(f"\n[red]Error:[/red] {e}")
        console.print("\n[yellow]Make sure Ollama is running:[/yellow]")
        console.print("  1. Install Ollama: https://ollama.ai/")
        console.print("  2. Start Ollama service")
        console.print("  3. Pull a model: ollama pull qwen2.5:0.5b")


if __name__ == "__main__":
    main()
