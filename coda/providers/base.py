"""Base provider interface for all LLM providers."""

from abc import ABC, abstractmethod
from typing import AsyncIterator, Dict, Iterator, List, Optional, Union
from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    """Message roles."""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"


@dataclass
class Message:
    """Chat message."""
    role: Role
    content: str
    name: Optional[str] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class ChatCompletion:
    """Chat completion response."""
    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class ChatCompletionChunk:
    """Streaming chat completion chunk."""
    content: str
    model: str
    finish_reason: Optional[str] = None
    usage: Optional[Dict] = None
    metadata: Dict = field(default_factory=dict)


@dataclass
class Model:
    """Model information."""
    id: str
    name: str
    provider: str
    context_length: Optional[int] = None
    max_tokens: Optional[int] = None
    supports_streaming: bool = True
    supports_functions: bool = False
    metadata: Dict = field(default_factory=dict)


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
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs
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
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs
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
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs
    ) -> ChatCompletion:
        """Async version of chat."""
        pass
    
    @abstractmethod
    async def achat_stream(
        self,
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Async version of chat_stream."""
        pass
    
    @abstractmethod
    def list_models(self) -> List[Model]:
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
    
    def get_model_info(self, model: str) -> Optional[Model]:
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