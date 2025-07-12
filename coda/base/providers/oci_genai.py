"""Oracle Cloud Infrastructure (OCI) Generative AI provider implementation using OCI SDK."""

import asyncio
import json
import os
from collections.abc import AsyncIterator, Iterator
from datetime import datetime
from pathlib import Path
from typing import Any

import oci
from oci.generative_ai import GenerativeAiClient
from oci.generative_ai_inference import GenerativeAiInferenceClient
from oci.generative_ai_inference.models import (
    AssistantMessage,
    ChatDetails,
    CohereChatBotMessage,
    CohereChatRequest,
    CohereParameterDefinition,
    CohereSystemMessage,
    CohereTool,
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

from .base import (
    BaseProvider,
    ChatCompletion,
    ChatCompletionChunk,
    Message,
    Model,
    Role,
    Tool,
    ToolCall,
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

        # Store region from config
        self.region = self.config.get("region", "us-phoenix-1")

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
            # Check if this is an authorization error
            error_msg = str(e)
            if "NotAuthorizedOrNotFound" in error_msg or "Authorization failed" in error_msg:
                # This is a critical auth error - don't provide fallback models
                # Extract region from error if available
                import re

                region_match = re.search(r"https://generativeai\.([^.]+)\.oci", error_msg)
                region = region_match.group(1) if region_match else self.region

                raise Exception(
                    f"OCI GenAI authorization failed. Please check:\n\n"
                    f"1. **IAM Policy**: Ensure your user/group has a policy like:\n"
                    f"   Allow group <your-group> to use generative-ai-family in compartment <compartment-name>\n\n"
                    f"2. **Service Availability**: Verify GenAI is available in '{region}' region:\n"
                    f"   https://docs.oracle.com/en-us/iaas/Content/generative-ai/overview.htm#regions\n\n"
                    f"3. **Compartment Access**: Verify you have access to compartment:\n"
                    f"   {self.compartment_id}\n\n"
                    f"4. **Quick Test**: Try running this OCI CLI command:\n"
                    f"   oci generative-ai model list --compartment-id {self.compartment_id}\n\n"
                    f"If the CLI command also fails, the issue is with OCI permissions, not Coda.\n"
                    f"Original error: {e.__class__.__name__}: {str(e)}"
                ) from e
            else:
                # For other errors, we might still try fallback
                # But let's be more cautious and just fail
                raise Exception(f"Failed to discover OCI GenAI models: {e}") from e

    def _get_fallback_models(self) -> list[Model]:
        """Get fallback models if discovery fails.

        NOTE: This method is currently not used because authorization
        failures mean fallback models won't work either. Kept for
        potential future use cases where temporary discovery issues
        might benefit from a fallback list.
        """
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
        tools: list[Tool] | None = None,
        **kwargs,
    ):
        """Create appropriate chat request based on provider."""
        provider = model.split(".")[0]

        if provider == "cohere":
            # Cohere uses a different format
            # We need to properly structure the conversation with tool results
            chat_history = []
            current_message = ""

            # Process messages to build chat history
            i = 0
            while i < len(messages):
                msg = messages[i]

                if msg.role == Role.SYSTEM:
                    chat_history.append(CohereSystemMessage(role="SYSTEM", message=msg.content))

                elif msg.role == Role.USER:
                    # Keep the last user message as current_message
                    if i == len(messages) - 1:
                        current_message = msg.content
                    else:
                        # Check if next message is assistant or tool
                        if i + 1 < len(messages) and messages[i + 1].role == Role.ASSISTANT:
                            # This user message will be paired with assistant response
                            chat_history.append(CohereUserMessage(role="USER", message=msg.content))
                        else:
                            # Standalone user message
                            chat_history.append(CohereUserMessage(role="USER", message=msg.content))

                elif msg.role == Role.ASSISTANT:
                    # Check if there are tool responses following this assistant message
                    assistant_content = msg.content
                    j = i + 1

                    # Collect any tool responses that follow
                    while j < len(messages) and messages[j].role == Role.TOOL:
                        tool_msg = messages[j]
                        tool_name = tool_msg.name if tool_msg.name else "tool"
                        assistant_content += (
                            f"\n\nTool execution result ({tool_name}): {tool_msg.content}"
                        )
                        j += 1

                    # Add the combined assistant + tool results message
                    chat_history.append(
                        CohereChatBotMessage(role="CHATBOT", message=assistant_content)
                    )

                    # Skip the tool messages we've already processed
                    i = j - 1

                elif msg.role == Role.TOOL:
                    # This shouldn't happen as we process tool messages with their assistant message
                    # But if it does, add it as a system message
                    tool_name = msg.name if msg.name else "tool"
                    chat_history.append(
                        CohereSystemMessage(
                            role="SYSTEM",
                            message=f"Tool execution result ({tool_name}): {msg.content}",
                        )
                    )

                i += 1

            # If we don't have a current message, check if we need to prompt for final answer
            if not current_message:
                # Check if the last message in history contains tool results
                if chat_history and isinstance(chat_history[-1], CohereChatBotMessage):
                    last_msg = chat_history[-1].message
                    if "Tool execution result" in last_msg:
                        # We have tool results, find the original user question for context
                        original_question = None
                        for msg in reversed(chat_history):
                            if isinstance(msg, CohereUserMessage):
                                original_question = msg.message
                                break

                        if original_question:
                            current_message = f'Based on the tool results above, please provide a complete answer to the user\'s question: "{original_question}"'
                        else:
                            current_message = "Based on the tool results above, please provide a complete answer to the user's original question."

                # Otherwise look for last user message
                if not current_message and chat_history:
                    for msg in reversed(chat_history):
                        if isinstance(msg, CohereUserMessage):
                            current_message = msg.message
                            # Remove this message from history to avoid duplication
                            chat_history.remove(msg)
                            break

                # If still no current message, create a default one
                if not current_message:
                    current_message = "Continue the conversation"

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
            elif tools:
                # Set a default max_tokens for tool calls to prevent early truncation
                params["max_tokens"] = 1000
            if top_p is not None:
                params["top_p"] = top_p
            if kwargs.get("frequency_penalty"):
                params["frequency_penalty"] = kwargs["frequency_penalty"]
            if kwargs.get("presence_penalty"):
                params["presence_penalty"] = kwargs["presence_penalty"]

            # Add tools if provided
            if tools:
                cohere_tools = self._convert_tools_to_cohere(tools)
                params["tools"] = cohere_tools
                # Lower temperature for better tool accuracy
                params["temperature"] = min(temperature, 0.3)
                # Add preamble to encourage tool use and provide final answer
                params[
                    "preamble_override"
                ] = """You are a helpful assistant with access to tools. When the user asks questions that require external information or actions, use the appropriate tools to help them.

IMPORTANT: After receiving tool results, you MUST provide a final answer to the user that incorporates the tool results. Do not call the same tool again if you already have the result. Simply explain the answer using the tool's output."""
                # Don't force single step - allow model to provide final answer
                # params["is_force_single_step"] = True

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

    def _convert_tools_to_cohere(self, tools: list[Tool]) -> list[CohereTool]:
        """Convert standard tools to Cohere format."""
        cohere_tools = []
        # Store mapping of sanitized names to original names for tool calls
        self._tool_name_mapping = {}

        for tool in tools:
            # Convert parameters from JSON Schema to Cohere format
            param_definitions = {}

            if "properties" in tool.parameters:
                for param_name, param_schema in tool.parameters["properties"].items():
                    # Convert type to uppercase as required by Cohere
                    param_type = param_schema.get("type", "string").upper()
                    if param_type == "INTEGER":
                        param_type = "FLOAT"  # Cohere uses FLOAT for numbers
                    elif param_type == "ARRAY":
                        param_type = "LIST"
                    elif param_type == "OBJECT":
                        param_type = "DICT"

                    param_def = CohereParameterDefinition(
                        description=param_schema.get("description", ""),
                        type=param_type,
                        is_required=param_name in tool.parameters.get("required", []),
                    )
                    param_definitions[param_name] = param_def

            # Sanitize tool name for OCI/Cohere compatibility (dots and hyphens not allowed)
            sanitized_name = tool.name.replace(".", "_").replace("-", "_")
            # Store mapping for tool call resolution
            self._tool_name_mapping[sanitized_name] = tool.name

            cohere_tool = CohereTool(
                name=sanitized_name,
                description=tool.description,
                parameter_definitions=param_definitions,
            )
            cohere_tools.append(cohere_tool)

        return cohere_tools

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
        """Send chat completion request using OCI SDK."""
        if not self.validate_model(model):
            raise ValueError(f"Model {model} is not supported")

        # Create chat request
        chat_request = self._create_chat_request(
            messages, model, temperature, max_tokens, top_p, stream=False, tools=tools, **kwargs
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
            content = ""
            tool_calls = None
            finish_reason = getattr(chat_response, "finish_reason", None)

            # Check for tool calls
            if hasattr(chat_response, "tool_calls") and chat_response.tool_calls:
                # Convert Cohere tool calls to our format
                tool_calls = []
                for tc in chat_response.tool_calls:
                    # Map sanitized name back to original name
                    original_name = getattr(self, "_tool_name_mapping", {}).get(tc.name, tc.name)
                    tool_call = ToolCall(
                        id=tc.name,  # Cohere doesn't provide IDs, use name
                        name=original_name,
                        arguments=tc.parameters if hasattr(tc, "parameters") else {},
                    )
                    tool_calls.append(tool_call)
                finish_reason = "tool_calls"

            # Get text content if available
            if hasattr(chat_response, "text") and chat_response.text:
                content = chat_response.text

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
            tool_calls = None  # Generic format doesn't support tools
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
            tool_calls=tool_calls if provider == "cohere" else None,
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
        tools: list[Tool] | None = None,
        **kwargs,
    ) -> Iterator[ChatCompletionChunk]:
        """Stream chat completion response using OCI SDK."""
        if not self.validate_model(model):
            raise ValueError(f"Model {model} is not supported")

        # Create chat request with streaming enabled
        chat_request = self._create_chat_request(
            messages, model, temperature, max_tokens, top_p, stream=True, tools=tools, **kwargs
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
                print(f"[{i + 1}/{len(models)}] Verifying {model.id}...", end=" ", flush=True)

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

    def check_service_access(self) -> dict[str, Any]:
        """Check if the OCI GenAI service is accessible with current configuration.

        Returns diagnostic information about service access.
        """
        diagnostics = {
            "config_valid": False,
            "service_accessible": False,
            "compartment_id": self.compartment_id,
            "region": self.region,
            "errors": [],
        }

        # Check 1: Configuration is loaded
        try:
            if not self.compartment_id:
                diagnostics["errors"].append("No compartment ID configured")
            else:
                diagnostics["config_valid"] = True
        except Exception as e:
            diagnostics["errors"].append(f"Config error: {str(e)}")

        # Check 2: Try to list models (this is what's failing)
        if diagnostics["config_valid"]:
            try:
                self.genai_client.list_models(compartment_id=self.compartment_id, limit=1)
                diagnostics["service_accessible"] = True
            except Exception as e:
                diagnostics["errors"].append(f"Service access error: {str(e)}")

        return diagnostics
