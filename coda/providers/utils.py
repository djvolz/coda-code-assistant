"""Shared utilities for provider implementations."""

from typing import List, Dict, Any, Optional

from .base import Message


def convert_messages_basic(messages: List[Message]) -> List[Dict[str, Any]]:
    """Convert Message objects to basic format for most providers.
    
    Args:
        messages: List of Message objects
        
    Returns:
        List of message dictionaries with role and content
    """
    return [
        {
            "role": msg.role.value,
            "content": msg.content,
        }
        for msg in messages
    ]


def convert_messages_with_name(messages: List[Message]) -> List[Dict[str, Any]]:
    """Convert Message objects to format supporting name field (e.g., OpenAI/LiteLLM).
    
    Args:
        messages: List of Message objects
        
    Returns:
        List of message dictionaries with role, content, and optional name
    """
    return [
        {
            "role": msg.role.value,
            "content": msg.content,
            **({"name": msg.name} if msg.name else {}),
        }
        for msg in messages
    ]


def extract_basic_model_info(model_data: Dict[str, Any], name_key: str = "name") -> Dict[str, Any]:
    """Extract basic model information from provider model data.
    
    Args:
        model_data: Raw model data from provider
        name_key: Key to use for model name
        
    Returns:
        Standardized model info dictionary
    """
    return {
        "name": model_data.get(name_key, "unknown"),
        "provider": model_data.get("provider", "unknown"),
        "description": model_data.get("description", ""),
        "context_length": model_data.get("context_length", 4096),
        "capabilities": model_data.get("capabilities", []),
    }


def build_request_params(
    model: str,
    temperature: float = 0.7,
    max_tokens: Optional[int] = None,
    top_p: Optional[float] = None,
    stop: Optional[List[str]] = None,
    stream: bool = False,
    **kwargs
) -> Dict[str, Any]:
    """Build common request parameters for provider API calls.
    
    Args:
        model: Model name
        temperature: Sampling temperature
        max_tokens: Maximum tokens to generate
        top_p: Top-p sampling parameter
        stop: Stop sequences
        stream: Whether to stream responses
        **kwargs: Additional parameters
        
    Returns:
        Parameters dictionary
    """
    params = {
        "model": model,
        "temperature": temperature,
        "stream": stream,
    }
    
    if max_tokens is not None:
        params["max_tokens"] = max_tokens
    if top_p is not None:
        params["top_p"] = top_p
    if stop:
        params["stop"] = stop if isinstance(stop, list) else [stop]
    
    # Add any additional parameters
    params.update(kwargs)
    
    return params