"""Ollama provider implementation for local model execution."""

import json
from collections.abc import AsyncIterator, Iterator

import httpx

from .base import (
    BaseProvider,
    ChatCompletion,
    ChatCompletionChunk,
    Message,
    Model,
    Tool,
)


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

    @property
    def name(self) -> str:
        """Provider name."""
        return "ollama"

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
            supports_functions=False,  # Ollama doesn't natively support functions
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
        try:
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

            # Calculate token usage if available
            usage = None
            if "prompt_eval_count" in result or "eval_count" in result:
                usage = {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0)
                    + result.get("eval_count", 0),
                }

            return ChatCompletion(
                content=content,
                model=model,
                finish_reason="stop",  # Ollama doesn't provide finish reasons
                usage=usage,
                metadata={
                    "total_duration": result.get("total_duration"),
                    "load_duration": result.get("load_duration"),
                    "prompt_eval_duration": result.get("prompt_eval_duration"),
                    "eval_duration": result.get("eval_duration"),
                },
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(
                    f"Model '{model}' not found. Please pull it first with: ollama pull {model}"
                ) from None
            raise RuntimeError(f"Ollama API error: {e.response.text}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama error: {str(e)}") from e

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
        try:
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
                                usage=usage,
                                metadata={
                                    "done": done,
                                },
                            )

                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(
                    f"Model '{model}' not found. Please pull it first with: ollama pull {model}"
                ) from None
            raise RuntimeError(f"Ollama streaming error: {e.response.text}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama streaming error: {str(e)}") from e

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

            # Calculate token usage if available
            usage = None
            if "prompt_eval_count" in result or "eval_count" in result:
                usage = {
                    "prompt_tokens": result.get("prompt_eval_count", 0),
                    "completion_tokens": result.get("eval_count", 0),
                    "total_tokens": result.get("prompt_eval_count", 0)
                    + result.get("eval_count", 0),
                }

            return ChatCompletion(
                content=content,
                model=model,
                finish_reason="stop",
                usage=usage,
                metadata={
                    "total_duration": result.get("total_duration"),
                    "load_duration": result.get("load_duration"),
                    "prompt_eval_duration": result.get("prompt_eval_duration"),
                    "eval_duration": result.get("eval_duration"),
                },
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(
                    f"Model '{model}' not found. Please pull it first with: ollama pull {model}"
                ) from None
            raise RuntimeError(f"Ollama async error: {e.response.text}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama async error: {str(e)}") from e

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
                                usage=usage,
                                metadata={
                                    "done": done,
                                },
                            )

                        except json.JSONDecodeError:
                            continue

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(
                    f"Model '{model}' not found. Please pull it first with: ollama pull {model}"
                ) from None
            raise RuntimeError(f"Ollama async streaming error: {e.response.text}") from e
        except Exception as e:
            raise RuntimeError(f"Ollama async streaming error: {str(e)}") from e

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
