"""Base provider interface for all LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    """Message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"  # For tool response messages


@dataclass
class Tool:
    """Tool definition for function calling."""

    name: str
    description: str
    parameters: dict  # JSON Schema format


@dataclass
class ToolCall:
    """Tool call request from the model."""

    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    """Result from executing a tool."""

    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass
class Message:
    """Chat message."""

    role: Role
    content: str
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None  # For tool response messages
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatCompletion:
    """Chat completion response."""

    content: str
    model: str
    finish_reason: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: dict | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatCompletionChunk:
    """Streaming chat completion chunk."""

    content: str
    model: str
    finish_reason: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: dict | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Model:
    """Model information."""

    id: str
    name: str
    provider: str
    context_length: int | None = None
    max_tokens: int | None = None
    supports_streaming: bool = True
    supports_functions: bool = False
    metadata: dict = field(default_factory=dict)


class BaseProvider(ABC):
    """Abstract base class for LLM providers."""

    def __init__(self, **kwargs):
        """Initialize provider with configuration."""
        self.config = kwargs

    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[Tool] | None = None,
        **kwargs,
    ) -> ChatCompletion:
        """
        Send chat completion request.

        Args:
            messages: List of chat messages
            model: Model identifier
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            **kwargs: Provider-specific parameters

        Returns:
            ChatCompletion response
        """
        pass

    @abstractmethod
    def chat_stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[Tool] | None = None,
        **kwargs,
    ) -> Iterator[ChatCompletionChunk]:
        """
        Stream chat completion response.

        Args:
            messages: List of chat messages
            model: Model identifier
            temperature: Sampling temperature (0-2)
            max_tokens: Maximum tokens to generate
            top_p: Nucleus sampling parameter
            stop: Stop sequences
            **kwargs: Provider-specific parameters

        Yields:
            ChatCompletionChunk objects
        """
        pass

    @abstractmethod
    async def achat(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        **kwargs,
    ) -> ChatCompletion:
        """Async version of chat."""
        pass

    @abstractmethod
    async def achat_stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        **kwargs,
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Async version of chat_stream."""
        pass

    @abstractmethod
    def list_models(self) -> list[Model]:
        """
        List available models.

        Returns:
            List of Model objects
        """
        pass

    def validate_model(self, model: str) -> bool:
        """
        Validate if model is supported.

        Args:
            model: Model identifier

        Returns:
            True if model is supported
        """
        models = self.list_models()
        return any(m.id == model for m in models)

    def get_model_info(self, model: str) -> Model | None:
        """
        Get model information.

        Args:
            model: Model identifier

        Returns:
            Model object if found, None otherwise
        """
        models = self.list_models()
        for m in models:
            if m.id == model:
                return m
        return None

    def _should_warn_about_tools(self, messages: list[Message]) -> bool:
        """
        Determine if we should warn about tool support based on the conversation content.

        Returns False for simple greetings and basic questions that likely don't need tools.
        """
        if not messages:
            return False

        # Get the last user message
        last_message = None
        for message in reversed(messages):
            if message.role == Role.USER:
                last_message = message
                break

        if not last_message:
            return False

        content = last_message.content.lower().strip()

        # Simple greetings and basic interactions - don't warn
        simple_patterns = [
            # Greetings
            "hi",
            "hello",
            "hey",
            "good morning",
            "good afternoon",
            "good evening",
            # Basic questions
            "how are you",
            "what's up",
            "how's it going",
            # Simple requests
            "tell me",
            "explain",
            "what is",
            "what are",
            "who is",
            "who are",
            "write",
            "create",
            "make",
            "help me understand",
            # Math and general knowledge
            "calculate",
            "what's",
            "how much",
            "convert",
        ]

        # Check if the message starts with any simple pattern
        for pattern in simple_patterns:
            if content.startswith(pattern):
                return False

        # Tool-like requests - do warn
        tool_patterns = [
            "read",
            "file",
            "directory",
            "folder",
            "search",
            "find",
            "execute",
            "run",
            "install",
            "download",
            "upload",
            "save",
            "delete",
            "remove",
            "move",
            "git",
            "commit",
            "push",
            "pull",
            "branch",
            "checkout",
            "status",
            "test",
            "build",
            "compile",
            "deploy",
            "server",
            "database",
            "api",
        ]

        # Check if the message contains tool-like keywords
        for pattern in tool_patterns:
            if pattern in content:
                return True

        # Default to not warning for short, simple messages
        if len(content) < 50 and not any(
            word in content for word in ["file", "folder", "execute", "run"]
        ):
            return False

        # For longer messages or unclear cases, show the warning
        return True

    def _show_tool_warning(self, model: str) -> None:
        """Show a clean warning about tool support limitations."""
        try:
            from rich.console import Console
            from rich.panel import Panel

            # Create a temporary console for the warning
            console = Console()

            warning_text = f"""⚠️  Tool Support Limitation

Model '{model}' does not support tool calling.
Proceeding without tools for this request.

For tool support, use a compatible model from your provider's tool-capable models."""

            console.print()
            console.print(
                Panel(
                    warning_text,
                    title="Notice",
                    border_style="yellow",
                    title_style="bold yellow",
                )
            )

        except Exception:
            # Fallback to simple print if Rich is not available
            print(f"\n⚠️  Model '{model}' does not support tool calling. Proceeding without tools.")
            print(
                "For tool support, use a compatible model from your provider's tool-capable models.\n"
            )
