"""Unit tests for the chat widget component."""

import os
import sys
from unittest.mock import Mock, patch

import pytest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, project_root)

from coda.web.components.chat_widget import render_chat_interface, render_message_with_code


class TestChatWidget:
    """Test suite for chat widget component."""

    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit for this specific module."""
        with patch("coda.web.components.chat_widget.st") as mock_st:
            # Create a mock session state that behaves like a dict but also has attributes
            class MockSessionState(dict):
                def __setattr__(self, key, value):
                    self[key] = value

                def __getattr__(self, key):
                    return self.get(key)

            mock_st.session_state = MockSessionState()
            mock_st.chat_input = Mock(return_value=None)

            # Mock container as context manager
            mock_container = Mock()
            mock_container.__enter__ = Mock(return_value=mock_container)
            mock_container.__exit__ = Mock(return_value=None)
            mock_st.container = Mock(return_value=mock_container)

            mock_st.chat_message = Mock()
            mock_st.markdown = Mock()
            mock_st.code = Mock()
            mock_st.spinner = Mock()
            yield mock_st

    @pytest.mark.unit
    def test_render_message_with_code_simple(self, mock_streamlit):
        """Test rendering message with code blocks."""
        content = "Here's the code:\n```python\nprint('Hello')\n```"

        render_message_with_code(content)

        # Should handle code blocks
        assert mock_streamlit.markdown.called or mock_streamlit.code.called

    @pytest.mark.unit
    def test_render_message_with_code_multiple(self, mock_streamlit):
        """Test rendering message with multiple code blocks."""
        content = "First:\n```python\ncode1\n```\nSecond:\n```js\ncode2\n```"

        render_message_with_code(content)

        # Should call code multiple times
        assert mock_streamlit.code.call_count >= 2

    @pytest.mark.unit
    def test_render_chat_interface_empty(self, mock_streamlit):
        """Test rendering empty chat interface."""
        mock_streamlit.session_state = {"messages": []}
        mock_streamlit.chat_input.return_value = None

        render_chat_interface("openai", "gpt-4")

        # Should create container and chat input
        mock_streamlit.container.assert_called_once()
        mock_streamlit.chat_input.assert_called_once()

    @pytest.mark.unit
    def test_render_chat_interface_with_messages(self, mock_streamlit):
        """Test rendering chat interface with messages."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        mock_streamlit.session_state = {"messages": messages}
        mock_streamlit.chat_input.return_value = None

        # Mock chat_message context manager
        mock_chat_message = Mock()
        mock_chat_message.__enter__ = Mock(return_value=Mock())
        mock_chat_message.__exit__ = Mock(return_value=None)
        mock_streamlit.chat_message.return_value = mock_chat_message

        render_chat_interface("openai", "gpt-4")

        # Should render all messages
        assert mock_streamlit.chat_message.call_count == 2

    @pytest.mark.unit
    def test_render_chat_interface_with_input(self, mock_streamlit):
        """Test rendering chat interface with user input."""
        # Use the MockSessionState class
        mock_streamlit.session_state["messages"] = []
        mock_streamlit.session_state["uploaded_files"] = []
        mock_streamlit.chat_input.return_value = "Test message"

        # Mock chat_message context manager
        mock_chat_message = Mock()
        mock_chat_message.__enter__ = Mock(return_value=Mock())
        mock_chat_message.__exit__ = Mock(return_value=None)
        mock_streamlit.chat_message.return_value = mock_chat_message

        # Mock spinner context manager
        mock_spinner = Mock()
        mock_spinner.__enter__ = Mock(return_value=Mock())
        mock_spinner.__exit__ = Mock(return_value=None)
        mock_streamlit.spinner.return_value = mock_spinner

        # Mock the AI response function
        with patch("coda.web.components.chat_widget.get_ai_response", return_value="Test response"):
            render_chat_interface("openai", "gpt-4")

        # Should add message to session state
        assert len(mock_streamlit.session_state["messages"]) > 0

    @pytest.mark.unit
    def test_render_message_with_code_no_language(self, mock_streamlit):
        """Test rendering code block without language specification."""
        content = "Code:\n```\nprint('test')\n```"

        render_message_with_code(content)

        # Should still render code block
        mock_streamlit.code.assert_called()

    @pytest.mark.unit
    def test_render_chat_interface_with_files(self, mock_streamlit):
        """Test chat interface with uploaded files."""
        # Use the MockSessionState class
        mock_streamlit.session_state["messages"] = []
        mock_streamlit.session_state["uploaded_files"] = [
            {"name": "test.py", "content": "print('hello')"}
        ]
        mock_streamlit.chat_input.return_value = "Analyze this file"

        # Mock context managers
        mock_chat_message = Mock()
        mock_chat_message.__enter__ = Mock(return_value=Mock())
        mock_chat_message.__exit__ = Mock(return_value=None)
        mock_streamlit.chat_message.return_value = mock_chat_message

        mock_spinner = Mock()
        mock_spinner.__enter__ = Mock(return_value=Mock())
        mock_spinner.__exit__ = Mock(return_value=None)
        mock_streamlit.spinner.return_value = mock_spinner

        with patch(
            "coda.web.components.file_manager.create_file_context_prompt",
            return_value="File context: ",
        ):
            with patch(
                "coda.web.components.chat_widget.get_ai_response", return_value="File analyzed"
            ):
                render_chat_interface("openai", "gpt-4")

        # Should clear uploaded files after use
        assert mock_streamlit.session_state["uploaded_files"] == []
