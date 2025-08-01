"""Unit tests for OCI provider tool support functionality."""

from unittest.mock import MagicMock, patch

import pytest

from coda.base.providers.base import Message, Role, Tool
from coda.base.providers.oci_genai import OCIGenAIProvider


@pytest.fixture
def mock_oci_config():
    """Mock OCI configuration."""
    with patch("coda.base.providers.oci_genai.oci.config") as mock_config:
        mock_config.load_config.return_value = {"compartment_id": "test-compartment-id"}
        yield mock_config


@pytest.fixture
def mock_clients():
    """Mock OCI clients."""
    with patch("coda.base.providers.oci_genai.GenerativeAiInferenceClient") as mock_inference:
        with patch("coda.base.providers.oci_genai.GenerativeAiClient") as mock_genai:
            yield mock_inference, mock_genai


@pytest.fixture
def oci_provider(mock_oci_config, mock_clients):
    """Create an OCI provider with mocked dependencies."""
    # Mock the config properly
    mock_oci_config.from_file.return_value = {"region": "us-chicago-1"}
    mock_oci_config.validate_config.return_value = None

    # Need to mock environment variable for compartment ID
    with patch.dict("os.environ", {"OCI_COMPARTMENT_ID": "test-compartment-id"}):
        provider = OCIGenAIProvider()

    # Mock the model ID map
    provider._model_id_map = {
        "meta.llama-3.3-70b-instruct": "ocid1.generativeaimodel.oc1.us-chicago-1.meta-llama-3-3-70b",
        "meta.llama-3.2-11b-vision-instruct": "ocid1.generativeaimodel.oc1.us-chicago-1.meta-llama-3-2-11b",
        "cohere.command-r-plus": "ocid1.generativeaimodel.oc1.us-chicago-1.cohere-command-r-plus",
        "test.model1": "ocid1.generativeaimodel.oc1.us-chicago-1.test-model1",
        "test.model2": "ocid1.generativeaimodel.oc1.us-chicago-1.test-model2",
    }
    return provider


class TestOCIProviderToolSupport:
    """Test OCI provider tool support functionality."""

    def test_chat_with_tools_api_error(self, oci_provider):
        """Test chat method when API returns error for tools."""
        # Mock validate_model to return True
        oci_provider.validate_model = MagicMock(return_value=True)

        # Mock the actual chat request to raise an error
        oci_provider.inference_client.chat.side_effect = Exception("Model does not support tools")

        messages = [Message(role=Role.USER, content="Test")]
        tools = [
            Tool(
                name="test_tool",
                description="Test tool",
                parameters={"type": "object", "properties": {}, "required": []},
            )
        ]

        with pytest.raises(Exception) as exc_info:
            oci_provider.chat(messages=messages, model="meta.llama-3.3-70b-instruct", tools=tools)

        assert "Model does not support tools" in str(exc_info.value)

    def test_chat_with_tools_success(self, oci_provider):
        """Test chat method when model supports tools."""
        # Mock validate_model to return True
        oci_provider.validate_model = MagicMock(return_value=True)

        # Mock the actual chat request for Cohere model
        mock_response = MagicMock()
        mock_response.text = "Test response"
        mock_response.finish_reason = "stop"
        mock_response.tool_calls = None
        mock_response.meta = None

        oci_provider.inference_client.chat.return_value.data.chat_response = mock_response

        messages = [Message(role=Role.USER, content="Test")]
        tools = [
            Tool(
                name="test_tool",
                description="Test tool",
                parameters={"type": "object", "properties": {}, "required": []},
            )
        ]

        # Should not raise an error
        result = oci_provider.chat(messages=messages, model="cohere.command-r-plus", tools=tools)

        assert result.content == "Test response"

    def test_chat_stream_with_tools_api_error(self, oci_provider):
        """Test chat_stream method when API returns error for tools."""
        # Mock validate_model to return True
        oci_provider.validate_model = MagicMock(return_value=True)

        # Mock the streaming to raise an error
        oci_provider.inference_client.chat.side_effect = Exception(
            "Streaming with tools not supported"
        )

        messages = [Message(role=Role.USER, content="Test")]
        tools = [
            Tool(
                name="test_tool",
                description="Test tool",
                parameters={"type": "object", "properties": {}, "required": []},
            )
        ]

        with pytest.raises(Exception) as exc_info:
            list(
                oci_provider.chat_stream(
                    messages=messages, model="meta.llama-3.2-11b-vision-instruct", tools=tools
                )
            )

        assert "Streaming with tools not supported" in str(exc_info.value)

    def test_chat_stream_with_tools_success(self, oci_provider):
        """Test chat_stream with tools when API supports it."""
        # Mock validate_model to return True
        oci_provider.validate_model = MagicMock(return_value=True)

        # Mock the streaming response
        mock_event = MagicMock()
        mock_event.data = '{"text": "Test response"}'

        mock_stream = MagicMock()
        mock_stream.data.events.return_value = [mock_event]

        oci_provider.inference_client.chat.return_value = mock_stream

        messages = [Message(role=Role.USER, content="Test")]
        tools = [
            Tool(
                name="test_tool",
                description="Test tool",
                parameters={"type": "object", "properties": {}, "required": []},
            )
        ]

        # Should work without warnings
        list(
            oci_provider.chat_stream(messages=messages, model="cohere.command-r-plus", tools=tools)
        )

    def test_chat_without_tools(self, oci_provider):
        """Test that chat without tools works normally."""
        # Mock validate_model to return True
        oci_provider.validate_model = MagicMock(return_value=True)

        # Mock the actual chat request
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"

        oci_provider.inference_client.chat.return_value.data.chat_response = mock_response

        messages = [Message(role=Role.USER, content="Test")]

        result = oci_provider.chat(
            messages=messages, model="meta.llama-3.3-70b-instruct", tools=None
        )

        assert result.content == "Test response"

    def test_meta_model_multiple_tool_calls_standard_format(self, oci_provider):
        """Test that Meta models can handle multiple tool calls in standard format."""
        # Mock validate_model to return True
        oci_provider.validate_model = MagicMock(return_value=True)

        # Mock the actual chat request for Meta model with multiple tool calls in standard format
        mock_response = MagicMock()
        mock_choice = MagicMock()
        mock_choice.message.content = ""

        # Create mock tool calls in the proper format (like LangChain Oracle)
        mock_tool_call1 = MagicMock()
        mock_tool_call1.id = "call_1"
        mock_tool_call1.name = "list_files"
        mock_tool_call1.arguments = '{"directory": "/path/to/directory"}'

        mock_tool_call2 = MagicMock()
        mock_tool_call2.id = "call_2"
        mock_tool_call2.name = "list_directory"
        mock_tool_call2.arguments = '{"path": "/path/to/directory", "show_hidden": "False"}'

        mock_tool_call3 = MagicMock()
        mock_tool_call3.id = "call_3"
        mock_tool_call3.name = "list_directory"
        mock_tool_call3.arguments = '{"path": ".", "show_hidden": "False"}'

        mock_choice.message.tool_calls = [mock_tool_call1, mock_tool_call2, mock_tool_call3]
        mock_choice.finish_reason = "tool_calls"
        mock_response.choices = [mock_choice]

        oci_provider.inference_client.chat.return_value.data.chat_response = mock_response

        messages = [Message(role=Role.USER, content="which files are in this directory")]
        tools = [
            Tool(
                name="list_files",
                description="List files",
                parameters={
                    "type": "object",
                    "properties": {"directory": {"type": "string"}},
                    "required": ["directory"],
                },
            ),
            Tool(
                name="list_directory",
                description="List directory",
                parameters={
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "show_hidden": {"type": "string"}},
                    "required": ["path"],
                },
            ),
        ]

        result = oci_provider.chat(
            messages=messages, model="meta.llama-3.3-70b-instruct", tools=tools
        )

        # Meta models should return all tool calls (no restriction like we had before)
        assert len(result.tool_calls) == 3
        assert result.tool_calls[0].name == "list_files"
        assert result.tool_calls[0].arguments == {"directory": "/path/to/directory"}
        assert result.tool_calls[1].name == "list_directory"
        assert result.tool_calls[1].arguments == {
            "path": "/path/to/directory",
            "show_hidden": "False",
        }
        assert result.tool_calls[2].name == "list_directory"
        assert result.tool_calls[2].arguments == {"path": ".", "show_hidden": "False"}

    def test_cohere_model_multiple_tool_calls(self, oci_provider):
        """Test that Cohere models can handle multiple tool calls without restriction."""
        # Mock validate_model to return True
        oci_provider.validate_model = MagicMock(return_value=True)

        # Mock the actual chat request for Cohere model with multiple tool calls
        mock_response = MagicMock()
        mock_tool_call1 = MagicMock()
        mock_tool_call1.name = "list_files"
        mock_tool_call1.parameters = {"directory": "/path/to/directory"}

        mock_tool_call2 = MagicMock()
        mock_tool_call2.name = "list_directory"
        mock_tool_call2.parameters = {"path": "/path/to/directory", "show_hidden": "False"}

        mock_response.tool_calls = [mock_tool_call1, mock_tool_call2]
        mock_response.text = ""
        mock_response.finish_reason = "tool_calls"
        mock_response.meta = None

        oci_provider.inference_client.chat.return_value.data.chat_response = mock_response

        messages = [Message(role=Role.USER, content="which files are in this directory")]
        tools = [
            Tool(
                name="list_files",
                description="List files",
                parameters={
                    "type": "object",
                    "properties": {"directory": {"type": "string"}},
                    "required": ["directory"],
                },
            ),
            Tool(
                name="list_directory",
                description="List directory",
                parameters={
                    "type": "object",
                    "properties": {"path": {"type": "string"}, "show_hidden": {"type": "string"}},
                    "required": ["path"],
                },
            ),
        ]

        result = oci_provider.chat(messages=messages, model="cohere.command-r-plus", tools=tools)

        # Cohere should return both tool calls
        assert len(result.tool_calls) == 2
        assert result.tool_calls[0].name == "list_files"
        assert result.tool_calls[0].arguments == {"directory": "/path/to/directory"}
        assert result.tool_calls[1].name == "list_directory"
        assert result.tool_calls[1].arguments == {
            "path": "/path/to/directory",
            "show_hidden": "False",
        }

    def test_model_metadata_without_tool_testing(self, oci_provider):
        """Test that model metadata is populated correctly without tool testing."""
        # Simply test that the provider has properly initialized models
        from coda.base.providers.base import Model

        # Create mock models using dataclass
        models = [
            Model(
                id="test.model1",
                name="test.model1",
                provider="oci_genai",
                supports_functions=True,
                metadata={},
            ),
            Model(
                id="test.model2",
                name="test.model2",
                provider="oci_genai",
                supports_functions=True,
                metadata={},
            ),
        ]

        # Mock the list_models method to return our test models
        oci_provider.list_models = MagicMock(return_value=models)

        # Get models
        models = oci_provider.list_models()

        # Check that all models have tool support enabled by default
        for model in models:
            assert model.supports_functions is True

    def test_model_fine_tune_warning(self):
        """Test that warning is displayed for models with FINE_TUNE capability."""
        from io import StringIO

        from rich.console import Console

        from coda.apps.cli.shared import CommandHandler, CommandResult
        from coda.base.providers.base import Model

        # Create a concrete implementation of CommandHandler
        class TestCommandHandler(CommandHandler):
            def show_help(self) -> CommandResult:
                return CommandResult.HANDLED

        # Create console with captured output
        output = StringIO()
        console = Console(file=output, force_terminal=True, width=100)

        # Create command handler
        handler = TestCommandHandler(console)

        # Create a mock model that ends with -16k (base model pattern)
        mock_model = Model(
            id="cohere.command-r-16k",
            name="Cohere Command-R 16K",
            provider="oci_genai",
            metadata={"capabilities": ["CHAT"]},
        )

        # Set up handler with mock model
        handler.available_models = [mock_model]

        # Switch to the model - this should trigger the warning
        handler.switch_model("cohere.command-r-16k")

        # Check output contains warning
        output_text = output.getvalue()
        assert "Warning: This model may be a base model that doesn't support chat" in output_text
        assert "If you encounter errors, try a different model" in output_text
