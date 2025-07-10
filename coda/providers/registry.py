"""Provider registry and factory for managing LLM providers."""

from typing import Any

from .base import BaseProvider
from .constants import PROVIDERS
from .mock_provider import MockProvider


class ProviderRegistry:
    """Registry for managing available providers."""

    _providers: dict[str, type[BaseProvider]] = {}
    _instances: dict[str, BaseProvider] = {}

    @classmethod
    def register(cls, name: str, provider_class: type[BaseProvider]) -> None:
        """
        Register a provider class.

        Args:
            name: Provider name
            provider_class: Provider class (must inherit from BaseProvider)
        """
        if not issubclass(provider_class, BaseProvider):
            raise TypeError(f"Provider {provider_class} must inherit from BaseProvider")
        cls._providers[name] = provider_class

    @classmethod
    def get_provider_class(cls, name: str) -> type[BaseProvider] | None:
        """
        Get a registered provider class.

        Args:
            name: Provider name

        Returns:
            Provider class if registered, None otherwise
        """
        return cls._providers.get(name)

    @classmethod
    def list_providers(cls) -> list[str]:
        """
        List all registered provider names.

        Returns:
            List of provider names
        """
        return list(cls._providers.keys())

    @classmethod
    def _hash_config(cls, config: dict) -> str:
        """Create a stable hash of configuration, handling non-hashable types."""
        import json

        def serialize_value(obj):
            """Convert objects to JSON-serializable form."""
            if isinstance(obj, list | dict):
                return json.dumps(obj, sort_keys=True)
            elif hasattr(obj, "__dict__"):
                return json.dumps(obj.__dict__, sort_keys=True)
            else:
                return str(obj)

        # Create a sorted list of key-value pairs with serialized values
        items = []
        for key, value in sorted(config.items()):
            serialized_value = serialize_value(value)
            items.append(f"{key}:{serialized_value}")

        # Hash the joined string
        config_str = "|".join(items)
        return str(hash(config_str))

    @classmethod
    def create_provider(cls, name: str, **kwargs) -> BaseProvider:
        """
        Create a provider instance.

        Args:
            name: Provider name
            **kwargs: Provider-specific configuration

        Returns:
            Provider instance

        Raises:
            ValueError: If provider is not registered
        """
        provider_class = cls._providers.get(name)
        if not provider_class:
            available = ", ".join(cls._providers.keys())
            raise ValueError(f"Unknown provider: {name}. Available providers: {available}")

        # Create a unique key for this provider instance
        config_key = f"{name}_{cls._hash_config(kwargs)}"

        # Return existing instance if already created with same config
        if config_key in cls._instances:
            return cls._instances[config_key]

        # Create new instance
        instance = provider_class(**kwargs)
        cls._instances[config_key] = instance
        return instance

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all cached provider instances."""
        cls._instances.clear()


# Register built-in providers - always available
ProviderRegistry.register(PROVIDERS.MOCK, MockProvider)

# Register optional providers if available
try:
    from .oci_genai import OCIGenAIProvider

    ProviderRegistry.register(PROVIDERS.OCI_GENAI, OCIGenAIProvider)
except ImportError:
    pass  # OCI provider not available

try:
    from .litellm_provider import LiteLLMProvider

    ProviderRegistry.register(PROVIDERS.LITELLM, LiteLLMProvider)
except ImportError:
    pass  # LiteLLM provider not available

try:
    from .ollama_provider import OllamaProvider

    ProviderRegistry.register(PROVIDERS.OLLAMA, OllamaProvider)
except ImportError:
    pass  # Ollama provider not available


class ProviderFactory:
    """Factory for creating provider instances with configuration management."""

    def __init__(self, config: dict[str, Any] | None = None):
        """
        Initialize factory with global configuration.

        Args:
            config: Global configuration dictionary
        """
        self.config = config or {}

    def create(self, provider_name: str, **kwargs) -> BaseProvider:
        """
        Create a provider instance with merged configuration.

        Args:
            provider_name: Name of the provider
            **kwargs: Provider-specific overrides

        Returns:
            Configured provider instance
        """
        # Get provider-specific config from global config
        provider_config = self.config.get("providers", {}).get(provider_name, {})

        # Merge with kwargs (kwargs take precedence)
        merged_config = {**provider_config, **kwargs}

        # Create provider
        return ProviderRegistry.create_provider(provider_name, **merged_config)

    def list_available(self) -> list[str]:
        """List available provider names."""
        return ProviderRegistry.list_providers()


def get_provider_registry() -> dict[str, type[BaseProvider]]:
    """Get the current provider registry as a dictionary."""
    return ProviderRegistry._providers.copy()
