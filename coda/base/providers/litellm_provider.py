"""LiteLLM provider implementation for gateway access to 100+ LLMs."""

from collections.abc import AsyncIterator, Iterator

import litellm
from litellm import acompletion, completion

from .base import (
    BaseProvider,
    ChatCompletion,
    ChatCompletionChunk,
    Message,
    Model,
    Tool,
)


class LiteLLMProvider(BaseProvider):
    """LiteLLM provider for unified access to multiple LLM providers."""

    def __init__(
        self,
        api_base: str | None = None,
        api_key: str | None = None,
        default_model: str = "gpt-3.5-turbo",
        **kwargs,
    ):
        """
        Initialize LiteLLM provider.

        Args:
            api_base: Optional API base URL for LiteLLM proxy server
            api_key: Optional API key for authentication
            default_model: Default model to use
            **kwargs: Additional provider-specific settings
        """
        super().__init__(**kwargs)

        # Configure LiteLLM
        if api_base:
            litellm.api_base = api_base
        if api_key:
            litellm.api_key = api_key

        self.default_model = default_model

        # Configure any additional settings
        for key, value in kwargs.items():
            if hasattr(litellm, key):
                setattr(litellm, key, value)

    @property
    def name(self) -> str:
        """Provider name."""
        return "litellm"

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """Convert our Message objects to LiteLLM format."""
        from .utils import convert_messages_with_name

        return convert_messages_with_name(messages)

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
        """Send chat completion request via LiteLLM."""
        try:
            # Convert messages to LiteLLM format
            litellm_messages = self._convert_messages(messages)

            # Prepare parameters
            params = {
                "model": model,
                "messages": litellm_messages,
                "temperature": temperature,
                "stream": False,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens
            if top_p is not None:
                params["top_p"] = top_p
            if stop:
                params["stop"] = stop

            # Add any additional kwargs
            params.update(kwargs)

            # Make request
            response = completion(**params)

            # Extract response
            choice = response.choices[0]
            content = choice.message.content
            finish_reason = choice.finish_reason

            # Extract usage
            usage = None
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return ChatCompletion(
                content=content,
                model=model,
                finish_reason=finish_reason,
                usage=usage,
                metadata={
                    "response_id": getattr(response, "id", None),
                    "created": getattr(response, "created", None),
                },
            )

        except Exception as e:
            # LiteLLM wraps provider-specific errors
            raise RuntimeError(f"LiteLLM error: {str(e)}") from e

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
        """Stream chat completion response via LiteLLM."""
        try:
            # Convert messages to LiteLLM format
            litellm_messages = self._convert_messages(messages)

            # Prepare parameters
            params = {
                "model": model,
                "messages": litellm_messages,
                "temperature": temperature,
                "stream": True,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens
            if top_p is not None:
                params["top_p"] = top_p
            if stop:
                params["stop"] = stop

            # Add any additional kwargs
            params.update(kwargs)

            # Make streaming request
            response_stream = completion(**params)

            # Process stream
            for chunk in response_stream:
                if hasattr(chunk, "choices") and chunk.choices:
                    choice = chunk.choices[0]

                    # Extract content from delta
                    content = ""
                    if hasattr(choice, "delta") and hasattr(choice.delta, "content"):
                        content = choice.delta.content or ""

                    # Get finish reason
                    finish_reason = getattr(choice, "finish_reason", None)

                    yield ChatCompletionChunk(
                        content=content,
                        model=model,
                        finish_reason=finish_reason,
                        usage=None,
                        metadata={
                            "chunk_id": getattr(chunk, "id", None),
                        },
                    )

        except Exception as e:
            raise RuntimeError(f"LiteLLM streaming error: {str(e)}") from e

    async def achat(
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
        """Async chat completion via LiteLLM."""
        try:
            # Convert messages to LiteLLM format
            litellm_messages = self._convert_messages(messages)

            # Prepare parameters
            params = {
                "model": model,
                "messages": litellm_messages,
                "temperature": temperature,
                "stream": False,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens
            if top_p is not None:
                params["top_p"] = top_p
            if stop:
                params["stop"] = stop

            # Add any additional kwargs
            params.update(kwargs)

            # Make async request
            response = await acompletion(**params)

            # Extract response
            choice = response.choices[0]
            content = choice.message.content
            finish_reason = choice.finish_reason

            # Extract usage
            usage = None
            if hasattr(response, "usage") and response.usage:
                usage = {
                    "prompt_tokens": response.usage.prompt_tokens,
                    "completion_tokens": response.usage.completion_tokens,
                    "total_tokens": response.usage.total_tokens,
                }

            return ChatCompletion(
                content=content,
                model=model,
                finish_reason=finish_reason,
                usage=usage,
                metadata={
                    "response_id": getattr(response, "id", None),
                    "created": getattr(response, "created", None),
                },
            )

        except Exception as e:
            raise RuntimeError(f"LiteLLM async error: {str(e)}") from e

    async def achat_stream(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[Tool] | None = None,
        **kwargs,
    ) -> AsyncIterator[ChatCompletionChunk]:
        """Async stream chat completion via LiteLLM."""
        try:
            # Convert messages to LiteLLM format
            litellm_messages = self._convert_messages(messages)

            # Prepare parameters
            params = {
                "model": model,
                "messages": litellm_messages,
                "temperature": temperature,
                "stream": True,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens
            if top_p is not None:
                params["top_p"] = top_p
            if stop:
                params["stop"] = stop

            # Add any additional kwargs
            params.update(kwargs)

            # Make async streaming request
            response_stream = await acompletion(**params)

            # Process stream
            async for chunk in response_stream:
                if hasattr(chunk, "choices") and chunk.choices:
                    choice = chunk.choices[0]

                    # Extract content from delta
                    content = ""
                    if hasattr(choice, "delta") and hasattr(choice.delta, "content"):
                        content = choice.delta.content or ""

                    # Get finish reason
                    finish_reason = getattr(choice, "finish_reason", None)

                    yield ChatCompletionChunk(
                        content=content,
                        model=model,
                        finish_reason=finish_reason,
                        usage=None,
                        metadata={
                            "chunk_id": getattr(chunk, "id", None),
                        },
                    )

        except Exception as e:
            raise RuntimeError(f"LiteLLM async streaming error: {str(e)}") from e

    def list_models(self) -> list[Model]:
        """
        List available models.

        Note: LiteLLM doesn't provide a standard way to list models
        across all providers. This returns a curated list of popular models.
        For proxy servers, this should be overridden or configured.
        """
        # Popular models across providers
        # This is a subset - LiteLLM supports 100+ models
        return [
            # OpenAI
            Model(
                id="gpt-4-turbo-preview",
                name="GPT-4 Turbo Preview",
                provider="openai",
                context_length=128000,
                max_tokens=4096,
                supports_streaming=True,
                supports_functions=True,
            ),
            Model(
                id="gpt-4",
                name="GPT-4",
                provider="openai",
                context_length=8192,
                max_tokens=4096,
                supports_streaming=True,
                supports_functions=True,
            ),
            Model(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider="openai",
                context_length=16385,
                max_tokens=4096,
                supports_streaming=True,
                supports_functions=True,
            ),
            # Anthropic
            Model(
                id="claude-3-opus-20240229",
                name="Claude 3 Opus",
                provider="anthropic",
                context_length=200000,
                max_tokens=4096,
                supports_streaming=True,
                supports_functions=False,
            ),
            Model(
                id="claude-3-sonnet-20240229",
                name="Claude 3 Sonnet",
                provider="anthropic",
                context_length=200000,
                max_tokens=4096,
                supports_streaming=True,
                supports_functions=False,
            ),
            # Google
            Model(
                id="gemini-pro",
                name="Gemini Pro",
                provider="google",
                context_length=32760,
                max_tokens=8192,
                supports_streaming=True,
                supports_functions=True,
            ),
            # Cohere
            Model(
                id="command-r-plus",
                name="Command R Plus",
                provider="cohere",
                context_length=128000,
                max_tokens=4000,
                supports_streaming=True,
                supports_functions=True,
            ),
            # Mistral
            Model(
                id="mistral-large-latest",
                name="Mistral Large",
                provider="mistral",
                context_length=32000,
                max_tokens=4096,
                supports_streaming=True,
                supports_functions=True,
            ),
        ]
