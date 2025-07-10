"""Unit tests for provider registry and factory."""

import pytest

from coda.base.providers import (
    BaseProvider,
    LiteLLMProvider,
    OCIGenAIProvider,
    OllamaProvider,
    ProviderFactory,
    ProviderRegistry,
)


class MockProvider(BaseProvider):
    """Mock provider for testing."""

    @property
    def name(self):
        return "mock"

    def chat(self, messages, model, **kwargs):
        pass

    def chat_stream(self, messages, model, **kwargs):
        pass

    async def achat(self, messages, model, **kwargs):
        pass

    async def achat_stream(self, messages, model, **kwargs):
        pass

    def list_models(self):
        return []


@pytest.mark.unit
class TestProviderRegistry:
    """Test provider registry functionality."""

    def test_register_provider(self):
        """Test registering a new provider."""
        # Register mock provider
        ProviderRegistry.register("test_mock", MockProvider)

        # Check it's registered
        assert "test_mock" in ProviderRegistry.list_providers()
        assert ProviderRegistry.get_provider_class("test_mock") == MockProvider

    def test_register_invalid_provider(self):
        """Test registering an invalid provider."""

        class NotAProvider:
            pass

        with pytest.raises(TypeError, match="must inherit from BaseProvider"):
            ProviderRegistry.register("invalid", NotAProvider)

    def test_list_providers(self):
        """Test listing available providers."""
        providers = ProviderRegistry.list_providers()

        # Check built-in providers are registered
        assert "oci_genai" in providers
        assert "litellm" in providers
        assert "ollama" in providers

    def test_get_provider_class(self):
        """Test getting provider class."""
        assert ProviderRegistry.get_provider_class("oci_genai") == OCIGenAIProvider
        assert ProviderRegistry.get_provider_class("litellm") == LiteLLMProvider
        assert ProviderRegistry.get_provider_class("ollama") == OllamaProvider
        assert ProviderRegistry.get_provider_class("nonexistent") is None

    def test_create_provider(self):
        """Test creating provider instances."""
        # Create OllamaProvider (doesn't require special config)
        provider = ProviderRegistry.create_provider("ollama", host="http://localhost:11434")
        assert isinstance(provider, OllamaProvider)
        assert provider.host == "http://localhost:11434"

    def test_create_unknown_provider(self):
        """Test creating unknown provider."""
        with pytest.raises(ValueError, match="Unknown provider"):
            ProviderRegistry.create_provider("nonexistent")

    def test_provider_instance_caching(self):
        """Test that providers with same config return same instance."""
        # Create two providers with same config
        provider1 = ProviderRegistry.create_provider("ollama", host="http://localhost:11434")
        provider2 = ProviderRegistry.create_provider("ollama", host="http://localhost:11434")

        # Should be the same instance
        assert provider1 is provider2

        # Different config should create new instance
        provider3 = ProviderRegistry.create_provider("ollama", host="http://localhost:11435")
        assert provider3 is not provider1

    def test_clear_instances(self):
        """Test clearing cached instances."""
        # Create a provider
        provider1 = ProviderRegistry.create_provider("ollama", host="http://localhost:11434")

        # Clear cache
        ProviderRegistry.clear_instances()

        # Create again - should be new instance
        provider2 = ProviderRegistry.create_provider("ollama", host="http://localhost:11434")
        assert provider1 is not provider2


@pytest.mark.unit
class TestProviderFactory:
    """Test provider factory functionality."""

    def test_create_with_global_config(self):
        """Test creating provider with global config."""
        config = {
            "providers": {
                "ollama": {
                    "host": "http://localhost:11434",
                    "timeout": 60.0,
                }
            }
        }

        factory = ProviderFactory(config)
        provider = factory.create("ollama")

        assert isinstance(provider, OllamaProvider)
        assert provider.host == "http://localhost:11434"
        assert provider.timeout == 60.0

    def test_create_with_override(self):
        """Test creating provider with config override."""
        config = {
            "providers": {
                "ollama": {
                    "host": "http://localhost:11434",
                    "timeout": 60.0,
                }
            }
        }

        factory = ProviderFactory(config)
        # Override timeout
        provider = factory.create("ollama", timeout=120.0)

        assert provider.timeout == 120.0  # Override should take precedence
        assert provider.host == "http://localhost:11434"  # Global config still used

    def test_create_without_config(self):
        """Test creating provider without global config."""
        factory = ProviderFactory()
        provider = factory.create("ollama", host="http://localhost:11434")

        assert isinstance(provider, OllamaProvider)
        assert provider.host == "http://localhost:11434"

    def test_list_available(self):
        """Test listing available providers from factory."""
        factory = ProviderFactory()
        providers = factory.list_available()

        assert "oci_genai" in providers
        assert "litellm" in providers
        assert "ollama" in providers
