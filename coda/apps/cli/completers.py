"""Enhanced tab completion system for Coda interactive CLI."""

from abc import ABC
from typing import TYPE_CHECKING

from prompt_toolkit.completion import Completer, Completion, PathCompleter
from prompt_toolkit.document import Document

if TYPE_CHECKING:
    from prompt_toolkit.completion import CompleteEvent

    from .command_registry import SlashCommand


class FuzzyMatcher:
    """Fuzzy matching utilities for command completion."""

    @staticmethod
    def fuzzy_match(text: str, candidate: str) -> tuple[bool, float]:
        """
        Check if text fuzzy matches candidate and return match score.

        Args:
            text: The user input text
            candidate: The candidate string to match against

        Returns:
            Tuple of (matches, score) where score is 0.0-1.0
        """
        text = text.lower()
        candidate = candidate.lower()

        # Exact match
        if text == candidate:
            return True, 1.0

        # Prefix match
        if candidate.startswith(text):
            return True, 0.9

        # Fuzzy match - all characters in order
        text_idx = 0
        matches = 0
        for char in candidate:
            if text_idx < len(text) and char == text[text_idx]:
                matches += 1
                text_idx += 1

        if text_idx == len(text):
            # All characters matched
            score = matches / len(candidate)
            return True, score * 0.8  # Lower score for fuzzy matches

        return False, 0.0


class BaseCompleter(Completer, ABC):
    """Base class for all custom completers."""

    def __init__(self):
        self._cache = {}
        self._cache_timeout = 60  # seconds

    def clear_cache(self):
        """Clear the completion cache."""
        self._cache.clear()


class SlashCommandCompleter(BaseCompleter):
    """Enhanced completer for slash commands with fuzzy matching."""

    def __init__(self, commands: dict[str, "SlashCommand"]):
        super().__init__()
        self.commands = commands

    def get_completions(self, document: Document, complete_event: "CompleteEvent"):
        text = document.text_before_cursor

        # Handle empty input - show all commands
        if not text.strip():
            yield from self._complete_all_commands()
            return

        # Must start with /
        if not text.startswith("/"):
            return

        # Parse command and check for subcommands
        has_space = " " in text
        parts = text.split(maxsplit=1)
        cmd_part = parts[0][1:]  # Remove leading /

        # If we have a space, check for subcommands
        if has_space and cmd_part in self.commands:
            yield from self._complete_subcommands(cmd_part, parts)
            return

        # Only complete command names if we don't have a space after the command
        if not has_space:
            yield from self._complete_command_names(cmd_part, text)

    def _complete_all_commands(self):
        """Complete all available commands when no input given."""
        from coda.services.config import get_config_service

        config_service = get_config_service()
        theme = config_service.theme_manager.get_console_theme()

        for cmd_name, cmd in sorted(self.commands.items()):
            yield Completion(
                f"/{cmd_name}",
                start_position=0,
                display=f"/{cmd_name}",
                display_meta=cmd.help_text,
                style=theme.info + " bold",
            )

    def _complete_subcommands(self, cmd_part: str, parts: list[str]):
        """Complete subcommands for the given command."""
        # Import here to avoid circular imports
        from coda.services.config import get_config_service

        from .command_registry import CommandRegistry

        config_service = get_config_service()
        theme = config_service.theme_manager.get_console_theme()

        cmd_def = CommandRegistry.get_command(cmd_part)
        if cmd_def and cmd_def.subcommands:
            subcommand_part = parts[1] if len(parts) > 1 else ""

            for sub in cmd_def.subcommands:
                matches, score = FuzzyMatcher.fuzzy_match(subcommand_part, sub.name)
                if matches:
                    yield Completion(
                        sub.name,
                        start_position=-len(subcommand_part),
                        display=sub.name,
                        display_meta=sub.description,
                        style=theme.success if score >= 0.9 else theme.warning,
                    )

    def _complete_command_names(self, cmd_part: str, text: str):
        """Complete command names with fuzzy matching."""
        from coda.services.config import get_config_service

        config_service = get_config_service()
        theme = config_service.theme_manager.get_console_theme()

        completions = []

        # Check main commands only (no aliases)
        for cmd_name, cmd in self.commands.items():
            matches, score = FuzzyMatcher.fuzzy_match(cmd_part, cmd_name)
            if matches:
                completions.append(
                    (
                        score,
                        Completion(
                            "/" + cmd_name,
                            start_position=-len(text),
                            display=f"/{cmd_name}",
                            display_meta=cmd.help_text,
                            style=theme.info + " bold" if score >= 0.9 else theme.info,
                        ),
                    )
                )

        # Sort by score (highest first) and yield
        for _score, completion in sorted(completions, key=lambda x: (-x[0], x[1].text)):
            yield completion


class DynamicValueCompleter(BaseCompleter):
    """Dynamic completer that uses command registry completion types."""

    def __init__(self, get_provider_func=None, session_commands=None, get_themes_func=None):
        super().__init__()
        self.get_provider = get_provider_func
        self.session_commands = session_commands
        self.get_themes = get_themes_func

    def get_completions(self, document: Document, complete_event: "CompleteEvent"):
        text = document.text_before_cursor

        # Must start with /
        if not text.startswith("/"):
            return

        # Parse command structure
        parts = text.split()
        if len(parts) < 1:
            return

        # Get the main command
        main_cmd_name = parts[0][1:]  # Remove /
        main_cmd = self._get_command(main_cmd_name)
        if not main_cmd:
            return

        # Check if we're completing a value for the main command
        if main_cmd.completion_type:
            yield from self._complete_main_command_value(text, parts, main_cmd)
            return

        # Check subcommands
        if main_cmd.subcommands and len(parts) >= 2:
            yield from self._complete_subcommand_value(text, parts, main_cmd)

    def _get_command(self, cmd_name: str):
        """Get command definition from registry."""
        from .command_registry import CommandRegistry

        return CommandRegistry.get_command(cmd_name)

    def _complete_main_command_value(self, text: str, parts: list[str], main_cmd):
        """Complete values for main command."""
        from coda.services.config import get_config_service

        config_service = get_config_service()
        theme = config_service.theme_manager.get_console_theme()

        if text.endswith(" ") and len(parts) == 1:
            # Command with no value yet - just typed space
            value_part = ""
            yield from self._complete_value(main_cmd.completion_type, value_part, theme)
        elif text.startswith(f"/{main_cmd.name} ") and len(parts) == 2:
            # Already typing the value
            value_part = parts[1]
            yield from self._complete_value(main_cmd.completion_type, value_part, theme)

    def _complete_subcommand_value(self, text: str, parts: list[str], main_cmd):
        """Complete values for subcommands."""
        from coda.services.config import get_config_service

        config_service = get_config_service()
        theme = config_service.theme_manager.get_console_theme()

        subcommand_name = parts[1]
        # Find the subcommand (including aliases)
        subcommand = None
        for sub in main_cmd.subcommands:
            if subcommand_name in sub.get_all_names():
                subcommand = sub
                break

        if subcommand and subcommand.completion_type:
            # Check if we're ready to complete the value
            if len(parts) == 2 and text.endswith(" "):
                # Just typed space after subcommand
                value_part = ""
                yield from self._complete_value(subcommand.completion_type, value_part, theme)
            elif len(parts) == 3:
                # Already typing the value
                value_part = parts[2]
                yield from self._complete_value(subcommand.completion_type, value_part, theme)

    def _complete_value(self, completion_type: str, value_part: str, theme):
        """Complete a value based on its type."""
        if completion_type == "model_name" and self.get_provider:
            provider = self.get_provider()
            if provider:
                try:
                    models = provider.list_models()
                    # Extract model IDs from Model objects
                    model_ids = [m.id if hasattr(m, "id") else str(m) for m in models]
                    for model_id in sorted(model_ids):
                        matches, score = FuzzyMatcher.fuzzy_match(value_part, model_id)
                        if matches:
                            yield Completion(
                                model_id,
                                start_position=-len(value_part),
                                display=model_id,
                                display_meta="AI Model",
                                style=(
                                    theme.assistant_message + " bold"
                                    if score >= 0.9
                                    else theme.assistant_message
                                ),
                            )
                except Exception:
                    pass

        elif completion_type == "session_name" and self.session_commands:
            try:
                sessions = self.session_commands.list_sessions()
                for session in sessions:
                    name = session["name"]
                    matches, score = FuzzyMatcher.fuzzy_match(value_part, name)
                    if matches:
                        msgs = session.get("message_count", 0)
                        date = session.get("updated_at", "Unknown")
                        meta = f"{msgs} msgs, {date}"

                        yield Completion(
                            name,
                            start_position=-len(value_part),
                            display=name,
                            display_meta=meta,
                            style=theme.warning + " bold" if score >= 0.9 else theme.warning,
                        )
            except Exception:
                pass

        elif completion_type == "theme_name" and self.get_themes:
            themes = self.get_themes()
            for theme_name in sorted(themes):
                matches, score = FuzzyMatcher.fuzzy_match(value_part, theme_name)
                if matches:
                    yield Completion(
                        theme_name,
                        start_position=-len(value_part),
                        display=theme_name,
                        display_meta="Theme",
                        style=theme.user_message + " bold" if score >= 0.9 else theme.user_message,
                    )


class CodaCompleter(BaseCompleter):
    """Main completer for Coda CLI that combines all completion features."""

    def __init__(
        self,
        slash_commands: dict[str, "SlashCommand"],
        get_provider_func=None,
        session_commands=None,
        get_themes_func=None,
    ):
        super().__init__()

        # Initialize sub-completers
        self.slash_completer = SlashCommandCompleter(slash_commands)
        self.path_completer = PathCompleter(expanduser=True)
        self.dynamic_completer = DynamicValueCompleter(
            get_provider_func, session_commands, get_themes_func
        )

    def get_completions(self, document: Document, complete_event: "CompleteEvent"):
        text = document.text_before_cursor

        # Priority order for completers

        # 1. Slash commands always take priority
        if text.startswith("/"):
            # Try both slash command and dynamic completion

            # First try slash command completion (for command names and subcommands)
            for completion in self.slash_completer.get_completions(document, complete_event):
                yield completion

            # Also try dynamic value completion (for model names, session names, etc.)
            for completion in self.dynamic_completer.get_completions(document, complete_event):
                yield completion

            return

        # 2. Empty input - show available slash commands
        elif not text.strip():
            yield from self.slash_completer.get_completions(document, complete_event)
            return

        # 3. Path completion for file paths
        elif "/" in text or text.startswith("~"):
            yield from self.path_completer.get_completions(document, complete_event)
            return

        # 4. No completions for regular text
        return
