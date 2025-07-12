#!/usr/bin/env python3
"""
Simple example demonstrating the agents service module without external dependencies.

This shows basic agent functionality with custom tools.
"""

import asyncio
from datetime import datetime

# Base layer imports
from coda.base.providers import MockProvider

# Service layer imports
from coda.services.agents import Agent, tool


# Simple custom tools
@tool(description="Get the current date and time")
def get_current_time() -> str:
    """Get current timestamp."""
    return f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


@tool(description="Calculate the sum of two numbers")
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@tool(description="Reverse a string")
def reverse_string(text: str) -> str:
    """Reverse the given string."""
    return text[::-1]


async def main():
    """Run a simple agent example."""
    print("Simple Coda Agents Example")
    print("=========================\n")

    # Create a mock provider
    provider = MockProvider()

    # Create agent with custom tools
    agent = Agent(
        provider=provider,
        model="mock-model",
        instructions="You are a helpful assistant with access to various tools.",
        tools=[get_current_time, add_numbers, reverse_string],
        temperature=0.7,
    )

    # Test various tool calls
    queries = [
        "What time is it?",
        "What's 42 plus 58?",
        "Can you reverse the string 'hello world'?",
    ]

    for query in queries:
        print(f"User: {query}")
        response = await agent.run_async(query)
        print(f"Agent: {response.content}\n")

    print("Example completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
