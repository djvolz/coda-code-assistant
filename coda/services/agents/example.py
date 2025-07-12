#!/usr/bin/env python3
"""
Example demonstrating the agents service module.

This shows how to:
1. Create custom tools with the @tool decorator
2. Use built-in tools
3. Integrate MCP tools via the adapter
4. Run an agent with tool calling capabilities

Run with: python -m coda.services.agents.example
"""

import asyncio
from datetime import datetime
from pathlib import Path

# Base layer imports (agents depends on these)
from coda.base.providers import MockProvider

# Service layer imports
from coda.services.agents import Agent, tool
from coda.services.agents.tool_adapter import MCPToolAdapter


# Example 1: Simple custom tools with @tool decorator
@tool(description="Get the current date and time")
def get_current_time() -> str:
    """Get current timestamp."""
    return f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


@tool(description="Calculate the sum of two numbers")
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


@tool(description="Read a text file")
async def read_file_async(file_path: str) -> str:
    """Async file reading example."""
    try:
        path = Path(file_path)
        if not path.exists():
            return f"Error: File {file_path} not found"

        # Simulate async operation
        await asyncio.sleep(0.1)
        return path.read_text()
    except Exception as e:
        return f"Error reading file: {str(e)}"


# Example 2: More complex tool with validation
@tool(name="weather_tool", description="Get weather for a city (mock)")
def get_weather(city: str, units: str = "celsius") -> str:
    """
    Get weather information for a city.

    Args:
        city: City name
        units: Temperature units (celsius or fahrenheit)
    """
    # Mock weather data
    weather_data = {
        "London": {"temp": 15, "condition": "Cloudy"},
        "New York": {"temp": 22, "condition": "Sunny"},
        "Tokyo": {"temp": 18, "condition": "Rainy"},
    }

    if city not in weather_data:
        return f"Weather data not available for {city}"

    data = weather_data[city]
    temp = data["temp"]

    if units == "fahrenheit":
        temp = (temp * 9 / 5) + 32
        unit_str = "°F"
    else:
        unit_str = "°C"

    return f"Weather in {city}: {temp}{unit_str}, {data['condition']}"


async def example_basic_tools():
    """Example using basic custom tools."""
    print("=== Example 1: Basic Custom Tools ===\n")

    # Create a mock provider for testing
    provider = MockProvider()

    # Create agent with custom tools
    agent = Agent(
        provider=provider,
        model="mock-model",
        instructions="You are a helpful assistant with access to various tools.",
        tools=[get_current_time, add_numbers, get_weather],
        temperature=0.7,
    )

    # Test various tool calls
    queries = [
        "What time is it?",
        "What's 42 plus 58?",
        "What's the weather in London?",
        "Tell me the weather in Tokyo in fahrenheit",
    ]

    for query in queries:
        print(f"User: {query}")
        response = await agent.run_async(query)
        print(f"Agent: {response.content}\n")


async def example_mcp_tools():
    """Example using MCP tools via adapter."""
    print("=== Example 2: MCP Tools Integration ===\n")

    try:
        # Get available MCP tools
        mcp_tools = MCPToolAdapter.get_all_tools()
        print(f"Found {len(mcp_tools)} MCP tools available")

        # Show first few tools
        for tool in mcp_tools[:5]:
            print(f"  - {tool.name}: {tool.description}")

        if mcp_tools:
            # Create agent with MCP tools
            provider = MockProvider()
            agent = Agent(
                provider=provider,
                model="mock-model",
                instructions="You are a file system assistant. Help users with file operations.",
                tools=mcp_tools[:10],  # Use first 10 tools
            )

            # Example file operation
            print("\nTesting MCP tool execution:")
            response = await agent.run_async("List files in the current directory")
            print(f"Agent: {response.content}")

    except Exception as e:
        print(f"Error with MCP tools: {e}")
        print("This is expected if MCP tools aren't properly initialized")


async def example_mixed_tools():
    """Example mixing custom and MCP tools."""
    print("\n=== Example 3: Mixed Tool Types ===\n")

    # Get some MCP tools
    mcp_tools = []
    try:
        all_mcp = MCPToolAdapter.get_all_tools()
        # Just get file-related tools
        mcp_tools = [t for t in all_mcp if "file" in t.name.lower()][:3]
    except Exception:
        pass

    # Combine with custom tools
    all_tools = [get_current_time, add_numbers, get_weather, read_file_async, *mcp_tools]

    print(f"Agent has {len(all_tools)} tools:")
    for t in all_tools:
        print(f"  - {t.name if hasattr(t, 'name') else t.__name__}")

    # Create agent
    provider = MockProvider()
    agent = Agent(
        provider=provider,
        model="mock-model",
        instructions="You are a general-purpose assistant with many capabilities.",
        tools=all_tools,
    )

    # Test mixed operations
    print("\nTesting mixed tool usage:")
    response = await agent.run_async(
        "First tell me the time, then calculate 123 + 456, and finally check the weather in New York"
    )
    print(f"Agent: {response.content}")


async def example_streaming():
    """Example with streaming responses."""
    print("\n=== Example 4: Streaming Responses ===\n")

    # Create agent with streaming
    provider = MockProvider()
    agent = Agent(
        provider=provider,
        model="mock-model",
        instructions="You are a helpful assistant.",
        tools=[get_current_time],
    )

    print("Streaming response:")
    content, messages = await agent.run_async_streaming(
        "Tell me about the current time and explain why time zones exist"
    )

    print(f"\nFinal content length: {len(content)} characters")
    print(f"Message history: {len(messages)} messages")


async def example_tool_inspection():
    """Example showing tool introspection."""
    print("\n=== Example 5: Tool Introspection ===\n")

    from coda.services.agents.function_tool import FunctionTool

    # Create FunctionTool from decorated function
    weather_tool = FunctionTool.from_callable(get_weather)

    print(f"Tool name: {weather_tool.name}")
    print(f"Description: {weather_tool.description}")
    print("Parameters schema:")

    import json

    print(json.dumps(weather_tool.parameters, indent=2))

    # Show tool execution
    print("\nDirect tool execution:")
    result = await weather_tool.execute({"city": "London", "units": "fahrenheit"})
    print(f"Result: {result}")


async def main():
    """Run all examples."""
    print("Coda Agents Service Module Examples")
    print("===================================\n")

    # Run examples
    await example_basic_tools()
    await example_mcp_tools()
    await example_mixed_tools()
    await example_streaming()
    await example_tool_inspection()

    print("\n=== Summary ===")
    print("✓ Created custom tools with @tool decorator")
    print("✓ Integrated MCP tools via adapter")
    print("✓ Mixed different tool types in one agent")
    print("✓ Demonstrated streaming responses")
    print("✓ Showed tool introspection capabilities")

    print("\nThe agents service provides flexible tool calling")
    print("capabilities that work with any LLM provider!")


if __name__ == "__main__":
    asyncio.run(main())
