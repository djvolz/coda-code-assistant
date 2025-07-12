# Coda Agent System

The Coda Agent System provides a powerful framework for building AI agents that can use tools to accomplish tasks. Based on the Oracle Cloud Infrastructure (OCI) Agent Developer Kit (ADK) architecture, it offers a clean and intuitive API for creating tool-enabled AI assistants.

## Overview

Agents are AI assistants that can:
- Execute tasks using provided tools
- Handle complex multi-step workflows
- Call functions and process results
- Manage conversation context
- Work with any provider that supports function calling

## Quick Start

### Creating a Simple Agent

```python
from coda.agents import Agent, tool
from coda.providers import ProviderFactory

# Define a tool using the @tool decorator
@tool(description="Calculate the sum of two numbers")
def add(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b

# Create provider and agent
config = get_config()
factory = ProviderFactory(config.to_dict())
provider = factory.create_provider("oci_genai")

agent = Agent(
    provider=provider,
    model="cohere.command-r-plus",
    instructions="You are a helpful math assistant.",
    tools=[add],
    name="Math Agent"
)

# Run the agent
response = agent.run("What is 42 + 58?")
print(response.content)  # "The sum of 42 and 58 is 100."
```

## Tool Development

### The @tool Decorator

Tools are Python functions decorated with `@tool`:

```python
from coda.agents import tool

@tool(description="Get current weather")
def get_weather(city: str) -> dict:
    """Get weather for a city."""
    # Implementation here
    return {"city": city, "temp": 72, "condition": "sunny"}

# With custom name
@tool(name="fetch_data", description="Fetch data from API")
async def get_api_data(endpoint: str) -> dict:
    """Async tool example."""
    # Async implementation
    return {"data": "example"}
```

### Tool Requirements

- Must be decorated with `@tool`
- Should have clear parameter names and types
- Can be sync or async functions
- Should return JSON-serializable data
- Include descriptive docstrings

### Built-in Tools

Coda provides several built-in tools:

```python
from coda.agents.builtin_tools import get_builtin_tools

# Available tools:
# - get_current_directory()
# - list_files(directory)
# - read_file(file_path)
# - write_file(file_path, content)
# - run_command(command)
# - get_datetime()
# - parse_json(json_string)
# - format_json(data)
# - fetch_data(url) [async]

agent = Agent(
    provider=provider,
    model="cohere.command-r-plus",
    tools=get_builtin_tools()
)
```

## Advanced Features

### Custom Instructions

```python
agent = Agent(
    provider=provider,
    model="cohere.command-r-plus",
    instructions="""You are an expert Python developer.
    When writing code:
    - Follow PEP 8 style guidelines
    - Include type hints
    - Add docstrings
    - Handle errors gracefully""",
    tools=[...],
)
```

### Async Execution

```python
# Async agent execution
response = await agent.run_async("Task description")

# Async tools
@tool(description="Fetch data from API")
async def fetch_api(url: str) -> dict:
    async with httpx.AsyncClient() as client:
        response = await client.get(url)
        return response.json()
```

### Multi-Step Workflows

```python
# Agent automatically handles multi-step tool calling
response = await agent.run_async(
    "Read config.json, update the version to 2.0, and save it back",
    max_steps=5  # Maximum tool execution steps
)
```

### Callbacks

```python
def on_tool_executed(required_action, performed_action):
    """Called after each tool execution."""
    print(f"Executed: {required_action.function_call.name}")
    print(f"Result: {performed_action.function_call_output}")

response = await agent.run_async(
    "Process data",
    on_fulfilled_action=on_tool_executed
)
```

### Agents as Tools

Agents can be converted to tools for use by other agents:

```python
# Create specialized agents
code_agent = Agent(
    provider=provider,
    model="cohere.command-r-plus",
    instructions="You write high-quality Python code.",
    tools=[write_file, run_command],
    name="Code Writer"
)

review_agent = Agent(
    provider=provider,
    model="cohere.command-r-plus",
    instructions="You review code for bugs and improvements.",
    tools=[read_file],
    name="Code Reviewer"
)

# Create master agent with sub-agents as tools
master_agent = Agent(
    provider=provider,
    model="cohere.command-r-plus",
    instructions="You coordinate code development tasks.",
    tools=[
        code_agent.as_tool(),
        review_agent.as_tool()
    ]
)

# Master agent can now delegate to sub-agents
response = await master_agent.run_async(
    "Write a Python function to calculate fibonacci numbers and have it reviewed"
)
```

## Integration with MCP Tools

Existing MCP tools can be used with agents:

```python
from coda.agents.tool_adapter import MCPToolAdapter

# Get all MCP tools as agent-compatible tools
mcp_tools = MCPToolAdapter.get_all_tools()

agent = Agent(
    provider=provider,
    model="cohere.command-r-plus",
    tools=mcp_tools
)
```

## CLI Integration

The agent system is integrated into Coda's interactive CLI:

```bash
# Start Coda with agent/tool support (default)
coda

# Tools are automatically available for Cohere models
# The agent will use tools when appropriate
```

## Best Practices

1. **Tool Design**
   - Keep tools focused on single tasks
   - Use clear, descriptive names
   - Provide detailed descriptions
   - Validate inputs and handle errors

2. **Agent Instructions**
   - Be specific about agent behavior
   - Include examples when helpful
   - Set appropriate temperature (lower for tools)

3. **Error Handling**
   - Tools should return error messages, not raise exceptions
   - Agents will incorporate errors into their reasoning

4. **Performance**
   - Use async tools for I/O operations
   - Set reasonable max_steps limits
   - Cache expensive operations when possible

## Supported Providers

Currently, tool calling is supported by:
- OCI GenAI (Cohere models only)
- Additional providers coming soon

## Examples

See `examples/agent_example.py` for complete working examples.