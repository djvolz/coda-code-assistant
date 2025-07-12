"""🔧 BASE MODULE
Provider implementations for Coda.

This module provides a unified interface for various LLM providers.
Providers with external dependencies are imported conditionally.
"""

# Always available - core functionality
from .base import (
    BaseProvider,
    ChatCompletion,
    ChatCompletionChunk,
    Message,
    Model,
    Role,
    Tool,
    ToolCall,
    ToolResult,
)
from .constants import PROVIDERS
from .mock_provider import MockProvider
from .registry import ProviderFactory, ProviderRegistry

# Optional providers - require external dependencies
try:
    from .litellm_provider import LiteLLMProvider
except ImportError:
    LiteLLMProvider = None  # type: ignore

try:
    from .oci_genai import OCIGenAIProvider
except ImportError:
    OCIGenAIProvider = None  # type: ignore

try:
    from .ollama_provider import OllamaProvider
except ImportError:
    OllamaProvider = None  # type: ignore

# Build __all__ dynamically based on available providers
__all__ = [
    # Base classes and types
    "BaseProvider",
    "ChatCompletion",
    "ChatCompletionChunk",
    "Message",
    "Model",
    "Role",
    "Tool",
    "ToolCall",
    "ToolResult",
    # Always available
    "MockProvider",
    "ProviderRegistry",
    "ProviderFactory",
    "PROVIDERS",
]

# Add optional providers if available
if LiteLLMProvider is not None:
    __all__.append("LiteLLMProvider")
if OCIGenAIProvider is not None:
    __all__.append("OCIGenAIProvider")
if OllamaProvider is not None:
    __all__.append("OllamaProvider")
