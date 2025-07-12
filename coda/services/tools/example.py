#!/usr/bin/env python3
"""
Example demonstrating the MCP tools service module.

This shows how to:
1. Use the tool registry
2. Execute tools programmatically
3. Create custom MCP tools
4. Handle permissions and validation
5. Work with different tool categories

Run with: python -m coda.services.tools.example
"""

import asyncio
from pathlib import Path
from typing import Any

# Service layer imports
from coda.services.tools import (
    BaseTool,
    ToolParameter,
    ToolParameterType,
    ToolResult,
    ToolSchema,
    execute_tool,
    get_tool_categories,
    get_tool_info,
    get_tool_stats,
    list_tools_by_category,
    tool_registry,
)
from coda.services.tools.permissions import PermissionManager


async def example_tool_discovery():
    """Example showing tool discovery and listing."""
    print("=== Example 1: Tool Discovery ===\n")

    # Get tool statistics
    stats = get_tool_stats()
    print("Tool Statistics:")
    print(f"  Total tools: {stats['total_tools']}")
    print(f"  Categories: {stats['categories']}")
    print(f"  Dangerous tools: {stats['dangerous_tools']}")
    print()

    # List categories
    categories = get_tool_categories()
    print(f"Available categories: {', '.join(categories)}")
    print()

    # List tools by category
    tools_by_cat = list_tools_by_category()
    for category, tools in list(tools_by_cat.items())[:3]:  # Show first 3
        print(f"{category}:")
        for tool in tools[:5]:  # Show first 5 tools
            print(f"  - {tool}")
        if len(tools) > 5:
            print(f"  ... and {len(tools) - 5} more")
        print()


async def example_tool_execution():
    """Example showing tool execution."""
    print("=== Example 2: Tool Execution ===\n")

    # Execute a simple tool
    try:
        # List files in current directory
        result = await execute_tool("list_directory", {"path": "."})

        print("Listing current directory:")
        if result.success:
            # Parse the result
            if isinstance(result.result, list):
                files = result.result[:10]  # Show first 10
                for file in files:
                    print(f"  - {file}")
                if len(result.result) > 10:
                    print(f"  ... and {len(result.result) - 10} more")
            else:
                print(result.result)
        else:
            print(f"Error: {result.error}")

    except Exception as e:
        print(f"Tool execution error: {e}")
    print()


async def example_tool_info():
    """Example showing detailed tool information."""
    print("=== Example 3: Tool Information ===\n")

    # Get info about specific tools
    tool_names = ["read_file", "write_file", "shell", "git_status"]

    for name in tool_names:
        info = get_tool_info(name)
        if info:
            print(f"Tool: {info['name']}")
            print(f"  Description: {info['description']}")
            print(f"  Category: {info['category']}")
            print(f"  Dangerous: {info['dangerous']}")

            if info["parameters"]:
                print("  Parameters:")
                for param_name, param_info in info["parameters"].items():
                    print(f"    - {param_name} ({param_info['type']}): {param_info['description']}")
                    if param_info["required"]:
                        print("      Required: Yes")
            print()


async def example_custom_tool():
    """Example creating a custom MCP tool."""
    print("=== Example 4: Custom MCP Tool ===\n")

    class CalculatorTool(BaseTool):
        """A simple calculator tool."""

        def get_schema(self) -> ToolSchema:
            return ToolSchema(
                name="calculator",
                description="Perform basic arithmetic operations",
                category="utilities",
                parameters={
                    "operation": ToolParameter(
                        type=ToolParameterType.STRING,
                        description="Operation to perform",
                        required=True,
                        enum=["add", "subtract", "multiply", "divide"],
                    ),
                    "a": ToolParameter(
                        type=ToolParameterType.NUMBER,
                        description="First number",
                        required=True,
                    ),
                    "b": ToolParameter(
                        type=ToolParameterType.NUMBER,
                        description="Second number",
                        required=True,
                    ),
                },
            )

        async def execute(self, arguments: dict[str, Any]) -> ToolResult:
            """Execute the calculation."""
            try:
                operation = arguments["operation"]
                a = float(arguments["a"])
                b = float(arguments["b"])

                if operation == "add":
                    result = a + b
                elif operation == "subtract":
                    result = a - b
                elif operation == "multiply":
                    result = a * b
                elif operation == "divide":
                    if b == 0:
                        return ToolResult(
                            success=False, error="Division by zero", tool="calculator"
                        )
                    result = a / b
                else:
                    return ToolResult(
                        success=False, error=f"Unknown operation: {operation}", tool="calculator"
                    )

                return ToolResult(
                    success=True,
                    result={"answer": result, "expression": f"{a} {operation} {b} = {result}"},
                    tool="calculator",
                )

            except Exception as e:
                return ToolResult(success=False, error=str(e), tool="calculator")

    # Register the custom tool
    calculator = CalculatorTool()
    tool_registry.register(calculator)

    print("Registered custom calculator tool")

    # Use the tool
    operations = [
        ("add", 10, 5),
        ("multiply", 7, 8),
        ("divide", 100, 25),
        ("divide", 10, 0),  # This should error
    ]

    for op, a, b in operations:
        result = await execute_tool("calculator", {"operation": op, "a": a, "b": b})
        if result.success:
            print(f"  {result.result['expression']}")
        else:
            print(f"  {a} {op} {b} = ERROR: {result.error}")
    print()


async def example_permission_handling():
    """Example showing permission handling."""
    print("=== Example 5: Permission Handling ===\n")

    # Get permissions object
    permissions = PermissionManager()

    # Check dangerous tools
    dangerous_tools = ["shell", "rm_file", "write_file"]

    print("Checking dangerous tool permissions:")
    for tool_name in dangerous_tools:
        tool = tool_registry.get_tool(tool_name)
        if tool:
            schema = tool.get_schema()
            if schema.dangerous:
                print(f"  {tool_name}: DANGEROUS - requires confirmation")
            else:
                print(f"  {tool_name}: Safe")
    print()

    # Example with path restrictions

    print("\nChecking user permissions:")
    user_id = "test-user"
    user_perms = permissions.get_user_permissions(user_id)
    print(f"  User: {user_id}")
    print(f"  Base level: {user_perms.base_permission}")
    print(f"  Number of rules: {len(user_perms.rules)}")


async def example_batch_operations():
    """Example showing batch tool operations."""
    print("\n=== Example 6: Batch Operations ===\n")

    # Create a temp directory for testing
    import tempfile

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp_path = Path(tmpdir)

        print(f"Working in temporary directory: {tmp_path}")

        # Batch create files
        files_to_create = ["test1.txt", "test2.txt", "data.json", "script.py"]

        for filename in files_to_create:
            result = await execute_tool(
                "write_file",
                {
                    "path": str(tmp_path / filename),
                    "content": f"This is {filename}",
                },
            )
            if result.success:
                print(f"  ✓ Created {filename}")
            else:
                print(f"  ✗ Failed to create {filename}: {result.error}")

        # List the created files
        print("\nListing created files:")
        result = await execute_tool("list_directory", {"path": str(tmp_path)})
        if result.success and isinstance(result.result, list):
            for file in result.result:
                print(f"  - {file}")

        # Read one of the files
        print("\nReading test1.txt:")
        result = await execute_tool("read_file", {"path": str(tmp_path / "test1.txt")})
        if result.success:
            print(f"  Content: {result.result}")


async def example_error_handling():
    """Example showing error handling."""
    print("\n=== Example 7: Error Handling ===\n")

    # Try various error conditions
    error_cases = [
        ("read_file", {"path": "/nonexistent/file.txt"}, "Reading non-existent file"),
        ("list_directory", {"path": "/root/secret"}, "Listing restricted directory"),
        ("unknown_tool", {}, "Using unknown tool"),
        ("write_file", {"path": "/etc/passwd", "content": "hack"}, "Writing to system file"),
    ]

    for tool_name, args, description in error_cases:
        print(f"{description}:")
        try:
            result = await execute_tool(tool_name, args)
            if result.success:
                print(f"  Unexpected success: {result.result}")
            else:
                print(f"  Expected error: {result.error}")
        except Exception as e:
            print(f"  Exception: {e}")
        print()


async def main():
    """Run all examples."""
    print("Coda Tools Service Module Examples")
    print("==================================\n")

    # Run examples
    await example_tool_discovery()
    await example_tool_execution()
    await example_tool_info()
    await example_custom_tool()
    await example_permission_handling()
    await example_batch_operations()
    await example_error_handling()

    print("=== Summary ===")
    print("✓ Discovered and listed available tools")
    print("✓ Executed tools programmatically")
    print("✓ Retrieved detailed tool information")
    print("✓ Created and registered custom MCP tool")
    print("✓ Demonstrated permission handling")
    print("✓ Performed batch operations")
    print("✓ Showed error handling patterns")

    print("\nThe tools service provides a comprehensive")
    print("MCP-based tool system for safe operations!")


if __name__ == "__main__":
    asyncio.run(main())
