"""Mock provider for testing session functionality."""

import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from .base import (
    BaseProvider,
    ChatCompletion,
    ChatCompletionChunk,
    Message,
    Model,
    Role,
    Tool,
    ToolResult,
)


class MockProvider(BaseProvider):
    """Mock provider that echoes back user input with context awareness."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.conversation_history = []

    @property
    def name(self) -> str:
        """Provider name."""
        return "mock"

    def list_models(self) -> list[Model]:
        """Return mock models for testing."""
        return [
            Model(
                id="mock-echo",
                name="Mock Echo Model",
                provider="mock",
                supports_functions=False,  # Echo model doesn't use tools
                metadata={
                    "capabilities": ["CHAT"],
                    "context_window": 4096,
                    "description": "Simple echo model for testing",
                },
            ),
            Model(
                id="mock-smart",
                name="Mock Smart Model",
                provider="mock",
                supports_functions=True,  # Smart model uses tools
                metadata={
                    "capabilities": ["CHAT"],
                    "context_window": 8192,
                    "description": "Intelligent model with NLP-based tool execution",
                },
            ),
        ]

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
        """Generate a mock response based on the conversation."""
        # Store conversation for context
        self.conversation_history = messages

        # Route to different behaviors based on model
        if model == "mock-echo":
            return self._handle_echo_model(messages, model, **kwargs)
        elif model == "mock-smart":
            return self._handle_smart_model(messages, model, tools, **kwargs)
        else:
            # Default behavior for other mock models
            return self._handle_echo_model(messages, model, **kwargs)

    def _handle_echo_model(self, messages: list[Message], model: str, **kwargs) -> ChatCompletion:
        """Handle mock-echo model - just echoes user input."""
        user_messages = [msg for msg in messages if msg.role == Role.USER]
        if not user_messages:
            content = "I don't see any user messages to echo."
        else:
            # Simple echo of the last user message
            content = f"Echo: {user_messages[-1].content}"

        # Add delay to simulate processing time
        time.sleep(0.5)  # Shorter delay for echo

        return ChatCompletion(
            content=content,
            model=model,
            finish_reason="stop",
            tool_calls=None,
            metadata={"provider": "mock", "model_type": "echo"},
        )

    def _handle_smart_model(
        self, messages: list[Message], model: str, tools: list[Tool] | None = None, **kwargs
    ) -> ChatCompletion:
        """Handle mock-smart model - uses NLP to execute tools."""
        # Check if we have tool results to summarize
        tool_messages = [msg for msg in messages if msg.role == Role.TOOL]
        if tool_messages:
            # We have tool execution results, provide a helpful summary
            content = self._generate_tool_response(messages, tool_messages)
            return ChatCompletion(
                content=content,
                model=model,
                finish_reason="stop",
                tool_calls=None,
                metadata={"provider": "mock", "model_type": "smart"},
            )

        # Get the last user message
        user_messages = [msg for msg in messages if msg.role == Role.USER]
        if not user_messages:
            return ChatCompletion(
                content="I don't see any user messages to respond to.",
                model=model,
                finish_reason="stop",
                tool_calls=None,
                metadata={"provider": "mock", "model_type": "smart"},
            )

        # For mock-smart, if we have tools, try to use NLP to execute them
        if tools and not kwargs.get("_manual_execution", False):
            last_user_content = user_messages[-1].content

            # Use NLP to detect if tools should be executed
            tool_calls = self._infer_tool_calls_from_response(last_user_content, tools)
            if tool_calls:
                # Execute tools manually using the sync method
                return self._execute_tools_manually_sync(messages, model, tools, **kwargs)

        # Default smart response without tools
        last_message = user_messages[-1].content.lower()

        if "hello" in last_message or "hi" in last_message:
            content = (
                "Hello! I'm the smart mock model. I can help you test tool execution features."
            )
        elif "help" in last_message:
            content = "I'm a smart mock AI assistant. I can execute tools automatically based on your requests."
        else:
            # Generate a contextual response
            content = f"I understand you said: '{user_messages[-1].content}'. How can I help you with that?"

        # Add delay to simulate processing time
        time.sleep(1.0)  # Medium delay for smart responses

        return ChatCompletion(
            content=content,
            model=model,
            finish_reason="stop",
            tool_calls=None,
            metadata={"provider": "mock", "model_type": "smart"},
        )

    def _execute_tools_manually_sync(
        self,
        messages: list[Message],
        model: str,
        tools: list[Tool],
        **kwargs,
    ) -> ChatCompletion:
        """
        Execute tools manually for mock-smart model.

        Simplified version that works reliably in mock context.
        """
        # 1. Use NLP to detect which tools to call
        user_messages = [msg for msg in messages if msg.role == Role.USER]
        if not user_messages:
            return ChatCompletion(
                content="No user message to process for tool execution.",
                model=model,
                finish_reason="stop",
                tool_calls=None,
                metadata={"provider": "mock", "manual_execution": True},
            )

        last_user_content = user_messages[-1].content
        tool_calls = self._infer_tool_calls_from_response(last_user_content, tools)

        if not tool_calls:
            return ChatCompletion(
                content=f"I understand you said: '{last_user_content}', but I couldn't detect any tools to execute.",
                model=model,
                finish_reason="stop",
                tool_calls=None,
                metadata={"provider": "mock", "manual_execution": True},
            )

        # 2. Execute tools synchronously
        tool_results = []

        for tool_call in tool_calls:
            try:
                # Execute tool directly
                import asyncio

                from coda.services.tools import execute_tool

                result = asyncio.run(execute_tool(tool_call.name, tool_call.arguments))

                tool_result = ToolResult(
                    tool_call_id=tool_call.id,
                    content=result.result if hasattr(result, "result") else str(result),
                    is_error=not getattr(result, "success", True),
                )
                tool_results.append(tool_result)
            except Exception as e:
                tool_results.append(
                    ToolResult(
                        tool_call_id=tool_call.id,
                        content=f"Error executing {tool_call.name}: {str(e)}",
                        is_error=True,
                    )
                )

        # 3. Generate response based on tool results
        if tool_results and not tool_results[0].is_error:
            # Successful tool execution
            if tool_calls[0].name == "read_file":
                content = "I've successfully read the file. The content has been processed."
            elif tool_calls[0].name == "list_files":
                content = "I've listed the directory contents successfully."
            elif tool_calls[0].name == "run_shell":
                content = "Command executed successfully."
            else:
                content = f"Tool '{tool_calls[0].name}' executed successfully."
        else:
            # Tool execution failed
            error_msg = tool_results[0].content if tool_results else "Unknown error"
            content = f"I tried to execute the tool but encountered an error: {error_msg}"

        # Add delay to simulate processing time
        time.sleep(1.5)

        return ChatCompletion(
            content=content,
            model=model,
            finish_reason="stop",
            tool_calls=tool_calls,
            metadata={
                "provider": "mock",
                "manual_execution": True,
                "tools_executed": len(tool_calls),
            },
        )

    def _generate_tool_response(self, messages: list[Message], tool_messages: list[Message]) -> str:
        """Generate a response based on tool execution results."""
        # Get the original user request
        user_messages = [msg for msg in messages if msg.role == Role.USER]
        if not user_messages:
            return "I executed the requested tools."

        last_user_message = user_messages[-1].content.lower()

        # Analyze tool results to provide contextual responses
        for tool_msg in tool_messages:
            content = tool_msg.content

            # Handle time-related requests
            if any(word in last_user_message for word in ["time", "clock", "hour", "minute"]):
                if "current time" in content.lower():
                    # Extract time from the tool result
                    return f"The current time is {content.split('Current time')[1].strip() if 'Current time' in content else content}."
                return f"Based on the time tool: {content}"

            # Handle file operations
            elif any(word in last_user_message for word in ["read", "file", "content"]):
                if "error" in content.lower() or "not found" in content.lower():
                    return f"I encountered an issue accessing the file: {content}"
                # Don't include file content in response to avoid Rich markup parsing issues
                return "I've successfully read the file. The content has been processed."

            # Handle directory listings
            elif any(
                word in last_user_message for word in ["list", "directory", "folder", "files"]
            ):
                return f"Here are the contents: {content}"

            # Handle shell commands
            elif any(word in last_user_message for word in ["run", "execute", "command", "shell"]):
                if "error" in content.lower():
                    return f"The command encountered an error: {content}"
                return f"Command executed successfully. Output: {content}"

            # Handle git operations
            elif any(word in last_user_message for word in ["git", "status", "commit", "branch"]):
                return f"Git operation completed: {content}"

            # Handle web requests
            elif any(word in last_user_message for word in ["fetch", "url", "web", "http"]):
                return f"I've fetched the web content: {content}"

            # Generic tool response
            else:
                return f"I've executed the requested operation. Result: {content}"

        return "I've completed the requested operations."

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
        """Stream a mock response word by word."""
        response = self.chat(messages, model, temperature, max_tokens, top_p, stop, tools, **kwargs)

        # Simulate streaming by yielding words
        words = response.content.split()
        for i, word in enumerate(words):
            # Add space except for first word
            content = word if i == 0 else f" {word}"

            yield ChatCompletionChunk(
                content=content,
                model=model,
                finish_reason="stop" if i == len(words) - 1 else None,
                metadata={"provider": "mock"},
            )

            # Small delay to simulate real streaming
            time.sleep(0.01)

    def get_model_info(self, model_id: str) -> dict[str, Any]:
        """Get information about a specific model."""
        models = {m.id: m for m in self.list_models()}
        if model_id in models:
            model = models[model_id]
            return {
                "id": model.id,
                "name": model.name,
                "provider": model.provider,
                "capabilities": model.metadata.get("capabilities", []),
                "context_window": model.metadata.get("context_window", 4096),
                "description": model.metadata.get("description", ""),
            }

        raise ValueError(f"Model {model_id} not found")

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
        """Async version of chat with proper async delay."""
        import asyncio

        # Use the same logic as sync version but with async delay
        self.conversation_history = messages

        # Check if we have tool results to summarize
        tool_messages = [msg for msg in messages if msg.role == Role.TOOL]
        if tool_messages:
            content = self._generate_tool_response(messages, tool_messages)
            await asyncio.sleep(2.5)  # Async delay for timer display
            return ChatCompletion(
                content=content,
                model=model,
                finish_reason="stop",
                tool_calls=None,
                metadata={"provider": "mock", "timestamp": datetime.now().isoformat()},
            )

        # Get the last user message
        user_messages = [msg for msg in messages if msg.role == Role.USER]
        if not user_messages:
            await asyncio.sleep(2.5)  # Async delay for timer display
            return ChatCompletion(
                content="I don't see any user messages to respond to.",
                model=model,
                finish_reason="stop",
                tool_calls=None,
                metadata={"provider": "mock", "timestamp": datetime.now().isoformat()},
            )

        # Generate the same response as sync version
        last_message = user_messages[-1].content.lower()

        if "hello" in last_message or "hi" in last_message:
            content = "Hello! How can I help you today?"
        elif "help" in last_message:
            content = "I'm a mock AI assistant. I can help you test session management features."
        else:
            # Echo back with conversation context
            response_parts = [f"You said: '{user_messages[-1].content}'"]
            if len(messages) > 1:
                response_parts.append(
                    f"This is message #{len([m for m in messages if m.role == Role.USER])} in our conversation."
                )
            if len(user_messages) > 1:
                response_parts.append(
                    f"Earlier you asked about: '{user_messages[-2].content[:50]}...'"
                )
            content = " ".join(response_parts)

        # Add async delay to simulate processing time for timer display
        await asyncio.sleep(2.5)  # Allow timer to show incremental updates

        return ChatCompletion(
            content=content,
            model=model,
            finish_reason="stop",
            tool_calls=None,
            metadata={"provider": "mock", "timestamp": datetime.now().isoformat()},
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
    ) -> Iterator[ChatCompletionChunk]:
        """Async version of chat_stream with proper async delay."""
        import asyncio

        # Get response using async chat
        response = await self.achat(
            messages, model, temperature, max_tokens, top_p, stop, tools, **kwargs
        )

        # Simulate streaming by yielding words
        words = response.content.split()
        for i, word in enumerate(words):
            # Add space except for first word
            content = word if i == 0 else f" {word}"

            yield ChatCompletionChunk(
                content=content,
                model=model,
                finish_reason="stop" if i == len(words) - 1 else None,
                metadata={"provider": "mock"},
            )

            # Small async delay to simulate real streaming
            await asyncio.sleep(0.01)

    def is_available(self) -> bool:
        """Mock provider is always available."""
        return True
