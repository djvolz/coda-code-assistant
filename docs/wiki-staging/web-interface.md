# Web Interface

Coda provides a modern web interface built with Streamlit that offers all the capabilities of the CLI in a user-friendly browser-based environment.

## Features

### Agent-Powered Chat
- **Full Agent Integration**: The web interface uses the same agent system as the CLI
- **Tool Access**: All builtin tools are available including file operations, web search, and code analysis
- **Streaming Responses**: Real-time status updates and progressive response rendering
- **Event-Driven UI**: Visual feedback for tool execution and agent thinking

### Tool Management
- **Tool Configuration**: Enable/disable tools as needed
- **Tool Descriptions**: View detailed information about available tools
- **Flexible Selection**: Choose which tools to make available to the agent

### Agent Settings
- **Temperature Control**: Adjust response creativity and randomness
- **Token Limits**: Configure maximum response length
- **Provider Selection**: Choose between different AI providers
- **Mode Toggle**: Switch between agent mode and direct provider mode

### File Integration
- **File Upload**: Upload files for analysis and context
- **File Download**: Download conversation history and outputs
- **Context Integration**: Files are automatically included in conversation context

### Session Management
- **Persistent Conversations**: All chats are automatically saved
- **Session History**: Browse and resume previous conversations
- **Cross-Platform Sync**: Sessions are shared between CLI and web interfaces

### Diagram Support
- **Automatic Rendering**: Mermaid and PlantUML diagrams are rendered visually
- **Multiple Formats**: Support for various diagram types
- **Expandable Views**: Diagrams can be viewed in expandable sections

## Usage

### Starting the Web Interface

```bash
# Run the web interface
coda web

# Or directly with Streamlit
streamlit run coda/apps/web/app.py
```

### Navigation

The web interface is organized into several pages:

- **Chat**: Main conversation interface with agent capabilities
- **Sessions**: Browse and manage conversation history  
- **Settings**: Configure providers, models, and system preferences
- **Dashboard**: Overview and quick access to common functions

### Agent Configuration

1. **Enable Agent Mode**: Toggle between agent mode and direct provider mode
2. **Select Tools**: Choose which tools the agent can access
3. **Adjust Settings**: Configure temperature and token limits
4. **Monitor Status**: View real-time agent status and tool execution

### Tool Categories

#### File Operations
- `get_current_directory` - Get working directory
- `list_files` - List directory contents
- `read_file` - Read file contents
- `write_file` - Write to files

#### System Operations  
- `run_command` - Execute shell commands
- `get_datetime` - Get current date/time

#### Data Processing
- `parse_json` - Parse JSON strings
- `format_json` - Format data as JSON
- `fetch_data` - Simulate API calls

#### Intelligence Tools
- `find_definition` - Find code definitions
- `analyze_code` - Analyze code structure
- `get_dependencies` - Extract dependencies
- `code_stats` - Generate code statistics
- `find_pattern` - Search for patterns

## Architecture

### Event System
The web interface uses an event-driven architecture to handle agent interactions:

```python
# Event types
- THINKING: Agent is processing
- TOOL_EXECUTION_START: Tool execution begins
- TOOL_EXECUTION_END: Tool execution completes
- RESPONSE_CHUNK: Streaming response data
- RESPONSE_COMPLETE: Response finished
- ERROR: Error occurred
- WARNING: Warning message
- STATUS_UPDATE: General status update
```

### Components

#### StreamlitAgentEventHandler
Handles agent events and renders them in the Streamlit interface:
- Status containers for tool execution feedback
- Progress indicators for long-running operations
- Error and warning display
- Streaming response rendering

#### WebAgentService
Manages agent lifecycle and configuration:
- Provider and model selection
- Tool filtering and management
- Session state integration
- Error handling and recovery

#### Tool Settings Component
Provides UI for tool configuration:
- Tool selection interface
- Description display
- Enable/disable functionality
- Integration with agent service

### Session Integration
Web sessions are fully integrated with the CLI session system:
- Shared database for conversation storage
- Consistent session management
- Cross-interface compatibility
- Message persistence and retrieval

## Best Practices

### Performance
- **Tool Selection**: Only enable needed tools to improve performance
- **Token Management**: Set appropriate token limits for your use case
- **File Handling**: Upload smaller files for better responsiveness

### Security
- **File Permissions**: Be careful with file operation tools
- **Command Execution**: Use `run_command` tool judiciously
- **Provider Configuration**: Ensure API keys are properly secured

### User Experience
- **Agent Status**: Monitor the agent status panel for execution feedback
- **Error Handling**: Check error messages in status updates
- **Progressive Enhancement**: Use tool descriptions to understand capabilities

## Troubleshooting

### Common Issues

#### Tool Access Errors
- Verify tools are enabled in Agent Settings
- Check file permissions for file operation tools
- Ensure proper provider configuration

#### Performance Issues
- Reduce number of enabled tools
- Lower token limits for faster responses
- Check network connectivity for external tools

#### Display Problems
- Refresh the page if UI becomes unresponsive
- Clear browser cache for persistent issues
- Check browser console for JavaScript errors

### Getting Help
- Use the `get_current_directory` tool to verify working directory
- Check the agent status panel for real-time information
- Review conversation history for context clues
- Refer to tool descriptions for usage guidance

## Integration with CLI

The web interface shares the same underlying architecture as the CLI:
- **Same Agent System**: Identical capabilities and behavior
- **Shared Tools**: All CLI tools available in web interface
- **Session Compatibility**: Sessions created in CLI appear in web interface
- **Configuration Sync**: Provider and model settings are shared

This ensures a consistent experience across all interfaces while providing the convenience of a graphical user interface.