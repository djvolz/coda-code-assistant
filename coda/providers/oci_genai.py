"""Oracle Cloud Infrastructure (OCI) Generative AI provider implementation using OCI SDK."""

import asyncio
import json
import os
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from pathlib import Path

import oci
from oci.generative_ai import GenerativeAiClient
from oci.generative_ai_inference import GenerativeAiInferenceClient
from oci.generative_ai_inference.models import (
    AssistantMessage,
    ChatDetails,
    CohereChatBotMessage,
    CohereChatRequest,
    CohereSystemMessage,
    CohereUserMessage,
    GenericChatRequest,
    OnDemandServingMode,
    SystemMessage,
    TextContent,
    UserMessage,
)

try:
    import tomllib
except ImportError:
    try:
        import tomli as tomllib
    except ImportError:
        tomllib = None

from coda.providers.base import (
    BaseProvider,
    ChatCompletion,
    ChatCompletionChunk,
    Message,
    Model,
    Role,
)


class OCIGenAIProvider(BaseProvider):
    """Oracle Cloud Infrastructure Generative AI provider using OCI SDK."""

    # Cache for discovered models
    _model_cache: list[Model] | None = None
    _cache_timestamp: datetime | None = None
    _cache_duration_hours = 24  # Cache models for 24 hours
    _model_id_map: dict[str, str] = {}  # Maps friendly names to OCI model IDs

    def __init__(
        self,
        compartment_id: str | None = None,
        config_file_location: str = "~/.oci/config",
        config_profile: str = "DEFAULT",
        **kwargs,
    ):
        """
        Initialize OCI GenAI provider using OCI SDK.

        Args:
            compartment_id: OCI compartment ID (can also be set via OCI_COMPARTMENT_ID env var or Coda config)
            config_file_location: Path to OCI config file
            config_profile: Profile name in config file
        """
        super().__init__(**kwargs)

        # Try to get compartment ID from multiple sources
        self.compartment_id = (
            compartment_id or os.getenv("OCI_COMPARTMENT_ID") or self._get_from_coda_config()
        )
        if not self.compartment_id:
            raise ValueError(
                "compartment_id is required. Set it via parameter, OCI_COMPARTMENT_ID env var, or ~/.config/coda/config.toml"
            )

        # Load OCI config
        self.config = oci.config.from_file(
            file_location=os.path.expanduser(config_file_location), profile_name=config_profile
        )

        # Validate config
        oci.config.validate_config(self.config)

        # Initialize the Generative AI clients
        self.inference_client = GenerativeAiInferenceClient(self.config)
        self.genai_client = GenerativeAiClient(self.config)

    def _get_from_coda_config(self) -> str | None:
        """Get compartment ID from Coda config file."""
        if not tomllib:
            return None

        config_path = Path.home() / ".config" / "coda" / "config.toml"
        if not config_path.exists():
            return None

        try:
            with open(config_path, "rb") as f:
                config = tomllib.load(f)

            # Navigate to providers.oci_genai.compartment_id
            return config.get("providers", {}).get("oci_genai", {}).get("compartment_id")
        except Exception:
            return None

    @property
    def name(self) -> str:
        """Provider name."""
        return "oci_genai"

    def _is_cache_valid(self) -> bool:
        """Check if the model cache is still valid."""
        if not self._cache_timestamp or not self._model_cache:
            return False

        age = datetime.now() - self._cache_timestamp
        return age.total_seconds() < (self._cache_duration_hours * 3600)
    
    def _get_model_context_length(self, model_id: str) -> int:
        """Get accurate context length for a model.
        
        Args:
            model_id: Model ID
            
        Returns:
            Context length in tokens
        """
        # Model context lengths (accurate values)
        context_lengths = {
            # Cohere models
            "cohere.command-r-plus": 128000,
            "cohere.command-r-16k": 16000,
            "cohere.command": 4000,
            
            # Meta Llama models
            "meta.llama-3.1-405b": 128000,
            "meta.llama-3.1-70b": 128000,
            "meta.llama-3.3-70b": 128000,
            "meta.llama-4-3-90b": 131072,
            
            # XAI models
            "xai.grok-3": 131072,
        }
        
        # Check exact match
        model_lower = model_id.lower()
        for key, length in context_lengths.items():
            if key in model_lower or model_lower.startswith(key):
                return length
        
        # Default based on model name patterns
        if "16k" in model_lower:
            return 16384
        elif "32k" in model_lower:
            return 32768
        elif "128k" in model_lower:
            return 128000
        elif "command-r-plus" in model_lower:
            return 128000
        elif "llama-3" in model_lower:
            return 128000
        elif "grok" in model_lower:
            return 131072
        
        # Conservative default
        return 4096

    def _discover_models(self) -> list[Model]:
        """Discover available models from OCI GenAI service."""
        try:
            # List models with chat capability from the service
            response = self.genai_client.list_models(
                compartment_id=self.compartment_id,
                capability=["TEXT_GENERATION", "CHAT"],
                lifecycle_state="ACTIVE",
            )

            discovered_models = []
            seen_model_ids = {}  # Track which model IDs we've already seen

            # Known working model mappings (as of Dec 2024)
            # These override discovered IDs for models we know have issues
            known_working_mappings = {
                "cohere.command-r-plus": "cohere.command-r-plus-08-2024",
                "cohere.command-r": "cohere.command-r-08-2024",
            }

            for model_summary in response.data.items:
                # Skip models that don't have chat capability
                capabilities = getattr(model_summary, "capabilities", [])
                if not any(cap in ["TEXT_GENERATION", "CHAT"] for cap in capabilities):
                    continue

                # Get display name and derive a proper model ID
                display_name = getattr(model_summary, "display_name", model_summary.id)
                vendor = getattr(model_summary, "vendor", "unknown")

                # For OCI models, prefer the display name as the model ID if it looks like a proper model name
                if display_name and "." in display_name and not display_name.startswith("ocid1"):
                    model_id = display_name
                    provider = display_name.split(".")[0]
                else:
                    # Fall back to using vendor + a simplified name
                    model_id = f"{vendor}.{display_name}" if display_name else model_summary.id
                    provider = vendor

                # Handle duplicates - prefer models with CHAT capability over TEXT_GENERATION only
                if model_id in seen_model_ids:
                    existing_model = seen_model_ids[model_id]
                    existing_caps = existing_model.metadata.get("capabilities", [])

                    # Skip if the existing model already has CHAT capability
                    if "CHAT" in existing_caps:
                        continue

                    # If new model has CHAT but existing doesn't, we'll replace it
                    if "CHAT" in capabilities and "CHAT" not in existing_caps:
                        # Remove the old model from discovered_models
                        discovered_models = [m for m in discovered_models if m.id != model_id]
                    else:
                        # Otherwise skip this duplicate
                        continue

                # Map provider-specific capabilities
                supports_functions = (
                    provider == "cohere"
                )  # Cohere models typically support functions
                supports_streaming = True  # Most OCI GenAI models support streaming

                # Create model object
                model = Model(
                    id=model_id,
                    name=display_name,
                    provider=provider,
                    context_length=self._get_model_context_length(model_id),
                    max_tokens=4000,  # Default max tokens
                    supports_streaming=supports_streaming,
                    supports_functions=supports_functions,
                    metadata={
                        "vendor": getattr(model_summary, "vendor", provider),
                        "version": getattr(model_summary, "version", None),
                        "type": getattr(model_summary, "type", None),
                        "lifecycle_state": getattr(model_summary, "lifecycle_state", None),
                        "capabilities": capabilities,
                        "is_long_term_supported": getattr(
                            model_summary, "is_long_term_supported", None
                        ),
                        "oci_model_id": model_summary.id,  # Store the actual OCI model ID
                    },
                )

                # Store mapping from friendly name to OCI model ID
                self._model_id_map[model_id] = model_summary.id

                # Track that we've seen this model ID
                seen_model_ids[model_id] = model
                discovered_models.append(model)

            # Apply known working mappings to fix problematic models
            for alias, working_id in known_working_mappings.items():
                if alias in self._model_id_map and working_id in self._model_id_map:
                    # Override the mapping with the known working ID
                    self._model_id_map[alias] = self._model_id_map[working_id]

            return discovered_models

        except Exception as e:
            # If discovery fails, fall back to a basic set of known models
            print(f"Warning: Model discovery failed ({e}), using fallback models")
            return self._get_fallback_models()

    def _get_fallback_models(self) -> list[Model]:
        """Get fallback models if discovery fails."""
        models = [
            {
                "id": "cohere.command-r-plus-08-2024",
                "name": "Cohere Command R Plus (08-2024)",
                "provider": "cohere",
                "supports_functions": True,
            },
            {
                "id": "cohere.command-r-08-2024",
                "name": "Cohere Command R (08-2024)",
                "provider": "cohere",
                "supports_functions": True,
            },
            {
                "id": "meta.llama-3.1-70b-instruct",
                "name": "Meta Llama 3.1 70B Instruct",
                "provider": "meta",
                "supports_functions": False,
            },
        ]
        
        return [
            Model(
                id=m["id"],
                name=m["name"],
                provider=m["provider"],
                context_length=self._get_model_context_length(m["id"]),
                max_tokens=4000,
                supports_streaming=True,
                supports_functions=m["supports_functions"],
            )
            for m in models
        ]

    def _create_chat_request(
        self,
        messages: list[Message],
        model: str,
        temperature: float,
        max_tokens: int | None,
        top_p: float | None,
        stream: bool,
        **kwargs,
    ):
        """Create appropriate chat request based on provider."""
        provider = model.split(".")[0]

        if provider == "cohere":
            # Cohere uses a different format
            # Extract the last user message as the main message
            # and convert previous messages to chat history
            chat_history = []
            current_message = ""

            for msg in messages:
                if msg.role == Role.USER:
                    current_message = msg.content
                elif msg.role == Role.ASSISTANT:
                    # Add previous user message and this assistant response to history
                    if chat_history and isinstance(chat_history[-1], CohereUserMessage):
                        # We have a user message, now add the assistant response
                        chat_history.append(
                            CohereChatBotMessage(role="CHATBOT", message=msg.content)
                        )
                elif msg.role == Role.SYSTEM:
                    chat_history.append(CohereSystemMessage(role="SYSTEM", message=msg.content))

            # Add remaining user messages to history if current_message is not the last
            for i, msg in enumerate(messages[:-1]):
                if msg.role == Role.USER and messages[i + 1].role != Role.ASSISTANT:
                    chat_history.append(CohereUserMessage(role="USER", message=msg.content))

            # Create Cohere request
            params = {
                "message": current_message,
                "is_stream": stream,
                "temperature": temperature,
            }

            if chat_history:
                params["chat_history"] = chat_history
            if max_tokens:
                params["max_tokens"] = max_tokens
            if top_p is not None:
                params["top_p"] = top_p
            if kwargs.get("frequency_penalty"):
                params["frequency_penalty"] = kwargs["frequency_penalty"]
            if kwargs.get("presence_penalty"):
                params["presence_penalty"] = kwargs["presence_penalty"]

            return CohereChatRequest(**params)

        else:
            # Generic format for Meta and others
            oci_messages = []

            for msg in messages:
                content = [TextContent(type="TEXT", text=msg.content)]

                if msg.role == Role.SYSTEM:
                    oci_msg = SystemMessage(role="SYSTEM", content=content)
                elif msg.role == Role.USER:
                    oci_msg = UserMessage(role="USER", content=content)
                elif msg.role == Role.ASSISTANT:
                    oci_msg = AssistantMessage(role="ASSISTANT", content=content)
                else:
                    # Default to user message
                    oci_msg = UserMessage(role="USER", content=content)

                oci_messages.append(oci_msg)

            # Create generic request
            params = {
                "messages": oci_messages,
                "is_stream": stream,
                "temperature": temperature,
            }

            if max_tokens:
                params["max_tokens"] = max_tokens
            if top_p is not None:
                params["top_p"] = top_p

            return GenericChatRequest(**params)

    def chat(
        self,
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        **kwargs,
    ) -> ChatCompletion:
        """Send chat completion request using OCI SDK."""
        if not self.validate_model(model):
            raise ValueError(f"Model {model} is not supported")

        # Create chat request
        chat_request = self._create_chat_request(
            messages, model, temperature, max_tokens, top_p, stream=False, **kwargs
        )

        # Create serving mode - use the actual OCI model ID
        actual_model_id = self._model_id_map.get(model, model)
        serving_mode = OnDemandServingMode(model_id=actual_model_id)

        # Create chat details
        chat_details = ChatDetails(
            compartment_id=self.compartment_id, serving_mode=serving_mode, chat_request=chat_request
        )

        # Make request
        response = self.inference_client.chat(chat_details)

        # Extract response based on provider type
        chat_response = response.data.chat_response
        provider = model.split(".")[0]

        if provider == "cohere":
            # Cohere response format
            if not hasattr(chat_response, "text") or not chat_response.text:
                raise ValueError("No response from model")

            content = chat_response.text
            finish_reason = getattr(chat_response, "finish_reason", None)

            # Cohere provides token usage differently
            usage = None
            if hasattr(chat_response, "meta") and chat_response.meta:
                meta = chat_response.meta
                if hasattr(meta, "billed_units") and meta.billed_units:
                    usage = {
                        "prompt_tokens": getattr(meta.billed_units, "input_tokens", None),
                        "completion_tokens": getattr(meta.billed_units, "output_tokens", None),
                        "total_tokens": None,
                    }
                    if usage["prompt_tokens"] and usage["completion_tokens"]:
                        usage["total_tokens"] = usage["prompt_tokens"] + usage["completion_tokens"]

        else:
            # Generic response format (Meta, etc.)
            choices = chat_response.choices

            if not choices:
                raise ValueError("No response from model")

            choice = choices[0]
            message = choice.message

            # Extract content based on type
            if hasattr(message.content, "__iter__") and not isinstance(message.content, str):
                # Content is a list
                content = message.content[0].text if message.content else ""
            else:
                # Content is a string
                content = message.content

            finish_reason = choice.finish_reason

            # Generic format usage
            usage = (
                {
                    "prompt_tokens": getattr(chat_response, "prompt_tokens", None),
                    "completion_tokens": getattr(chat_response, "completion_tokens", None),
                    "total_tokens": getattr(chat_response, "total_tokens", None),
                }
                if hasattr(chat_response, "prompt_tokens")
                else None
            )

        return ChatCompletion(
            content=content,
            model=model,
            finish_reason=finish_reason,
            usage=usage,
            metadata={
                "model_version": getattr(chat_response, "model_version", None),
                "model": getattr(chat_response, "model", None),
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
        **kwargs,
    ) -> Iterator[ChatCompletionChunk]:
        """Stream chat completion response using OCI SDK."""
        if not self.validate_model(model):
            raise ValueError(f"Model {model} is not supported")

        # Create chat request with streaming enabled
        chat_request = self._create_chat_request(
            messages, model, temperature, max_tokens, top_p, stream=True, **kwargs
        )

        # Create serving mode - use the actual OCI model ID
        actual_model_id = self._model_id_map.get(model, model)
        serving_mode = OnDemandServingMode(model_id=actual_model_id)

        # Create chat details
        chat_details = ChatDetails(
            compartment_id=self.compartment_id, serving_mode=serving_mode, chat_request=chat_request
        )

        # Make streaming request
        response_stream = self.inference_client.chat(chat_details)

        # Process events
        for event in response_stream.data.events():
            if hasattr(event, "data"):
                try:
                    # Parse the SSE data
                    data = json.loads(event.data)

                    # Handle different response formats based on provider
                    if "cohere" in model.lower():
                        # Cohere models might have a different format
                        # Check for text directly in data
                        if "text" in data and "finishReason" not in data:
                            # Regular streaming chunk
                            yield ChatCompletionChunk(
                                content=data.get("text", ""),
                                model=model,
                                finish_reason=None,
                                usage=None,
                                metadata={},
                            )
                        elif "finishReason" in data:
                            # Final event - don't include text to avoid duplication
                            yield ChatCompletionChunk(
                                content="",
                                model=model,
                                finish_reason=data.get("finishReason"),
                                usage=None,
                                metadata={},
                            )
                        # Check for eventType and other Cohere-specific fields
                        elif "eventType" in data:
                            if data["eventType"] == "text-generation":
                                yield ChatCompletionChunk(
                                    content=data.get("text", ""),
                                    model=model,
                                    finish_reason=None,
                                    usage=None,
                                    metadata={},
                                )
                            elif data["eventType"] == "stream-end":
                                yield ChatCompletionChunk(
                                    content="",
                                    model=model,
                                    finish_reason=data.get("finishReason", "stop"),
                                    usage=None,
                                    metadata={},
                                )
                    else:
                        # Handle xAI and Meta models (existing logic)
                        message = data.get("message", {})
                        content = ""
                        finish_reason = data.get("finishReason")

                        if message:
                            # Extract content from message.content[0].text
                            message_content = message.get("content", [])
                            if message_content and isinstance(message_content, list):
                                content = message_content[0].get("text", "")

                            yield ChatCompletionChunk(
                                content=content,
                                model=model,
                                finish_reason=finish_reason,
                                usage=None,
                                metadata={},
                            )
                        elif finish_reason:
                            # Handle final event with finish reason
                            yield ChatCompletionChunk(
                                content="",
                                model=model,
                                finish_reason=finish_reason,
                                usage=None,
                                metadata={},
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
        **kwargs,
    ) -> ChatCompletion:
        """Async version of chat - runs sync version in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None, self.chat, messages, model, temperature, max_tokens, top_p, stop, **kwargs
        )

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
        """Async version of chat_stream - runs sync version in executor."""
        loop = asyncio.get_event_loop()

        # Run the sync iterator in a thread
        sync_iterator = await loop.run_in_executor(
            None, self.chat_stream, messages, model, temperature, max_tokens, top_p, stop, **kwargs
        )

        # Convert to async iterator
        for chunk in sync_iterator:
            yield chunk

    def list_models(self) -> list[Model]:
        """List available models from OCI GenAI service."""
        # Check cache first
        if self._is_cache_valid():
            return self._model_cache

        # Discover models from OCI
        models = self._discover_models()

        # Update cache
        self._model_cache = models
        self._cache_timestamp = datetime.now()

        return models

    def refresh_models(self) -> list[Model]:
        """Force refresh of the model cache."""
        self._model_cache = None
        self._cache_timestamp = None
        return self.list_models()

    def verify_model(self, model_id: str) -> dict[str, any]:
        """Verify if a model is actually usable by making a minimal test request.

        Args:
            model_id: The model ID to verify

        Returns:
            Dict with verification results including success status and any error message
        """
        try:
            # First check if model is in our list
            if not self.validate_model(model_id):
                return {
                    "success": False,
                    "model_id": model_id,
                    "error": "Model not found in available models list",
                    "oci_model_id": None,
                }

            # Get the OCI model ID
            oci_model_id = self._model_id_map.get(model_id)
            if not oci_model_id:
                return {
                    "success": False,
                    "model_id": model_id,
                    "error": "No OCI model ID mapping found",
                    "oci_model_id": None,
                }

            # Try a minimal chat request
            test_messages = [Message(role=Role.USER, content="Hi")]

            try:
                response = self.chat(
                    messages=test_messages,
                    model=model_id,
                    temperature=0.1,
                    max_tokens=10,
                )

                return {
                    "success": True,
                    "model_id": model_id,
                    "oci_model_id": oci_model_id,
                    "response": response.content[:50] if response.content else None,
                    "error": None,
                }

            except Exception as e:
                return {
                    "success": False,
                    "model_id": model_id,
                    "oci_model_id": oci_model_id,
                    "error": str(e),
                }

        except Exception as e:
            return {
                "success": False,
                "model_id": model_id,
                "error": f"Verification failed: {str(e)}",
                "oci_model_id": None,
            }

    def verify_all_models(self, verbose: bool = True) -> list[dict[str, any]]:
        """Verify all available models to see which ones are actually usable.

        Args:
            verbose: Whether to print progress

        Returns:
            List of verification results for each model
        """
        models = self.list_models()
        results = []

        if verbose:
            print(f"Verifying {len(models)} models...")
            print("-" * 60)

        for i, model in enumerate(models):
            if verbose:
                print(f"[{i+1}/{len(models)}] Verifying {model.id}...", end=" ", flush=True)

            result = self.verify_model(model.id)
            results.append(result)

            if verbose:
                if result["success"]:
                    print("✓ OK")
                else:
                    print(f"✗ FAILED: {result['error']}")

        if verbose:
            # Summary
            successful = sum(1 for r in results if r["success"])
            print("-" * 60)
            print(f"Summary: {successful}/{len(models)} models verified successfully")

            # Show failed models
            failed = [r for r in results if not r["success"]]
            if failed:
                print(f"\nFailed models ({len(failed)}):")
                for r in failed:
                    print(f"  - {r['model_id']}: {r['error']}")

        return results
