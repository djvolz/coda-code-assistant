"""Unit tests for OCI provider tool support functionality."""

from unittest.mock import MagicMock, patch

import pytest

from coda.base.providers.base import Message, Role, Tool
from coda.base.providers.oci_genai import OCIGenAIProvider


@pytest.fixture
def mock_oci_config():
    """Mock OCI configuration."""
    with patch('coda.base.providers.oci_genai.oci.config') as mock_config:
        mock_config.load_config.return_value = {
            "compartment_id": "test-compartment-id"
        }
        yield mock_config


@pytest.fixture
def mock_clients():
    """Mock OCI clients."""
    with patch('coda.base.providers.oci_genai.GenerativeAiInferenceClient') as mock_inference:
        with patch('coda.base.providers.oci_genai.GenerativeAiClient') as mock_genai:
            yield mock_inference, mock_genai


@pytest.fixture
def oci_provider(mock_oci_config, mock_clients):
    """Create an OCI provider with mocked dependencies."""
    with patch.object(OCIGenAIProvider, '_initialize_models'):
        provider = OCIGenAIProvider()
        # Mock the tool tester
        provider._tool_tester = MagicMock()
        return provider


class TestOCIProviderToolSupport:
    """Test OCI provider tool support functionality."""
    
    def test_chat_with_tools_not_supported(self, oci_provider):
        """Test chat method when model doesn't support tools."""
        # Configure tool tester to indicate no support
        oci_provider._tool_tester.get_tool_support.return_value = {
            "tested": True,
            "tools_work": False,
            "error": "fine-tuning base model"
        }
        
        messages = [Message(role=Role.USER, content="Test")]
        tools = [Tool(
            name="test_tool",
            description="Test tool",
            parameters={"type": "object", "properties": {}, "required": []}
        )]
        
        with pytest.raises(ValueError) as exc_info:
            oci_provider.chat(
                messages=messages,
                model="meta.llama-3.3-70b-instruct",
                tools=tools
            )
        
        assert "does not support tool/function calling" in str(exc_info.value)
        assert "fine-tuning base model" in str(exc_info.value)
    
    def test_chat_with_tools_supported(self, oci_provider):
        """Test chat method when model supports tools."""
        # Configure tool tester to indicate support
        oci_provider._tool_tester.get_tool_support.return_value = {
            "tested": True,
            "tools_work": True,
            "streaming_tools": False
        }
        
        # Mock the actual chat request
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        
        oci_provider.inference_client.chat.return_value.data.chat_response = mock_response
        
        messages = [Message(role=Role.USER, content="Test")]
        tools = [Tool(
            name="test_tool",
            description="Test tool",
            parameters={"type": "object", "properties": {}, "required": []}
        )]
        
        # Should not raise an error
        result = oci_provider.chat(
            messages=messages,
            model="cohere.command-r-plus",
            tools=tools
        )
        
        assert result.content == "Test response"
    
    def test_chat_stream_with_tools_not_supported(self, oci_provider):
        """Test chat_stream method when model doesn't support tools."""
        # Configure tool tester to indicate no support
        oci_provider._tool_tester.get_tool_support.return_value = {
            "tested": True,
            "tools_work": False,
            "error": "model not found (404)"
        }
        
        messages = [Message(role=Role.USER, content="Test")]
        tools = [Tool(
            name="test_tool",
            description="Test tool",
            parameters={"type": "object", "properties": {}, "required": []}
        )]
        
        with pytest.raises(ValueError) as exc_info:
            list(oci_provider.chat_stream(
                messages=messages,
                model="meta.llama-3.2-11b-vision-instruct",
                tools=tools
            ))
        
        assert "does not support tool/function calling" in str(exc_info.value)
        assert "model not found (404)" in str(exc_info.value)
    
    def test_chat_stream_with_tools_partial_support(self, oci_provider, caplog):
        """Test chat_stream with model that supports tools but not in streaming."""
        # Configure tool tester to indicate partial support
        oci_provider._tool_tester.get_tool_support.return_value = {
            "tested": True,
            "tools_work": True,
            "streaming_tools": False
        }
        
        # Mock the streaming response
        mock_event = MagicMock()
        mock_event.data = '{"text": "Test response"}'
        
        mock_stream = MagicMock()
        mock_stream.data.events.return_value = [mock_event]
        
        oci_provider.inference_client.chat.return_value = mock_stream
        
        messages = [Message(role=Role.USER, content="Test")]
        tools = [Tool(
            name="test_tool",
            description="Test tool",
            parameters={"type": "object", "properties": {}, "required": []}
        )]
        
        # Should log warning but not raise error
        list(oci_provider.chat_stream(
            messages=messages,
            model="cohere.command-r-plus",
            tools=tools
        ))
        
        # Check warning was logged
        assert any("supports tools but not in streaming mode" in record.message 
                  for record in caplog.records)
    
    def test_get_tool_tester_lazy_loading(self, oci_provider):
        """Test that tool tester is lazy loaded and prepopulated."""
        # Reset the tool tester
        oci_provider._tool_tester = None
        
        with patch('coda.base.providers.oci_genai.OCIToolTester') as mock_tester_class:
            mock_tester = MagicMock()
            mock_tester_class.return_value = mock_tester
            
            # First call should create the tester
            tester1 = oci_provider._get_tool_tester()
            
            assert tester1 is mock_tester
            mock_tester.prepopulate_known_results.assert_called_once()
            
            # Second call should return the same instance
            tester2 = oci_provider._get_tool_tester()
            assert tester2 is tester1
            
            # Prepopulate should only be called once
            assert mock_tester.prepopulate_known_results.call_count == 1
    
    def test_chat_without_tools(self, oci_provider):
        """Test that chat without tools doesn't check tool support."""
        # Mock the actual chat request
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = "Test response"
        mock_response.choices[0].finish_reason = "stop"
        
        oci_provider.inference_client.chat.return_value.data.chat_response = mock_response
        
        messages = [Message(role=Role.USER, content="Test")]
        
        # Should not check tool support when no tools provided
        result = oci_provider.chat(
            messages=messages,
            model="meta.llama-3.3-70b-instruct",
            tools=None
        )
        
        assert result.content == "Test response"
        # Tool tester should not have been called
        oci_provider._tool_tester.get_tool_support.assert_not_called()
    
    def test_model_metadata_tool_support(self, oci_provider):
        """Test that model metadata includes tool support information."""
        # Mock list_models to return test models
        test_models = [
            MagicMock(
                id="test.model1",
                display_name="Test Model 1",
                provider="test",
                version="1.0",
                time_created="2025-01-01",
                lifecycle_state="ACTIVE",
                capabilities=["text-generation"],
                is_long_term_supported=True,
                lifecycle_details=None,
                vendor="test"
            ),
            MagicMock(
                id="test.model2",
                display_name="Test Model 2",
                provider="test",
                version="1.0",
                time_created="2025-01-01",
                lifecycle_state="ACTIVE",
                capabilities=["text-generation"],
                is_long_term_supported=True,
                lifecycle_details=None,
                vendor="test"
            )
        ]
        
        oci_provider.genai_client.list_models.return_value.data = test_models
        
        # Configure tool support for models
        def mock_tool_support(model_id, provider=None):
            if model_id == "test.model1":
                return {
                    "tested": True,
                    "tools_work": True,
                    "streaming_tools": False
                }
            else:
                return {
                    "tested": True,
                    "tools_work": False,
                    "error": "not supported"
                }
        
        oci_provider._tool_tester.get_tool_support.side_effect = mock_tool_support
        
        # Get models
        models = oci_provider.list_models()
        
        # Check that tool support info is in metadata
        model1 = next(m for m in models if m.id == "test.model1")
        assert model1.supports_functions is True
        assert "non-streaming only" in model1.metadata["tool_support_notes"][0]
        
        model2 = next(m for m in models if m.id == "test.model2")
        assert model2.supports_functions is False
        assert "error: not supported" in model2.metadata["tool_support_notes"][0]