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
        from coda.services.config import get_config_service

        config_service = get_config_service()
        self.theme_manager = config_service.theme_manager
        self.console_theme = self.theme_manager.get_console_theme()

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
            self.console.print(
                f"\n[{self.console_theme.warning}]Current mode:[/{self.console_theme.warning}] {self.current_mode.value}"
            )
            self.console.print(
                f"[{self.console_theme.dim}]{get_mode_description(self.current_mode)}[/{self.console_theme.dim}]\n"
            )

            self.console.print(
                f"[{self.console_theme.bold}]Available modes:[/{self.console_theme.bold}]"
            )
            for mode in DeveloperMode:
                if mode == self.current_mode:
                    self.console.print(
                        f"  [{self.console_theme.success}]▶ {mode.value}[/{self.console_theme.success}] - {get_mode_description(mode)}"
                    )
                else:
                    self.console.print(
                        f"  [{self.console_theme.info}]{mode.value}[/{self.console_theme.info}] - {get_mode_description(mode)}"
                    )

            self.console.print(
                f"\n[{self.console_theme.dim}]Usage: /mode <mode_name>[/{self.console_theme.dim}]"
            )
            return CommandResult.HANDLED

        try:
            self.current_mode = DeveloperMode(mode_str.lower())
            self.console.print(
                f"[{self.console_theme.success}]Switched to {self.current_mode.value} mode[/{self.console_theme.success}]"
            )
            self.console.print(
                f"[{self.console_theme.dim}]{get_mode_description(self.current_mode)}[/{self.console_theme.dim}]"
            )
            return CommandResult.HANDLED
        except ValueError:
            self.console.print(
                f"[{self.console_theme.error}]Invalid mode: {mode_str}[/{self.console_theme.error}]"
            )
            valid_modes = ", ".join(m.value for m in DeveloperMode)
            self.console.print(f"Valid modes: {valid_modes}")
            return CommandResult.HANDLED

    def switch_model(self, model_name: str) -> CommandResult:
        """Switch to a different model."""
        if not self.available_models:
            self.console.print(
                f"[{self.console_theme.warning}]No models available.[/{self.console_theme.warning}]"
            )
            return CommandResult.HANDLED

        if not model_name:
            # Show current model and available models
            self.console.print(
                f"\n[{self.console_theme.warning}]Current model:[/{self.console_theme.warning}] {self.current_model}"
            )
            self.console.print(
                f"\n[{self.console_theme.bold}]Available models:[/{self.console_theme.bold}]"
            )

            # Show top 10 models
            for i, model in enumerate(self.available_models[:10]):
                self.console.print(
                    f"  {i + 1}. [{self.console_theme.info}]{model.id}[/{self.console_theme.info}]"
                )

            if len(self.available_models) > 10:
                self.console.print(
                    f"  [{self.console_theme.dim}]... and {len(self.available_models) - 10} more[/{self.console_theme.dim}]"
                )

            self.console.print(
                f"\n[{self.console_theme.dim}]Usage: /model <model_name>[/{self.console_theme.dim}]"
            )
            return CommandResult.HANDLED

        # Try to switch to the specified model
        matching_models = [m for m in self.available_models if model_name.lower() in m.id.lower()]
        if matching_models:
            selected_model = matching_models[0]
            self.current_model = selected_model.id
            self.console.print(
                f"[{self.console_theme.success}]Switched to model: {self.current_model}[/{self.console_theme.success}]"
            )
        else:
            self.console.print(
                f"[{self.console_theme.error}]Model not found: {model_name}[/{self.console_theme.error}]"
            )

        return CommandResult.HANDLED

    def show_provider_info(self, args: str) -> CommandResult:
        """Show provider information."""
        if not args:
            self.console.print(
                f"\n[{self.console_theme.bold}]Provider Management[/{self.console_theme.bold}]"
            )
            self.console.print(
                f"[{self.console_theme.warning}]Current provider:[/{self.console_theme.warning}] {self.provider_name}\n"
            )

            self.console.print(
                f"[{self.console_theme.bold}]Available providers:[/{self.console_theme.bold}]"
            )

            # Show all known providers with status
            if self.factory:
                available = self.factory.list_available()
                for provider in available:
                    if provider == self.provider_name:
                        self.console.print(
                            f"  [{self.console_theme.success}]▶ {provider}[/{self.console_theme.success}]"
                        )
                    else:
                        self.console.print(
                            f"  [{self.console_theme.info}]{provider}[/{self.console_theme.info}]"
                        )
            else:
                # Default list when factory is not available
                providers = [
                    ("oci_genai", "Oracle Cloud Infrastructure GenAI"),
                    ("ollama", "Local models via Ollama"),
                    ("litellm", "100+ providers via LiteLLM"),
                ]
                for provider_id, desc in providers:
                    if provider_id == self.provider_name:
                        self.console.print(
                            f"  [{self.console_theme.success}]▶ {provider_id}[/{self.console_theme.success}] - {desc}"
                        )
                    else:
                        self.console.print(
                            f"  [{self.console_theme.info}]{provider_id}[/{self.console_theme.info}] - {desc}"
                        )

            self.console.print(
                f"\n[{self.console_theme.dim}]Note: Provider switching requires restart[/{self.console_theme.dim}]"
            )
        else:
            if self.provider_name and args.lower() == self.provider_name.lower():
                self.console.print(
                    f"[{self.console_theme.success}]Already using {self.provider_name} provider[/{self.console_theme.success}]"
                )
            else:
                self.console.print(
                    f"[{self.console_theme.warning}]Provider switching not supported in current mode. "
                    f"Please restart with --provider option.[/{self.console_theme.warning}]"
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
            self.console.print(
                "[{self.console_theme.error}]Tools system not available. Please check installation.[/{self.console_theme.error}]"
            )
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
            self.console.print(
                f"[{self.console_theme.error}]Unknown tools subcommand: {subcommand}[/{self.console_theme.error}]"
            )
            self.console.print("Usage: /tools [list|info|categories|stats|help]")

        return CommandResult.HANDLED

    def _show_tools_overview(self):
        """Show tools overview."""
        from coda.services.tools import get_tool_stats

        stats = get_tool_stats()

        self.console.print(
            f"\n[{self.console_theme.bold}]🔧 Coda Tools System[/{self.console_theme.bold}]"
        )
        self.console.print(
            f"Total tools: [{self.console_theme.info}]{stats['total_tools']}[/{self.console_theme.info}]"
        )
        self.console.print(
            f"Categories: [{self.console_theme.info}]{stats['categories']}[/{self.console_theme.info}]"
        )
        if stats["dangerous_tools"] > 0:
            self.console.print(
                f"Dangerous tools: [{self.console_theme.warning}]{stats['dangerous_tools']}[/{self.console_theme.warning}]"
            )

        self.console.print(
            f"\n[{self.console_theme.bold}]Available commands:[/{self.console_theme.bold}]"
        )
        self.console.print(
            f"  [{self.console_theme.info}]/tools list[/{self.console_theme.info}]       - List all available tools"
        )
        self.console.print(
            f"  [{self.console_theme.info}]/tools list <category>[/{self.console_theme.info}] - List tools in a category"
        )
        self.console.print(
            f"  [{self.console_theme.info}]/tools info <tool>[/{self.console_theme.info}]    - Show detailed tool information"
        )
        self.console.print(
            f"  [{self.console_theme.info}]/tools categories[/{self.console_theme.info}]     - Show all tool categories"
        )
        self.console.print(
            f"  [{self.console_theme.info}]/tools stats[/{self.console_theme.info}]          - Show tool statistics"
        )
        self.console.print(
            f"  [{self.console_theme.info}]/tools help[/{self.console_theme.info}]           - Show detailed help"
        )

        self.console.print(
            f"\n[{self.console_theme.dim}]Use AI to call tools in conversation (tools currently read-only)[/{self.console_theme.dim}]"
        )

    def _show_tools_list(self, category: str = None):
        """Show list of tools, optionally filtered by category."""
        from coda.services.tools import get_available_tools, get_tool_categories

        if category:
            # List tools in specific category
            tools = get_available_tools(category)
            if not tools:
                available_categories = get_tool_categories()
                self.console.print(
                    f"[{self.console_theme.error}]Category '{category}' not found.[/{self.console_theme.error}]"
                )
                self.console.print(f"Available categories: {', '.join(available_categories)}")
                return

            self.console.print(
                f"\n[{self.console_theme.bold}]Tools in '{category}' category:[/{self.console_theme.bold}]"
            )
            for tool in tools:
                danger_indicator = " ⚠️" if tool.dangerous else ""
                self.console.print(
                    f"  [{self.console_theme.info}]{tool.name}[/{self.console_theme.info}]{danger_indicator}"
                )
                self.console.print(f"    {tool.description}")
        else:
            # List all tools grouped by category
            from coda.services.tools import get_tool_info, list_tools_by_category

            tools_by_cat = list_tools_by_category()

            self.console.print(
                f"\n[{self.console_theme.bold}]Available Tools by Category:[/{self.console_theme.bold}]"
            )
            for cat, tool_names in tools_by_cat.items():
                self.console.print(
                    f"\n[{self.console_theme.warning}]{cat.title()}:[/{self.console_theme.warning}]"
                )
                for tool_name in tool_names:
                    tool_info = get_tool_info(tool_name)
                    if tool_info:
                        danger_indicator = " ⚠️" if tool_info.get("dangerous", False) else ""
                        self.console.print(
                            f"  [{self.console_theme.info}]{tool_name}[/{self.console_theme.info}]{danger_indicator} - {tool_info['description']}"
                        )

    def _show_tool_info(self, tool_name: str):
        """Show detailed information about a specific tool."""
        if not tool_name:
            self.console.print(
                "[{self.console_theme.error}]Please specify a tool name.[/{self.console_theme.error}]"
            )
            self.console.print("Usage: /tools info <tool_name>")
            return

        from coda.services.tools import get_tool_info

        tool_info = get_tool_info(tool_name)
        if not tool_info:
            self.console.print(
                f"[{self.console_theme.error}]Tool '{tool_name}' not found.[/{self.console_theme.error}]"
            )
            return

        self.console.print(
            f"\n[{self.console_theme.bold}]Tool: {tool_info['name']}[/{self.console_theme.bold}]"
        )
        self.console.print(
            f"Category: [{self.console_theme.info}]{tool_info['category']}[/{self.console_theme.info}]"
        )
        self.console.print(
            f"Server: [{self.console_theme.info}]{tool_info['server']}[/{self.console_theme.info}]"
        )
        if tool_info["dangerous"]:
            self.console.print(
                f"⚠️  [{self.console_theme.warning}]This tool requires special permissions[/{self.console_theme.warning}]"
            )

        self.console.print(f"\n[{self.console_theme.bold}]Description:[/{self.console_theme.bold}]")
        self.console.print(f"  {tool_info['description']}")

        if tool_info["parameters"]:
            self.console.print(
                f"\n[{self.console_theme.bold}]Parameters:[/{self.console_theme.bold}]"
            )
            for param_name, param_info in tool_info["parameters"].items():
                required_str = " (required)" if param_info["required"] else " (optional)"
                default_str = (
                    f" [default: {param_info['default']}]"
                    if param_info.get("default") is not None
                    else ""
                )

                self.console.print(
                    f"  [{self.console_theme.info}]{param_name}[/{self.console_theme.info}] ({param_info['type']}){required_str}{default_str}"
                )
                self.console.print(f"    {param_info['description']}")
        else:
            self.console.print(
                f"\n[{self.console_theme.dim}]No parameters required[/{self.console_theme.dim}]"
            )

    def _show_tool_categories(self):
        """Show all tool categories."""
        from coda.services.tools import get_tool_categories, list_tools_by_category

        categories = get_tool_categories()
        tools_by_cat = list_tools_by_category()

        self.console.print(
            f"\n[{self.console_theme.bold}]Tool Categories:[/{self.console_theme.bold}]"
        )
        for category in sorted(categories):
            tool_count = len(tools_by_cat.get(category, []))
            self.console.print(
                f"  [{self.console_theme.info}]{category}[/{self.console_theme.info}] ({tool_count} tools)"
            )

    def _show_tool_stats(self):
        """Show tool statistics."""
        from coda.services.tools import get_tool_stats

        stats = get_tool_stats()

        self.console.print(
            f"\n[{self.console_theme.bold}]Tool System Statistics:[/{self.console_theme.bold}]"
        )
        self.console.print(
            f"Total tools: [{self.console_theme.info}]{stats['total_tools']}[/{self.console_theme.info}]"
        )
        self.console.print(
            f"Categories: [{self.console_theme.info}]{stats['categories']}[/{self.console_theme.info}]"
        )
        self.console.print(
            f"Dangerous tools: [{self.console_theme.warning}]{stats['dangerous_tools']}[/{self.console_theme.warning}]"
        )

        self.console.print(
            f"\n[{self.console_theme.bold}]Tools by category:[/{self.console_theme.bold}]"
        )
        for category, count in stats["tools_by_category"].items():
            self.console.print(
                f"  [{self.console_theme.info}]{category}[/{self.console_theme.info}]: {count}"
            )

        if stats["dangerous_tool_names"]:
            self.console.print(
                f"\n[{self.console_theme.bold}]Dangerous tools:[/{self.console_theme.bold}]"
            )
            for tool_name in stats["dangerous_tool_names"]:
                self.console.print(
                    f"  [{self.console_theme.warning}]{tool_name}[/{self.console_theme.warning}] ⚠️"
                )

    def handle_mcp_command(self, args: str) -> CommandResult:
        """Handle MCP server management commands."""

        if not args:
            # Show main MCP overview
            self._show_mcp_overview()
            return CommandResult.HANDLED

        parts = args.split(maxsplit=1)
        subcommand = parts[0].lower()
        subargs = parts[1] if len(parts) > 1 else ""

        if subcommand == "list" or subcommand == "ls":
            self._show_mcp_servers()
        elif subcommand == "status":
            self._show_mcp_status(subargs)
        elif subcommand == "start":
            self._start_mcp_server(subargs)
        elif subcommand == "stop":
            self._stop_mcp_server(subargs)
        elif subcommand == "restart":
            self._restart_mcp_server(subargs)
        elif subcommand == "config":
            self._show_mcp_config(subargs)
        else:
            self.console.print(
                f"[{self.console_theme.error}]Unknown MCP subcommand: {subcommand}[/{self.console_theme.error}]"
            )
            self.console.print("Usage: /mcp [list|status|start|stop|restart|config]")

        return CommandResult.HANDLED

    def _show_mcp_overview(self):
        """Show MCP system overview."""
        from coda.base.config import ConfigManager

        self.console.print(
            f"🔧 [{self.console_theme.bold}]MCP Server Management[/{self.console_theme.bold}]"
        )
        self.console.print()

        try:
            config_manager = ConfigManager(app_name="coda")
            config = config_manager.get_mcp_config()
            if not config.servers:
                self.console.print(
                    f"[{self.console_theme.warning}]No MCP servers configured[/{self.console_theme.warning}]"
                )
                self.console.print(
                    f"\n[{self.console_theme.dim}]Add servers to mcp.json to get started[/{self.console_theme.dim}]"
                )
                return

            self.console.print(
                f"📊 Found [{self.console_theme.bold}]{len(config.servers)}[/{self.console_theme.bold}] configured server(s):"
            )
            for name, server in config.servers.items():
                status = "✅ enabled" if server.enabled else "❌ disabled"
                if server.command:
                    self.console.print(
                        f"  • [{self.console_theme.bold}]{name}[/{self.console_theme.bold}]: {server.command} {' '.join(server.args)} ({status})"
                    )
                elif server.url:
                    self.console.print(
                        f"  • [{self.console_theme.bold}]{name}[/{self.console_theme.bold}]: {server.url} ({status})"
                    )

        except Exception as e:
            self.console.print(
                f"[{self.console_theme.error}]Error loading MCP configuration: {e}[/{self.console_theme.error}]"
            )

        self.console.print(
            f"\n[{self.console_theme.dim}]Use '/mcp list' to see detailed server status[/{self.console_theme.dim}]"
        )

    def _show_mcp_servers(self):
        """Show list of MCP servers."""
        from coda.base.config import ConfigManager

        try:
            config_manager = ConfigManager(app_name="coda")
            config = config_manager.get_mcp_config()
            if not config.servers:
                self.console.print(
                    f"[{self.console_theme.warning}]No MCP servers configured[/{self.console_theme.warning}]"
                )
                return

            self.console.print(
                f"📋 [{self.console_theme.bold}]MCP Servers[/{self.console_theme.bold}]"
            )
            self.console.print()

            for name, server in config.servers.items():
                status_icon = "✅" if server.enabled else "❌"
                self.console.print(
                    f"{status_icon} [{self.console_theme.bold}]{name}[/{self.console_theme.bold}]"
                )
                if server.command:
                    self.console.print(f"   Command: {server.command} {' '.join(server.args)}")
                elif server.url:
                    self.console.print(f"   URL: {server.url}")
                self.console.print(f"   Enabled: {server.enabled}")
                if server.env:
                    self.console.print(f"   Environment: {server.env}")
                self.console.print()

        except Exception as e:
            self.console.print(
                f"[{self.console_theme.error}]Error: {e}[/{self.console_theme.error}]"
            )

    def _show_mcp_status(self, server_name: str):
        """Show status of specific MCP server."""
        from coda.base.config import ConfigManager

        try:
            config_manager = ConfigManager(app_name="coda")
            config = config_manager.get_mcp_config()

            if server_name:
                if server_name not in config.servers:
                    self.console.print(
                        f"[{self.console_theme.error}]Server '{server_name}' not found[/{self.console_theme.error}]"
                    )
                    return
                servers = {server_name: config.servers[server_name]}
            else:
                servers = config.servers

            if not servers:
                self.console.print(
                    f"[{self.console_theme.warning}]No servers to show status for[/{self.console_theme.warning}]"
                )
                return

            for name, server in servers.items():
                status = "🟢 Running" if server.enabled else "🔴 Stopped"
                self.console.print(
                    f"[{self.console_theme.bold}]{name}[/{self.console_theme.bold}]: {status}"
                )

        except Exception as e:
            self.console.print(
                f"[{self.console_theme.error}]Error: {e}[/{self.console_theme.error}]"
            )

    def _start_mcp_server(self, server_name: str):
        """Start an MCP server."""
        if not server_name:
            self.console.print(
                f"[{self.console_theme.error}]Please specify a server name[/{self.console_theme.error}]"
            )
            return

        self.console.print(
            f"[{self.console_theme.warning}]Starting MCP server '{server_name}' is not yet implemented[/{self.console_theme.warning}]"
        )

    def _stop_mcp_server(self, server_name: str):
        """Stop an MCP server."""
        if not server_name:
            self.console.print(
                f"[{self.console_theme.error}]Please specify a server name[/{self.console_theme.error}]"
            )
            return

        self.console.print(
            f"[{self.console_theme.warning}]Stopping MCP server '{server_name}' is not yet implemented[/{self.console_theme.warning}]"
        )

    def _restart_mcp_server(self, server_name: str):
        """Restart an MCP server."""
        if not server_name:
            self.console.print(
                f"[{self.console_theme.error}]Please specify a server name[/{self.console_theme.error}]"
            )
            return

        self.console.print(
            f"[{self.console_theme.warning}]Restarting MCP server '{server_name}' is not yet implemented[/{self.console_theme.warning}]"
        )

    def _show_mcp_config(self, config_path: str):
        """Show MCP configuration."""
        from pathlib import Path

        from coda.base.config import ConfigManager

        try:
            # Use base config module organization structure
            config_manager = ConfigManager(app_name="coda")

            # Get MCP config and determine which file was used
            config_manager.get_mcp_config()

            # Search for the actual config file that exists (same logic as ConfigManager)
            config_files = [Path.cwd() / "mcp.json", config_manager.get_config_dir() / "mcp.json"]

            config_file = None
            for cf in config_files:
                if cf.exists():
                    config_file = cf
                    break

            if not config_file:
                self.console.print(
                    f"[{self.console_theme.warning}]No mcp.json file found[/{self.console_theme.warning}]"
                )
                return

            self.console.print(
                f"📄 [{self.console_theme.bold}]MCP Configuration[/{self.console_theme.bold}] ({config_file})"
            )
            self.console.print()

            with open(config_file) as f:
                content = f.read()
                self.console.print(
                    f"[{self.console_theme.dim}]{content}[/{self.console_theme.dim}]"
                )

        except Exception as e:
            self.console.print(
                f"[{self.console_theme.error}]Error reading config: {e}[/{self.console_theme.error}]"
            )
