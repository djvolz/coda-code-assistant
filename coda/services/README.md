# Services Layer

The services layer contains higher-level modules that orchestrate and coordinate base modules to provide complex functionality. These modules are not standalone - they depend on base modules but provide powerful abstractions for applications.

## Architecture

```
services/
├── agents/      # AI agent framework with tool calling
├── config/      # Configuration management service
└── tools/       # MCP-based tool system for various operations
```

## Modules

### ⚙️ config/
**Purpose**: Unified configuration management integrating base config and theme modules

The config service provides:
- High-level configuration API with sensible defaults
- Theme management integration
- XDG directory standard support
- Environment variable overrides
- Backward compatibility during migration

**Key Components**:
- `AppConfig` - Main service class integrating config and theme management
- `get_config_service()` - Get the global configuration instance
- Migration utilities for old configuration formats

**Dependencies**:
- `coda.base.config` - For TOML file management
- `coda.base.theme` - For theme management

### 🤖 agents/
**Purpose**: Orchestrates AI providers with tool execution capabilities

The agents module provides a flexible framework for creating AI agents that can:
- Execute tools and functions during conversations
- Handle streaming responses
- Manage conversation state
- Support both synchronous and asynchronous operations

**Key Components**:
- `Agent` - Main class that manages AI conversations with tool calling
- `@tool` decorator - Simple way to create tools from Python functions
- `FunctionTool` - Tool abstraction with automatic JSON schema generation
- `MCPToolAdapter` - Bridge to use MCP tools with agents

**Dependencies**:
- `coda.base.providers` - For LLM provider interfaces
- `coda.base.search` - For code intelligence tools
- `coda.services.tools` - For MCP tool integration

### 🛠️ tools/
**Purpose**: Comprehensive Model Context Protocol (MCP) based tool system

The tools module provides a rich set of tools for:
- File system operations (read, write, edit, search)
- Shell command execution
- Git repository operations
- Web scraping and interaction
- Code intelligence operations

**Key Components**:
- `BaseTool` - Abstract base class for all MCP tools
- `ToolRegistry` - Central registry for tool discovery
- `ToolExecutor` - Handles tool execution with provider integration
- Permission system for security
- MCP server and client implementations

**Dependencies**:
- `coda.base.providers` - For tool definitions
- `coda.base.search` - For code analysis capabilities
- `coda.base.session` - For tool execution history

## Tool Systems Comparison

The services layer currently has two tool systems:

### 1. Decorator-based Tools (agents/)
```python
from coda.services.agents import tool

@tool(description="Get current time")
def get_time() -> str:
    return datetime.now().isoformat()
```

**Pros**:
- Simple and pythonic
- Automatic parameter schema generation
- Easy to create ad-hoc tools
- Good for simple functions

**Cons**:
- Limited parameter validation
- No built-in permission system
- Less structured than MCP

### 2. MCP-based Tools (tools/)
```python
from coda.services.tools import BaseTool, ToolSchema

class TimeTool(BaseTool):
    def get_schema(self) -> ToolSchema:
        return ToolSchema(
            name="get_time",
            description="Get current time",
            category="utilities"
        )
```

**Pros**:
- Full MCP protocol compliance
- Rich parameter validation
- Permission system
- Tool categories and metadata
- Server/client architecture

**Cons**:
- More verbose to create
- Requires understanding MCP

## Integration Examples

### Tool Systems Working Together

The two tool systems can work together via the adapter:

```python
from coda.services.agents import Agent
from coda.services.agents.tool_adapter import MCPToolAdapter
from coda.base.providers import ProviderFactory

# Get MCP tools as FunctionTools
mcp_tools = MCPToolAdapter.get_all_tools()

# Create agent with both tool types
agent = Agent(
    provider=ProviderFactory.create("ollama"),
    model="llama2",
    tools=[
        custom_tool,      # Decorator-based
        *mcp_tools        # MCP-based via adapter
    ]
)

# Run agent
response = await agent.run_async("Analyze this codebase")
```

### Configuration-Driven Services

All services can be configured through the config service:

```python
from coda.services.config import get_config_service
from coda.services.agents import Agent
from coda.base.providers import ProviderFactory

# Get configuration
config = get_config_service()

# Create provider with config
factory = ProviderFactory(config.to_dict())
provider = factory.create(config.default_provider)

# Create agent with themed console
agent = Agent(
    provider=provider,
    model="llama3",
    console=config.theme_manager.get_console()
)

# Agent uses configured defaults
# (temperature, max_tokens, etc from config)
```

## Design Principles

1. **Orchestration over Implementation** - Services coordinate base modules rather than implementing core functionality
2. **Provider Agnostic** - Work with any LLM provider that implements the base interface
3. **Tool Flexibility** - Support multiple tool creation patterns for different use cases
4. **Safety First** - Permission systems and validation for dangerous operations
5. **Async by Default** - Built for concurrent operations

## Future Considerations

1. **Tool System Consolidation** - Consider unifying the two tool systems with a common interface
2. **Service Discovery** - Add service registry for dynamic service loading
3. **Middleware System** - Add hooks for cross-cutting concerns (logging, auth, etc.)
4. **Event System** - Publish events for tool execution, agent actions, etc.

## Testing

Services should be tested at multiple levels:
- Unit tests for individual components
- Integration tests for service interactions
- End-to-end tests with real providers
- Performance tests for concurrent operations

See the `tests/services/` directory for examples.