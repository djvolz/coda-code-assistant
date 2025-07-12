"""Session management commands for the interactive CLI."""

import os
from datetime import datetime
from typing import Any

from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.table import Table

from coda.base.session import Session, SessionManager
from coda.base.session.constants import (
    AUTO_DATE_FORMAT as AUTO_SESSION_DATE_FORMAT,
)
from coda.base.session.constants import (
    AUTO_PREFIX as AUTO_SESSION_PREFIX,
)
from coda.base.session.constants import (
    LIMIT_DELETE as SESSION_DELETE_LIMIT,
)
from coda.base.session.constants import (
    LIMIT_INFO as SESSION_INFO_LIMIT,
)
from coda.base.session.constants import (
    LIMIT_LAST as SESSION_LAST_LIMIT,
)
from coda.base.session.constants import (
    LIMIT_LIST as SESSION_LIST_LIMIT,
)
from coda.base.session.constants import (
    LIMIT_SEARCH as SESSION_SEARCH_LIMIT,
)


class SessionCommands:
    """Handles session-related slash commands."""

    def __init__(self, session_manager: SessionManager | None = None):
        """Initialize session commands.

        Args:
            session_manager: SessionManager instance. If None, creates a new one.
        """
        self.manager = session_manager or SessionManager()
        # Get themed console from the app layer
        from coda.services.config import get_config_service

        config = get_config_service()
        self.console = config.theme_manager.get_console()
        self.current_session_id: str | None = None
        self.current_messages: list[dict[str, Any]] = []
        self.auto_save_enabled: bool = True  # Auto-save by default
        self._has_user_message: bool = False  # Track if we have a user message

    def handle_session_command(self, args: list[str]) -> str | None:
        """Handle /session command and subcommands.

        Args:
            args: Command arguments

        Returns:
            Response message or None
        """
        if not args:
            return self._show_session_help()

        subcommand = args[0].lower()

        if subcommand in ["save", "s"]:
            return self._save_session(args[1:])
        elif subcommand in ["load", "l"]:
            return self._load_session(args[1:])
        elif subcommand in ["last"]:
            return self._load_last_session()
        elif subcommand in ["list", "ls"]:
            return self._list_sessions(args[1:])
        elif subcommand in ["branch", "b"]:
            return self._branch_session(args[1:])
        elif subcommand in ["delete", "d", "rm"]:
            return self._delete_session(args[1:])
        elif subcommand in ["delete-all"]:
            return self._delete_all_sessions(args[1:])
        elif subcommand in ["info", "i"]:
            return self._session_info(args[1:])
        elif subcommand in ["search"]:
            return self._search_sessions(args[1:])
        elif subcommand in ["rename", "r"]:
            return self._rename_session(args[1:])
        elif subcommand in ["tools", "t"]:
            return self._show_session_tools(args[1:])
        else:
            return f"Unknown session subcommand: {subcommand}. Use /session help for options."

    def _show_session_help(self) -> str:
        """Show session command help."""
        # Base layer cannot depend on apps layer, so we define help directly
        help_text = """
[bold]Session Management Commands[/bold]

[cyan]/session save [name][/cyan] - Save current conversation
[cyan]/session load <id|name>[/cyan] - Load a saved session
[cyan]/session last[/cyan] - Load the most recent session
[cyan]/session list[/cyan] - List all saved sessions
[cyan]/session branch [name][/cyan] - Create a branch from current session
[cyan]/session delete <id|name>[/cyan] - Delete a session
[cyan]/session delete-all [--auto-only][/cyan] - Delete all/auto sessions
[cyan]/session info [id][/cyan] - Show session details
[cyan]/session search <query>[/cyan] - Search sessions
[cyan]/session rename [id] <new_name>[/cyan] - Rename a session
[cyan]/session tools [id][/cyan] - Show tool usage for a session

[dim]Aliases: /s, save→s, load→l, list→ls, branch→b, delete→d/rm, info→i, rename→r, tools→t[/dim]
"""
        self.console.print(Panel(help_text, title="Session Help", border_style="cyan"))
        return None

    def _save_session(self, args: list[str]) -> str:
        """Save current conversation as a session."""
        if not self.current_messages:
            return "No messages to save."

        # Get session name
        if args:
            name = " ".join(args)
        else:
            name = Prompt.ask(
                "Session name", default=f"Session {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            )

        # Get description
        description = Prompt.ask("Description (optional)", default="")

        # Create or update session
        if self.current_session_id:
            # Update existing session
            self.manager.update_session(
                self.current_session_id, name=name, description=description if description else None
            )
            return f"Session updated: {name}"
        else:
            # Create new session
            # Get provider and model from first assistant message
            provider = "unknown"
            model = "unknown"
            mode = "general"

            for msg in self.current_messages:
                if msg.get("role") == "assistant" and msg.get("metadata"):
                    provider = msg["metadata"].get("provider", provider)
                    model = msg["metadata"].get("model", model)
                    mode = msg["metadata"].get("mode", mode)
                    break

            session = self.manager.create_session(
                name=name,
                description=description if description else None,
                provider=provider,
                model=model,
                mode=mode,
            )

            # Save all messages
            for msg in self.current_messages:
                self.manager.add_message(
                    session_id=session.id,
                    role=msg["role"],
                    content=msg["content"],
                    metadata=msg.get("metadata", {}),
                    model=msg.get("metadata", {}).get("model"),
                    provider=msg.get("metadata", {}).get("provider"),
                    token_usage=msg.get("metadata", {}).get("token_usage"),
                    cost=msg.get("metadata", {}).get("cost"),
                )

            self.current_session_id = session.id
            return f"Session saved: {name} (ID: {session.id[:8]}...)"

    def _load_session(self, args: list[str]) -> str:
        """Load a saved session."""
        if not args:
            return "Please specify a session ID or name to load."

        session_ref = " ".join(args)

        # Try to find session by ID or name
        session = self._find_session(session_ref)
        if not session:
            return f"Session not found: {session_ref}"

        # Load messages
        messages = self.manager.get_messages(session.id)

        # Convert to internal format
        self.current_messages = []
        for msg in messages:
            self.current_messages.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                    "metadata": {
                        "provider": msg.provider or session.provider,
                        "model": msg.model or session.model,
                        "mode": msg.message_metadata.get("mode", session.mode),
                        "token_usage": (
                            {
                                "prompt_tokens": msg.prompt_tokens,
                                "completion_tokens": msg.completion_tokens,
                                "total_tokens": msg.total_tokens,
                            }
                            if msg.total_tokens
                            else None
                        ),
                        "cost": msg.cost,
                    },
                }
            )

        self.current_session_id = session.id

        # Display session info
        self.console.print(f"\n[green]Loaded session:[/green] {session.name}")
        self.console.print(
            f"[dim]Provider:[/dim] {session.provider} | [dim]Model:[/dim] {session.model}"
        )
        self.console.print(
            f"[dim]Messages:[/dim] {len(messages)} | [dim]Created:[/dim] {session.created_at.strftime('%Y-%m-%d %H:%M')}"
        )

        if session.description:
            self.console.print(f"[dim]Description:[/dim] {session.description}")

        # Set flag to indicate messages were loaded for CLI integration
        self._messages_loaded = True

        return None

    def _list_sessions(self, args: list[str]) -> str:
        """List saved sessions."""
        sessions = self.manager.get_active_sessions(limit=SESSION_LIST_LIMIT)

        if not sessions:
            return "No saved sessions found."

        # Create table
        table = Table(title="Saved Sessions", show_header=True, header_style="bold cyan")
        table.add_column("ID", style="dim", width=12)
        table.add_column("Name", style="bold")
        table.add_column("Provider/Model", style="cyan")
        table.add_column("Messages", justify="right")
        table.add_column("Last Active", style="green")

        for session in sessions:
            table.add_row(
                session.id[:8] + "...",
                session.name[:40] + ("..." if len(session.name) > 40 else ""),
                f"{session.provider}/{session.model.split('.')[-1][:20]}",
                str(session.message_count),
                session.accessed_at.strftime("%Y-%m-%d %H:%M"),
            )

        self.console.print(table)
        return None

    def _branch_session(self, args: list[str]) -> str:
        """Create a branch from current session."""
        if not self.current_session_id:
            return "No active session to branch from. Save or load a session first."

        # Get branch name
        if args:
            name = " ".join(args)
        else:
            parent_session = self.manager.get_session(self.current_session_id)
            name = Prompt.ask("Branch name", default=f"{parent_session.name} (branch)")

        # Get last message ID for branch point
        messages = self.manager.get_messages(self.current_session_id)
        if not messages:
            return "No messages in current session to branch from."

        last_message = messages[-1]

        # Create branch
        branch_session = self.manager.create_session(
            name=name,
            provider=messages[0].provider or "unknown",
            model=messages[0].model or "unknown",
            mode=self.current_messages[0].get("metadata", {}).get("mode", "general"),
            parent_id=self.current_session_id,
            branch_point_message_id=last_message.id,
        )

        # Switch to branch
        self.current_session_id = branch_session.id

        return f"Created branch: {name} (ID: {branch_session.id[:8]}...)"

    def _delete_session(self, args: list[str]) -> str:
        """Delete a session."""
        if not args:
            return "Please specify a session ID or name to delete."

        session_ref = " ".join(args)

        # Find session
        session = self._find_session(session_ref)
        if not session:
            return f"Session not found: {session_ref}"

        # Confirm deletion
        if not Confirm.ask(f"Delete session '{session.name}'?"):
            return "Deletion cancelled."

        # Check if it's the current session
        if session.id == self.current_session_id:
            self.current_session_id = None

        # Delete session
        self.manager.delete_session(session.id)

        return f"Session deleted: {session.name}"

    def _session_info(self, args: list[str]) -> str:
        """Show detailed session information."""
        if args:
            session_ref = " ".join(args)
            session = self._find_session(session_ref)
            if not session:
                return f"Session not found: {session_ref}"
        elif self.current_session_id:
            session = self.manager.get_session(self.current_session_id)
        else:
            return "No session specified or loaded."

        # Create info panel
        info_lines = [
            f"[bold]Name:[/bold] {session.name}",
            f"[bold]ID:[/bold] {session.id}",
            f"[bold]Provider:[/bold] {session.provider}",
            f"[bold]Model:[/bold] {session.model}",
            f"[bold]Mode:[/bold] {session.mode}",
            f"[bold]Status:[/bold] {session.status}",
            f"[bold]Created:[/bold] {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"[bold]Updated:[/bold] {session.updated_at.strftime('%Y-%m-%d %H:%M:%S')}",
            f"[bold]Messages:[/bold] {session.message_count}",
            (
                f"[bold]Total Tokens:[/bold] {session.total_tokens:,}"
                if session.total_tokens
                else "[bold]Total Tokens:[/bold] 0"
            ),
        ]

        if session.total_cost:
            info_lines.append(f"[bold]Total Cost:[/bold] ${session.total_cost:.4f}")

        if session.description:
            info_lines.append(f"\n[bold]Description:[/bold]\n{session.description}")

        if session.parent_id:
            parent = self.manager.get_session(session.parent_id)
            if parent:
                info_lines.append(f"\n[bold]Branched from:[/bold] {parent.name}")

        # Base modules should not use themed output - just return plain text

        self.console.print(
            Panel("\n".join(info_lines), title="Session Information", border_style="cyan")
        )
        return None

    def _search_sessions(self, args: list[str]) -> str:
        """Search sessions by content."""
        if not args:
            return "Please provide a search query."

        query = " ".join(args)
        results = self.manager.search_sessions(query, limit=SESSION_SEARCH_LIMIT)

        if not results:
            return f"No sessions found matching: {query}"

        self.console.print(f"\n[bold]Search Results for:[/bold] {query}\n")

        for session, messages in results:
            self.console.print(f"[bold cyan]{session.name}[/bold cyan] ({session.id[:8]}...)")
            self.console.print(
                f"[dim]{session.provider}/{session.model} - {session.message_count} messages[/dim]"
            )

            # Show matching messages
            for msg in messages[:3]:  # Show up to 3 matches
                excerpt = msg.content[:100].replace("\n", " ")
                if len(msg.content) > 100:
                    excerpt += "..."
                self.console.print(f"  [yellow]→[/yellow] [{msg.role}] {excerpt}")

            if len(messages) > 3:
                self.console.print(f"  [dim]... and {len(messages) - 3} more matches[/dim]")

            self.console.print()

        return None

    def _load_last_session(self) -> str:
        """Load the most recent session."""
        # Get the most recent session
        sessions = self.manager.get_active_sessions(limit=SESSION_LAST_LIMIT)

        if not sessions:
            return "No sessions found to load."

        # Load the most recent session
        session = sessions[0]

        # Load messages
        messages = self.manager.get_messages(session.id)

        # Convert to internal format
        self.current_messages = []
        for msg in messages:
            self.current_messages.append(
                {
                    "role": msg.role,
                    "content": msg.content,
                    "metadata": {
                        "provider": msg.provider or session.provider,
                        "model": msg.model or session.model,
                        "mode": msg.message_metadata.get("mode", session.mode),
                        "token_usage": (
                            {
                                "prompt_tokens": msg.prompt_tokens,
                                "completion_tokens": msg.completion_tokens,
                                "total_tokens": msg.total_tokens,
                            }
                            if msg.total_tokens
                            else None
                        ),
                        "cost": msg.cost,
                    },
                }
            )

        self.current_session_id = session.id

        # Display session info
        self.console.print(f"\n[green]Loaded last session:[/green] {session.name}")
        self.console.print(
            f"[dim]Provider:[/dim] {session.provider} | [dim]Model:[/dim] {session.model}"
        )
        self.console.print(
            f"[dim]Messages:[/dim] {len(messages)} | [dim]Created:[/dim] {session.created_at.strftime('%Y-%m-%d %H:%M')}"
        )

        if session.description:
            self.console.print(f"[dim]Description:[/dim] {session.description}")

        # Set flag to indicate messages were loaded for CLI integration
        self._messages_loaded = True

        return None

    def _rename_session(self, args: list[str]) -> str:
        """Rename a session."""
        if not args:
            # If no args, rename current session
            if not self.current_session_id:
                return "No current session. Please specify a session ID or name to rename."

            new_name = Prompt.ask("New name for current session")
            session_id = self.current_session_id
        elif len(args) == 1:
            # Only new name provided, rename current session
            if not self.current_session_id:
                return "No current session. Please specify a session ID or name to rename."

            new_name = args[0]
            session_id = self.current_session_id
        else:
            # Session ref and new name provided
            session_ref = args[0]
            new_name = " ".join(args[1:])

            # Find the session
            session = self._find_session(session_ref)
            if not session:
                return f"Session not found: {session_ref}"

            session_id = session.id

        # Update the session name
        try:
            self.manager.update_session(session_id, name=new_name)

            # If it's the current session, update our local name tracking
            if session_id == self.current_session_id:
                # Update the name in current_messages metadata if needed
                for msg in self.current_messages:
                    if msg.get("metadata", {}).get("session_name"):
                        msg["metadata"]["session_name"] = new_name

            return f"Session renamed to: {new_name}"
        except Exception as e:
            return f"Failed to rename session: {str(e)}"

    def _delete_all_sessions(self, args: list[str]) -> str:
        """Delete all sessions or only auto-saved sessions."""
        # Check for --auto-only flag
        auto_only = "--auto-only" in args

        # Get all sessions
        sessions = self.manager.get_active_sessions(limit=SESSION_DELETE_LIMIT)

        if not sessions:
            return "No sessions found to delete."

        # Filter for auto-saved sessions if requested
        if auto_only:
            sessions = [s for s in sessions if s.name.startswith(AUTO_SESSION_PREFIX)]
            if not sessions:
                return "No auto-saved sessions found to delete."

        # Show what will be deleted
        session_count = len(sessions)
        session_type = "auto-saved" if auto_only else "all"

        self.console.print(
            f"\n[yellow]Warning:[/yellow] This will delete {session_count} {session_type} session(s):"
        )

        # Show first 10 sessions
        for _i, session in enumerate(sessions[:10]):
            self.console.print(f"  • {session.name} ({session.id[:8]}...)")

        if len(sessions) > 10:
            self.console.print(f"  ... and {len(sessions) - 10} more")

        # Confirm deletion
        if not Confirm.ask(
            f"\n[red]Delete {session_count} {session_type} session(s)?[/red]", default=False
        ):
            return "Deletion cancelled."

        # Delete sessions
        deleted_count = 0
        failed_count = 0

        # Clear current session if it's being deleted
        current_ids = [s.id for s in sessions]
        if self.current_session_id in current_ids:
            self.current_session_id = None
            self.current_messages = []
            self._has_user_message = False

        # Base modules should not use themed output - just return plain text

        with self.console.status(
            f"[cyan]Deleting {session_count} sessions...[/cyan]", spinner="dots"
        ):
            for session in sessions:
                try:
                    self.manager.delete_session(session.id)
                    deleted_count += 1
                except Exception as e:
                    self.console.print(f"[red]Failed to delete {session.name}: {str(e)}[/red]")
                    failed_count += 1

        if failed_count > 0:
            return f"Deleted {deleted_count} session(s), {failed_count} failed."
        else:
            return f"Successfully deleted {deleted_count} {session_type} session(s)."

    def _show_session_tools(self, args: list[str]) -> str:
        """Show tool usage for a session."""
        # Get session ID
        if args:
            session_id = args[0]
            session = self._find_session(session_id)
            if not session:
                return f"Session not found: {session_id}"
            session_id = session.id
        elif self.current_session_id:
            session_id = self.current_session_id
        else:
            return "No session specified or loaded. Use: /session tools <id>"

        # Get tool history
        tool_history = self.manager.get_tool_history(session_id)
        if not tool_history:
            return "No tool usage found in this session."

        # Get summary
        summary = self.manager.get_session_tools_summary(session_id)

        # Create display
        from rich.panel import Panel
        from rich.table import Table

        # Summary panel
        summary_text = f"""[bold]Tool Usage Summary[/bold]

Total tool calls: [cyan]{summary["total_tool_calls"]}[/cyan]
Unique tools used: [cyan]{summary["unique_tools"]}[/cyan]
Most used tool: [cyan]{summary["most_used"] or "N/A"}[/cyan]

[bold]Tool Counts:[/bold]"""

        for tool, count in sorted(summary["tool_counts"].items(), key=lambda x: x[1], reverse=True):
            summary_text += f"\n  • {tool}: {count} call{'s' if count > 1 else ''}"

        self.console.print(Panel(summary_text, title="Tool Usage", border_style="cyan"))

        # Detailed history table
        if len(tool_history) <= 20:  # Show all if reasonable number
            table = Table(title="Tool Call History", show_header=True, header_style="bold cyan")
            table.add_column("Seq", style="dim", width=4)
            table.add_column("Type", style="bold", width=8)
            table.add_column("Tool/Result", style="cyan")
            table.add_column("Time", style="green")

            for entry in tool_history:
                if entry["type"] == "call":
                    tool_info = ", ".join(
                        f"{call['name']}({call.get('id', 'no-id')[:8]})"
                        for call in entry["tool_calls"]
                    )
                    table.add_row(
                        str(entry["sequence"]),
                        "CALL",
                        tool_info,
                        entry["created_at"].strftime("%H:%M:%S"),
                    )
                else:  # result
                    result_preview = (
                        entry["content"][:50] + "..."
                        if len(entry["content"]) > 50
                        else entry["content"]
                    )
                    result_preview = result_preview.replace("\n", " ")
                    table.add_row(
                        str(entry["sequence"]),
                        "RESULT",
                        result_preview,
                        entry["created_at"].strftime("%H:%M:%S"),
                    )

            self.console.print(table)
        else:
            self.console.print(
                f"\n[dim]Full history contains {len(tool_history)} entries. Showing summary only.[/dim]"
            )

        return None

    def _find_session(self, session_ref: str) -> Session | None:
        """Find session by ID or name."""
        # First try by ID
        sessions = self.manager.get_active_sessions(limit=SESSION_INFO_LIMIT)

        # Try exact ID match
        for session in sessions:
            if session.id == session_ref or session.id.startswith(session_ref):
                return session

        # Try name match (case insensitive)
        session_ref_lower = session_ref.lower()
        for session in sessions:
            if session.name.lower() == session_ref_lower:
                return session

        # Try partial name match
        for session in sessions:
            if session_ref_lower in session.name.lower():
                return session

        return None

    def handle_export_command(self, args: list[str]) -> str | None:
        """Handle /export command.

        Args:
            args: Command arguments

        Returns:
            Response message or None
        """
        if not args:
            return self._show_export_help()

        format = args[0].lower()
        if format not in ["json", "markdown", "md", "txt", "text", "html"]:
            return f"Unknown export format: {format}. Use: json, markdown, txt, or html"

        # Normalize format names
        if format == "md":
            format = "markdown"
        elif format == "text":
            format = "txt"

        # Get session to export
        if len(args) > 1:
            session_ref = " ".join(args[1:])
            session = self._find_session(session_ref)
            if not session:
                return f"Session not found: {session_ref}"
            session_id = session.id
        elif self.current_session_id:
            session_id = self.current_session_id
            session = self.manager.get_session(session_id)
        else:
            return "No session specified or loaded."

        # Export session
        try:
            content = self.manager.export_session(session_id, format)

            # Generate filename
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safe_name = "".join(
                c for c in session.name if c.isalnum() or c in (" ", "-", "_")
            ).rstrip()
            filename = f"{safe_name}_{timestamp}.{format}"

            # Get export directory
            export_dir = os.path.expanduser("~/Documents/coda_exports")
            os.makedirs(export_dir, exist_ok=True)
            filepath = os.path.join(export_dir, filename)

            # Write file
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

            self.console.print(f"[green]✓[/green] Exported to: {filepath}")
            return None

        except Exception as e:
            return f"Export failed: {str(e)}"

    def _show_export_help(self) -> str:
        """Show export command help."""
        help_text = """
[bold]Export Commands[/bold]

[cyan]/export json [session][/cyan] - Export as JSON
[cyan]/export markdown [session][/cyan] - Export as Markdown
[cyan]/export txt [session][/cyan] - Export as plain text
[cyan]/export html [session][/cyan] - Export as HTML

[dim]Aliases: /e, markdown→md, txt→text[/dim]
[dim]If no session specified, exports current session[/dim]
[dim]Files saved to: ~/Documents/coda_exports/[/dim]
"""
        # Base modules should not use themed output - just return plain text

        self.console.print(Panel(help_text, title="Export Help", border_style="cyan"))
        return None

    def add_message(self, role: str, content: str, metadata: dict[str, Any] | None = None):
        """Add a message to the current conversation.

        Args:
            role: Message role
            content: Message content
            metadata: Optional metadata
        """
        msg = {"role": role, "content": content, "metadata": metadata or {}}
        self.current_messages.append(msg)

        # Track if we have a user message
        if role == "user":
            self._has_user_message = True

        # Auto-create session on first user-assistant exchange if enabled
        if (
            self.auto_save_enabled
            and not self.current_session_id
            and self._has_user_message
            and role == "assistant"
            and len(self.current_messages) >= 2
        ):  # At least user + assistant message
            # Auto-create session with timestamp name
            timestamp = datetime.now().strftime(AUTO_SESSION_DATE_FORMAT)
            auto_name = f"{AUTO_SESSION_PREFIX}{timestamp}"

            # Get provider and model from metadata
            provider = metadata.get("provider", "unknown") if metadata else "unknown"
            model = metadata.get("model", "unknown") if metadata else "unknown"
            mode = metadata.get("mode", "general") if metadata else "general"

            try:
                session = self.manager.create_session(
                    name=auto_name,
                    description="Auto-saved conversation",
                    provider=provider,
                    model=model,
                    mode=mode,
                )

                self.current_session_id = session.id

                # Save all existing messages to the new session
                for existing_msg in self.current_messages:
                    self.manager.add_message(
                        session_id=session.id,
                        role=existing_msg["role"],
                        content=existing_msg["content"],
                        metadata=existing_msg.get("metadata", {}),
                        model=existing_msg.get("metadata", {}).get("model"),
                        provider=existing_msg.get("metadata", {}).get("provider"),
                        token_usage=existing_msg.get("metadata", {}).get("token_usage"),
                        cost=existing_msg.get("metadata", {}).get("cost"),
                    )

                # Notify user about auto-save (subtly)
                self.console.print(f"[dim]💾 Auto-saved session: {auto_name}[/dim]")

            except Exception as e:
                # Don't fail the conversation if auto-save fails
                self.console.print(f"[dim yellow]⚠️  Auto-save failed: {str(e)}[/dim yellow]")

        # If we have an active session, save to database
        elif self.current_session_id:
            self.manager.add_message(
                session_id=self.current_session_id,
                role=role,
                content=content,
                metadata=metadata,
                model=metadata.get("model") if metadata else None,
                provider=metadata.get("provider") if metadata else None,
                token_usage=metadata.get("token_usage") if metadata else None,
                cost=metadata.get("cost") if metadata else None,
            )

    def get_context_messages(
        self, model: str | None = None, max_tokens: int | None = None
    ) -> tuple[list[dict[str, Any]], bool]:
        """Get current conversation messages for context with intelligent windowing.

        Args:
            model: Model name for context limits
            max_tokens: Maximum token limit

        Returns:
            Tuple of (messages, was_truncated)
        """
        if self.current_session_id:
            # Use session manager's context windowing
            return self.manager.get_session_context(
                self.current_session_id, model=model, max_tokens=max_tokens
            )
        else:
            # Return current messages without windowing
            return self.current_messages, False

    def get_loaded_messages_for_cli(self) -> list:
        """Get loaded messages in CLI format (Message objects) for conversation history.

        Returns:
            List of Message objects for CLI conversation history, or empty list if no session loaded.
        """
        if not hasattr(self, "_messages_loaded") or not self._messages_loaded:
            return []

        from coda.base.providers import Message, Role

        cli_messages = []
        for msg in self.current_messages:
            # Convert role string to Role enum
            role_map = {
                "user": Role.USER,
                "assistant": Role.ASSISTANT,
                "system": Role.SYSTEM,
                "tool": Role.USER,  # Fallback for tool messages
            }
            role = role_map.get(msg["role"], Role.USER)

            cli_messages.append(Message(role=role, content=msg["content"]))

        # Reset the flag after providing messages
        self._messages_loaded = False

        return cli_messages

    def was_conversation_cleared(self) -> bool:
        """Check if conversation was cleared and reset the flag.

        Returns:
            True if conversation was cleared since last check.
        """
        if hasattr(self, "_conversation_cleared") and self._conversation_cleared:
            self._conversation_cleared = False
            return True
        return False

    def clear_conversation(self):
        """Clear current conversation."""
        self.current_messages = []
        self.current_session_id = None
        self._messages_loaded = False
        self._conversation_cleared = True
