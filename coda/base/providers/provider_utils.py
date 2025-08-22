"""Common utilities for provider implementations."""

from collections.abc import Callable
from typing import TypeVar

import httpx

T = TypeVar("T")


class ProviderError(Exception):
    """Base exception for provider errors."""

    pass


class ModelNotFoundError(ProviderError):
    """Raised when a model is not found."""

    pass


class ToolNotSupportedError(ProviderError):
    """Raised when a model doesn't support tools."""

    pass


class ProviderConnectionError(ProviderError):
    """Raised when provider connection fails."""

    pass


class ProviderErrorHandler:
    """Utility class for standardized error handling across providers."""

    @staticmethod
    def handle_http_error(e: httpx.HTTPStatusError, model: str, provider_name: str) -> Exception:
        """
        Convert HTTP errors to standardized provider exceptions.

        Args:
            e: The HTTP error
            model: Model name
            provider_name: Provider name

        Returns:
            Appropriate provider exception
        """
        error_text = e.response.text

        if e.response.status_code == 404:
            return ModelNotFoundError(
                f"Model '{model}' not found in {provider_name}. "
                f"Please check the model name or pull it first."
            )
        elif "does not support tools" in error_text:
            return ToolNotSupportedError(
                f"Model '{model}' does not support tool calling in {provider_name}"
            )
        elif e.response.status_code >= 500:
            return ProviderConnectionError(
                f"{provider_name} server error ({e.response.status_code}): {error_text}"
            )
        else:
            return ProviderError(
                f"{provider_name} API error ({e.response.status_code}): {error_text}"
            )

    @staticmethod
    def with_tool_fallback(func: Callable[..., T], *args, tools=None, **kwargs) -> T:
        """
        Execute a function with automatic tool fallback.

        Args:
            func: Function to execute
            *args: Positional arguments
            tools: Tools list (will be set to None on fallback)
            **kwargs: Keyword arguments

        Returns:
            Function result
        """
        try:
            return func(*args, tools=tools, **kwargs)
        except ToolNotSupportedError:
            if tools is not None:
                return func(*args, tools=None, **kwargs)
            raise


class HTTPClientMixin:
    """Mixin for proper HTTP client management."""

    def __init__(self, timeout: float = 120.0, **kwargs):
        super().__init__(**kwargs)
        self.timeout = timeout
        self._client = None
        self._async_client = None

    @property
    def client(self) -> httpx.Client:
        """Get or create sync HTTP client."""
        if self._client is None:
            self._client = httpx.Client(timeout=self.timeout)
        return self._client

    @property
    def async_client(self) -> httpx.AsyncClient:
        """Get or create async HTTP client."""
        if self._async_client is None:
            self._async_client = httpx.AsyncClient(timeout=self.timeout)
        return self._async_client

    def close(self):
        """Close HTTP clients."""
        if self._client:
            self._client.close()
            self._client = None
        if self._async_client:
            import asyncio

            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._async_client.aclose())
                else:
                    loop.run_until_complete(self._async_client.aclose())
            except Exception:
                pass
            self._async_client = None

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self._async_client:
            await self._async_client.aclose()
            self._async_client = None
        if self._client:
            self._client.close()
            self._client = None
