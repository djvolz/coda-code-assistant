#!/usr/bin/env python3
"""Simple test of agent functionality."""

import asyncio

from coda.agents import Agent, tool
from coda.configuration import get_config
from coda.providers import ProviderFactory


@tool(description="Add two numbers")
def add(a: int, b: int) -> int:
    """Add two numbers."""
    return a + b


async def main():
    # Load configuration
    config = get_config()
    factory = ProviderFactory(config.to_dict())

    # Create provider
    provider = factory.create("oci_genai")

    # Create agent
    agent = Agent(
        provider=provider,
        model="cohere.command-r-plus",
        instructions="You are a helpful assistant. Use the add tool when asked to add numbers.",
        tools=[add],
        temperature=0.1,  # Very low temperature for consistency
    )

    print("Testing agent with simple addition...")

    # Run test
    response = await agent.run_async("What is 25 + 17?", max_steps=2)

    print(f"\nFinal response: {response.content}")
    print(f"\nMessages in conversation: {len(response.data.get('messages', []))}")


if __name__ == "__main__":
    asyncio.run(main())
