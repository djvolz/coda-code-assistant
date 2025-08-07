"""Tool-enabled chat functionality for the CLI."""

import asyncio
import json
import time

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from coda.base.providers.base import Message, Role, Tool
from coda.services.tools.executor import ToolExecutor


class ToolChatHandler:
    """Handles AI chat with tool calling capabilities."""

    def __init__(self, provider_instance, cli, console: Console):
        """Initialize the tool chat handler."""
        self.provider = provider_instance
        self.cli = cli
        self.console = console
        self.executor = ToolExecutor()
        self.tools_enabled = True
        from coda.services.config import get_config_service

        config_service = get_config_service()
        self.theme = config_service.theme_manager.get_console_theme()

    def should_use_tools(self, model: str) -> bool:
        """Check if the current model supports tools."""
        # Only Cohere models support tools in OCI
        return model.startswith("cohere.") and self.tools_enabled

    async def chat_with_tools(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int = 2000,
        system_prompt: str | None = None,
    ) -> tuple[str, list[Message]]:
        """
        Handle a chat interaction with tool support.

        Returns:
            Tuple of (final_response, updated_messages)
        """
        # Add system prompt if provided
        if system_prompt and (not messages or messages[0].role != Role.SYSTEM):
            messages.insert(0, Message(role=Role.SYSTEM, content=system_prompt))

        # Check if we should use tools
        if not self.should_use_tools(model):
            # Fallback to regular streaming chat
            return await self._stream_chat(messages, model, temperature, max_tokens), messages

        # Get available tools
        tools = self.executor.get_available_tools()

        # Make the initial request with tools
        try:
            response = await asyncio.to_thread(
                self.provider.chat,
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,
            )

            # Check if we got tool calls
            if response.tool_calls:
                return await self._handle_tool_calls(
                    messages, response, model, temperature, max_tokens, tools
                )
            else:
                # No tool calls, just return the response
                self._print_response(response.content)
                messages.append(Message(role=Role.ASSISTANT, content=response.content))
                return response.content, messages

        except Exception as e:
            error_msg = f"Error during tool-enabled chat: {str(e)}"
            self.console.print(f"[{self.theme.error}]{error_msg}[/{self.theme.error}]")
            return error_msg, messages

    async def _handle_tool_calls(
        self,
        messages: list[Message],
        response,
        model: str,
        temperature: float,
        max_tokens: int,
        tools: list[Tool],
    ) -> tuple[str, list[Message]]:
        """Handle tool calls from the AI."""
        # Print AI's intent
        if response.content:
            self._print_response(response.content)

        # Add assistant message with tool calls
        messages.append(
            Message(
                role=Role.ASSISTANT, content=response.content or "", tool_calls=response.tool_calls
            )
        )

        # Execute each tool call
        self.console.print(f"\n[{self.theme.dim}]Executing tools...[/{self.theme.dim}]")

        for tool_call in response.tool_calls:
            # Show tool execution with timer
            start_time = time.time()

            self.console.print(
                f"\n[{self.theme.info}]→ Running tool:[/{self.theme.info}] {tool_call.name}"
            )
            if tool_call.arguments:
                args_str = json.dumps(tool_call.arguments, indent=2)
                self.console.print(
                    Panel(
                        Syntax(args_str, "json", theme=self.theme.code_theme),
                        title=f"[{self.theme.info}]Arguments[/{self.theme.info}]",
                        border_style=self.theme.info,
                        expand=False,
                    )
                )

            # Execute the tool with timer display
            # Start async execution
            async def execute_with_timer(tc=tool_call):
                nonlocal result
                result = await self.executor.execute_tool_call(tc)

            result = None
            task = asyncio.create_task(execute_with_timer())

            # Use centralized timer utility
            from coda.apps.cli.utils import simple_thinking_animation

            await simple_thinking_animation(
                task=task,
                console=self.console,
                message="Executing",
                theme_info=self.theme.info,
                theme_bold=self.theme.bold,
                min_display_time=0.0,  # No minimum display time for tool execution
            )

            # Get the result
            await task
            elapsed = time.time() - start_time

            # Show execution time
            self.console.print(f"[{self.theme.dim}]Completed in {elapsed:.1f}s[/{self.theme.dim}]")

            # Show result
            if result.is_error:
                self.console.print(
                    f"[{self.theme.error}]✗ Error:[/{self.theme.error}] {result.content}"
                )
            else:
                self.console.print(f"[{self.theme.success}]✓ Result:[/{self.theme.success}]")
                # Try to format as JSON if possible
                try:
                    result_json = json.loads(result.content)
                    self.console.print(
                        Panel(
                            Syntax(
                                json.dumps(result_json, indent=2),
                                "json",
                                theme=self.theme.code_theme,
                            ),
                            border_style=self.theme.success,
                            expand=False,
                        )
                    )
                except (json.JSONDecodeError, TypeError):
                    # Not JSON, print as text
                    self.console.print(
                        Panel(result.content, border_style=self.theme.info, expand=False)
                    )

            # Add tool result to messages
            messages.append(
                Message(role=Role.TOOL, content=result.content, tool_call_id=result.tool_call_id)
            )

        # Make another request to get the final response
        self.console.print(f"\n[{self.theme.dim}]Getting final response...[/{self.theme.dim}]")

        try:
            final_response = await asyncio.to_thread(
                self.provider.chat,
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                tools=tools,  # Still provide tools in case AI needs more
            )

            # Print and return the final response
            self.console.print(f"\n[{self.theme.info} bold]Assistant:[/{self.theme.info} bold]")
            self._print_response(final_response.content)

            messages.append(Message(role=Role.ASSISTANT, content=final_response.content))
            return final_response.content, messages

        except Exception as e:
            error_msg = f"Error getting final response: {str(e)}"
            self.console.print(f"[{self.theme.error}]{error_msg}[/{self.theme.error}]")
            return error_msg, messages

    async def _stream_chat(
        self,
        messages: list[Message],
        model: str,
        temperature: float,
        max_tokens: int,
    ) -> str:
        """Fallback streaming chat without tools."""
        full_response = ""
        first_chunk = True

        try:
            stream = self.provider.chat_stream(
                messages=messages,
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
            )

            for chunk in stream:
                if first_chunk:
                    self.console.print(
                        f"\n[{self.theme.info} bold]Assistant:[/{self.theme.info} bold] ", end=""
                    )
                    first_chunk = False

                # Check for interrupt
                if self.cli.interrupt_event.is_set():
                    self.console.print(
                        f"\n\n[{self.theme.warning}]Response interrupted by user[/{self.theme.warning}]"
                    )
                    break

                # Stream the response
                self.console.print(chunk.content, end="")
                full_response += chunk.content

            # Add newline after streaming
            if full_response:
                self.console.print()

        except Exception as e:
            self.console.print(
                f"\n[{self.theme.error}]Error during streaming: {str(e)}[/{self.theme.error}]"
            )

        return full_response

    def _print_response(self, content: str):
        """Print AI response with formatting."""
        self.console.print(
            f"\n[{self.theme.info} bold]Assistant:[/{self.theme.info} bold] {content}"
        )
