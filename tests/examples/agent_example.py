#!/usr/bin/env python3
"""Example of using the Coda Agent system."""

import asyncio

from coda.base.providers import ProviderFactory
from coda.services.agents import Agent, tool
from coda.services.config import get_config_service


# Define custom tools using the @tool decorator
@tool(description="Calculate the sum of two numbers")
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@tool(description="Get information about a city")
async def get_city_info(city: str) -> dict:
    """Get basic information about a city."""
    # Simulate an async API call
    await asyncio.sleep(0.5)

    city_data = {
        "New York": {"population": 8_336_817, "country": "USA", "timezone": "EST"},
        "London": {"population": 9_002_488, "country": "UK", "timezone": "GMT"},
        "Tokyo": {"population": 13_960_000, "country": "Japan", "timezone": "JST"},
        "Paris": {"population": 2_161_000, "country": "France", "timezone": "CET"},
    }

    if city in city_data:
        return city_data[city]
    else:
        return {"error": f"No data available for {city}"}


async def main():
    """Run example agent interactions."""
    # Load configuration
    config = get_config_service()
    factory = ProviderFactory(config.to_dict())

    # Use OCI provider with Cohere model (supports tools)
    provider = factory.create("oci_genai")

    # Create agent with custom tools
    agent = Agent(
        provider=provider,
        model="cohere.command-r-plus",  # Tool-enabled model
        instructions="You are a helpful assistant that can perform calculations and look up city information.",
        tools=[add_numbers, get_city_info],
        name="Example Agent",
        temperature=0.3,  # Lower temperature for tool accuracy
    )

    # Example 1: Simple calculation
    print("Example 1: Calculation")
    print("-" * 40)
    response = await agent.run_async("What is 42 + 58?")
    print(f"Result: {response.content}\n")

    # Example 2: City information lookup
    print("Example 2: City Information")
    print("-" * 40)
    response = await agent.run_async("Tell me about Tokyo's population and timezone.")
    print(f"Result: {response.content}\n")

    # Example 3: Complex query requiring multiple tools
    print("Example 3: Complex Query")
    print("-" * 40)
    response = await agent.run_async(
        "If New York has X people and London has Y people, what is X + Y? "
        "Also tell me which timezone each city is in."
    )
    print(f"Result: {response.content}\n")

    # Example 4: Using built-in tools
    from coda.services.agents.builtin_tools import get_builtin_tools

    agent_with_builtin = Agent(
        provider=provider,
        model="cohere.command-r-plus",
        instructions="You are a helpful assistant with access to file system and other tools.",
        tools=get_builtin_tools(),
        name="System Agent",
    )

    print("Example 4: Built-in Tools")
    print("-" * 40)
    response = await agent_with_builtin.run_async("What files are in the current directory?")
    print(f"Result: {response.content}\n")


if __name__ == "__main__":
    asyncio.run(main())
