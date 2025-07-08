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
