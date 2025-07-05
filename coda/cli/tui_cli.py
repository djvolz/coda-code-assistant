"""Textual-based interactive CLI with enhanced UI capabilities."""

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Optional

from rich.console import Console as RichConsole
from rich.markdown import Markdown
from rich.syntax import Syntax
from textual import events, on, work
from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Footer, Header, Input, Label, RichLog, Static
from textual.worker import Worker, WorkerState

from .shared import DeveloperMode, get_system_prompt


class MessageWidget(Static):
    """Widget for displaying a single message."""

    def __init__(self, content: str, is_user: bool = True, timestamp: Optional[datetime] = None):
        super().__init__()
        self.content = content
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now()
        self.update_content()

    def update_content(self):
        """Update the displayed content."""
        role = "You" if self.is_user else "Assistant"
        role_style = "bold cyan" if self.is_user else "bold green"
        time_str = self.timestamp.strftime("%H:%M:%S")
        
        # Format the message with role and timestamp
        formatted = f"[dim]{time_str}[/dim] [{role_style}]{role}[/{role_style}]\n{self.content}"
        self.update(formatted)


class ChatHistory(ScrollableContainer):
    """Scrollable container for chat messages."""

    def compose(self) -> ComposeResult:
        yield Container(id="chat-messages")

    def add_message(self, content: str, is_user: bool = True):
        """Add a new message to the chat history."""
        msg = MessageWidget(content, is_user)
        self.query_one("#chat-messages").mount(msg)
        self.scroll_end()


class CommandPalette(Input):
    """Enhanced input widget with command palette functionality."""

    def __init__(self):
        super().__init__(
            placeholder="Type your message or / for commands...",
            id="command-input"
        )

    async def action_submit(self):
        """Handle input submission."""
        if self.value.strip():
            # Post the message event
            self.post_message(self.Submitted(self.value))
            self.value = ""

    class Submitted(events.Message):
        """Message sent when input is submitted."""
        def __init__(self, value: str):
            super().__init__()
            self.value = value


class TextualInteractiveCLI(App):
    """Textual-based interactive CLI application."""

    CSS = """
    Screen {
        background: $surface;
    }

    #chat-container {
        height: 1fr;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }

    #chat-messages {
        padding: 1;
    }

    MessageWidget {
        margin-bottom: 1;
        padding: 1;
    }

    #input-container {
        height: 3;
        margin: 1 1 0 1;
    }

    #command-input {
        width: 1fr;
    }

    #status-bar {
        height: 1;
        background: $panel;
        color: $text;
        padding: 0 1;
    }

    .button-container {
        width: auto;
        height: 3;
        margin: 0 1;
    }

    Button {
        margin: 0 1;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear", "Clear chat"),
        ("ctrl+p", "command_palette", "Command palette"),
        ("f1", "help", "Help"),
    ]

    def __init__(self):
        super().__init__()
        self.current_mode = DeveloperMode.GENERAL
        self.conversation_history = []
        self.current_worker: Optional[Worker] = None

    def compose(self) -> ComposeResult:
        """Create the UI layout."""
        yield Header(show_clock=True)
        
        # Main chat area
        with Container(id="main-container"):
            yield ChatHistory(id="chat-container")
            
            # Input area with buttons
            with Horizontal(id="input-container"):
                yield CommandPalette()
                with Horizontal(classes="button-container"):
                    yield Button("Send", variant="primary", id="send-button")
                    yield Button("Clear", variant="warning", id="clear-button")
        
        # Status bar
        yield Static(
            f"Mode: {self.current_mode.value} | Provider: Not connected",
            id="status-bar"
        )
        
        yield Footer()

    def on_mount(self):
        """Handle mount event."""
        # Add welcome message
        chat = self.query_one(ChatHistory)
        chat.add_message(
            "Welcome to CODA Interactive CLI (Textual Edition)!\n"
            "Type your message or use / for commands. Press F1 for help.",
            is_user=False
        )
        
        # Focus on input
        self.query_one("#command-input").focus()

    @on(CommandPalette.Submitted)
    async def handle_input_submission(self, event: CommandPalette.Submitted):
        """Handle input submission from command palette."""
        await self.process_input(event.value)

    @on(Button.Pressed, "#send-button")
    async def handle_send_button(self):
        """Handle send button press."""
        input_widget = self.query_one("#command-input", CommandPalette)
        if input_widget.value.strip():
            await self.process_input(input_widget.value)
            input_widget.value = ""

    @on(Button.Pressed, "#clear-button")
    async def handle_clear_button(self):
        """Handle clear button press."""
        await self.action_clear()

    async def process_input(self, text: str):
        """Process user input."""
        if not text.strip():
            return

        chat = self.query_one(ChatHistory)
        
        # Add user message
        chat.add_message(text, is_user=True)
        self.conversation_history.append({"role": "user", "content": text})

        # Handle commands
        if text.startswith("/"):
            await self.handle_command(text)
        else:
            # Process as regular message
            await self.process_message(text)

    async def handle_command(self, command: str):
        """Handle slash commands."""
        chat = self.query_one(ChatHistory)
        
        parts = command[1:].split(maxsplit=1)
        cmd = parts[0] if parts else ""
        args = parts[1] if len(parts) > 1 else ""

        # Command routing
        if cmd == "help":
            self.show_help()
        elif cmd == "mode":
            self.switch_mode(args)
        elif cmd == "clear":
            await self.action_clear()
        elif cmd == "exit" or cmd == "quit":
            self.exit()
        else:
            chat.add_message(f"Unknown command: /{cmd}", is_user=False)

    def show_help(self):
        """Show help information."""
        chat = self.query_one(ChatHistory)
        help_text = """
## Available Commands

- `/help` - Show this help message
- `/mode [mode]` - Switch developer mode (general, code, debug, explain, review, refactor, plan)
- `/clear` - Clear the conversation
- `/exit` or `/quit` - Exit the application

## Keyboard Shortcuts

- `Ctrl+C` - Quit
- `Ctrl+L` - Clear chat
- `Ctrl+P` - Open command palette
- `F1` - Show help
"""
        chat.add_message(help_text, is_user=False)

    def switch_mode(self, mode_name: str):
        """Switch developer mode."""
        chat = self.query_one(ChatHistory)
        
        if not mode_name:
            # Show current mode and available modes
            modes = [mode.value for mode in DeveloperMode]
            chat.add_message(
                f"Current mode: {self.current_mode.value}\n"
                f"Available modes: {', '.join(modes)}",
                is_user=False
            )
            return

        # Try to switch mode
        try:
            new_mode = DeveloperMode(mode_name.lower())
            self.current_mode = new_mode
            
            # Update status bar
            self.update_status_bar()
            
            chat.add_message(f"Switched to {new_mode.value} mode", is_user=False)
        except ValueError:
            chat.add_message(f"Invalid mode: {mode_name}", is_user=False)

    def update_status_bar(self):
        """Update the status bar."""
        status = self.query_one("#status-bar", Static)
        status.update(f"Mode: {self.current_mode.value} | Provider: Not connected")

    @work(exclusive=True)
    async def process_message(self, message: str):
        """Process a regular message (not a command)."""
        chat = self.query_one(ChatHistory)
        
        # Add placeholder for assistant response
        chat.add_message("Thinking...", is_user=False)
        
        # Here you would integrate with the actual AI provider
        # For now, we'll simulate a response
        await asyncio.sleep(1)
        
        # Remove the "Thinking..." message and add actual response
        messages = chat.query_one("#chat-messages").children
        if messages and messages[-1].content == "Thinking...":
            await messages[-1].remove()
        
        # Simulated response
        response = f"I received your message: '{message}'. In {self.current_mode.value} mode, I would process this accordingly."
        chat.add_message(response, is_user=False)
        
        self.conversation_history.append({"role": "assistant", "content": response})

    async def action_clear(self):
        """Clear the chat history."""
        chat = self.query_one(ChatHistory)
        container = chat.query_one("#chat-messages")
        await container.remove_children()
        
        # Reset conversation history
        self.conversation_history = []
        
        # Add cleared message
        chat.add_message("Conversation cleared.", is_user=False)

    async def action_command_palette(self):
        """Open command palette (placeholder for future implementation)."""
        chat = self.query_one(ChatHistory)
        chat.add_message("Command palette coming soon!", is_user=False)

    async def action_help(self):
        """Show help via F1."""
        self.show_help()

    async def action_quit(self):
        """Quit the application."""
        self.exit()


def run_textual_cli():
    """Run the Textual-based CLI."""
    app = TextualInteractiveCLI()
    app.run()


if __name__ == "__main__":
    run_textual_cli()