#!/usr/bin/env python3
"""
Test example showing agent tool functionality directly.
"""

import asyncio
from datetime import datetime

# Service layer imports
from coda.services.agents import FunctionTool, tool


# Simple custom tools
@tool(description="Get the current date and time")
def get_current_time() -> str:
    """Get current timestamp."""
    return f"Current time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"


@tool(description="Calculate the sum of two numbers")
def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


async def main():
    """Test tool functionality directly."""
    print("Testing Agent Tools")
    print("==================\n")

    # Test 1: Tool decoration
    print("Test 1: Tool decoration")
    print(f"get_current_time is tool: {hasattr(get_current_time, '_is_tool')}")
    print(f"Tool name: {get_current_time._tool_name}")
    print(f"Tool description: {get_current_time._tool_description}")
    print()

    # Test 2: FunctionTool creation
    print("Test 2: FunctionTool creation")
    func_tool = FunctionTool.from_callable(get_current_time)
    print(f"Name: {func_tool.name}")
    print(f"Description: {func_tool.description}")
    print(f"Parameters: {func_tool.parameters}")
    print()

    # Test 3: Direct tool execution
    print("Test 3: Direct tool execution")
    result = await func_tool.execute({})
    print(f"Result: {result}")
    print()

    # Test 4: Tool with parameters
    print("Test 4: Tool with parameters")
    add_tool = FunctionTool.from_callable(add_numbers)
    print(f"Add tool parameters: {add_tool.parameters}")
    result = await add_tool.execute({"a": 42, "b": 58})
    print(f"42 + 58 = {result}")
    print()

    # Test 5: Error handling
    print("Test 5: Error handling")
    try:
        # This should fail - not decorated
        def not_a_tool():
            pass

        FunctionTool.from_callable(not_a_tool)
    except ValueError as e:
        print(f"Expected error: {e}")

    print("\nAll tests completed successfully!")


if __name__ == "__main__":
    asyncio.run(main())
