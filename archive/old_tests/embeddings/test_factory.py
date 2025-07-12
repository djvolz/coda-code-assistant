"""Tests for the embedding provider factory."""

from unittest.mock import Mock, patch

import pytest

from coda.embeddings.base import BaseEmbeddingProvider
from coda.embeddings.factory import EmbeddingProviderFactory, create_embedding_provider
from coda.embeddings.mock import MockEmbeddingProvider
from coda.embeddings.oci import OCIEmbeddingProvider
from coda.embeddings.ollama import OllamaEmbeddingProvider
from coda.embeddings.sentence_transformers import SentenceTransformersProvider


class TestEmbeddingProviderFactory:
    """Test the EmbeddingProviderFactory class."""

    def test_provider_registry(self):
        """Test that all providers are registered."""
        assert "oci" in EmbeddingProviderFactory.PROVIDERS
        assert "mock" in EmbeddingProviderFactory.PROVIDERS
        assert "sentence-transformers" in EmbeddingProviderFactory.PROVIDERS
        assert "ollama" in EmbeddingProviderFactory.PROVIDERS

    def test_aliases(self):
        """Test provider aliases."""
        assert EmbeddingProviderFactory.ALIASES["st"] == "sentence-transformers"
        assert EmbeddingProviderFactory.ALIASES["sbert"] == "sentence-transformers"
        assert EmbeddingProviderFactory.ALIASES["local"] == "sentence-transformers"

    def test_create_mock_provider(self):
        """Test creating a mock provider."""
        provider = EmbeddingProviderFactory.create_provider("mock")
        assert isinstance(provider, MockEmbeddingProvider)
        assert provider.model_id == "mock-768d"  # Default model

    def test_create_mock_provider_custom_model(self):
        """Test creating a mock provider with custom model."""
        provider = EmbeddingProviderFactory.create_provider("mock", model_id="mock-1024d")
        assert isinstance(provider, MockEmbeddingProvider)
        assert provider.model_id == "mock-1024d"

    def test_create_sentence_transformers_provider(self):
        """Test creating a sentence-transformers provider."""
        provider = EmbeddingProviderFactory.create_provider("sentence-transformers")
        assert isinstance(provider, SentenceTransformersProvider)
        assert provider.model_id == "all-MiniLM-L6-v2"  # Default model

    def test_create_ollama_provider(self):
        """Test creating an Ollama provider."""
        provider = EmbeddingProviderFactory.create_provider("ollama")
        assert isinstance(provider, OllamaEmbeddingProvider)
        assert provider.model_id == "mxbai-embed-large"  # Default model

    def test_create_provider_with_alias(self):
        """Test creating a provider using an alias."""
        provider = EmbeddingProviderFactory.create_provider("st")
        assert isinstance(provider, SentenceTransformersProvider)

        provider2 = EmbeddingProviderFactory.create_provider("local")
        assert isinstance(provider2, SentenceTransformersProvider)

    def test_create_provider_case_insensitive(self):
        """Test that provider names are case-insensitive."""
        provider1 = EmbeddingProviderFactory.create_provider("MOCK")
        assert isinstance(provider1, MockEmbeddingProvider)

        provider2 = EmbeddingProviderFactory.create_provider("Sentence-Transformers")
        assert isinstance(provider2, SentenceTransformersProvider)

    def test_create_provider_unknown_type(self):
        """Test error handling for unknown provider type."""
        with pytest.raises(ValueError, match="Unknown provider type: unknown"):
            EmbeddingProviderFactory.create_provider("unknown")

    def test_create_provider_with_kwargs(self):
        """Test creating providers with additional kwargs."""
        provider = EmbeddingProviderFactory.create_provider(
            "ollama", model_id="custom-model", base_url="http://remote:11434", timeout=60.0
        )
        assert isinstance(provider, OllamaEmbeddingProvider)
        assert provider.model_id == "custom-model"
        assert provider.base_url == "http://remote:11434"
        assert provider.timeout == 60.0

    @patch("coda.embeddings.oci.create_standalone_oci_provider")
    def test_create_oci_provider(self, mock_create_oci):
        """Test creating an OCI provider with special handling."""
        mock_provider = Mock(spec=OCIEmbeddingProvider)
        mock_create_oci.return_value = mock_provider

        provider = EmbeddingProviderFactory.create_provider(
            "oci",
            model_id="cohere.embed-english-v3.0",
            compartment_id="test-compartment",
            profile="TEST",
        )

        assert provider is mock_provider
        mock_create_oci.assert_called_once_with(
            model_id="cohere.embed-english-v3.0",
            compartment_id="test-compartment",
            config_file=None,
            profile="TEST",
        )

    def test_default_model_ids(self):
        """Test that default model IDs are set correctly."""
        # OCI
        with patch("coda.embeddings.oci.create_standalone_oci_provider") as mock_create_oci:
            mock_create_oci.return_value = Mock()
            EmbeddingProviderFactory.create_provider("oci")
            assert mock_create_oci.call_args[1]["model_id"] == "cohere.embed-multilingual-v3.0"

        # Sentence-transformers
        provider = EmbeddingProviderFactory.create_provider("sentence-transformers")
        assert provider.model_id == "all-MiniLM-L6-v2"

        # Ollama
        provider = EmbeddingProviderFactory.create_provider("ollama")
        assert provider.model_id == "mxbai-embed-large"

        # Mock
        provider = EmbeddingProviderFactory.create_provider("mock")
        assert provider.model_id == "mock-768d"

    def test_create_provider_error_handling(self):
        """Test error handling during provider creation."""
        with patch.object(MockEmbeddingProvider, "__init__", side_effect=Exception("Init failed")):
            with pytest.raises(Exception, match="Init failed"):
                EmbeddingProviderFactory.create_provider("mock")

    def test_list_providers(self):
        """Test listing available providers."""
        providers = EmbeddingProviderFactory.list_providers()

        assert isinstance(providers, dict)
        assert "oci" in providers
        assert "mock" in providers
        assert "sentence-transformers" in providers
        assert "ollama" in providers

        # Check descriptions
        assert "Oracle Cloud" in providers["oci"]
        assert "Mock provider" in providers["mock"]
        assert "sentence-transformers" in providers["sentence-transformers"]
        assert "Ollama" in providers["ollama"]

    def test_get_provider_info(self):
        """Test getting provider information."""
        # OCI info
        oci_info = EmbeddingProviderFactory.get_provider_info("oci")
        assert oci_info["requires_auth"] is True
        assert oci_info["requires_internet"] is True
        assert oci_info["default_model"] == "cohere.embed-multilingual-v3.0"
        assert len(oci_info["example_models"]) > 0

        # Mock info
        mock_info = EmbeddingProviderFactory.get_provider_info("mock")
        assert mock_info["requires_auth"] is False
        assert mock_info["requires_internet"] is False
        assert mock_info["default_model"] == "mock-768d"

        # Sentence-transformers info
        st_info = EmbeddingProviderFactory.get_provider_info("sentence-transformers")
        assert st_info["requires_auth"] is False
        assert st_info["requires_internet"] is False
        assert st_info["default_model"] == "all-MiniLM-L6-v2"

        # Ollama info
        ollama_info = EmbeddingProviderFactory.get_provider_info("ollama")
        assert ollama_info["requires_auth"] is False
        assert ollama_info["requires_internet"] is False
        assert ollama_info["default_model"] == "mxbai-embed-large"

    def test_get_provider_info_with_alias(self):
        """Test getting provider info using alias."""
        info = EmbeddingProviderFactory.get_provider_info("st")
        assert info["default_model"] == "all-MiniLM-L6-v2"

        info2 = EmbeddingProviderFactory.get_provider_info("local")
        assert info2["default_model"] == "all-MiniLM-L6-v2"

    def test_get_provider_info_unknown(self):
        """Test getting info for unknown provider."""
        info = EmbeddingProviderFactory.get_provider_info("unknown-provider")
        assert info["description"] == "Unknown provider"
        assert info["requires_auth"] == "unknown"
        assert info["requires_internet"] == "unknown"
        assert info["default_model"] == "unknown"
        assert info["example_models"] == []


class TestCreateEmbeddingProvider:
    """Test the convenience function create_embedding_provider."""

    def test_create_with_defaults(self):
        """Test creating provider with all defaults."""
        provider = create_embedding_provider()
        assert isinstance(provider, MockEmbeddingProvider)
        assert provider.model_id == "mock-768d"

    def test_create_with_type(self):
        """Test creating provider with specified type."""
        provider = create_embedding_provider(provider_type="sentence-transformers")
        assert isinstance(provider, SentenceTransformersProvider)

    def test_create_with_model(self):
        """Test creating provider with specified model."""
        provider = create_embedding_provider(
            provider_type="sentence-transformers", model_id="all-mpnet-base-v2"
        )
        assert isinstance(provider, SentenceTransformersProvider)
        assert provider.model_id == "all-mpnet-base-v2"

    def test_create_with_kwargs(self):
        """Test creating provider with additional kwargs."""
        provider = create_embedding_provider(
            provider_type="ollama",
            model_id="nomic-embed-text",
            base_url="http://custom:11434",
            timeout=45.0,
        )
        assert isinstance(provider, OllamaEmbeddingProvider)
        assert provider.model_id == "nomic-embed-text"
        assert provider.base_url == "http://custom:11434"
        assert provider.timeout == 45.0


class TestFactoryIntegration:
    """Integration tests for the factory."""

    def test_all_providers_implement_interface(self):
        """Test that all created providers implement the base interface."""
        for provider_type in EmbeddingProviderFactory.PROVIDERS.keys():
            # Skip OCI which requires special setup
            if provider_type == "oci":
                continue

            provider = EmbeddingProviderFactory.create_provider(provider_type)
            assert isinstance(provider, BaseEmbeddingProvider)

            # Check required attributes
            assert hasattr(provider, "model_id")
            assert hasattr(provider, "embed_text")
            assert hasattr(provider, "embed_batch")
            assert hasattr(provider, "get_model_info")
            assert hasattr(provider, "list_models")

    def test_factory_consistency(self):
        """Test that factory behaves consistently."""
        # Same inputs should produce equivalent providers
        provider1 = EmbeddingProviderFactory.create_provider("mock", model_id="test-model")
        provider2 = EmbeddingProviderFactory.create_provider("mock", model_id="test-model")

        assert type(provider1) == type(provider2)
        assert provider1.model_id == provider2.model_id

    @pytest.mark.parametrize(
        "alias,expected_type",
        [
            ("st", SentenceTransformersProvider),
            ("sbert", SentenceTransformersProvider),
            ("local", SentenceTransformersProvider),
        ],
    )
    def test_all_aliases_work(self, alias, expected_type):
        """Test that all aliases create the correct provider type."""
        provider = EmbeddingProviderFactory.create_provider(alias)
        assert isinstance(provider, expected_type)
