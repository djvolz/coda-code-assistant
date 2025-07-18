# Agent Architecture Comparison Matrix

## Overview
This document provides a side-by-side comparison of agent architectures across Aider, Codex, Gemini, Dify, LLM (Simon Willison), and Goose to identify patterns and best practices for our own agent implementation.

## Core Architecture Patterns

| Feature | Aider | Codex | Gemini | Dify | LLM | Goose |
|---------|-------|-------|--------|------|-----|-------|
| **Primary Language** | Python | TypeScript/JavaScript | TypeScript/JavaScript | Python | Python | Rust |
| **Agent Core Class** | `Coder` (base_coder.py) | `AgentLoop` | `CoreToolScheduler` | `AgentStrategy` | `ChainResponse` | `Agent` + `SubAgent` |
| **Main Loop Pattern** | Reflection-based with max retries | Continuous agent-loop | Event-driven state machine | ReAct/Function calling | Chain-based | Multi-agent coordination |
| **Error Recovery** | Reflection + Exponential backoff | Loop detection + backoff | State recovery + checkpoints | Bounded iterations | Simple exceptions | Type-safe error handling |
| **Context Management** | Token checking + Summarization | Transcript maintenance | History curation | Scratchpad pattern | SQLite persistence | Resource-based with priorities |
| **Streaming Support** | Yes, with interrupts | AsyncIterable | SSE events | Generator-based | Basic print streaming | MCP notifications + SSE |

## Agentic Loop Patterns

### Aider
- **Reflection Loop**: Errors → Reflection Message → Retry (max 3)
- **Edit-Run-Test Cycle**: Edit → Commit → Lint → Test → Reflect
- **Context Overflow**: Summarize old messages → Continue

### Codex
- **Agent-Loop Pattern**: Continuous execution until task completion
- **Tool Execution**: Pre-approved or requires user confirmation
- **State Tracking**: Maintains pending function calls and responses

### Gemini
- **Event-Driven Pattern**: Server-sent events for streaming
- **Tool State Machine**: validating → awaiting_approval → executing → completed
- **Cancellation Support**: ESC key interrupts with graceful cleanup

### Dify
- **ReAct Pattern**: Thought → Action → Observation cycles
- **Function Calling**: Direct LLM function calling
- **Bounded Iterations**: Max iteration limits

### LLM
- **Chain Pattern**: Automatic tool execution loops
- **Chain Limits**: Default 5 iterations max
- **Simple Flow**: Request → Tool Calls → Results → Repeat

### Goose
- **Multi-Agent Pattern**: Parent-subagent task delegation
- **Router Selection**: LLM or vector search for tool routing
- **Recipe Execution**: YAML-defined structured workflows
- **MCP Protocol**: Standardized tool communication

## Tool/Command Execution

| Project | Command Pattern | Safety Mechanisms | Integration Style |
|---------|----------------|-------------------|-------------------|
| **Aider** | `/command` system with Commands class | User approval, git rollback | Shell commands + Edit blocks |
| **Codex** | Tool approval workflows | Three-tier approval + sandboxing | Direct execution with safety |
| **Gemini** | MCP tool scheduling | State machine + checkpointing | Dynamic tool discovery |
| **Dify** | Plugin-based tools | Iteration limits | Provider pattern |
| **LLM** | Function-as-tool | Optional `--tools-approve` | Simple function calls |
| **Goose** | MCP-compliant extensions | Env var validation + permissions | Multi-transport (SSE/HTTP/Stdio) |

## Edit/Code Modification Patterns

### Aider
- **Multiple Formats**: EditBlock, WholeFile, UnifiedDiff, Patch
- **Factory Pattern**: Dynamic coder selection based on model
- **Validation**: Strict parsing with clear error messages

### Codex
- **Apply Patch**: Special handling for code modifications
- **Shell Commands**: Platform-specific sandboxing
- **Approval Levels**: suggest/auto-edit/full-auto

### Gemini
- **Tool Parameters**: Editable before execution
- **Approval Modes**: DEFAULT/YOLO settings
- **MCP Integration**: External tool servers

### Dify
- **Plugin Tools**: YAML configuration
- **Message Types**: Text, JSON, Image, Log
- **Tool Results**: Generator-based streaming

### LLM
- **Function Tools**: Any Python function can be a tool
- **Tool Output**: String or ToolOutput with attachments
- **Toolbox Pattern**: Group related tools as class methods

### Goose
- **MCP Tools**: Standard protocol for tool definition
- **Extension Instructions**: Each extension provides context
- **Router Selection**: Tool routing based on task relevance
- **Subagent Delegation**: Complex edits via specialized agents

## State Management

| Project | Conversation State | File Tracking | History Management |
|---------|-------------------|---------------|-------------------|
| **Aider** | `cur_messages` + `done_messages` | `aider_edited_files` set | Git commits + summaries |
| **Codex** | Conversation transcript | Session state | Approved commands memory |
| **Gemini** | History curation | Tool execution state | Checkpointing system |
| **Dify** | Scratchpad pattern | Plugin session state | Thought/action/observation |
| **LLM** | SQLite persistence | N/A | Database logging |
| **Goose** | Per-agent contexts | Resource tracking | Session storage + recipes |

## Key Design Patterns

### Aider
1. **Reflection over Retry**: Send errors back to LLM for intelligent fixes
2. **Factory Pattern**: For coder selection
3. **Exception-based Flow**: `SwitchCoder` for dynamic switching
4. **Git-centric**: All changes tracked in git

### Codex
1. **Agent-Loop Model**: Continuous execution with tool feedback
2. **Three-Tier Approval**: Balances automation with safety
3. **Hybrid Architecture**: TypeScript/Rust for performance
4. **Pre-execution Safety**: Validate before running

### Gemini
1. **Event-Driven Streaming**: SSE for real-time updates
2. **Tool State Machine**: Complex state management
3. **MCP Protocol**: Extensible tool ecosystem
4. **Checkpointing**: Git-based rollback capability

### Dify
1. **Plugin Architecture**: Complete separation of concerns
2. **Multiple Strategies**: ReAct and Function Calling
3. **Scratchpad Pattern**: Clear reasoning history
4. **Generator Streaming**: Memory-efficient output

### LLM
1. **Function-as-Tool**: Maximum simplicity
2. **Chain Pattern**: Automatic tool loops
3. **Pluggy Plugins**: Python ecosystem integration
4. **Database Logging**: Built-in observability

### Goose
1. **Multi-Agent Design**: Parent-subagent task delegation
2. **Router Pattern**: Intelligent tool selection
3. **MCP Protocol**: Standardized extension interface
4. **Rust Safety**: Type-safe concurrent execution

## Performance Optimizations

| Project | Streaming | Caching | Context Optimization |
|---------|-----------|---------|---------------------|
| **Aider** | Real-time with interrupts | Prompt caching, model warming | Token counting, summarization |
| **Codex** | AsyncIterable streams | Provider-specific optimizations | Context overflow handling |
| **Gemini** | Event-driven SSE streams | Multi-transport caching | Thought/content separation |
| **Dify** | Generator-based streaming | Memory-efficient processing | Bounded iteration limits |
| **Goose** | MCP notifications + SSE | Resource prioritization | Per-agent context isolation |
| **LLM** | Basic print streaming | SQLite caching | Chain limits |

## Best Practices Identified

### From Aider
- Use reflection loops for intelligent error recovery
- Implement multiple edit formats for flexibility
- Deep git integration for safety and traceability
- Stream responses with interrupt handling
- Factory pattern for extensibility

### From Codex
- Pre-execution safety assessment for defense-in-depth security
- Three-tier approval system balancing automation with safety
- Hybrid TypeScript/Rust architecture for performance
- Agent-loop pattern for complex multi-step tasks
- Comprehensive sandboxing with platform-specific implementations

### From Gemini
- Event-driven streaming for sophisticated real-time interactions
- MCP protocol integration for extensible tool ecosystem
- Tool parameter modification for user control
- Checkpointing system for safety through rollback
- Sophisticated state management for complex scenarios

### From Dify
- Plugin architecture for enterprise-level customization
- Multiple agent strategies for different use cases
- Structured reasoning patterns (ReAct) for transparency
- Generator-based streaming for efficiency
- Workflow integration for complex automation

### From LLM
- Simple function-as-tool pattern for developer ease
- Chain-based automatic tool execution
- Pluggy-based plugin system for Python ecosystem
- Database logging for all interactions
- Pragmatic design over complex architecture

## Recommendations for Our Implementation

### Must-Have Features
1. **Reflection-based error handling** (from Aider)
2. **Enhanced loop detection** (from Codex)
3. **Tool state management** (from Gemini)
4. **Multiple agent strategies** (from Dify)
5. **Simple tool definition** (from LLM)

### Architecture Decisions
1. **Factory pattern for agent types** (from Aider)
2. **Plugin architecture for tools** (from Dify)
3. **Event-driven streaming** (from Gemini)
4. **Hybrid approach combining best practices** from all four

### Safety and Recovery
1. **Git integration for rollback** (from Aider)
2. **Three-tier approval system** (from Codex)
3. **Checkpointing system** (from Gemini)
4. **Bounded iteration limits** (from Dify)

### Implementation Priorities

**Phase 1 (Immediate)**:
- Add reflection loops to existing agent system
- Implement tool state machine
- Enhanced loop detection

**Phase 2 (Medium-term)**:
- Plugin architecture for tools
- Multiple agent strategies
- Safety assessment system

**Phase 3 (Long-term)**:
- Event-driven streaming
- MCP protocol support
- Checkpointing system

---

**Conclusion**: Each project offers unique strengths. Our implementation should combine:
- Aider's reflection patterns for intelligent error recovery
- Codex's safety mechanisms for security-first execution
- Gemini's sophisticated state management for complex workflows
- Dify's plugin architecture for enterprise extensibility
- LLM's simplicity for developer-friendly tool creation
- Goose's multi-agent coordination and MCP protocol support

This hybrid approach will create a robust, extensible, and safe agent system that balances power with pragmatism.