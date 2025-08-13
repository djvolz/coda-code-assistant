"""CLI event handler for agent events."""

import json

from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.syntax import Syntax

from coda.services.agents.agent_types import AgentEvent, AgentEventHandler, AgentEventType


class CLIAgentEventHandler(AgentEventHandler):
    """Handles agent events for CLI display."""

    def __init__(self, console, theme_manager):
        self.console = console
        self.theme = theme_manager.get_console_theme()
        self.markdown_buffer = None  # Initialize markdown buffer when needed

    def handle_event(self, event: AgentEvent) -> None:
        """Handle agent event with appropriate CLI formatting."""

        if event.type == AgentEventType.THINKING:
            self.console.print(
                f"[{self.theme.bold} {self.theme.info}]{event.message}[/{self.theme.bold} {self.theme.info}]"
            )
        elif event.type == AgentEventType.TOOL_EXECUTION_START:
            # Finalize any existing markdown buffer before tool output
            if self.markdown_buffer:
                self.markdown_buffer.finalize()
                self.markdown_buffer = None

            self.console.print(f"\n[{self.theme.info}]→ {event.message}[/{self.theme.info}]")
            if event.data and "arguments" in event.data:
                args_str = json.dumps(event.data["arguments"], indent=2)
                self.console.print(
                    Panel(
                        Syntax(args_str, "json", theme="monokai"),
                        title=f"[{self.theme.info}]Arguments[/{self.theme.info}]",
                        expand=False,
                    )
                )
        elif event.type == AgentEventType.TOOL_EXECUTION_END:
            self.console.print(f"[{self.theme.success}]✓ Result:[/{self.theme.success}]")
            if event.data and "output" in event.data:
                output = event.data["output"]
                # Try to format as JSON
                try:
                    result_json = json.loads(output)
                    self.console.print(
                        Panel(
                            Syntax(json.dumps(result_json, indent=2), "json", theme="monokai"),
                            expand=False,
                        )
                    )
                except Exception:
                    self.console.print(Panel(output, expand=False))
        elif event.type == AgentEventType.ERROR:
            # Finalize any existing markdown buffer before error output
            if self.markdown_buffer:
                self.markdown_buffer.finalize()
                self.markdown_buffer = None

            if event.data and event.data.get("is_error", False):
                self.console.print(
                    f"[{self.theme.error}]✗ Error:[/{self.theme.error}] {event.data.get('output', event.message)}"
                )
            else:
                self.console.print(
                    f"[{self.theme.error}]Error:[/{self.theme.error}] {event.message}"
                )
        elif event.type == AgentEventType.WARNING:
            self.console.print(f"[{self.theme.warning}]{event.message}[/{self.theme.warning}]")
        elif event.type == AgentEventType.STATUS_UPDATE:
            self.console.print(f"[{self.theme.info}]{event.message}[/{self.theme.info}]")
        elif event.type == AgentEventType.RESPONSE_CHUNK:
            # Initialize markdown buffer if needed
            if self.markdown_buffer is None:
                self.markdown_buffer = MarkdownStreamBuffer(self.console, self.theme)

            # Add chunk to markdown buffer for processing
            self.markdown_buffer.add_chunk(event.message)
        elif event.type == AgentEventType.RESPONSE_COMPLETE:
            # Finalize markdown buffer to render any remaining content
            if self.markdown_buffer:
                self.markdown_buffer.finalize()
                self.markdown_buffer = None

            # Don't print the response complete message since we've already rendered the content
            # self.console.print(
            #     f"\n[{self.theme.bold} {self.theme.info}]{agent_name}:[/{self.theme.bold} {self.theme.info}] {event.message}"
            # )
        elif event.type == AgentEventType.FINAL_ANSWER_NEEDED:
            self.console.print(f"[{self.theme.warning}]{event.message}[/{self.theme.warning}]")


class MarkdownStreamBuffer:
    """Buffer for streaming markdown content with live display."""

    def __init__(self, console, theme):
        self.console = console
        self.theme = theme
        self.buffer = ""
        self.live = None
        self.show_streaming = True  # Control whether to show streaming

    def add_chunk(self, chunk: str):
        """Add a new chunk to the buffer and optionally show streaming."""
        self.buffer += chunk

        if not self.show_streaming:
            return

        # Create live display on first chunk
        if self.live is None:
            # For long content, use a simpler approach
            # Just show a status message instead of the full content
            status_text = f"Receiving response... ({len(self.buffer.split())} words)"
            panel = Panel(
                status_text,
                title=f"[{self.theme.info}]Streaming[/{self.theme.info}]",
                border_style=self.theme.dim,
                expand=False,
            )
            # Use transient=True for the status panel
            self.live = Live(panel, console=self.console, refresh_per_second=4, transient=True)
            self.live.start()
        else:
            # Update just the word count, not the full content
            word_count = len(self.buffer.split())
            status_text = f"Receiving response... ({word_count} words)"
            panel = Panel(
                status_text,
                title=f"[{self.theme.info}]Streaming[/{self.theme.info}]",
                border_style=self.theme.dim,
                expand=False,
            )
            self.live.update(panel)

    def finalize(self):
        """Stop live display and render the complete buffer as rich markdown."""
        # Stop the live display
        if self.live:
            self.live.stop()
            self.live = None

        if self.buffer.strip():
            try:
                # Render the complete content as beautiful markdown
                markdown = Markdown(self.buffer.strip())
                self.console.print(markdown)

            except Exception:
                # Fall back to plain text if markdown parsing fails
                self.console.print(self.buffer.strip())  # Add final newline if needed
