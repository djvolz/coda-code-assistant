#!/usr/bin/env python3
"""Debug agent tool calling."""

import asyncio

from rich.console import Console

from coda.agents import Agent, tool
from coda.configuration import get_config
from coda.providers import ProviderFactory


@tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


async def main():
    console = Console()

    # Load configuration
    config = get_config()
    factory = ProviderFactory(config.to_dict())

    # Create provider
    provider = factory.create("oci_genai")

    # Create agent
    agent = Agent(
        provider=provider,
        model="cohere.command-r-plus",
        instructions="You are a helpful assistant. When asked to add numbers, use the add tool and then provide the final answer.",
        tools=[add],
        temperature=0.1,
        console=console,
    )

    console.print("[cyan]Testing agent with debug output...[/cyan]")

    # Run test with explicit steps
    response = await agent.run_async("What is 25 + 17? Please add these numbers.", max_steps=3)

    console.print(f"\n[green]Final response:[/green] {response.content}")

    # Show conversation history
    console.print("\n[cyan]Conversation history:[/cyan]")
    messages = response.data.get("messages", [])
    for i, msg in enumerate(messages):
        role = msg.role.value if hasattr(msg.role, "value") else str(msg.role)
        content = msg.content[:100] + "..." if len(msg.content) > 100 else msg.content
        tool_calls = (
            f" [tools: {len(msg.tool_calls)}]"
            if hasattr(msg, "tool_calls") and msg.tool_calls
            else ""
        )
        console.print(f"  {i + 1}. {role}{tool_calls}: {content}")


if __name__ == "__main__":
    asyncio.run(main())
