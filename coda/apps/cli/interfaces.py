"""Interfaces and protocols for CLI components to avoid circular imports."""

from typing import Any, Protocol

from prompt_toolkit.completion import CompleteEvent, Completion
from prompt_toolkit.document import Document


class CompletionProvider(Protocol):
    """Protocol for completion providers."""

    def get_completions(
        self, document: Document, complete_event: CompleteEvent
    ) -> list[Completion]:
        """Get completions for the given document."""
        ...


class CommandHandler(Protocol):
    """Protocol for command handlers."""

    def handle(self, args: str) -> Any:
        """Handle a command with the given arguments."""
        ...


class CommandDefinitionProtocol(Protocol):
    """Protocol for command definitions."""

    name: str
    description: str
    aliases: list[str]
    completion_type: str | None

    def get_all_names(self) -> list[str]:
        """Get all names including aliases."""
        ...


class SessionManagerProtocol(Protocol):
    """Protocol for session management."""

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all available sessions."""
        ...


class ProviderProtocol(Protocol):
    """Protocol for AI providers."""

    def list_models(self) -> list[Any]:
        """List available models."""
        ...
