"""Base provider interface for all LLM providers."""

import re
import uuid
from abc import ABC, abstractmethod
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass, field
from enum import Enum


class Role(str, Enum):
    """Message roles."""

    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"  # For tool response messages


@dataclass
class Tool:
    """Tool definition for function calling."""

    name: str
    description: str
    parameters: dict  # JSON Schema format


@dataclass
class ToolCall:
    """Tool call request from the model."""

    id: str
    name: str
    arguments: dict


@dataclass
class ToolResult:
    """Result from executing a tool."""

    tool_call_id: str
    content: str
    is_error: bool = False


@dataclass
class Message:
    """Chat message."""

    role: Role
    content: str
    name: str | None = None
    tool_calls: list[ToolCall] | None = None
    tool_call_id: str | None = None  # For tool response messages
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatCompletion:
    """Chat completion response."""

    content: str
    model: str
    finish_reason: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: dict | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class ChatCompletionChunk:
    """Streaming chat completion chunk."""

    content: str
    model: str
    finish_reason: str | None = None
    tool_calls: list[ToolCall] | None = None
    usage: dict | None = None
    metadata: dict = field(default_factory=dict)


@dataclass
class Model:
    """Model information."""

    id: str
    name: str
    provider: str
    context_length: int | None = None
    max_tokens: int | None = None
    supports_streaming: bool = True
    supports_functions: bool = False
    metadata: dict = field(default_factory=dict)


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
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[Tool] | None = None,
        **kwargs,
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
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        tools: list[Tool] | None = None,
        **kwargs,
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
        messages: list[Message],
        model: str,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        **kwargs,
    ) -> ChatCompletion:
        """Async version of chat."""
        pass

    @abstractmethod
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
        """Async version of chat_stream."""
        pass

    @abstractmethod
    def list_models(self) -> list[Model]:
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

    def get_model_info(self, model: str) -> Model | None:
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

    async def _execute_tools_manually(
        self,
        messages: list[Message],
        model: str,
        tools: list[Tool],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        **kwargs,
    ) -> ChatCompletion:
        """
        Execute tools manually when model doesn't support tool calling.

        This method:
        1. Gets initial response from model without tools
        2. Analyzes response to infer which tools should be called
        3. Executes tools and adds results to conversation
        4. Gets final response incorporating tool results

        Args:
            messages: Chat messages
            model: Model name
            tools: Available tools
            **kwargs: Additional parameters

        Returns:
            ChatCompletion with tool results integrated
        """
        # 1. Get initial response without tools
        # Use direct method call instead of self.chat to avoid recursion issues
        # Note: This will be overridden in child classes to call their native method
        initial_response = await self.achat(
            messages,
            model,
            temperature,
            max_tokens,
            top_p,
            stop,
            tools=None,
            _manual_execution=True,
            **kwargs,
        )

        # 2. Infer which tools to call based on the response
        tool_calls = self._infer_tool_calls_from_response(initial_response.content, tools)

        if not tool_calls:
            # No tools needed, return original response
            return initial_response

        # 3. Execute tools
        tool_results = []
        for tool_call in tool_calls:
            try:
                result = await self._execute_single_tool(tool_call)
                tool_results.append(result)
            except Exception as e:
                # Add error result
                tool_results.append(
                    ToolResult(
                        tool_call_id=tool_call.id,
                        content=f"Error executing {tool_call.name}: {str(e)}",
                        is_error=True,
                    )
                )

        # 4. Build new conversation with tool results
        new_messages = messages + [
            Message(role=Role.ASSISTANT, content=initial_response.content, tool_calls=tool_calls)
        ]

        # Add tool results
        for result in tool_results:
            new_messages.append(
                Message(role=Role.TOOL, content=result.content, tool_call_id=result.tool_call_id)
            )

        # 5. Get final response
        final_response = await self.achat(
            new_messages
            + [
                Message(
                    role=Role.USER,
                    content="Please provide a complete answer based on the tool results above.",
                )
            ],
            model,
            temperature,
            max_tokens,
            top_p,
            stop,
            tools=None,  # Don't try tools again
            _manual_execution=True,  # Prevent recursion
            **kwargs,
        )

        # 6. Return combined response
        return ChatCompletion(
            content=final_response.content,
            model=model,
            finish_reason="stop",
            tool_calls=tool_calls,
            usage=final_response.usage,
            metadata={
                "manual_tool_execution": True,
                "initial_response": initial_response.content,
                "tool_results_count": len(tool_results),
            },
        )

    def _infer_tool_calls_from_response(
        self, response_content: str, tools: list[Tool]
    ) -> list[ToolCall]:
        """
        Infer which tools should be called using NLP-based semantic analysis.

        Analyzes the intent and entities in the response to intelligently
        match with available tool capabilities.

        Args:
            response_content: The model's response text
            tools: Available tools

        Returns:
            List of ToolCall objects to execute
        """
        tool_calls = []

        # Create intent classifier
        intent_classifier = self._create_intent_classifier(response_content, tools)

        # Get tool recommendations with confidence scores
        tool_recommendations = intent_classifier.analyze()

        # Execute high-confidence tool matches
        for tool_name, args, confidence in tool_recommendations:
            if confidence > 0.7:  # High confidence threshold
                tool_calls.append(
                    ToolCall(
                        id=f"manual_{uuid.uuid4().hex[:8]}",
                        name=tool_name,
                        arguments=args,
                    )
                )

        return tool_calls

    def _create_intent_classifier(self, response_content: str, tools: list[Tool]):
        """Create an intent classifier for the given response and available tools."""
        from .tool_intent_classifier import ToolIntentClassifier

        return ToolIntentClassifier(response_content, tools)

    def _extract_tool_arguments(self, content: str, tool: Tool) -> dict:
        """Extract tool arguments from content."""
        args = {}

        # For file operations, try to extract file paths
        if tool.name in ["read_file", "write_file"]:
            # Look for quoted file paths
            file_matches = re.findall(r"['\"]([^'\"]+\.[a-zA-Z]+)['\"]", content)
            if file_matches:
                args["filepath"] = file_matches[0]  # Use correct parameter name

        elif tool.name == "run_shell":
            # Look for command in backticks or after keywords
            cmd_matches = re.findall(r"`([^`]+)`", content)
            if cmd_matches:
                args["command"] = cmd_matches[0]
            else:
                # Try to extract after "run" or "execute"
                cmd_matches = re.findall(r"(?:run|execute)\s+(.+?)(?:\.|$)", content)
                if cmd_matches:
                    args["command"] = cmd_matches[0].strip()

        elif tool.name == "web_search":
            # Extract search query
            search_matches = re.findall(r"search.*?for\s+(.+?)(?:\.|$)", content)
            if search_matches:
                args["query"] = search_matches[0].strip()

        return args

    def _extract_arguments_from_matches(self, matches: list, tool: Tool) -> dict:
        """Extract arguments from regex matches."""
        args = {}

        if tool.name in ["read_file", "write_file"] and matches:
            # For file operations, use the file path from matches
            if isinstance(matches[0], tuple) and len(matches[0]) > 1:
                args["filepath"] = matches[0][1]  # Second group is the file path
            else:
                args["filepath"] = matches[0]

        return args

    async def _execute_single_tool(self, tool_call: ToolCall) -> ToolResult:
        """Execute a single tool call."""
        try:
            # Import here to avoid circular dependencies
            from coda.services.tools import execute_tool

            result = await execute_tool(tool_call.name, tool_call.arguments)
            return ToolResult(
                tool_call_id=tool_call.id,
                content=result.result if hasattr(result, "result") else str(result),
                is_error=not getattr(result, "success", True),
            )
        except Exception as e:
            return ToolResult(
                tool_call_id=tool_call.id,
                content=f"Error: {str(e)}",
                is_error=True,
            )

    def _execute_tools_manually_sync(
        self,
        messages: list[Message],
        model: str,
        tools: list[Tool],
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        **kwargs,
    ) -> ChatCompletion:
        """
        Sync version of manual tool execution.

        Uses asyncio to run the async version in a sync context.
        """
        import asyncio

        try:
            # Check if we're already in an async context
            asyncio.get_running_loop()
            # If we get here, we're in an async context, but this is a sync method
            # We need to schedule it properly
            import concurrent.futures

            # Run in thread pool to avoid blocking the event loop
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(
                    lambda: asyncio.run(
                        self._execute_tools_manually(
                            messages, model, tools, temperature, max_tokens, top_p, stop, **kwargs
                        )
                    )
                )
                return future.result()

        except RuntimeError:
            # No running loop, safe to create one
            return asyncio.run(
                self._execute_tools_manually(
                    messages, model, tools, temperature, max_tokens, top_p, stop, **kwargs
                )
            )

    def _execute_tools_manually_streaming(
        self,
        messages: list[Message],
        model: str,
        tools: list[Tool],
        base_func: callable,
        temperature: float = 0.7,
        max_tokens: int | None = None,
        top_p: float | None = None,
        stop: str | list[str] | None = None,
        **kwargs,
    ) -> Iterator[ChatCompletionChunk]:
        """
        Convert manual tool execution into streaming chunks.

        This executes tools manually and yields the response as chunks.
        """
        # Execute tools manually to get the full response
        full_response = self._execute_tools_manually_sync(
            messages, model, tools, temperature, max_tokens, top_p, stop, **kwargs
        )

        # Convert the response into streaming chunks
        content = full_response.content
        tool_calls = full_response.tool_calls

        # Split content into chunks (simulate streaming)
        words = content.split()
        chunk_size = max(1, len(words) // 10)  # ~10 chunks

        for i in range(0, len(words), chunk_size):
            chunk_words = words[i : i + chunk_size]
            chunk_content = " ".join(chunk_words)

            # Add space after chunk unless it's the last one
            if i + chunk_size < len(words):
                chunk_content += " "

            is_final = i + chunk_size >= len(words)

            yield ChatCompletionChunk(
                content=chunk_content,
                model=model,
                finish_reason="stop" if is_final else None,
                tool_calls=(
                    tool_calls if is_final else None
                ),  # Only include tool calls in final chunk
                usage=full_response.usage if is_final else None,
                metadata={
                    "manual_tool_execution": True,
                    "chunk_index": i // chunk_size,
                    "is_final": is_final,
                },
            )
