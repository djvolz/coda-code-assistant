"""Chat session management for CLI."""

from rich.console import Console
from rich.prompt import Prompt

from coda.base.providers import BaseProvider, Message, Model, Role
from coda.configuration import CodaConfig

from .basic_commands import BasicCommandProcessor
from .shared import DeveloperMode
from .shared.modes import get_system_prompt

# Optional agent imports for tool support
try:
    from .agent_chat import AgentChatHandler

    AGENT_SUPPORT = True
except ImportError:
    AGENT_SUPPORT = False


class ChatSession:
    """Manages chat sessions for both one-shot and interactive modes."""

    def __init__(
        self,
        provider: BaseProvider,
        model: str,
        config: CodaConfig,
        console: Console,
        provider_name: str,
        factory,
        unique_models: list[Model],
    ):
        self.provider = provider
        self.model = model
        self.config = config
        self.console = console
        self.messages: list[Message] = []

        # Initialize command processor
        self.cmd_processor = BasicCommandProcessor(console)
        self.cmd_processor.set_provider_info(provider_name, provider, factory, model, unique_models)

    def set_mode(self, mode: str):
        """Set the developer mode."""
        self.cmd_processor.current_mode = DeveloperMode(mode)

    def get_chat_parameters(self) -> dict:
        """Get chat generation parameters from config."""
        return {
            "temperature": self.config.to_dict().get("temperature", 0.7),
            "max_tokens": self.config.to_dict().get("max_tokens", 2000),
        }

    def stream_response(self, messages: list[Message], model: str | None = None) -> str:
        """Stream a response from the provider and return the full text."""
        full_response = ""
        params = self.get_chat_parameters()
        current_model = model or self.model

        # Check if we should use agent-based chat with tools
        if AGENT_SUPPORT and self._should_use_tools(current_model):
            try:
                import asyncio

                # Use agent chat handler for tool support
                agent_handler = AgentChatHandler(self.provider, self, self.console)

                # Run with agent system (handle async call)
                try:
                    # Try to get the current event loop
                    asyncio.get_running_loop()
                    # If we're in an async context, we need to handle this differently
                    # For now, fall back to regular streaming to avoid complications
                    self.console.print(
                        "[yellow]Tool support requires async context, falling back to regular mode[/yellow]\n"
                    )
                except RuntimeError:
                    # No event loop running, we can create one
                    response_content, _ = asyncio.run(
                        agent_handler.chat_with_agent(
                            messages=messages,  # Pass all messages, let agent handler extract user input
                            model=current_model,
                            **params,
                        )
                    )

                    # Print the response (agent handler doesn't auto-print in some cases)
                    if response_content:
                        self.console.print(response_content, end="")
                        full_response = response_content

                    return full_response

            except Exception as e:
                # Fall back to regular streaming if agent fails
                self.console.print(
                    f"\n[yellow]Tool support failed ({e}), falling back to regular mode[/yellow]\n"
                )

        # Regular streaming without tools
        try:
            for chunk in self.provider.chat_stream(
                messages=messages, model=current_model, **params
            ):
                self.console.print(chunk.content, end="")
                full_response += chunk.content
        except KeyboardInterrupt:
            self.console.print("\n\n[yellow]Response interrupted[/yellow]")
            full_response += " [interrupted]"

        return full_response

    def _should_use_tools(self, model: str) -> bool:
        """Check if we should use tools for the given model."""
        # Find the model info
        model_info = next((m for m in self.provider.list_models() if m.id == model), None)
        return model_info and model_info.supports_functions

    def run_one_shot(self, prompt: str):
        """Execute a single prompt and exit."""
        from coda.base.theme import get_console_theme

        theme = get_console_theme()

        self.console.print(f"\n[{theme.user_message}]User:[/{theme.user_message}] {prompt}")

        # Check if this is a slash command
        if prompt.startswith("/"):
            cmd_result = self.cmd_processor.process_command(prompt)
            if cmd_result == "exit":
                return
            elif cmd_result == "continue":
                return
            # If command was handled, don't send to AI
            return

        self.console.print(
            f"\n[{theme.assistant_message}]Assistant:[/{theme.assistant_message}] ", end=""
        )

        # Get system prompt based on mode
        system_prompt = get_system_prompt(self.cmd_processor.current_mode)

        messages = []
        if system_prompt:
            messages.append(Message(role=Role.SYSTEM, content=system_prompt))
        messages.append(Message(role=Role.USER, content=prompt))

        self.stream_response(messages)
        self.console.print("\n")

    def run_interactive(self):
        """Run an interactive chat session."""
        self.console.print("\n[dim]Type /help for commands, /exit to quit[/dim]\n")

        while True:
            try:
                # Get user input
                user_input = Prompt.ask("[bold]You[/bold]")
            except KeyboardInterrupt:
                # Handle Ctrl+C gracefully - just clear the line and continue
                self.console.print()  # New line for cleaner display
                continue
            except EOFError:
                # Handle Ctrl+D as exit
                self.console.print("\n[dim]Goodbye![/dim]")
                break

            # Process potential slash commands
            cmd_result = self.cmd_processor.process_command(user_input)

            if cmd_result == "exit":
                break
            elif cmd_result == "clear":
                self.messages = []
                self.console.print("[yellow]Conversation cleared[/yellow]\n")
                continue
            elif cmd_result == "continue":
                # Command was handled, continue to next iteration
                continue
            elif cmd_result is not None:
                # Unknown command result
                continue

            # Skip empty input
            if not user_input.strip():
                continue

            # Get system prompt based on mode
            system_prompt = get_system_prompt(self.cmd_processor.current_mode)

            # Prepare messages with system prompt
            chat_messages = []
            if system_prompt:
                chat_messages.append(Message(role=Role.SYSTEM, content=system_prompt))

            # Add conversation history and new message
            chat_messages.extend(self.messages)
            chat_messages.append(Message(role=Role.USER, content=user_input))

            # Get AI response
            from coda.base.theme import get_console_theme

            theme = get_console_theme()
            self.console.print(
                f"\n[{theme.assistant_message}]Assistant:[/{theme.assistant_message}] ", end=""
            )

            # Use current model from command processor (may have been changed via /model)
            current_model = self.cmd_processor.current_model or self.model
            full_response = self.stream_response(chat_messages, current_model)

            # Add messages to history
            self.messages.append(Message(role=Role.USER, content=user_input))
            self.messages.append(Message(role=Role.ASSISTANT, content=full_response))
            self.console.print("\n")
