# Reference Documentation

This directory contains reference documentation for Coda features and components.

## 📖 Available References

### [Agents Reference](./agents.md)
Complete reference for the agent framework:
- Agent architecture and components
- Tool integration with agents
- Streaming responses and UI integration
- Configuration and customization

### [Tools Reference](./tools.md)
MCP (Model Context Protocol) tools documentation:
- Tool types and categories
- Built-in tools overview
- External tool integration
- Tool development guide

### [Mock Provider Reference](./mock_provider_reference.md)
Testing with the mock LLM provider:
- Mock provider features
- Configuring mock responses
- Testing strategies
- Command simulation

### [Enhanced Tab Completion](./enhanced-tab-completion.md)
Advanced CLI tab completion features:
- Tab completion system architecture
- Custom completers
- Integration with commands
- Performance optimizations

### [Search UI Improvements](./search-ui-improvements.md)
Search interface enhancements:
- Semantic search UI features
- Result visualization
- Performance improvements
- User experience optimizations

## 🔍 Quick Reference

### Common Tasks

**Using Agents:**
```python
from coda.services.agents import Agent
agent = Agent(provider=provider, model="gpt-4")
```

**Configuring Tools:**
```python
from coda.services.tools import ToolRegistry
registry = ToolRegistry()
registry.register(my_tool)
```

**Testing with Mock Provider:**
```python
provider = MockProvider(default_model="gpt-4-mock")
provider.set_response("test", "Mock response")
```

## 📊 Reference Categories

| Category | Purpose | Primary Users |
|----------|---------|---------------|
| Agents | AI agent capabilities | Developers integrating AI |
| Tools | MCP tool system | Tool developers |
| Mock Provider | Testing infrastructure | Test writers |
| Tab Completion | CLI enhancements | CLI users |
| Search UI | Search features | End users |

## 🔗 Related Documentation

- [API Documentation](../api/) - Module APIs
- [Guides](../guides/) - How-to guides
- [Testing](../testing/) - Testing documentation