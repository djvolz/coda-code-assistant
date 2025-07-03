"""Oracle Cloud Infrastructure (OCI) Generative AI provider implementation using OCI SDK."""

import json
import os
from pathlib import Path
from typing import AsyncIterator, Dict, Iterator, List, Optional, Union
from datetime import datetime
import asyncio

import oci
from oci.generative_ai_inference import GenerativeAiInferenceClient
from oci.generative_ai_inference.models import (
    ChatDetails,
    OnDemandServingMode,
    CohereChatRequest,
    GenericChatRequest,
    CohereUserMessage,
    CohereChatBotMessage,
    CohereSystemMessage,
    UserMessage,
    AssistantMessage,
    SystemMessage,
    TextContent,
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
    
    # Supported models
    MODELS = {
        "cohere.command-r-plus-08-2024": Model(
            id="cohere.command-r-plus-08-2024",
            name="Cohere Command R Plus (08-2024)",
            provider="cohere",
            context_length=128000,
            max_tokens=4000,
            supports_streaming=True,
            supports_functions=True,
        ),
        "cohere.command-r-08-2024": Model(
            id="cohere.command-r-08-2024",
            name="Cohere Command R (08-2024)",
            provider="cohere",
            context_length=128000,
            max_tokens=4000,
            supports_streaming=True,
            supports_functions=True,
        ),
        "meta.llama-3.1-70b-instruct": Model(
            id="meta.llama-3.1-70b-instruct",
            name="Meta Llama 3.1 70B Instruct",
            provider="meta",
            context_length=128000,
            max_tokens=4000,
            supports_streaming=True,
            supports_functions=False,
        ),
        "meta.llama-3.1-405b-instruct": Model(
            id="meta.llama-3.1-405b-instruct",
            name="Meta Llama 3.1 405B Instruct",
            provider="meta",
            context_length=128000,
            max_tokens=4000,
            supports_streaming=True,
            supports_functions=False,
        ),
    }
    
    def __init__(
        self,
        compartment_id: Optional[str] = None,
        config_file_location: str = "~/.oci/config",
        config_profile: str = "DEFAULT",
        **kwargs
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
        self.compartment_id = compartment_id or os.getenv("OCI_COMPARTMENT_ID") or self._get_from_coda_config()
        if not self.compartment_id:
            raise ValueError(
                "compartment_id is required. Set it via parameter, OCI_COMPARTMENT_ID env var, or ~/.config/coda/config.toml"
            )
        
        # Load OCI config
        self.config = oci.config.from_file(
            file_location=os.path.expanduser(config_file_location),
            profile_name=config_profile
        )
        
        # Validate config
        oci.config.validate_config(self.config)
        
        # Initialize the Generative AI client
        self.client = GenerativeAiInferenceClient(self.config)
    
    def _get_from_coda_config(self) -> Optional[str]:
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
    
    def _create_chat_request(
        self,
        messages: List[Message],
        model: str,
        temperature: float,
        max_tokens: Optional[int],
        top_p: Optional[float],
        stream: bool,
        **kwargs
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
                            CohereChatBotMessage(
                                role="CHATBOT",
                                message=msg.content
                            )
                        )
                elif msg.role == Role.SYSTEM:
                    chat_history.append(
                        CohereSystemMessage(
                            role="SYSTEM",
                            message=msg.content
                        )
                    )
                    
            # Add remaining user messages to history if current_message is not the last
            for i, msg in enumerate(messages[:-1]):
                if msg.role == Role.USER and messages[i+1].role != Role.ASSISTANT:
                    chat_history.append(
                        CohereUserMessage(
                            role="USER",
                            message=msg.content
                        )
                    )
            
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
        messages: List[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        top_p: Optional[float] = None,
        stop: Optional[Union[str, List[str]]] = None,
        **kwargs
    ) -> ChatCompletion:
        """Send chat completion request using OCI SDK."""
        if not self.validate_model(model):
            raise ValueError(f"Model {model} is not supported")
        
        # Create chat request
        chat_request = self._create_chat_request(
            messages, model, temperature, max_tokens, top_p, stream=False, **kwargs
        )
        
        # Create serving mode - OCI expects just the model name
        serving_mode = OnDemandServingMode(
            model_id=model
        )
        
        # Create chat details
        chat_details = ChatDetails(
            compartment_id=self.compartment_id,
            serving_mode=serving_mode,
            chat_request=chat_request
        )
        
        # Make request
        response = self.client.chat(chat_details)
        
        # Extract response based on provider type
        chat_response = response.data.chat_response
        provider = model.split(".")[0]
        
        if provider == "cohere":
            # Cohere response format
            if not hasattr(chat_response, 'text') or not chat_response.text:
                raise ValueError("No response from model")
                
            content = chat_response.text
            finish_reason = getattr(chat_response, 'finish_reason', None)
            
            # Cohere provides token usage differently
            usage = None
            if hasattr(chat_response, 'meta') and chat_response.meta:
                meta = chat_response.meta
                if hasattr(meta, 'billed_units') and meta.billed_units:
                    usage = {
                        "prompt_tokens": getattr(meta.billed_units, 'input_tokens', None),
                        "completion_tokens": getattr(meta.billed_units, 'output_tokens', None),
                        "total_tokens": None
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
            if hasattr(message.content, '__iter__') and not isinstance(message.content, str):
                # Content is a list
                content = message.content[0].text if message.content else ""
            else:
                # Content is a string
                content = message.content
                
            finish_reason = choice.finish_reason
            
            # Generic format usage
            usage = {
                "prompt_tokens": getattr(chat_response, "prompt_tokens", None),
                "completion_tokens": getattr(chat_response, "completion_tokens", None),
                "total_tokens": getattr(chat_response, "total_tokens", None),
            } if hasattr(chat_response, "prompt_tokens") else None
        
        return ChatCompletion(
            content=content,
            model=model,
            finish_reason=finish_reason,
            usage=usage,
            metadata={
                "model_version": getattr(chat_response, "model_version", None),
                "model": getattr(chat_response, "model", None),
            }
        )
    
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
        """Stream chat completion response using OCI SDK."""
        if not self.validate_model(model):
            raise ValueError(f"Model {model} is not supported")
        
        # Create chat request with streaming enabled
        chat_request = self._create_chat_request(
            messages, model, temperature, max_tokens, top_p, stream=True, **kwargs
        )
        
        # Create serving mode - OCI expects just the model name
        serving_mode = OnDemandServingMode(
            model_id=model
        )
        
        # Create chat details
        chat_details = ChatDetails(
            compartment_id=self.compartment_id,
            serving_mode=serving_mode,
            chat_request=chat_request
        )
        
        # Make streaming request
        response_stream = self.client.chat(chat_details)
        
        # Process events
        for event in response_stream.data.events():
            if hasattr(event, "data"):
                try:
                    # Parse the SSE data
                    data = json.loads(event.data)
                    chat_response = data.get("chatResponse", {})
                    choices = chat_response.get("choices", [])
                    
                    if choices:
                        choice = choices[0]
                        delta = choice.get("delta", {})
                        content = delta.get("content", "")
                        
                        if isinstance(content, list) and content:
                            content = content[0].get("text", "")
                        
                        yield ChatCompletionChunk(
                            content=content,
                            model=model,
                            finish_reason=choice.get("finishReason"),
                            usage=chat_response.get("usage"),
                            metadata={}
                        )
                except json.JSONDecodeError:
                    continue
    
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
        """Async version of chat - runs sync version in executor."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.chat,
            messages,
            model,
            temperature,
            max_tokens,
            top_p,
            stop,
            **kwargs
        )
    
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
        """Async version of chat_stream - runs sync version in executor."""
        loop = asyncio.get_event_loop()
        
        # Run the sync iterator in a thread
        sync_iterator = await loop.run_in_executor(
            None,
            self.chat_stream,
            messages,
            model,
            temperature,
            max_tokens,
            top_p,
            stop,
            **kwargs
        )
        
        # Convert to async iterator
        for chunk in sync_iterator:
            yield chunk
    
    def list_models(self) -> List[Model]:
        """List available models."""
        return list(self.MODELS.values())