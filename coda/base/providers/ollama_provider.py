"""Ollama provider implementation for local model execution."""

import json
from collections.abc import AsyncIterator, Callable, Iterator
from typing import TypeVar

import httpx

from .base import (
    BaseProvider,
    ChatCompletion,
    ChatCompletionChunk,
    Message,
    Model,
    Tool,
    ToolCall,
)
from .tool_converter import ToolConverter

T = TypeVar("T")


class OllamaProvider(BaseProvider):
    """Ollama provider for local LLM execution."""

    def __init__(self, host: str = "http://localhost:11434", timeout: float = 120.0, **kwargs):
        """
        Initialize Ollama provider.

        Args:
            host: Ollama server URL
            timeout: Request timeout in seconds
            **kwargs: Additional provider settings
        """
        super().__init__(**kwargs)
        self.host = host.rstrip("/")
        self.timeout = timeout
        self._client = httpx.Client(timeout=timeout)
        self._async_client = httpx.AsyncClient(timeout=timeout)

    def _handle_tool_fallback(
        self,
        func: Callable,
        messages: list[Message],
        model: str,
        tools: list[Tool] | None,
        *args,
        **kwargs,
    ) -> T:
        """
        Handle tool fallback for methods that may fail with tool support errors.

        Args:
            func: The function to call
            messages: Chat messages
            model: Model name
            tools: Optional tools list
            *args: Additional positional arguments
            **kwargs: Additional keyword arguments

        Returns:
            The result from the function call
        """
        try:
            return func(messages, model, *args, tools=tools, **kwargs)
        except httpx.HTTPStatusError as e:
            error_text = e.response.text

            # If model doesn't support tools and we have tools, retry without them
            if "does not support tools" in error_text and tools:
                # Only show warning if this seems like a query that might actually need tools
                if self._should_warn_about_tools(messages):
                    self._show_tool_warning(model)
                # Retry without tools
                return func(messages, model, *args, tools=None, **kwargs)

            # Handle other errors
            if e.response.status_code == 404:
                raise ValueError(
                    f"Model '{model}' not found. Please pull it first with: ollama pull {model}"
                ) from None

            raise RuntimeError(f"Ollama API error: {error_text}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama error: {str(e)}") from e

    def _handle_stream_fallback(
        self,
        func: Callable,
        messages: list[Message],
        model: str,
        tools: list[Tool] | None,
        *args,
        **kwargs,
    ) -> Iterator[ChatCompletionChunk]:
        """
        Handle tool fallback for streaming methods.

        Yields chunks from the function, handling tool fallback if needed.
        """
        try:
            yield from func(messages, model, *args, tools=tools, **kwargs)
        except httpx.HTTPStatusError as e:
            error_text = e.response.text

            # If model doesn't support tools and we have tools, retry without them
            if "does not support tools" in error_text and tools:
                # Only show warning if this seems like a query that might actually need tools
                if self._should_warn_about_tools(messages):
                    self._show_tool_warning(model)
                # Retry without tools
                yield from func(messages, model, *args, tools=None, **kwargs)
                return

            # Handle other errors
            if e.response.status_code == 404:
                raise ValueError(
                    f"Model '{model}' not found. Please pull it first with: ollama pull {model}"
                ) from None

            raise RuntimeError(f"Ollama streaming error: {error_text}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama streaming error: {str(e)}") from e

    @property
    def name(self) -> str:
        """Provider name."""
        return "ollama"

    def supports_tool_calling(self, model_name: str) -> bool:
        """Check if the model supports tool calling by attempting a test call."""
        # For now, assume all models might support tools and let the API decide
        # This avoids maintaining a hardcoded list that gets outdated
        # The actual compatibility check happens when tools are used
        return True

    def _parse_tool_calls(self, message: dict) -> list[ToolCall] | None:
        """Parse tool calls from Ollama response message."""
        return ToolConverter.parse_tool_calls_ollama(message)

    def _convert_messages(self, messages: list[Message]) -> list[dict]:
        """Convert our Message objects to Ollama format."""
        from .utils import convert_messages_basic

        return convert_messages_basic(messages)

    def _extract_model_info(self, model_data: dict) -> Model:
        """Extract model information from Ollama model data."""
        model_name = model_data.get("name", "unknown")

        # Parse model info from details if available
        details = model_data.get("details", {})
        parameter_size = details.get("parameter_size", "")

        # Estimate context length based on model
        context_length = 4096  # Default
        if "32k" in model_name.lower():
            context_length = 32768
        elif "16k" in model_name.lower():
            context_length = 16384
        elif "8k" in model_name.lower():
            context_length = 8192
        elif "100k" in model_name.lower():
            context_length = 102400

        return Model(
            id=model_name,
            name=model_name,
            provider="ollama",
            context_length=context_length,
            max_tokens=4096,  # Ollama models typically support 4k output
            supports_streaming=True,
            supports_functions=self.supports_tool_calling(model_name),
            metadata={
                "parameter_size": parameter_size,
                "family": details.get("family", ""),
                "format": details.get("format", ""),
                "families": details.get("families", []),
                "size": model_data.get("size", 0),
                "digest": model_data.get("digest", ""),
            },
        )

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
        """Send chat completion request to Ollama."""
        return self._handle_tool_fallback(
            self._chat_native_ollama,
            messages,
            model,
            tools,
            temperature,
            max_tokens,
            top_p,
            stop,
            **kwargs,
        )

    def _chat_native_ollama(
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
        """Send chat completion request using native Ollama API."""
        # Convert messages
        ollama_messages = self._convert_messages(messages)

        # Prepare request data
        data = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        # Add tools if provided - let Ollama decide if it supports them
        if tools:
            ollama_tools = ToolConverter.to_ollama(tools)
            if ollama_tools:
                data["tools"] = ollama_tools

        # Add optional parameters
        if max_tokens:
            data["options"]["num_predict"] = max_tokens
        if top_p is not None:
            data["options"]["top_p"] = top_p
        if stop:
            data["options"]["stop"] = stop if isinstance(stop, list) else [stop]

        # Add any additional options from kwargs
        for key, value in kwargs.items():
            if key not in data:
                data["options"][key] = value

        # Make request
        response = self._client.post(
            f"{self.host}/api/chat",
            json=data,
        )
        response.raise_for_status()

        # Parse response
        result = response.json()

        # Extract message content
        message = result.get("message", {})
        content = message.get("content", "")

        # Parse tool calls if present
        tool_calls = self._parse_tool_calls(message)

        # Calculate token usage if available
        usage = None
        if "prompt_eval_count" in result or "eval_count" in result:
            usage = {
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
            }

        return ChatCompletion(
            content=content,
            model=model,
            finish_reason="stop",  # Ollama doesn't provide finish reasons
            tool_calls=tool_calls,
            usage=usage,
            metadata={
                "total_duration": result.get("total_duration"),
                "load_duration": result.get("load_duration"),
                "prompt_eval_duration": result.get("prompt_eval_duration"),
                "eval_duration": result.get("eval_duration"),
            },
        )

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
        """Stream chat completion response from Ollama."""
        yield from self._handle_stream_fallback(
            self._chat_stream_native_ollama,
            messages,
            model,
            tools,
            temperature,
            max_tokens,
            top_p,
            stop,
            **kwargs,
        )

    def _chat_stream_native_ollama(
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
        """Stream chat completion using native Ollama API."""
        # Convert messages
        ollama_messages = self._convert_messages(messages)

        # Prepare request data
        data = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }

        # Add tools if provided - let Ollama decide if it supports them
        if tools:
            ollama_tools = ToolConverter.to_ollama(tools)
            if ollama_tools:
                data["tools"] = ollama_tools

        # Add optional parameters
        if max_tokens:
            data["options"]["num_predict"] = max_tokens
        if top_p is not None:
            data["options"]["top_p"] = top_p
        if stop:
            data["options"]["stop"] = stop if isinstance(stop, list) else [stop]

        # Add any additional options from kwargs
        for key, value in kwargs.items():
            if key not in data:
                data["options"][key] = value

        # Make streaming request
        with self._client.stream(
            "POST",
            f"{self.host}/api/chat",
            json=data,
        ) as response:
            response.raise_for_status()

            # Process stream
            for line in response.iter_lines():
                if line:
                    try:
                        chunk_data = json.loads(line)

                        # Extract message content
                        message = chunk_data.get("message", {})
                        content = message.get("content", "")

                        # Check if this is the final chunk
                        done = chunk_data.get("done", False)
                        finish_reason = "stop" if done else None

                        # Handle tool calls - they might come in the final chunk
                        tool_calls = None
                        if done:
                            tool_calls = self._parse_tool_calls(message)

                        # Extract usage from final chunk
                        usage = None
                        if done and (
                            "prompt_eval_count" in chunk_data or "eval_count" in chunk_data
                        ):
                            usage = {
                                "prompt_tokens": chunk_data.get("prompt_eval_count", 0),
                                "completion_tokens": chunk_data.get("eval_count", 0),
                                "total_tokens": chunk_data.get("prompt_eval_count", 0)
                                + chunk_data.get("eval_count", 0),
                            }

                        yield ChatCompletionChunk(
                            content=content,
                            model=model,
                            finish_reason=finish_reason,
                            tool_calls=tool_calls,
                            usage=usage,
                            metadata={
                                "done": done,
                            },
                        )

                    except json.JSONDecodeError:
                        continue

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
        """Async chat completion via Ollama."""
        try:
            return await self._achat_native_ollama(
                messages, model, temperature, max_tokens, top_p, stop, tools, **kwargs
            )
        except httpx.HTTPStatusError as e:
            error_text = e.response.text

            # If model doesn't support tools and we have tools, retry without them
            if "does not support tools" in error_text and tools:
                # Only show warning if this seems like a query that might actually need tools
                if self._should_warn_about_tools(messages):
                    self._show_tool_warning(model)
                # Retry without tools
                return await self._achat_native_ollama(
                    messages, model, temperature, max_tokens, top_p, stop, None, **kwargs
                )

            # Handle other errors
            if e.response.status_code == 404:
                raise ValueError(
                    f"Model '{model}' not found. Please pull it first with: ollama pull {model}"
                ) from None

            raise RuntimeError(f"Ollama async error: {error_text}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama async error: {str(e)}") from e

    async def _achat_native_ollama(
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
        """Async chat completion using native Ollama API."""
        # Convert messages
        ollama_messages = self._convert_messages(messages)

        # Prepare request data
        data = {
            "model": model,
            "messages": ollama_messages,
            "stream": False,
            "options": {
                "temperature": temperature,
            },
        }

        # Add tools if provided - let Ollama decide if it supports them
        if tools:
            ollama_tools = ToolConverter.to_ollama(tools)
            if ollama_tools:
                data["tools"] = ollama_tools

        # Add optional parameters
        if max_tokens:
            data["options"]["num_predict"] = max_tokens
        if top_p is not None:
            data["options"]["top_p"] = top_p
        if stop:
            data["options"]["stop"] = stop if isinstance(stop, list) else [stop]

        # Add any additional options from kwargs
        for key, value in kwargs.items():
            if key not in data:
                data["options"][key] = value

        # Make async request
        response = await self._async_client.post(
            f"{self.host}/api/chat",
            json=data,
        )
        response.raise_for_status()

        # Parse response
        result = response.json()

        # Extract message content
        message = result.get("message", {})
        content = message.get("content", "")

        # Parse tool calls if present
        tool_calls = self._parse_tool_calls(message)

        # Calculate token usage if available
        usage = None
        if "prompt_eval_count" in result or "eval_count" in result:
            usage = {
                "prompt_tokens": result.get("prompt_eval_count", 0),
                "completion_tokens": result.get("eval_count", 0),
                "total_tokens": result.get("prompt_eval_count", 0) + result.get("eval_count", 0),
            }

        return ChatCompletion(
            content=content,
            model=model,
            finish_reason="stop",
            tool_calls=tool_calls,
            usage=usage,
            metadata={
                "total_duration": result.get("total_duration"),
                "load_duration": result.get("load_duration"),
                "prompt_eval_duration": result.get("prompt_eval_duration"),
                "eval_duration": result.get("eval_duration"),
            },
        )

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
        """Async stream chat completion via Ollama."""
        try:
            async for chunk in self._achat_stream_native_ollama(
                messages, model, temperature, max_tokens, top_p, stop, tools, **kwargs
            ):
                yield chunk
        except httpx.HTTPStatusError as e:
            error_text = e.response.text

            # If model doesn't support tools and we have tools, retry without them
            if "does not support tools" in error_text and tools:
                # Only show warning if this seems like a query that might actually need tools
                if self._should_warn_about_tools(messages):
                    self._show_tool_warning(model)
                # Retry without tools
                async for chunk in self._achat_stream_native_ollama(
                    messages, model, temperature, max_tokens, top_p, stop, None, **kwargs
                ):
                    yield chunk
                return

            # Handle other errors
            if e.response.status_code == 404:
                raise ValueError(
                    f"Model '{model}' not found. Please pull it first with: ollama pull {model}"
                ) from None

            raise RuntimeError(f"Ollama async streaming error: {error_text}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama async streaming error: {str(e)}") from e

    async def _achat_stream_native_ollama(
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
        """Async stream chat completion using native Ollama API."""
        # Convert messages
        ollama_messages = self._convert_messages(messages)

        # Prepare request data
        data = {
            "model": model,
            "messages": ollama_messages,
            "stream": True,
            "options": {
                "temperature": temperature,
            },
        }

        # Add tools if provided - let Ollama decide if it supports them
        if tools:
            ollama_tools = ToolConverter.to_ollama(tools)
            if ollama_tools:
                data["tools"] = ollama_tools

        # Add optional parameters
        if max_tokens:
            data["options"]["num_predict"] = max_tokens
        if top_p is not None:
            data["options"]["top_p"] = top_p
        if stop:
            data["options"]["stop"] = stop if isinstance(stop, list) else [stop]

        # Add any additional options from kwargs
        for key, value in kwargs.items():
            if key not in data:
                data["options"][key] = value

        # Make async streaming request
        async with self._async_client.stream(
            "POST",
            f"{self.host}/api/chat",
            json=data,
        ) as response:
            response.raise_for_status()

            # Process stream
            async for line in response.aiter_lines():
                if line:
                    try:
                        chunk_data = json.loads(line)

                        # Extract message content
                        message = chunk_data.get("message", {})
                        content = message.get("content", "")

                        # Check if this is the final chunk
                        done = chunk_data.get("done", False)
                        finish_reason = "stop" if done else None

                        # Handle tool calls - they might come in the final chunk
                        tool_calls = None
                        if done:
                            tool_calls = self._parse_tool_calls(message)

                        # Extract usage from final chunk
                        usage = None
                        if done and (
                            "prompt_eval_count" in chunk_data or "eval_count" in chunk_data
                        ):
                            usage = {
                                "prompt_tokens": chunk_data.get("prompt_eval_count", 0),
                                "completion_tokens": chunk_data.get("eval_count", 0),
                                "total_tokens": chunk_data.get("prompt_eval_count", 0)
                                + chunk_data.get("eval_count", 0),
                            }

                        yield ChatCompletionChunk(
                            content=content,
                            model=model,
                            finish_reason=finish_reason,
                            tool_calls=tool_calls,
                            usage=usage,
                            metadata={
                                "done": done,
                            },
                        )

                    except json.JSONDecodeError:
                        continue

    def list_models(self) -> list[Model]:
        """List available models from Ollama."""
        try:
            response = self._client.get(f"{self.host}/api/tags")
            response.raise_for_status()

            data = response.json()
            models = []

            for model_data in data.get("models", []):
                models.append(self._extract_model_info(model_data))

            return models

        except Exception as e:
            # Return empty list if Ollama is not running
            print(f"Warning: Could not list Ollama models: {e}")
            return []

    def pull_model(self, model: str) -> None:
        """Pull a model from Ollama registry."""
        try:
            # Make pull request
            response = self._client.post(
                f"{self.host}/api/pull",
                json={"name": model},
                timeout=None,  # Pulling can take a long time
            )
            response.raise_for_status()

            # Process streaming response
            for line in response.iter_lines():
                if line:
                    data = json.loads(line)
                    status = data.get("status", "")
                    if status:
                        print(f"Ollama: {status}")

        except Exception as e:
            raise RuntimeError(f"Failed to pull model '{model}': {str(e)}") from e

    def delete_model(self, model: str) -> None:
        """Delete a model from Ollama."""
        try:
            response = self._client.delete(
                f"{self.host}/api/delete",
                json={"name": model},
            )
            response.raise_for_status()

        except Exception as e:
            raise RuntimeError(f"Failed to delete model '{model}': {str(e)}") from e

    def __del__(self):
        """Cleanup clients on deletion."""
        if hasattr(self, "_client"):
            self._client.close()
        if hasattr(self, "_async_client"):
            try:
                import asyncio

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    loop.create_task(self._async_client.aclose())
                else:
                    loop.run_until_complete(self._async_client.aclose())
            except Exception:
                pass
