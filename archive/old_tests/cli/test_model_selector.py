"""Tests for the model selector functionality."""

from unittest.mock import Mock

import pytest

from coda.cli.model_selector import ModelSelector


@pytest.mark.unit
class TestModelSelector:
    """Test the model selector functionality."""

    @pytest.fixture
    def mock_models(self):
        """Create mock model objects."""
        models = []
        for i in range(5):
            model = Mock()
            model.id = f"model-{i}"
            model.provider = f"provider-{i % 2}"
            model.metadata = {"capabilities": ["CHAT"]}
            models.append(model)
        return models

    @pytest.fixture
    def selector(self, mock_models):
        """Create a model selector instance."""
        console = Mock()
        return ModelSelector(mock_models, console)

    def test_initialization(self, selector, mock_models):
        """Test selector initialization."""
        assert selector.models == mock_models
        assert selector.filtered_models == mock_models
        assert selector.selected_index == 0
        assert selector.search_text == ""

    def test_filter_models_no_search(self, selector, mock_models):
        """Test filtering with no search text."""
        selector.filter_models()
        assert selector.filtered_models == mock_models

    def test_filter_models_with_search(self, selector):
        """Test filtering with search text."""
        selector.search_text = "model-2"
        selector.filter_models()
        assert len(selector.filtered_models) == 1
        assert selector.filtered_models[0].id == "model-2"

    def test_filter_models_provider_search(self, selector):
        """Test filtering by provider name."""
        selector.search_text = "provider-1"
        selector.filter_models()
        # Should find models with provider-1
        assert len(selector.filtered_models) == 2
        assert all(m.provider == "provider-1" for m in selector.filtered_models)

    def test_filter_models_case_insensitive(self, selector):
        """Test case-insensitive filtering."""
        selector.search_text = "MODEL-2"
        selector.filter_models()
        assert len(selector.filtered_models) == 1
        assert selector.filtered_models[0].id == "model-2"

    def test_basic_model_selection_valid(self, selector):
        """Test basic model selection with valid input."""
        selector.console.input.return_value = "2"
        result = selector.select_model_basic()
        assert result == "model-1"

    def test_basic_model_selection_default(self, selector):
        """Test basic model selection with default input."""
        selector.console.input.return_value = ""
        result = selector.select_model_basic()
        assert result == "model-0"

    def test_basic_model_selection_invalid_retry(self, selector):
        """Test basic model selection with invalid input then valid."""
        selector.console.input.side_effect = ["invalid", "100", "1"]
        result = selector.select_model_basic()
        assert result == "model-0"
        # Should print error messages
        assert selector.console.print.call_count >= 3

    def test_basic_model_selection_keyboard_interrupt(self, selector):
        """Test handling keyboard interrupt during selection."""
        selector.console.input.side_effect = KeyboardInterrupt()
        with pytest.raises(SystemExit) as exc_info:
            selector.select_model_basic()
        assert exc_info.value.code == 0

    def test_create_model_list_text(self, selector):
        """Test HTML generation for model list."""
        html = selector.create_model_list_text()
        html_str = str(html)

        # Should contain title
        assert "Select a Model" in html_str

        # Should show first model as selected
        assert "▶ model-0" in html_str

        # Should show other models
        assert "model-1" in html_str

        # Should show help text
        assert "Navigate" in html_str
        assert "Select" in html_str
