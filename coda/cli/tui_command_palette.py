"""Enhanced Textual CLI with command palette functionality."""

import asyncio
from datetime import datetime
from typing import Any, Optional

from rich.console import Console as RichConsole
from textual import on, work
from textual.app import App, ComposeResult
from textual.command import DiscoveryHit, Hit, Hits, Provider
from textual.containers import Container, Horizontal, ScrollableContainer
from textual.widgets import Button, Footer, Header, Input, Static

from .shared import DeveloperMode, get_system_prompt


class CodaCommandProvider(Provider):
    """Command provider for CODA commands."""

    async def search(self, query: str) -> Hits:
        """Search for commands matching the query."""
        matcher = self.matcher(query)
        
        commands = [
            ("mode:general", "Switch to General mode", self.switch_mode),
            ("mode:code", "Switch to Code mode", self.switch_mode),
            ("mode:debug", "Switch to Debug mode", self.switch_mode),
            ("mode:explain", "Switch to Explain mode", self.switch_mode),
            ("mode:review", "Switch to Review mode", self.switch_mode),
            ("mode:refactor", "Switch to Refactor mode", self.switch_mode),
            ("mode:plan", "Switch to Plan mode", self.switch_mode),
            ("clear", "Clear conversation", self.clear_chat),
            ("export:markdown", "Export as Markdown", self.export),
            ("export:json", "Export as JSON", self.export),
            ("export:html", "Export as HTML", self.export),
            ("theme:dark", "Switch to dark theme", self.switch_theme),
            ("theme:light", "Switch to light theme", self.switch_theme),
            ("help", "Show help", self.show_help),
        ]
        
        for cmd_id, description, callback in commands:
            if matcher.match(cmd_id) or matcher.match(description):
                yield Hit(
                    matcher.highlight(description),
                    callback,
                    cmd_id,
                    help=f"Execute: {cmd_id}"
                )

    def switch_mode(self, mode_id: str) -> None:
        """Switch developer mode."""
        mode_name = mode_id.split(":")[1]
        app = self.app
        if hasattr(app, 'switch_mode'):
            app.switch_mode(mode_name)

    def switch_theme(self, theme_id: str) -> None:
        """Switch theme."""
        theme_name = theme_id.split(":")[1]
        app = self.app
        if hasattr(app, 'notify'):
            app.notify(f"Theme '{theme_name}' will be applied (coming soon)")

    def export(self, export_id: str) -> None:
        """Export conversation."""
        format_name = export_id.split(":")[1]
        app = self.app
        if hasattr(app, 'notify'):
            app.notify(f"Export to {format_name} coming soon")

    def clear_chat(self) -> None:
        """Clear the chat."""
        app = self.app
        if hasattr(app, 'clear_chat'):
            app.clear_chat()

    def show_help(self) -> None:
        """Show help."""
        app = self.app
        if hasattr(app, 'show_help'):
            app.show_help()


class MessageDisplay(Static):
    """Widget for displaying messages with markdown support."""

    def __init__(self, role: str, content: str, timestamp: Optional[datetime] = None):
        super().__init__()
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.update_display()

    def update_display(self):
        """Update the displayed content."""
        role_style = "bold cyan" if self.role == "You" else "bold green"
        time_str = self.timestamp.strftime("%H:%M")
        
        header = f"[dim]{time_str}[/dim] [{role_style}]{self.role}[/{role_style}]"
        self.update(f"{header}\n\n{self.content}")


class EnhancedInput(Input):
    """Enhanced input with multi-line support and better placeholder."""

    DEFAULT_CSS = """
    EnhancedInput {
        height: 3;
        border: tall $accent;
        padding: 0 1;
    }
    
    EnhancedInput:focus {
        border: tall $success;
    }
    """

    def __init__(self):
        super().__init__(
            placeholder="Ask anything... (Ctrl+P for commands, Enter to send)",
            id="main-input"
        )


class TextualCLIWithPalette(App):
    """Enhanced Textual CLI with command palette."""
    
    COMMANDS = {CodaCommandProvider}

    CSS = """
    Screen {
        background: $surface;
    }

    #chat-container {
        height: 1fr;
        overflow-y: auto;
        border: solid $primary;
        margin: 1;
        padding: 1;
    }

    MessageDisplay {
        margin-bottom: 2;
        padding: 1;
        background: $panel;
        border: solid $primary;
    }

    #input-area {
        height: 5;
        padding: 1;
        dock: bottom;
    }

    #status-line {
        height: 1;
        background: $panel;
        color: $text;
        padding: 0 1;
        dock: bottom;
    }

    Button {
        margin: 0 1;
        min-width: 10;
    }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear_chat", "Clear"),
        ("ctrl+p", "command_palette", "Commands"),
        ("f1", "help", "Help"),
        ("ctrl+e", "export", "Export"),
    ]

    def __init__(self):
        super().__init__()
        self._current_mode = DeveloperMode.GENERAL
        self._messages = []

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header(show_clock=True)
        
        # Chat container
        with ScrollableContainer(id="chat-container"):
            yield Container(id="messages")
        
        # Input area
        with Horizontal(id="input-area"):
            yield EnhancedInput()
            yield Button("Send", variant="primary", id="send")
            yield Button("Clear", variant="warning", id="clear")
        
        # Status line
        yield Static(self.get_status_text(), id="status-line")
        
        yield Footer()

    def get_status_text(self) -> str:
        """Get current status text."""
        return f"Mode: {self._current_mode.value} | Ready | Messages: {len(self._messages)}"

    def on_mount(self):
        """Initialize on mount."""
        self.add_message("Assistant", 
            "Welcome to CODA Interactive CLI!\n\n"
            "- Type your question and press Enter\n"
            "- Press **Ctrl+P** for command palette\n"
            "- Press **F1** for help\n"
            "- Use **/command** syntax for quick commands"
        )
        
        # Focus input
        self.query_one("#main-input").focus()

    def add_message(self, role: str, content: str):
        """Add a message to the chat."""
        msg = MessageDisplay(role, content)
        self._messages.append({"role": role.lower(), "content": content})
        
        container = self.query_one("#messages")
        container.mount(msg)
        
        # Update status
        self.query_one("#status-line", Static).update(self.get_status_text())
        
        # Scroll to bottom
        self.query_one("#chat-container").scroll_end()

    @on(Input.Submitted, "#main-input")
    async def handle_input(self, event: Input.Submitted):
        """Handle input submission."""
        text = event.value.strip()
        if not text:
            return
        
        # Clear input
        event.input.value = ""
        
        # Add user message
        self.add_message("You", text)
        
        # Process input
        if text.startswith("/"):
            await self.process_command(text)
        else:
            await self.process_message(text)

    @on(Button.Pressed, "#send")
    async def send_pressed(self):
        """Handle send button."""
        input_widget = self.query_one("#main-input", Input)
        if input_widget.value.strip():
            input_widget.action_submit()

    @on(Button.Pressed, "#clear")
    async def clear_pressed(self):
        """Handle clear button."""
        await self.action_clear_chat()

    async def process_command(self, command: str):
        """Process slash commands."""
        parts = command[1:].split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "mode":
            self.switch_mode(args)
        elif cmd == "help":
            self.show_help()
        elif cmd == "clear":
            await self.action_clear_chat()
        elif cmd in ["exit", "quit"]:
            self.exit()
        else:
            self.add_message("System", f"Unknown command: /{cmd}")

    def switch_mode(self, mode_name: str):
        """Switch developer mode."""
        if not mode_name:
            modes = [m.value for m in DeveloperMode]
            self.add_message("System", 
                f"Current mode: **{self._current_mode.value}**\n\n"
                f"Available modes: {', '.join(modes)}"
            )
            return
        
        try:
            self._current_mode = DeveloperMode(mode_name.lower())
            self.query_one("#status-line", Static).update(self.get_status_text())
            self.add_message("System", f"Switched to **{self._current_mode.value}** mode")
            self.notify(f"Mode: {self._current_mode.value}")
        except ValueError:
            self.add_message("System", f"Invalid mode: {mode_name}")

    def show_help(self):
        """Show help information."""
        help_text = """
## CODA Interactive CLI Help

### Commands
- `/mode [name]` - Switch developer mode
- `/help` - Show this help
- `/clear` - Clear conversation
- `/exit` - Exit application

### Keyboard Shortcuts
- **Ctrl+P** - Open command palette
- **Ctrl+L** - Clear chat
- **Ctrl+E** - Export conversation
- **F1** - Show help
- **Ctrl+C** - Quit

### Developer Modes
- **general** - General conversation
- **code** - Code generation
- **debug** - Debugging assistance
- **explain** - Code explanation
- **review** - Code review
- **refactor** - Refactoring suggestions
- **plan** - Architecture planning
"""
        self.add_message("Help", help_text)

    @work(exclusive=True)
    async def process_message(self, message: str):
        """Process regular messages."""
        # Add placeholder
        self.add_message("Assistant", "*Thinking...*")
        
        # Simulate AI processing
        await asyncio.sleep(1.5)
        
        # Remove thinking message
        messages_container = self.query_one("#messages")
        if messages_container.children:
            await messages_container.children[-1].remove()
        
        # Add response
        response = (
            f"I received your message in **{self._current_mode.value}** mode.\n\n"
            f"Message: \"{message}\"\n\n"
            f"(This is a demonstration. Connect to an AI provider for real responses.)"
        )
        self.add_message("Assistant", response)

    async def action_clear_chat(self):
        """Clear the chat."""
        await self.clear_chat()

    async def clear_chat(self):
        """Clear all messages."""
        container = self.query_one("#messages")
        await container.remove_children()
        self._messages.clear()
        
        self.add_message("System", "Conversation cleared.")
        self.query_one("#status-line", Static).update(self.get_status_text())

    async def action_help(self):
        """Show help via F1."""
        self.show_help()

    async def action_export(self):
        """Export conversation."""
        self.notify("Export functionality coming soon!")

    def action_command_palette(self) -> None:
        """Show command palette."""
        # The command palette is automatically shown by Textual
        # when this action is triggered
        pass


def run_enhanced_textual_cli():
    """Run the enhanced Textual CLI."""
    app = TextualCLIWithPalette()
    app.run()


if __name__ == "__main__":
    run_enhanced_textual_cli()