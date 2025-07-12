"""Unit tests for the model selector component."""

from unittest.mock import Mock, patch

import pytest

from coda.providers.base import Model
from coda.web.components.model_selector import render_model_selector


class TestModelSelector:
    """Test suite for model selector functionality."""

    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit components."""
        with patch("coda.web.components.model_selector.st") as mock_st:
            mock_st.selectbox = Mock(return_value="gpt-4")
            mock_st.warning = Mock()
            mock_st.error = Mock()
            yield mock_st

    @pytest.fixture
    def mock_state_utils(self):
        """Mock state utility functions."""
        with (
            patch("coda.web.components.model_selector.get_state_value") as mock_get,
            patch("coda.web.components.model_selector.set_state_value") as mock_set,
        ):
            yield mock_get, mock_set

    @pytest.fixture
    def mock_provider_factory(self):
        """Mock ProviderFactory."""
        with patch("coda.web.components.model_selector.ProviderFactory") as mock_factory_class:
            yield mock_factory_class

    @pytest.fixture
    def sample_models(self):
        """Sample model objects."""
        return [
            Model(
                id="gpt-4", name="GPT-4", provider="openai", context_length=8192, max_tokens=4096
            ),
            Model(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider="openai",
                context_length=4096,
                max_tokens=4096,
            ),
            Model(
                id="gpt-4-turbo",
                name="GPT-4 Turbo",
                provider="openai",
                context_length=128000,
                max_tokens=4096,
            ),
        ]

    def test_render_with_provider_selected(
        self, mock_streamlit, mock_state_utils, mock_provider_factory, sample_models
    ):
        """Test rendering with a provider selected."""
        mock_get, mock_set = mock_state_utils

        # Mock config
        config = {"providers": {"openai": {"enabled": True}}}
        mock_get.side_effect = lambda key, default=None: {
            "config": config,
            "current_model": "gpt-4",
            "openai_models": {m.id: m for m in sample_models},
        }.get(key, default)

        # Mock provider factory and provider
        mock_provider = Mock()
        mock_provider.list_models.return_value = sample_models
        mock_factory = Mock()
        mock_factory.create.return_value = mock_provider
        mock_provider_factory.return_value = mock_factory

        result = render_model_selector("openai")

        # Verify provider was created
        mock_factory.create.assert_called_once_with("openai")

        # Verify selectbox was called with correct models
        mock_streamlit.selectbox.assert_called_once()
        call_args = mock_streamlit.selectbox.call_args
        assert call_args[0][0] == "Model"
        assert call_args[1]["options"] == ["gpt-4", "gpt-3.5-turbo", "gpt-4-turbo"]
        assert call_args[1]["index"] == 0

        # Verify models were stored
        assert mock_set.call_count == 2
        mock_set.assert_any_call("openai_models", {m.id: m for m in sample_models})
        mock_set.assert_any_call("current_model", "gpt-4")

        assert result == "gpt-4"

    def test_render_without_provider(self, mock_streamlit, mock_state_utils):
        """Test rendering without a provider."""
        result = render_model_selector(None)

        # Verify disabled selectbox was rendered
        mock_streamlit.selectbox.assert_called_once_with("Model", [], disabled=True)
        assert result is None

    def test_model_persistence(self, mock_streamlit, mock_state_utils, mock_provider_factory):
        """Test that selected model is persisted."""
        mock_get, mock_set = mock_state_utils

        ollama_models = [
            Model(
                id="llama2", name="Llama 2", provider="ollama", context_length=4096, max_tokens=4096
            ),
            Model(
                id="codellama",
                name="Code Llama",
                provider="ollama",
                context_length=4096,
                max_tokens=4096,
            ),
            Model(
                id="mistral",
                name="Mistral",
                provider="ollama",
                context_length=8192,
                max_tokens=4096,
            ),
        ]

        config = {"providers": {"ollama": {"enabled": True}}}
        mock_get.side_effect = lambda key, default=None: {
            "config": config,
            "current_model": "codellama",
            "ollama_models": {m.id: m for m in ollama_models},
        }.get(key, default)

        # Mock provider factory and provider
        mock_provider = Mock()
        mock_provider.list_models.return_value = ollama_models
        mock_factory = Mock()
        mock_factory.create.return_value = mock_provider
        mock_provider_factory.return_value = mock_factory

        # Mock user selecting a different model
        mock_streamlit.selectbox.return_value = "mistral"

        result = render_model_selector("ollama")

        # Verify new model was saved
        mock_set.assert_any_call("current_model", "mistral")
        assert result == "mistral"

    def test_provider_switch_model_update(
        self, mock_streamlit, mock_state_utils, mock_provider_factory
    ):
        """Test model update when switching providers."""
        mock_get, mock_set = mock_state_utils

        litellm_models = [
            Model(
                id="claude-2",
                name="Claude 2",
                provider="litellm",
                context_length=100000,
                max_tokens=4096,
            ),
            Model(
                id="claude-instant",
                name="Claude Instant",
                provider="litellm",
                context_length=100000,
                max_tokens=4096,
            ),
        ]

        config = {"providers": {"litellm": {"enabled": True}}}
        mock_get.side_effect = lambda key, default=None: {
            "config": config,
            "current_model": "gpt-4",  # Model from previous provider
            "litellm_models": {m.id: m for m in litellm_models},
        }.get(key, default)

        # Mock provider factory and provider
        mock_provider = Mock()
        mock_provider.list_models.return_value = litellm_models
        mock_factory = Mock()
        mock_factory.create.return_value = mock_provider
        mock_provider_factory.return_value = mock_factory

        mock_streamlit.selectbox.return_value = "claude-2"

        result = render_model_selector("litellm")

        # Should select first model from new provider
        call_args = mock_streamlit.selectbox.call_args
        assert call_args[1]["index"] == 0  # First model since gpt-4 not in list
        assert result == "claude-2"

    def test_invalid_model_handling(self, mock_streamlit, mock_state_utils, mock_provider_factory):
        """Test handling of invalid current model."""
        mock_get, mock_set = mock_state_utils

        models = [
            Model(
                id="gpt-4", name="GPT-4", provider="openai", context_length=8192, max_tokens=4096
            ),
            Model(
                id="gpt-3.5-turbo",
                name="GPT-3.5 Turbo",
                provider="openai",
                context_length=4096,
                max_tokens=4096,
            ),
        ]

        config = {"providers": {"openai": {"enabled": True}}}
        mock_get.side_effect = lambda key, default=None: {
            "config": config,
            "current_model": "invalid-model",
            "openai_models": {m.id: m for m in models},
        }.get(key, default)

        # Mock provider factory and provider
        mock_provider = Mock()
        mock_provider.list_models.return_value = models
        mock_factory = Mock()
        mock_factory.create.return_value = mock_provider
        mock_provider_factory.return_value = mock_factory

        mock_streamlit.selectbox.return_value = "gpt-4"

        render_model_selector("openai")

        # Should default to first model
        call_args = mock_streamlit.selectbox.call_args
        assert call_args[1]["index"] == 0

    def test_empty_model_list(self, mock_streamlit, mock_state_utils, mock_provider_factory):
        """Test handling of empty model list."""
        mock_get, mock_set = mock_state_utils

        config = {"providers": {"openai": {"enabled": True}}}
        mock_get.side_effect = lambda key, default=None: {
            "config": config,
            "current_model": None,
        }.get(key, default)

        # Mock provider factory and provider
        mock_provider = Mock()
        mock_provider.list_models.return_value = []  # Empty model list
        mock_factory = Mock()
        mock_factory.create.return_value = mock_provider
        mock_provider_factory.return_value = mock_factory

        result = render_model_selector("openai")

        # Should show warning
        mock_streamlit.warning.assert_called_once_with("No models available for OPENAI")
        assert result is None

    def test_no_config(self, mock_streamlit, mock_state_utils):
        """Test handling when config is not available."""
        mock_get, _ = mock_state_utils
        mock_get.return_value = None

        result = render_model_selector("openai")

        assert result is None

    def test_provider_error(self, mock_streamlit, mock_state_utils, mock_provider_factory):
        """Test handling when provider creation fails."""
        mock_get, mock_set = mock_state_utils

        config = {"providers": {"openai": {"enabled": True}}}
        mock_get.side_effect = lambda key, default=None: {
            "config": config,
            "current_model": None,
        }.get(key, default)

        # Mock provider factory to raise error
        mock_factory = Mock()
        mock_factory.create.side_effect = Exception("Provider error")
        mock_provider_factory.return_value = mock_factory

        result = render_model_selector("openai")

        # Should show error
        mock_streamlit.error.assert_called_once_with(
            "Error loading models for OPENAI: Provider error"
        )
        assert result is None

    def test_model_format_function(
        self, mock_streamlit, mock_state_utils, mock_provider_factory, sample_models
    ):
        """Test the model format function."""
        mock_get, mock_set = mock_state_utils

        config = {"providers": {"openai": {"enabled": True}}}
        mock_get.side_effect = lambda key, default=None: {
            "config": config,
            "current_model": "gpt-4",
            "openai_models": {m.id: m for m in sample_models},
        }.get(key, default)

        # Mock provider factory and provider
        mock_provider = Mock()
        mock_provider.list_models.return_value = sample_models
        mock_factory = Mock()
        mock_factory.create.return_value = mock_provider
        mock_provider_factory.return_value = mock_factory

        render_model_selector("openai")

        # Check that format_func was provided
        call_args = mock_streamlit.selectbox.call_args
        format_func = call_args[1]["format_func"]

        # Test format function
        assert format_func("gpt-4") == "GPT-4 (gpt-4)"
        assert format_func("gpt-3.5-turbo") == "GPT-3.5 Turbo (gpt-3.5-turbo)"

    def test_display_name_mapping(self, mock_streamlit, mock_state_utils, mock_provider_factory):
        """Test provider display name mapping."""
        mock_get, mock_set = mock_state_utils

        config = {"providers": {"oci_genai": {"enabled": True}}}
        mock_get.side_effect = lambda key, default=None: {
            "config": config,
            "current_model": None,
        }.get(key, default)

        # Mock provider factory and provider
        mock_provider = Mock()
        mock_provider.list_models.return_value = []
        mock_factory = Mock()
        mock_factory.create.return_value = mock_provider
        mock_provider_factory.return_value = mock_factory

        render_model_selector("oci_genai")

        # Should use friendly display name
        mock_streamlit.warning.assert_called_once_with("No models available for OCI GenAI")
