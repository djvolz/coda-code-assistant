"""Integrated Textual CLI with provider support."""

import asyncio
from datetime import datetime
from typing import Optional

from rich.console import Console as RichConsole
from rich.markdown import Markdown
from textual import on, work
from textual.app import App, ComposeResult
from textual.command import DiscoveryHit, Hit, Hits, Provider as CommandProvider
from textual.containers import Container, Horizontal, ScrollableContainer, Vertical
from textual.widgets import Button, Footer, Header, Input, Static

from coda.providers import Message, ProviderFactory, Role

from .shared import DeveloperMode, get_system_prompt


class ProviderCommands(CommandProvider):
    """Command provider for provider and model switching."""

    async def search(self, query: str) -> Hits:
        """Search for provider commands."""
        matcher = self.matcher(query)
        
        app = self.app
        if not hasattr(app, '_provider_factory'):
            return
            
        # Get available providers
        providers = app._provider_factory.list_providers()
        
        for provider_name in providers:
            if matcher.match(f"provider:{provider_name}"):
                yield Hit(
                    f"Switch to {provider_name} provider",
                    lambda p=provider_name: app.switch_provider(p),
                    f"provider:{provider_name}"
                )


class ModeCommands(CommandProvider):
    """Command provider for developer modes."""

    async def search(self, query: str) -> Hits:
        """Search for mode commands."""
        matcher = self.matcher(query)
        
        modes = [
            ("general", "General conversation and assistance"),
            ("code", "Optimized for writing new code"),
            ("debug", "Focus on error analysis"),
            ("explain", "Detailed code explanations"),
            ("review", "Security and code quality review"),
            ("refactor", "Code improvement suggestions"),
            ("plan", "Architecture planning and system design"),
        ]
        
        for mode_name, description in modes:
            if matcher.match(f"mode:{mode_name}") or matcher.match(description):
                yield Hit(
                    f"Mode: {mode_name} - {description}",
                    lambda m=mode_name: self.app.switch_mode(m),
                    f"mode:{mode_name}"
                )


class GeneralCommands(CommandProvider):
    """General command provider."""

    async def search(self, query: str) -> Hits:
        """Search for general commands."""
        matcher = self.matcher(query)
        
        commands = [
            ("clear", "Clear conversation", self.app.clear_chat),
            ("help", "Show help", self.app.show_help),
            ("export:markdown", "Export conversation as Markdown", lambda: self.app.export("markdown")),
            ("export:json", "Export conversation as JSON", lambda: self.app.export("json")),
            ("export:html", "Export conversation as HTML", lambda: self.app.export("html")),
        ]
        
        for cmd_id, description, callback in commands:
            if matcher.match(cmd_id) or matcher.match(description):
                yield Hit(
                    description,
                    callback,
                    cmd_id
                )


class MessageBox(Static):
    """Message display widget with markdown support."""

    def __init__(self, role: str, content: str, timestamp: Optional[datetime] = None):
        super().__init__()
        self.role = role
        self.content = content
        self.timestamp = timestamp or datetime.now()
        self.border_title = f"{role} - {self.timestamp.strftime('%H:%M:%S')}"


class IntegratedTextualCLI(App):
    """Textual CLI with full provider integration."""
    
    CSS = """
    Screen {
        background: $surface;
    }

    #chat-container {
        height: 1fr;
        margin: 1;
        padding: 1;
        scrollbar-gutter: stable;
    }

    #messages {
        height: auto;
    }

    MessageBox {
        margin-bottom: 1;
        padding: 1;
        border: solid $primary;
        height: auto;
    }

    MessageBox.user {
        border: solid cyan;
    }

    MessageBox.assistant {
        border: solid green;
    }

    MessageBox.system {
        border: solid yellow;
    }

    #input-container {
        height: 5;
        dock: bottom;
        padding: 1;
    }

    #main-input {
        height: 3;
        border: tall $accent;
        padding: 0 1;
    }

    #main-input:focus {
        border: tall $success;
    }

    #status-bar {
        height: 1;
        background: $panel;
        dock: bottom;
        padding: 0 1;
    }

    .buttons {
        height: 3;
        width: auto;
        margin: 0 1;
    }

    Button {
        margin: 0 1;
    }
    """
    
    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+l", "clear", "Clear"),
        ("ctrl+p", "command_palette", "Commands"),
        ("f1", "help", "Help"),
        ("pageup", "scroll_up", "Scroll up"),
        ("pagedown", "scroll_down", "Scroll down"),
        ("home", "scroll_home", "Scroll to top"),
        ("end", "scroll_end", "Scroll to bottom"),
    ]
    
    COMMANDS = {ModeCommands, ProviderCommands, GeneralCommands}

    def __init__(self, provider_factory: Optional[ProviderFactory] = None, 
                 provider_name: Optional[str] = None,
                 model: Optional[str] = None,
                 config: Optional[object] = None):
        super().__init__()
        self._provider_factory = provider_factory
        self._provider_name = provider_name
        self._provider = None
        self._model = model
        self._config = config
        self._current_mode = DeveloperMode.GENERAL
        self._messages = []
        self._available_models = []

    def compose(self) -> ComposeResult:
        """Compose the UI."""
        yield Header(show_clock=True)
        
        # Chat area
        with ScrollableContainer(id="chat-container"):
            yield Container(id="messages")
        
        # Input area
        with Vertical(id="input-container"):
            yield Input(
                placeholder="Type your message or press Ctrl+P for commands...",
                id="main-input"
            )
            with Horizontal(classes="buttons"):
                yield Button("Send", variant="primary", id="send")
                yield Button("Clear", variant="warning", id="clear")
                yield Button("Mode", id="mode")
                yield Button("Help", id="help")
        
        # Status bar
        yield Static(self.get_status(), id="status-bar")
        
        yield Footer()

    def get_status(self) -> str:
        """Get status bar text."""
        provider = self._provider_name or "Not connected"
        model = self._model or "No model"
        return f"Mode: {self._current_mode.value} | Provider: {provider} | Model: {model}"

    async def on_mount(self):
        """Initialize on mount."""
        # Add welcome message
        self.add_message("System", 
            "Welcome to CODA Textual CLI!\n\n"
            "Initializing provider connection..."
        )
        
        # Initialize provider if available
        if self._provider_factory and self._provider_name:
            await self.initialize_provider()
        
        # Focus input
        self.query_one("#main-input").focus()

    async def initialize_provider(self):
        """Initialize the provider connection."""
        try:
            self._provider = self._provider_factory.create(self._provider_name)
            self.add_message("System", f"✓ Connected to {self._provider_name}")
            
            # Get available models
            models = self._provider.list_models()
            self._available_models = [m.id for m in models]
            
            # Select model if not specified
            if not self._model and self._available_models:
                self._model = self._available_models[0]
                
            self.add_message("System", 
                f"✓ Using model: {self._model}\n"
                f"✓ Found {len(self._available_models)} available models\n\n"
                "Ready! Type your message or press Ctrl+P for commands."
            )
            
            # Update status
            self.query_one("#status-bar").update(self.get_status())
            
        except Exception as e:
            self.add_message("System", f"Error initializing provider: {str(e)}")

    def add_message(self, role: str, content: str):
        """Add a message to the chat."""
        # Create message box
        msg_box = MessageBox(role, content)
        msg_box.add_class(role.lower())
        
        # Store in history
        self._messages.append({"role": role.lower(), "content": content})
        
        # Add to UI
        container = self.query_one("#messages")
        container.mount(msg_box)
        
        # Update message content
        if role != "System":
            msg_box.update(Markdown(content))
        else:
            msg_box.update(content)
        
        # Scroll to bottom
        chat_container = self.query_one("#chat-container")
        # Use call_after_refresh to ensure scroll happens after layout
        self.call_after_refresh(chat_container.scroll_end)

    @on(Input.Submitted, "#main-input")
    async def handle_input_submitted(self, event: Input.Submitted):
        """Handle input submission."""
        text = event.value.strip()
        if not text:
            return
            
        # Clear input
        event.input.value = ""
        
        # Add user message
        self.add_message("You", text)
        
        # Process command or message
        if text.startswith("/"):
            await self.process_command(text)
        else:
            self.process_message(text)

    async def process_command(self, command: str):
        """Process slash commands."""
        parts = command[1:].split(maxsplit=1)
        cmd = parts[0].lower() if parts else ""
        args = parts[1] if len(parts) > 1 else ""
        
        if cmd == "help":
            self.show_help()
        elif cmd == "mode":
            if args:
                self.switch_mode(args)
            else:
                self.show_modes()
        elif cmd == "clear":
            await self.clear_chat()
        elif cmd == "model":
            self.show_models()
        elif cmd in ["exit", "quit"]:
            self.exit()
        else:
            self.add_message("System", f"Unknown command: /{cmd}")

    @work(exclusive=True)
    async def process_message(self, text: str):
        """Process regular message with AI."""
        if not self._provider:
            self.add_message("System", "No provider connected. Please connect to a provider first.")
            return
            
        # Build messages for API
        messages = []
        
        # Add system prompt
        system_prompt = get_system_prompt(self._current_mode)
        messages.append(Message(role=Role.SYSTEM, content=system_prompt))
        
        # Add conversation history (filter out system messages)
        for msg in self._messages:
            if msg["role"] in ["you", "user"]:
                messages.append(Message(role=Role.USER, content=msg["content"]))
            elif msg["role"] == "assistant":
                messages.append(Message(role=Role.ASSISTANT, content=msg["content"]))
        
        # Add placeholder for response
        self.add_message("Assistant", "*Thinking...*")
        
        try:
            # Stream response
            response_text = ""
            container = self.query_one("#messages")
            msg_widgets = container.children
            if msg_widgets:
                msg_widget = msg_widgets[-1]
            else:
                self.add_message("System", "Error: No message widget found")
                return
            
            stream = self._provider.chat_stream(
                messages=messages,
                model=self._model,
                temperature=0.7,
                max_tokens=2000
            )
            
            for chunk in stream:
                if chunk.content:
                    response_text += chunk.content
                    # Update the message widget
                    try:
                        msg_widget.update(Markdown(response_text))
                    except Exception:
                        msg_widget.update(response_text)
                    
                    # Auto-scroll during streaming
                    chat_container = self.query_one("#chat-container")
                    self.call_after_refresh(chat_container.scroll_end)
                    
            # Update final message in history
            if self._messages and self._messages[-1]["content"] == "*Thinking...*":
                self._messages[-1]["content"] = response_text
                
        except Exception as e:
            # Update error message
            if self._messages and self._messages[-1]["content"] == "*Thinking...*":
                self._messages[-1]["content"] = f"Error: {str(e)}"
            try:
                container = self.query_one("#messages")
                msg_widgets = container.children
                if msg_widgets:
                    msg_widgets[-1].update(f"Error: {str(e)}")
            except Exception:
                self.add_message("System", f"Error: {str(e)}")

    def switch_mode(self, mode_name: str):
        """Switch developer mode."""
        try:
            self._current_mode = DeveloperMode(mode_name.lower())
            self.query_one("#status-bar").update(self.get_status())
            self.add_message("System", f"Switched to {self._current_mode.value} mode")
        except ValueError:
            self.add_message("System", f"Invalid mode: {mode_name}")

    def show_modes(self):
        """Show available modes."""
        modes = [m.value for m in DeveloperMode]
        self.add_message("System", 
            f"Current mode: **{self._current_mode.value}**\n\n"
            f"Available modes: {', '.join(modes)}\n\n"
            "Use `/mode <name>` to switch"
        )

    def show_models(self):
        """Show available models."""
        if not self._available_models:
            self.add_message("System", "No models available. Connect to a provider first.")
            return
            
        self.add_message("System",
            f"Current model: **{self._model}**\n\n"
            f"Available models ({len(self._available_models)}):\n" +
            "\n".join(f"- {m}" for m in self._available_models[:10]) +
            ("\n..." if len(self._available_models) > 10 else "")
        )

    def switch_provider(self, provider_name: str):
        """Switch to a different provider."""
        self.add_message("System", f"Provider switching to {provider_name} coming soon!")

    def show_help(self):
        """Show help information."""
        help_text = """
## CODA Textual CLI Help

### Commands
- `/help` - Show this help
- `/mode [name]` - Switch developer mode  
- `/model` - Show available models
- `/clear` - Clear conversation
- `/exit` - Exit application

### Keyboard Shortcuts  
- **Ctrl+P** - Open command palette
- **Ctrl+L** - Clear chat
- **F1** - Show help
- **Ctrl+C** - Quit
- **Page Up/Down** - Scroll chat
- **Home/End** - Scroll to top/bottom

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

    async def clear_chat(self):
        """Clear the chat."""
        container = self.query_one("#messages")
        await container.remove_children()
        self._messages.clear()
        self.add_message("System", "Conversation cleared.")

    def export(self, format: str):
        """Export conversation."""
        self.add_message("System", f"Export to {format} coming soon!")

    @on(Button.Pressed, "#send")
    async def send_pressed(self):
        """Handle send button."""
        input_widget = self.query_one("#main-input", Input)
        if input_widget.value.strip():
            input_widget.action_submit()

    @on(Button.Pressed, "#clear")
    async def clear_pressed(self):
        """Handle clear button."""
        await self.clear_chat()

    @on(Button.Pressed, "#mode")
    def mode_pressed(self):
        """Handle mode button."""
        self.show_modes()

    @on(Button.Pressed, "#help")
    def help_pressed(self):
        """Handle help button."""
        self.show_help()

    async def action_clear(self):
        """Clear action."""
        await self.clear_chat()

    async def action_help(self):
        """Help action."""
        self.show_help()

    def action_scroll_up(self):
        """Scroll chat up."""
        chat_container = self.query_one("#chat-container")
        chat_container.scroll_up()

    def action_scroll_down(self):
        """Scroll chat down."""
        chat_container = self.query_one("#chat-container")
        chat_container.scroll_down()

    def action_scroll_home(self):
        """Scroll to top of chat."""
        chat_container = self.query_one("#chat-container")
        chat_container.scroll_home()

    def action_scroll_end(self):
        """Scroll to bottom of chat."""
        chat_container = self.query_one("#chat-container")
        chat_container.scroll_end()


def run_integrated_textual_cli(provider_factory=None, provider_name=None, model=None, config=None):
    """Run the integrated Textual CLI."""
    app = IntegratedTextualCLI(
        provider_factory=provider_factory,
        provider_name=provider_name,
        model=model,
        config=config
    )
    app.run()


if __name__ == "__main__":
    run_integrated_textual_cli()