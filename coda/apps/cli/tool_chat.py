"""Tool-enabled chat functionality for the CLI."""

import asyncio
import json

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
            self.console.print(f"[red]{error_msg}[/red]")
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
        self.console.print("\n[dim]Executing tools...[/dim]")

        for tool_call in response.tool_calls:
            # Show tool execution
            self.console.print(f"\n[cyan]→ Running tool:[/cyan] {tool_call.name}")
            if tool_call.arguments:
                args_str = json.dumps(tool_call.arguments, indent=2)
                self.console.print(
                    Panel(
                        Syntax(args_str, "json", theme="monokai"),
                        title="[cyan]Arguments[/cyan]",
                        expand=False,
                    )
                )

            # Execute the tool
            result = await self.executor.execute_tool_call(tool_call)

            # Show result
            if result.is_error:
                self.console.print(f"[red]✗ Error:[/red] {result.content}")
            else:
                self.console.print("[green]✓ Result:[/green]")
                # Try to format as JSON if possible
                try:
                    result_json = json.loads(result.content)
                    self.console.print(
                        Panel(
                            Syntax(json.dumps(result_json, indent=2), "json", theme="monokai"),
                            expand=False,
                        )
                    )
                except (json.JSONDecodeError, TypeError):
                    # Not JSON, print as text
                    self.console.print(Panel(result.content, expand=False))

            # Add tool result to messages
            messages.append(
                Message(role=Role.TOOL, content=result.content, tool_call_id=result.tool_call_id)
            )

        # Make another request to get the final response
        self.console.print("\n[dim]Getting final response...[/dim]")

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
            self.console.print("\n[bold cyan]Assistant:[/bold cyan]")
            self._print_response(final_response.content)

            messages.append(Message(role=Role.ASSISTANT, content=final_response.content))
            return final_response.content, messages

        except Exception as e:
            error_msg = f"Error getting final response: {str(e)}"
            self.console.print(f"[red]{error_msg}[/red]")
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
                    self.console.print("\n[bold cyan]Assistant:[/bold cyan] ", end="")
                    first_chunk = False

                # Check for interrupt
                if self.cli.interrupt_event.is_set():
                    self.console.print("\n\n[yellow]Response interrupted by user[/yellow]")
                    break

                # Stream the response
                self.console.print(chunk.content, end="")
                full_response += chunk.content

            # Add newline after streaming
            if full_response:
                self.console.print()

        except Exception as e:
            self.console.print(f"\n[red]Error during streaming: {str(e)}[/red]")

        return full_response

    def _print_response(self, content: str):
        """Print AI response with formatting."""
        self.console.print(f"\n[bold cyan]Assistant:[/bold cyan] {content}")
