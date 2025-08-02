"""CLI event handler for agent events."""

import json

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax

from coda.base.theme import ThemeManager
from coda.services.agents.agent_types import AgentEvent, AgentEventHandler, AgentEventType


class CLIAgentEventHandler(AgentEventHandler):
    """Handles agent events for CLI display."""

    def __init__(self, console: Console, theme_manager: ThemeManager):
        self.console = console
        self.theme = theme_manager.get_console_theme()

    def handle_event(self, event: AgentEvent) -> None:
        """Handle agent event with appropriate CLI formatting."""
        if event.type == AgentEventType.THINKING:
            self.console.print(
                f"[{self.theme.bold} {self.theme.info}]{event.message}[/{self.theme.bold} {self.theme.info}]"
            )
        elif event.type == AgentEventType.TOOL_EXECUTION_START:
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
            # For streaming text chunks
            end_char = event.data.get("end", "") if event.data else ""
            self.console.print(event.message, end=end_char)
        elif event.type == AgentEventType.RESPONSE_COMPLETE:
            agent_name = event.data.get("agent_name", "Agent") if event.data else "Agent"
            self.console.print(
                f"\n[{self.theme.bold} {self.theme.info}]{agent_name}:[/{self.theme.bold} {self.theme.info}] {event.message}"
            )
        elif event.type == AgentEventType.FINAL_ANSWER_NEEDED:
            self.console.print(f"[{self.theme.warning}]{event.message}[/{self.theme.warning}]")
