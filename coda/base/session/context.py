"""Context management for sessions with intelligent windowing."""

from dataclasses import dataclass
from typing import Any

try:
    import tiktoken

    HAS_TIKTOKEN = True
except ImportError:
    HAS_TIKTOKEN = False

from coda.base.providers.base import BaseProvider


@dataclass
class ContextWindow:
    """Represents a context window configuration."""

    max_tokens: int
    max_messages: int
    preserve_system: bool = True
    summarization_threshold: float = 0.8  # Summarize when 80% full


class ContextManager:
    """Manages context windowing and optimization for sessions."""

    def __init__(self, model: str = "gpt-3.5-turbo", provider: BaseProvider | None = None):
        """Initialize context manager.

        Args:
            model: Model name for token counting
            provider: Optional provider instance to get model info from
        """
        self.model = model
        self.provider = provider
        self._init_tokenizer()

        # Fallback context limits for when provider info is not available
        # These are kept for backwards compatibility and as defaults
        self.fallback_context_limits = {
            # OCI GenAI models
            "cohere.command-r-plus": 128000,
            "cohere.command-r-16k": 16000,
            "cohere.command": 4000,
            "meta.llama-3.1-405b": 128000,
            "meta.llama-3.1-70b": 128000,
            "meta.llama-3.3-70b": 128000,
            "meta.llama-4-3-90b": 131072,
            "xai.grok-3": 131072,
            # OpenAI models
            "gpt-4": 8192,
            "gpt-4-32k": 32768,
            "gpt-4-turbo": 128000,
            "gpt-4-turbo-preview": 128000,
            "gpt-3.5-turbo": 4096,
            "gpt-3.5-turbo-16k": 16384,
            # Default
            "default": 4096,
        }

    def _init_tokenizer(self):
        """Initialize the tokenizer for token counting."""
        if not HAS_TIKTOKEN:
            self.tokenizer = None
            return

        try:
            # Try to use tiktoken for accurate token counting
            self.tokenizer = tiktoken.encoding_for_model(self.model)
        except Exception:
            # Fallback to cl100k_base encoding
            try:
                self.tokenizer = tiktoken.get_encoding("cl100k_base")
            except Exception:
                # If tiktoken is not available, use approximate counting
                self.tokenizer = None

    def count_tokens(self, text: str) -> int:
        """Count tokens in text.

        Args:
            text: Text to count tokens for

        Returns:
            Approximate token count
        """
        if self.tokenizer:
            return len(self.tokenizer.encode(text))
        else:
            # Approximate: 1 token ≈ 4 characters or 0.75 words
            return max(len(text) // 4, len(text.split()) * 3 // 4)

    def count_message_tokens(self, message: dict[str, Any]) -> int:
        """Count tokens in a message.

        Args:
            message: Message dict with role and content

        Returns:
            Token count including overhead
        """
        # Message overhead (role, formatting)
        overhead = 4

        # Count content tokens
        content_tokens = self.count_tokens(message.get("content", ""))

        return overhead + content_tokens

    def get_model_context_limit(self, model: str) -> int:
        """Get context limit for a model.

        Args:
            model: Model name

        Returns:
            Maximum context tokens
        """
        # First try to get from provider if available
        if self.provider:
            model_info = self.provider.get_model_info(model)
            if model_info and model_info.context_length:
                return model_info.context_length

        # Fall back to hardcoded limits
        # Check exact match first
        if model in self.fallback_context_limits:
            return self.fallback_context_limits[model]

        # Check partial matches
        model_lower = model.lower()
        for key, limit in self.fallback_context_limits.items():
            if key in model_lower or model_lower in key:
                return limit

        # Default
        return self.fallback_context_limits["default"]

    def optimize_context(
        self,
        messages: list[dict[str, Any]],
        model: str,
        target_tokens: int | None = None,
        preserve_last_n: int = 10,
    ) -> tuple[list[dict[str, Any]], bool]:
        """Optimize message context to fit within token limits.

        Args:
            messages: List of message dicts
            model: Model name
            target_tokens: Target token limit (uses model default if None)
            preserve_last_n: Number of recent messages to always preserve

        Returns:
            Tuple of (optimized messages, was_truncated)
        """
        if not messages:
            return [], False

        # Get token limit
        if target_tokens is None:
            model_limit = self.get_model_context_limit(model)
            # Reserve 20% for response
            target_tokens = int(model_limit * 0.8)

        # Count total tokens
        total_tokens = sum(self.count_message_tokens(msg) for msg in messages)

        # If within limit, return as is
        if total_tokens <= target_tokens:
            return messages, False

        # Preserve system messages and recent messages
        preserved_messages = []
        preserved_tokens = 0

        # Always keep system messages
        for msg in messages:
            if msg.get("role") == "system":
                preserved_messages.append(msg)
                preserved_tokens += self.count_message_tokens(msg)

        # Keep last N messages
        recent_messages = []
        recent_tokens = 0
        for msg in reversed(messages[-preserve_last_n:]):
            if msg.get("role") != "system":
                msg_tokens = self.count_message_tokens(msg)
                if preserved_tokens + recent_tokens + msg_tokens <= target_tokens:
                    recent_messages.insert(0, msg)
                    recent_tokens += msg_tokens

        # Try to fit older messages
        remaining_tokens = target_tokens - preserved_tokens - recent_tokens
        older_messages = []

        for msg in messages[:-preserve_last_n]:
            if msg.get("role") != "system":
                msg_tokens = self.count_message_tokens(msg)
                if msg_tokens <= remaining_tokens:
                    older_messages.append(msg)
                    remaining_tokens -= msg_tokens

        # Combine messages
        optimized = preserved_messages + older_messages + recent_messages

        # Sort by original order (assuming messages have indices or timestamps)
        # For now, we'll maintain relative order

        # Check if any truncation occurred
        was_truncated = len(optimized) < len(messages)

        return optimized, was_truncated

    def create_summary_message(
        self, messages: list[dict[str, Any]], max_tokens: int = 500
    ) -> dict[str, Any]:
        """Create a summary message for truncated context.

        Args:
            messages: Messages to summarize
            max_tokens: Maximum tokens for summary

        Returns:
            Summary message dict
        """
        # Count messages by role
        role_counts = {}
        for msg in messages:
            role = msg.get("role", "unknown")
            role_counts[role] = role_counts.get(role, 0) + 1

        # Create summary
        summary_parts = [
            f"[Previous conversation summary: {len(messages)} messages",
            f"({role_counts.get('user', 0)} user, {role_counts.get('assistant', 0)} assistant)]",
        ]

        # Add key points from messages (simplified for now)
        # In a real implementation, this could use LLM to summarize
        key_topics = self._extract_key_topics(messages)
        if key_topics:
            summary_parts.append(f"Key topics: {', '.join(key_topics[:5])}")

        summary = " ".join(summary_parts)

        return {"role": "system", "content": summary}

    def _extract_key_topics(self, messages: list[dict[str, Any]]) -> list[str]:
        """Extract key topics from messages (simplified implementation).

        Args:
            messages: Messages to analyze

        Returns:
            List of key topics
        """
        # Simple keyword extraction
        # In production, this could use NLP or LLM
        topics = []

        # Common programming keywords to look for
        keywords = [
            "function",
            "class",
            "database",
            "api",
            "error",
            "bug",
            "feature",
            "test",
            "deploy",
            "config",
            "security",
            "performance",
        ]

        # Count keyword occurrences
        keyword_counts = {}
        for msg in messages:
            content = msg.get("content", "").lower()
            for keyword in keywords:
                if keyword in content:
                    keyword_counts[keyword] = keyword_counts.get(keyword, 0) + 1

        # Get top topics
        sorted_topics = sorted(keyword_counts.items(), key=lambda x: x[1], reverse=True)
        topics = [topic for topic, _ in sorted_topics[:5]]

        return topics

    def get_context_window(self, model: str, mode: str = "balanced") -> ContextWindow:
        """Get recommended context window configuration.

        Args:
            model: Model name
            mode: Context mode (aggressive, balanced, conservative)

        Returns:
            ContextWindow configuration
        """
        model_limit = self.get_model_context_limit(model)

        if mode == "aggressive":
            # Use 90% of context
            max_tokens = int(model_limit * 0.9)
            max_messages = 100
        elif mode == "conservative":
            # Use 60% of context
            max_tokens = int(model_limit * 0.6)
            max_messages = 30
        else:  # balanced
            # Use 75% of context
            max_tokens = int(model_limit * 0.75)
            max_messages = 50

        return ContextWindow(max_tokens=max_tokens, max_messages=max_messages, preserve_system=True)
