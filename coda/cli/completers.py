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
            for cmd_name, cmd in sorted(self.commands.items()):
                yield Completion(
                    f"/{cmd_name}",
                    start_position=0,
                    display=f"/{cmd_name}",
                    display_meta=cmd.help_text,
                    style="fg:cyan bold",
                )
            return

        # Must start with /
        if not text.startswith("/"):
            return

        # Get the command part (before first space)
        parts = text.split(maxsplit=1)
        cmd_part = parts[0][1:]  # Remove leading /

        # If we have a space, we're completing subcommands
        if len(parts) > 1 and cmd_part in self.commands:
            cmd = self.commands[cmd_part]
            if hasattr(cmd, "get_autocomplete_options"):
                subcommand_part = parts[1]
                options = cmd.get_autocomplete_options()

                for option in sorted(options):
                    matches, score = FuzzyMatcher.fuzzy_match(subcommand_part, option)
                    if matches:
                        yield Completion(
                            option,
                            start_position=-len(subcommand_part),
                            display=option,
                            display_meta=f"Score: {score:.1%}" if score < 1.0 else None,
                            style="fg:green" if score >= 0.9 else "fg:yellow",
                        )
            return

        # Complete command names with fuzzy matching
        completions = []

        # Check main commands
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
                            style="fg:cyan bold" if score >= 0.9 else "fg:cyan",
                        ),
                    )
                )

            # Check aliases
            for alias in cmd.aliases:
                matches, score = FuzzyMatcher.fuzzy_match(cmd_part, alias)
                if matches:
                    completions.append(
                        (
                            score * 0.95,  # Slightly lower priority for aliases
                            Completion(
                                "/" + alias,
                                start_position=-len(text),
                                display=f"/{alias}",
                                display_meta=f"→ /{cmd_name}",
                                style="fg:blue italic",
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

        # Import here to avoid circular imports
        from .command_registry import CommandRegistry

        # Parse command structure
        parts = text.split()
        if len(parts) < 1:
            return

        # Get the main command
        main_cmd_name = parts[0][1:]  # Remove /
        main_cmd = CommandRegistry.get_command(main_cmd_name)
        if not main_cmd:
            return

        # Check if we're completing a value for the main command
        if main_cmd.completion_type and text.startswith(f"/{main_cmd_name} "):
            value_part = text[len(f"/{main_cmd_name} ") :]
            yield from self._complete_value(main_cmd.completion_type, value_part)
            return

        # Check subcommands
        if main_cmd.subcommands and len(parts) >= 2:
            subcommand_name = parts[1]
            # Find the subcommand (including aliases)
            subcommand = None
            for sub in main_cmd.subcommands:
                if subcommand_name in sub.get_all_names():
                    subcommand = sub
                    break

            if subcommand and subcommand.completion_type:
                # We're completing the value after the subcommand
                prefix = f"/{main_cmd_name} {subcommand_name} "
                if text.startswith(prefix):
                    value_part = text[len(prefix) :]
                    yield from self._complete_value(subcommand.completion_type, value_part)

    def _complete_value(self, completion_type: str, value_part: str):
        """Complete a value based on its type."""
        if completion_type == "model_name" and self.get_provider:
            provider = self.get_provider()
            if provider:
                try:
                    models = provider.list_models()
                    for model in sorted(models):
                        matches, score = FuzzyMatcher.fuzzy_match(value_part, model)
                        if matches:
                            yield Completion(
                                model,
                                start_position=-len(value_part),
                                display=model,
                                display_meta="Model",
                                style="fg:magenta bold" if score >= 0.9 else "fg:magenta",
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
                        meta = f"{msgs} messages, {date}"

                        yield Completion(
                            name,
                            start_position=-len(value_part),
                            display=name,
                            display_meta=meta,
                            style="fg:yellow bold" if score >= 0.9 else "fg:yellow",
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
                        style="fg:cyan bold" if score >= 0.9 else "fg:cyan",
                    )


class EnhancedCompleter(BaseCompleter):
    """Enhanced combined completer with all features."""

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
            # First try slash command completion
            slash_completions = list(self.slash_completer.get_completions(document, complete_event))
            if slash_completions:
                yield from slash_completions
                return

            # Then try dynamic value completion
            yield from self.dynamic_completer.get_completions(document, complete_event)
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
