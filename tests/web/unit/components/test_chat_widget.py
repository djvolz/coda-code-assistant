"""Unit tests for the chat widget component."""

import pytest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
import streamlit as st
from datetime import datetime
import asyncio

from coda.web.components.chat_widget import (
    render_chat_interface,
    render_message_with_code,
    get_ai_response,
    save_to_session
)


class TestChatWidget:
    """Test suite for chat widget functionality."""
    
    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit components."""
        with patch('coda.web.components.chat_widget.st') as mock_st:
            # Create a proper session_state mock
            mock_session_state = Mock()
            mock_session_state.get = Mock(return_value=[])
            
            # Set up all the st attributes
            mock_st.session_state = mock_session_state
            mock_st.container = Mock(return_value=Mock(__enter__=Mock(return_value=Mock()), __exit__=Mock()))
            mock_st.chat_message = Mock(return_value=Mock(__enter__=Mock(return_value=Mock()), __exit__=Mock()))
            mock_st.chat_input = Mock(return_value=None)
            mock_st.markdown = Mock()
            mock_st.code = Mock()
            mock_st.error = Mock()
            mock_st.spinner = Mock(return_value=Mock(__enter__=Mock(return_value=Mock()), __exit__=Mock()))
            
            yield mock_st
    
    @pytest.fixture
    def mock_state_utils(self):
        """Mock state utility functions."""
        with patch('coda.web.components.chat_widget.get_state_value') as mock_get, \
             patch('coda.web.components.chat_widget.set_state_value') as mock_set:
            yield mock_get, mock_set
    
    
    def test_render_chat_interface_empty(self, mock_streamlit):
        """Test rendering with no messages."""
        mock_streamlit.session_state.get.return_value = []
        mock_streamlit.chat_input.return_value = None
        
        render_chat_interface("openai", "gpt-4")
        
        # Verify container was created
        mock_streamlit.container.assert_called_once()
        # Verify chat input was rendered
        mock_streamlit.chat_input.assert_called_once_with("Type your message here...")
    
    def test_render_chat_interface_with_messages(self, mock_streamlit):
        """Test rendering with existing messages."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"}
        ]
        mock_streamlit.session_state.get.return_value = messages
        mock_streamlit.chat_input.return_value = None
        
        render_chat_interface("openai", "gpt-4")
        
        # Verify messages were rendered
        assert mock_streamlit.chat_message.call_count == 2
        assert mock_streamlit.markdown.call_count == 2
    
    def test_render_chat_interface_with_code(self, mock_streamlit):
        """Test rendering messages with code blocks."""
        messages = [
            {"role": "assistant", "content": "Here's code:\n```python\nprint('hello')\n```"}
        ]
        mock_streamlit.session_state.get.return_value = messages
        mock_streamlit.chat_input.return_value = None
        
        with patch('coda.web.components.chat_widget.render_message_with_code') as mock_render:
            render_chat_interface("openai", "gpt-4")
            mock_render.assert_called_once()
    
    def test_render_chat_interface_user_input(self, mock_streamlit, mock_state_utils):
        """Test handling user input."""
        mock_get, mock_set = mock_state_utils
        mock_get.return_value = {"providers": {"openai": {"api_key": "test"}}}
        
        initial_messages = []
        mock_streamlit.session_state.get.side_effect = lambda key, default: {
            "messages": initial_messages,
            "uploaded_files": []
        }.get(key, default)
        mock_streamlit.session_state.messages = initial_messages
        mock_streamlit.chat_input.return_value = "Test question"
        
        with patch('coda.web.components.chat_widget.get_ai_response', return_value="Test response"), \
             patch('coda.web.components.chat_widget.save_to_session'):
            render_chat_interface("openai", "gpt-4")
        
        # Verify user message was displayed
        assert any("user" in str(call) for call in mock_streamlit.chat_message.call_args_list)
        assert mock_streamlit.markdown.called
    
    def test_render_message_with_code_simple(self):
        """Test rendering a message with code blocks."""
        with patch('coda.web.components.chat_widget.st') as mock_st:
            content = "Here's code:\n```python\ndef hello():\n    print('world')\n```\nEnd of code."
            
            render_message_with_code(content)
            
            # Check markdown was called for text parts
            assert mock_st.markdown.call_count == 2
            # Check code was called for code block
            mock_st.code.assert_called_once()
            code_call = mock_st.code.call_args
            assert "def hello():" in code_call[0][0]
            assert code_call[1]['language'] == "python"
    
    def test_render_message_with_code_no_language(self):
        """Test rendering code block without language specification."""
        with patch('coda.web.components.chat_widget.st') as mock_st:
            content = "Code:\n```\nprint('test')\n```"
            
            render_message_with_code(content)
            
            mock_st.code.assert_called_once()
            assert mock_st.code.call_args[1]['language'] == "python"  # Default
    
    def test_render_message_with_code_multiple_blocks(self):
        """Test rendering multiple code blocks."""
        with patch('coda.web.components.chat_widget.st') as mock_st:
            content = "First:\n```python\ncode1\n```\nSecond:\n```javascript\ncode2\n```"
            
            render_message_with_code(content)
            
            assert mock_st.code.call_count == 2
            assert mock_st.markdown.call_count == 2
    
    def test_get_ai_response_success(self, mock_state_utils):
        """Test successful AI response."""
        mock_get, _ = mock_state_utils
        mock_get.return_value = {"providers": {"openai": {"api_key": "test"}}}
        
        messages = [{"role": "user", "content": "Hello"}]
        
        with patch('coda.web.components.chat_widget.ProviderFactory') as mock_factory_class:
            # Mock the provider
            mock_provider = Mock()
            mock_response = Mock()
            mock_response.content = "Test response"
            
            # Create a coroutine that returns the response
            async def mock_complete(*args, **kwargs):
                return mock_response
            
            mock_provider.complete = mock_complete
            
            # Mock the factory
            mock_factory = Mock()
            mock_factory.create.return_value = mock_provider
            mock_factory_class.return_value = mock_factory
            
            # Run the function
            response = get_ai_response("openai", "gpt-4", messages)
            
            assert response == "Test response"
    
    def test_get_ai_response_no_config(self, mock_state_utils):
        """Test AI response with no config."""
        mock_get, _ = mock_state_utils
        mock_get.return_value = None
        
        response = get_ai_response("openai", "gpt-4", [])
        
        assert response is None
    
    def test_get_ai_response_invalid_provider(self, mock_state_utils):
        """Test AI response with invalid provider."""
        mock_get, _ = mock_state_utils
        mock_get.return_value = {"openai": {}}
        
        with patch('coda.web.components.chat_widget.ProviderFactory') as mock_factory_class:
            mock_factory = Mock()
            mock_factory.create.side_effect = ValueError("Unknown provider")
            mock_factory_class.return_value = mock_factory
            
            with patch('coda.web.components.chat_widget.st.error') as mock_error:
                response = get_ai_response("invalid", "model", [])
                
                assert response is None
                mock_error.assert_called_once()
    
    def test_get_ai_response_exception(self, mock_state_utils):
        """Test AI response with exception."""
        mock_get, _ = mock_state_utils
        mock_get.return_value = {"providers": {"openai": {"api_key": "test"}}}
        
        with patch('coda.web.components.chat_widget.ProviderFactory') as mock_factory_class:
            mock_factory_class.side_effect = Exception("Test error")
            
            with patch('coda.web.components.chat_widget.st.error') as mock_error:
                response = get_ai_response("openai", "gpt-4", [])
                
                assert response is None
                mock_error.assert_called_once()
    
    def test_save_to_session_new_session(self, mock_state_utils):
        """Test saving to a new session."""
        mock_get, mock_set = mock_state_utils
        
        mock_session_manager = Mock()
        mock_session = Mock(id="session-123")
        mock_session_manager.create_session.return_value = mock_session
        
        mock_get.side_effect = lambda key: {
            "session_manager": mock_session_manager,
            "current_session_id": None
        }.get(key)
        
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"}
        ]
        
        save_to_session("openai", "gpt-4", messages)
        
        # Verify session was created
        mock_session_manager.create_session.assert_called_once()
        # Verify messages were added
        assert mock_session_manager.add_message.call_count == 2
        # Verify session ID was saved
        mock_set.assert_called_with("current_session_id", "session-123")
    
    def test_save_to_session_existing_session(self, mock_state_utils):
        """Test saving to an existing session."""
        mock_get, _ = mock_state_utils
        
        mock_session_manager = Mock()
        mock_get.side_effect = lambda key: {
            "session_manager": mock_session_manager,
            "current_session_id": "existing-session"
        }.get(key)
        
        messages = [
            {"role": "user", "content": "Previous message"},
            {"role": "assistant", "content": "Previous response"},
            {"role": "user", "content": "New message"},
            {"role": "assistant", "content": "New response"}
        ]
        
        save_to_session("openai", "gpt-4", messages)
        
        # Should not create new session
        mock_session_manager.create_session.assert_not_called()
        # Should add only the last two messages
        assert mock_session_manager.add_message.call_count == 2
    
    def test_save_to_session_no_manager(self, mock_state_utils):
        """Test saving when session manager is not available."""
        mock_get, _ = mock_state_utils
        mock_get.return_value = None
        
        # Should not raise error
        save_to_session("openai", "gpt-4", [])
    
    def test_save_to_session_exception(self, mock_state_utils):
        """Test saving with exception."""
        mock_get, _ = mock_state_utils
        
        mock_session_manager = Mock()
        mock_session_manager.create_session.side_effect = Exception("DB error")
        
        mock_get.side_effect = lambda key: {
            "session_manager": mock_session_manager,
            "current_session_id": None
        }.get(key)
        
        with patch('coda.web.components.chat_widget.st.error') as mock_error:
            save_to_session("openai", "gpt-4", [{"role": "user", "content": "Test"}])
            
            mock_error.assert_called_once()
            assert "Error saving to session" in str(mock_error.call_args)
    
    def test_render_chat_interface_with_uploaded_files(self, mock_streamlit, mock_state_utils):
        """Test handling uploaded files in chat."""
        mock_get, _ = mock_state_utils
        mock_get.return_value = {"providers": {"openai": {"api_key": "test"}}}
        
        uploaded_files = [{"name": "test.txt", "content": "file content"}]
        mock_streamlit.session_state.get.side_effect = lambda key, default: {
            "messages": [],
            "uploaded_files": uploaded_files
        }.get(key, default)
        mock_streamlit.session_state.uploaded_files = uploaded_files
        mock_streamlit.chat_input.return_value = "Analyze this file"
        
        # create_file_context_prompt is imported from file_manager in the actual code
        with patch('coda.web.components.file_manager.create_file_context_prompt', return_value="File context: "), \
             patch('coda.web.components.chat_widget.get_ai_response', return_value="Analysis complete"), \
             patch('coda.web.components.chat_widget.save_to_session'):
            render_chat_interface("openai", "gpt-4")
        
        # Verify uploaded files were cleared
        assert mock_streamlit.session_state.uploaded_files == []