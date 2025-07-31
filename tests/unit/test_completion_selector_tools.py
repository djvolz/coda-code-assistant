"""Unit tests for completion selector tool support indicators."""

from unittest.mock import MagicMock

from coda.apps.cli.completion_selector import CompletionModelSelector, OptionCompleter


class MockModel:
    """Mock model for testing."""

    def __init__(self, id, provider, supports_functions=None, metadata=None):
        self.id = id
        self.provider = provider
        self.supports_functions = supports_functions
        self.metadata = metadata or {}


class TestCompletionSelectorToolSupport:
    """Test tool support indicators in completion selector."""

    def test_option_completer_tool_indicators(self):
        """Test that OptionCompleter shows correct tool indicators."""
        options = [
            ("model1", "Provider1", {"tools": "Yes"}),
            ("model2", "Provider2", {"tools": "Partial"}),
            ("model3", "Provider3", {"tools": "Error"}),
            ("model4", "Provider4", {"tools": "No"}),
            ("model5", "Provider5", {"tools": "Unknown"}),
        ]

        completer = OptionCompleter(options)

        # Mock document
        mock_doc = MagicMock()
        mock_doc.text_before_cursor = ""

        # Get completions
        completions = list(completer.get_completions(mock_doc, None))

        # Check that all models are returned with correct indicators
        assert len(completions) == 5

        # Check display text contains correct emoji indicators
        displays = [c.display for c in completions]

        assert any("🔧 Tools" in str(d) for d in displays)  # Yes
        assert any("⚠️  Partial Tools" in str(d) for d in displays)  # Partial
        assert any("🚫 Tool Error" in str(d) for d in displays)  # Error
        assert any("❌ No Tools" in str(d) for d in displays)  # No
        assert any("❓ Untested" in str(d) for d in displays)  # Unknown

    def test_model_selector_full_tool_support(self):
        """Test model with full tool support."""
        models = [MockModel(id="test.model", provider="test", supports_functions=True, metadata={})]

        selector = CompletionModelSelector(models=models)

        # Check options format
        assert len(selector.options) == 1
        value, desc, metadata = selector.options[0]

        assert value == "test.model"
        assert desc == "test"
        assert metadata["tools"] == "Yes"

    def test_model_selector_partial_tool_support(self):
        """Test model with partial tool support (non-streaming only)."""
        models = [
            MockModel(
                id="test.model",
                provider="test",
                supports_functions=True,
                metadata={"tool_support_notes": ["non-streaming only"]},
            )
        ]

        selector = CompletionModelSelector(models=models)

        metadata = selector.options[0][2]
        assert metadata["tools"] == "Partial"

    def test_model_selector_tool_error(self):
        """Test model with tool support error."""
        models = [
            MockModel(
                id="test.model",
                provider="test",
                supports_functions=False,
                metadata={"tool_support_notes": ["error: fine-tuning base model"]},
            )
        ]

        selector = CompletionModelSelector(models=models)

        metadata = selector.options[0][2]
        assert metadata["tools"] == "Error"

    def test_model_selector_no_tool_support(self):
        """Test model with no tool support."""
        models = [
            MockModel(id="test.model", provider="test", supports_functions=False, metadata={})
        ]

        selector = CompletionModelSelector(models=models)

        metadata = selector.options[0][2]
        assert metadata["tools"] == "No"

    def test_model_selector_unknown_tool_support(self):
        """Test model with unknown tool support."""
        models = [
            MockModel(
                id="test.model",
                provider="test",
                # No supports_functions attribute
            )
        ]

        selector = CompletionModelSelector(models=models)

        metadata = selector.options[0][2]
        # When supports_functions is not set, it defaults to "No" not "Unknown"
        assert metadata["tools"] in ["No", "Unknown"]

    def test_model_selector_preserves_other_metadata(self):
        """Test that other metadata is preserved along with tool info."""
        models = [
            MockModel(
                id="test.model",
                provider="test",
                supports_functions=True,
                metadata={"context_window": 128000, "capabilities": ["text", "code", "math"]},
            )
        ]

        selector = CompletionModelSelector(models=models)

        metadata = selector.options[0][2]
        assert metadata["tools"] == "Yes"
        assert metadata["context"] == "128,000"
        assert metadata["caps"] == "text,code"

    def test_model_selector_instruction_text(self):
        """Test that instruction text explains tool indicators."""
        selector = CompletionModelSelector(models=[])

        expected = "Select a model (🔧 = tools work, ⚠️ = partial support, 🚫 = known errors, ❌ = no tools, ❓ = untested)"
        assert selector.instruction_text == expected

    def test_option_completer_search_filtering(self):
        """Test that search works with tool metadata."""
        options = [
            ("cohere.command", "cohere", {"tools": "Yes"}),
            ("meta.llama", "meta", {"tools": "No"}),
        ]

        completer = OptionCompleter(options)

        # Search for "cohere"
        mock_doc = MagicMock()
        mock_doc.text_before_cursor = "cohere"

        completions = list(completer.get_completions(mock_doc, None))

        # Should only return cohere model
        assert len(completions) == 1
        assert completions[0].text == "cohere.command"
        assert "🔧 Tools" in str(completions[0].display)

    def test_option_completer_metadata_ordering(self):
        """Test that tool metadata appears first in display."""
        options = [("model1", "provider", {"context": "128k", "tools": "Yes", "caps": "text,code"})]

        completer = OptionCompleter(options)

        mock_doc = MagicMock()
        mock_doc.text_before_cursor = ""

        completions = list(completer.get_completions(mock_doc, None))
        display = str(completions[0].display)

        # Tool indicator should appear before other metadata
        tools_pos = display.find("🔧 Tools")
        context_pos = display.find("context:")
        caps_pos = display.find("caps:")

        assert tools_pos < context_pos
        assert tools_pos < caps_pos
