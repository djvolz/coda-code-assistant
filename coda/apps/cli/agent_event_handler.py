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
        self.max_preview_lines = 4  # Show first 4 lines as preview
        self.max_preview_chars = 200  # Limit total preview characters

    def add_chunk(self, chunk: str):
        """Add a new chunk to the buffer and optionally show streaming."""
        self.buffer += chunk

        if not self.show_streaming:
            return

        # Create live display on first chunk
        if self.live is None:
            preview_content = self._get_preview_content()
            panel = Panel(
                preview_content,
                title=f"[{self.theme.info}]Response Preview[/{self.theme.info}]",
                border_style=self.theme.dim,
                expand=False,
            )
            # Use transient=True for the status panel
            self.live = Live(panel, console=self.console, refresh_per_second=4, transient=True)
            self.live.start()
        else:
            # Update preview content
            preview_content = self._get_preview_content()
            panel = Panel(
                preview_content,
                title=f"[{self.theme.info}]Response Preview[/{self.theme.info}]",
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

    def _get_preview_content(self) -> str:
        """Generate preview content showing first few lines and word count.

        Returns:
            Formatted preview string with first lines and metadata
        """
        if not self.buffer.strip():
            return "Receiving response..."

        try:
            # Get word count
            word_count = len(self.buffer.split())

            # Split buffer into lines and get first few lines
            lines = self.buffer.strip().split("\n")
            preview_lines = []
            total_chars = 0

            for line in lines[: self.max_preview_lines]:
                # Clean line of any control characters that might cause issues
                line = "".join(char for char in line if char.isprintable() or char.isspace())

                # Truncate very long lines to prevent UI issues
                if len(line) > 80:
                    line = line[:77] + "..."

                # Check if adding this line would exceed character limit
                if total_chars + len(line) > self.max_preview_chars:
                    break

                preview_lines.append(line)
                total_chars += len(line)

            # Join preview lines
            preview_text = "\n".join(preview_lines)

            # Add ellipsis if there's more content
            has_more = len(lines) > len(preview_lines) or total_chars >= self.max_preview_chars
            ellipsis = "\n..." if has_more and preview_text else ""

            # Add word count at the end
            status_line = f"\n({word_count} words)"

            return f"{preview_text}{ellipsis}{status_line}"

        except Exception:
            # Fallback to simple word count if preview generation fails
            word_count = len(self.buffer.split()) if self.buffer else 0
            return f"Receiving response... ({word_count} words)"
