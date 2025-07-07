"""Mock provider for testing session functionality."""

import time
from collections.abc import Iterator
from datetime import datetime
from typing import Any

from .base import BaseProvider, ChatCompletion, ChatCompletionChunk, Message, Model, Role, Tool


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
                metadata={
                    "capabilities": ["CHAT"],
                    "context_window": 4096,
                    "supports_functions": True,
                    "description": "Echoes back with conversation awareness and tool support",
                },
            ),
            Model(
                id="mock-smart",
                name="Mock Smart Model",
                provider="mock",
                metadata={
                    "capabilities": ["CHAT"],
                    "context_window": 8192,
                    "supports_functions": True,
                    "description": "Provides contextual responses with tool support",
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
                metadata={"provider": "mock", "timestamp": datetime.now().isoformat()},
            )

        # Get the last user message
        user_messages = [msg for msg in messages if msg.role == Role.USER]
        if not user_messages:
            return ChatCompletion(
                content="I don't see any user messages to respond to.",
                model=model,
                finish_reason="stop",
                tool_calls=None,
                metadata={"provider": "mock", "timestamp": datetime.now().isoformat()},
            )

        last_message = user_messages[-1].content.lower()

        # Generate contextual responses based on conversation
        # IMPORTANT: Check for memory questions FIRST before topic-specific responses
        if "what were we discussing" in last_message or "talking about" in last_message:
            # Only look for topics in PREVIOUS messages (not the current one asking about discussion)
            topics = []
            previous_messages = messages[
                :-1
            ]  # Exclude the current "what were we discussing" message

            if not previous_messages:
                content = "I don't see any previous conversation to reference."
            else:
                for msg in previous_messages:
                    # Handle different message types safely
                    if hasattr(msg, "content") and isinstance(msg.content, str):
                        msg_content = msg.content.lower()
                        if "python" in msg_content:
                            topics.append("Python programming")
                        if "decorator" in msg_content:
                            topics.append("Python decorators")
                        if "javascript" in msg_content:
                            topics.append("JavaScript")

                if topics:
                    content = f"We were discussing: {', '.join(set(topics))}. What would you like to know more about?"
                else:
                    content = "I don't see any specific topics we were discussing previously."

        elif "python" in last_message:
            if any(
                "decorator" in msg.content.lower()
                for msg in messages
                if hasattr(msg, "content") and isinstance(msg.content, str)
            ):
                content = "Yes, we were discussing Python decorators. They are functions that modify other functions, using the @decorator syntax."
            else:
                content = "Python is a high-level programming language known for its simplicity and readability."

        elif "javascript" in last_message:
            content = (
                "JavaScript is a dynamic programming language primarily used for web development."
            )

        elif "decorator" in last_message and len(messages) == 1:
            # If this is the only message, provide general info
            content = "Decorators in Python are a way to modify functions using the @ syntax. For example: @property or @staticmethod."

        elif "decorator" in last_message and len(messages) > 1:
            # If part of a conversation, check for context
            if any(
                "decorator" in msg.content.lower()
                for msg in messages[:-1]
                if hasattr(msg, "content") and isinstance(msg.content, str)
            ):
                content = "Yes, we were discussing Python decorators. They are functions that modify other functions, using the @decorator syntax."
            else:
                content = "Decorators in Python are a way to modify functions using the @ syntax. For example: @property or @staticmethod."

        elif "hello" in last_message or "hi" in last_message:
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

            # Add context about previous messages
            if len(user_messages) > 1:
                response_parts.append(
                    f"Earlier you asked about: '{user_messages[-2].content[:50]}...'"
                )

            content = " ".join(response_parts)

        # Return ChatCompletion object
        return ChatCompletion(
            content=content,
            model=model,
            finish_reason="stop",
            tool_calls=None,
            metadata={"provider": "mock", "timestamp": datetime.now().isoformat()},
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
                return f"I've read the file. Here's the content: {content}"

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
        """Async version of chat (delegates to sync)."""
        return self.chat(messages, model, temperature, max_tokens, top_p, stop, tools, **kwargs)

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
        """Async version of chat_stream (delegates to sync)."""
        for chunk in self.chat_stream(
            messages, model, temperature, max_tokens, top_p, stop, tools, **kwargs
        ):
            yield chunk

    def is_available(self) -> bool:
        """Mock provider is always available."""
        return True
