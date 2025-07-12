# Basic CLI Mode Archive

This directory contains the archived basic CLI mode implementation that was removed to simplify the codebase and focus on the interactive mode.

## Archived Files

- `basic_commands.py` - Basic mode slash command handling
- `main_with_basic_mode.py` - Original main.py with basic mode support
- `chat_session.py` - Chat session implementation that supported both basic and interactive modes

## Why Archived

The basic mode was archived because:

1. **Interactive mode is more feature-rich** - It includes all basic mode functionality plus:
   - Session management (save, load, branch)
   - Export capabilities (json, markdown, html)
   - Theme selection
   - Codebase intelligence commands
   - Semantic search
   - Observability features
   - Auto-completion and command history

2. **Maintenance burden** - Supporting two modes meant duplicate code and testing

3. **Better user experience** - Interactive mode provides a much better UX with prompt-toolkit

4. **Graceful fallback** - Interactive mode already handles cases where prompt-toolkit isn't available

## Basic Mode Features

The basic mode supported:
- `/help` - Show help
- `/model` - Switch model
- `/provider` - Show provider info
- `/mode` - Switch developer mode
- `/tools` or `/t` - Basic tool management
- `/clear` - Clear conversation
- `/exit` - Exit application

## Restoration

If needed, these files can be restored and integrated back into the main codebase. The key integration points would be:

1. Restore the `--basic` flag handling in `main.py`
2. Re-add the `run_basic_mode()` function
3. Integrate `BasicCommandProcessor` from `basic_commands.py`
4. Update `ChatSession` to support both modes again

## Archive Date

Archived on: 2025-01-10
Commit: (to be added after commit)