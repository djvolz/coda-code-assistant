"""Shared command handling logic for CLI modes."""

from abc import ABC, abstractmethod
from enum import Enum
from typing import Any

from rich.console import Console

from coda.base.providers import ProviderFactory

from .modes import DeveloperMode, get_mode_description


class CommandResult(Enum):
    """Result types for command processing."""

    CONTINUE = "continue"  # Command handled, continue to next iteration
    EXIT = "exit"  # Exit the application
    CLEAR = "clear"  # Clear conversation
    HANDLED = "handled"  # Command handled successfully


class CommandHandler(ABC):
    """Base class for command handling with shared logic."""

    def __init__(self, console: Console):
        self.console = console
        self.current_mode = DeveloperMode.GENERAL
        self.current_model = None
        self.available_models = []
        self.provider_name = None
        self.provider_instance = None
        self.factory = None

    def set_provider_info(
        self,
        provider_name: str,
        provider_instance: Any,
        factory: ProviderFactory,
        model: str,
        models: list,
    ):
        """Set provider information for command processing."""
        self.provider_name = provider_name
        self.provider_instance = provider_instance
        self.factory = factory
        self.current_model = model
        self.available_models = models

    @abstractmethod
    def show_help(self) -> CommandResult:
        """Show help information. Must be implemented by subclasses."""
        pass

    def switch_mode(self, mode_str: str) -> CommandResult:
        """Switch to a different developer mode."""
        if not mode_str:
            # Show current mode and available modes
            self.console.print(f"\n[yellow]Current mode:[/yellow] {self.current_mode.value}")
            self.console.print(f"[dim]{get_mode_description(self.current_mode)}[/dim]\n")

            self.console.print("[bold]Available modes:[/bold]")
            for mode in DeveloperMode:
                if mode == self.current_mode:
                    self.console.print(
                        f"  [green]▶ {mode.value}[/green] - {get_mode_description(mode)}"
                    )
                else:
                    self.console.print(
                        f"  [cyan]{mode.value}[/cyan] - {get_mode_description(mode)}"
                    )

            self.console.print("\n[dim]Usage: /mode <mode_name>[/dim]")
            return CommandResult.HANDLED

        try:
            self.current_mode = DeveloperMode(mode_str.lower())
            self.console.print(f"[green]Switched to {self.current_mode.value} mode[/green]")
            self.console.print(f"[dim]{get_mode_description(self.current_mode)}[/dim]")
            return CommandResult.HANDLED
        except ValueError:
            self.console.print(f"[red]Invalid mode: {mode_str}[/red]")
            valid_modes = ", ".join(m.value for m in DeveloperMode)
            self.console.print(f"Valid modes: {valid_modes}")
            return CommandResult.HANDLED

    def switch_model(self, model_name: str) -> CommandResult:
        """Switch to a different model."""
        if not self.available_models:
            self.console.print("[yellow]No models available.[/yellow]")
            return CommandResult.HANDLED

        if not model_name:
            # Show current model and available models
            self.console.print(f"\n[yellow]Current model:[/yellow] {self.current_model}")
            self.console.print("\n[bold]Available models:[/bold]")

            # Show top 10 models
            for i, model in enumerate(self.available_models[:10]):
                self.console.print(f"  {i + 1}. [cyan]{model.id}[/cyan]")

            if len(self.available_models) > 10:
                self.console.print(f"  [dim]... and {len(self.available_models) - 10} more[/dim]")

            self.console.print("\n[dim]Usage: /model <model_name>[/dim]")
            return CommandResult.HANDLED

        # Try to switch to the specified model
        matching_models = [m for m in self.available_models if model_name.lower() in m.id.lower()]
        if matching_models:
            self.current_model = matching_models[0].id
            self.console.print(f"[green]Switched to model: {self.current_model}[/green]")
        else:
            self.console.print(f"[red]Model not found: {model_name}[/red]")

        return CommandResult.HANDLED

    def show_provider_info(self, args: str) -> CommandResult:
        """Show provider information."""
        if not args:
            self.console.print("\n[bold]Provider Management[/bold]")
            self.console.print(f"[yellow]Current provider:[/yellow] {self.provider_name}\n")

            self.console.print("[bold]Available providers:[/bold]")

            # Show all known providers with status
            if self.factory:
                available = self.factory.list_available()
                for provider in available:
                    if provider == self.provider_name:
                        self.console.print(f"  [green]▶ {provider}[/green]")
                    else:
                        self.console.print(f"  [cyan]{provider}[/cyan]")
            else:
                # Default list when factory is not available
                providers = [
                    ("oci_genai", "Oracle Cloud Infrastructure GenAI"),
                    ("ollama", "Local models via Ollama"),
                    ("litellm", "100+ providers via LiteLLM"),
                ]
                for provider_id, desc in providers:
                    if provider_id == self.provider_name:
                        self.console.print(f"  [green]▶ {provider_id}[/green] - {desc}")
                    else:
                        self.console.print(f"  [cyan]{provider_id}[/cyan] - {desc}")

            self.console.print("\n[dim]Note: Provider switching requires restart[/dim]")
        else:
            if self.provider_name and args.lower() == self.provider_name.lower():
                self.console.print(f"[green]Already using {self.provider_name} provider[/green]")
            else:
                self.console.print(
                    "[yellow]Provider switching not supported in current mode. "
                    "Please restart with --provider option.[/yellow]"
                )

        return CommandResult.HANDLED

    def clear_conversation(self) -> CommandResult:
        """Clear the conversation."""
        return CommandResult.CLEAR

    def exit_application(self) -> CommandResult:
        """Exit the application."""
        return CommandResult.EXIT

    def handle_tools_command(self, args: str) -> CommandResult:
        """Handle tools command and subcommands."""
        try:
            from coda.services.tools import (  # noqa: F401
                get_available_tools,
                get_tool_categories,
                get_tool_info,
                get_tool_stats,
                list_tools_by_category,
            )
        except ImportError:
            self.console.print("[red]Tools system not available. Please check installation.[/red]")
            return CommandResult.HANDLED

        if not args:
            # Show main tools menu
            self._show_tools_overview()
            return CommandResult.HANDLED

        parts = args.split(maxsplit=1)
        subcommand = parts[0].lower()
        subargs = parts[1] if len(parts) > 1 else ""

        if subcommand == "list":
            self._show_tools_list(subargs)
        elif subcommand == "info":
            self._show_tool_info(subargs)
        elif subcommand == "categories":
            self._show_tool_categories()
        elif subcommand == "stats":
            self._show_tool_stats()
        elif subcommand == "help":
            self._show_tools_help()
        else:
            self.console.print(f"[red]Unknown tools subcommand: {subcommand}[/red]")
            self.console.print("Usage: /tools [list|info|categories|stats|help]")

        return CommandResult.HANDLED

    def _show_tools_overview(self):
        """Show tools overview."""
        from coda.services.tools import get_tool_stats

        stats = get_tool_stats()

        self.console.print("\n[bold]🔧 Coda Tools System[/bold]")
        self.console.print(f"Total tools: [cyan]{stats['total_tools']}[/cyan]")
        self.console.print(f"Categories: [cyan]{stats['categories']}[/cyan]")
        if stats["dangerous_tools"] > 0:
            self.console.print(f"Dangerous tools: [yellow]{stats['dangerous_tools']}[/yellow]")

        self.console.print("\n[bold]Available commands:[/bold]")
        self.console.print("  [cyan]/tools list[/cyan]       - List all available tools")
        self.console.print("  [cyan]/tools list <category>[/cyan] - List tools in a category")
        self.console.print("  [cyan]/tools info <tool>[/cyan]    - Show detailed tool information")
        self.console.print("  [cyan]/tools categories[/cyan]     - Show all tool categories")
        self.console.print("  [cyan]/tools stats[/cyan]          - Show tool statistics")
        self.console.print("  [cyan]/tools help[/cyan]           - Show detailed help")

        self.console.print(
            "\n[dim]Use AI to call tools in conversation (tools currently read-only)[/dim]"
        )

    def _show_tools_list(self, category: str = None):
        """Show list of tools, optionally filtered by category."""
        from coda.services.tools import get_available_tools, get_tool_categories

        if category:
            # List tools in specific category
            tools = get_available_tools(category)
            if not tools:
                available_categories = get_tool_categories()
                self.console.print(f"[red]Category '{category}' not found.[/red]")
                self.console.print(f"Available categories: {', '.join(available_categories)}")
                return

            self.console.print(f"\n[bold]Tools in '{category}' category:[/bold]")
            for tool in tools:
                danger_indicator = " ⚠️" if tool.dangerous else ""
                self.console.print(f"  [cyan]{tool.name}[/cyan]{danger_indicator}")
                self.console.print(f"    {tool.description}")
        else:
            # List all tools grouped by category
            from coda.services.tools import get_tool_info, list_tools_by_category

            tools_by_cat = list_tools_by_category()

            self.console.print("\n[bold]Available Tools by Category:[/bold]")
            for cat, tool_names in tools_by_cat.items():
                self.console.print(f"\n[yellow]{cat.title()}:[/yellow]")
                for tool_name in tool_names:
                    tool_info = get_tool_info(tool_name)
                    if tool_info:
                        danger_indicator = " ⚠️" if tool_info.get("dangerous", False) else ""
                        self.console.print(
                            f"  [cyan]{tool_name}[/cyan]{danger_indicator} - {tool_info['description']}"
                        )

    def _show_tool_info(self, tool_name: str):
        """Show detailed information about a specific tool."""
        if not tool_name:
            self.console.print("[red]Please specify a tool name.[/red]")
            self.console.print("Usage: /tools info <tool_name>")
            return

        from coda.services.tools import get_tool_info

        tool_info = get_tool_info(tool_name)
        if not tool_info:
            self.console.print(f"[red]Tool '{tool_name}' not found.[/red]")
            return

        self.console.print(f"\n[bold]Tool: {tool_info['name']}[/bold]")
        self.console.print(f"Category: [cyan]{tool_info['category']}[/cyan]")
        self.console.print(f"Server: [cyan]{tool_info['server']}[/cyan]")
        if tool_info["dangerous"]:
            self.console.print("⚠️  [yellow]This tool requires special permissions[/yellow]")

        self.console.print("\n[bold]Description:[/bold]")
        self.console.print(f"  {tool_info['description']}")

        if tool_info["parameters"]:
            self.console.print("\n[bold]Parameters:[/bold]")
            for param_name, param_info in tool_info["parameters"].items():
                required_str = " (required)" if param_info["required"] else " (optional)"
                default_str = (
                    f" [default: {param_info['default']}]"
                    if param_info.get("default") is not None
                    else ""
                )

                self.console.print(
                    f"  [cyan]{param_name}[/cyan] ({param_info['type']}){required_str}{default_str}"
                )
                self.console.print(f"    {param_info['description']}")
        else:
            self.console.print("\n[dim]No parameters required[/dim]")

    def _show_tool_categories(self):
        """Show all tool categories."""
        from coda.services.tools import get_tool_categories, list_tools_by_category

        categories = get_tool_categories()
        tools_by_cat = list_tools_by_category()

        self.console.print("\n[bold]Tool Categories:[/bold]")
        for category in sorted(categories):
            tool_count = len(tools_by_cat.get(category, []))
            self.console.print(f"  [cyan]{category}[/cyan] ({tool_count} tools)")

    def _show_tool_stats(self):
        """Show tool statistics."""
        from coda.services.tools import get_tool_stats

        stats = get_tool_stats()

        self.console.print("\n[bold]Tool System Statistics:[/bold]")
        self.console.print(f"Total tools: [cyan]{stats['total_tools']}[/cyan]")
        self.console.print(f"Categories: [cyan]{stats['categories']}[/cyan]")
        self.console.print(f"Dangerous tools: [yellow]{stats['dangerous_tools']}[/yellow]")

        self.console.print("\n[bold]Tools by category:[/bold]")
        for category, count in stats["tools_by_category"].items():
            self.console.print(f"  [cyan]{category}[/cyan]: {count}")

        if stats["dangerous_tool_names"]:
            self.console.print("\n[bold]Dangerous tools:[/bold]")
            for tool_name in stats["dangerous_tool_names"]:
                self.console.print(f"  [yellow]{tool_name}[/yellow] ⚠️")

    def _show_tools_help(self):
        """Show detailed tools help."""
        self.console.print("\n[bold]🔧 Coda Tools System Help[/bold]")

        self.console.print("\n[bold]What are tools?[/bold]")
        self.console.print("Tools are functions that AI can call to perform specific tasks like:")
        self.console.print("  • File operations (read, write, edit)")
        self.console.print("  • Shell command execution")
        self.console.print("  • Web searches and content fetching")
        self.console.print("  • Git operations")

        self.console.print("\n[bold]How to use tools:[/bold]")
        self.console.print("1. Tools are automatically available to the AI")
        self.console.print("2. Simply ask the AI to perform tasks that require tools")
        self.console.print("3. The AI will call appropriate tools automatically")
        self.console.print("4. You can see tool results in the conversation")

        self.console.print("\n[bold]Safety features:[/bold]")
        self.console.print("• Dangerous tools (⚠️) require explicit approval")
        self.console.print("• Shell commands are filtered for security")
        self.console.print("• File operations use safe paths")
        self.console.print("• All tool calls are logged")

        self.console.print("\n[bold]Available commands:[/bold]")
        self.console.print("  [cyan]/tools[/cyan]                 - Show tools overview")
        self.console.print("  [cyan]/tools list[/cyan]             - List all tools")
        self.console.print("  [cyan]/tools list <category>[/cyan]  - List tools in category")
        self.console.print("  [cyan]/tools info <tool>[/cyan]      - Show tool details")
        self.console.print("  [cyan]/tools categories[/cyan]       - List categories")
        self.console.print("  [cyan]/tools stats[/cyan]            - Show statistics")
