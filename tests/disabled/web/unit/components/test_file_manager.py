"""Unit tests for the file manager component."""

from unittest.mock import MagicMock, Mock, patch

import pytest

from coda.web.components.file_manager import (
    create_file_context_prompt,
    download_chat_history,
    download_session_data,
    format_file_size,
    generate_markdown_history,
    get_language_from_filename,
    is_text_file,
    render_file_download_section,
    render_file_upload_widget,
)


class TestFileManager:
    """Test suite for file manager functionality."""

    @pytest.fixture
    def mock_uploaded_file(self):
        """Create a mock uploaded file."""
        file = Mock()
        file.name = "test_document.txt"
        file.size = 1024  # 1KB
        file.type = "text/plain"
        file.read = Mock(return_value=b"This is test file content")
        file.seek = Mock()
        return file

    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit components."""
        with patch("coda.web.components.file_manager.st") as mock_st:
            # Setup expander context manager
            mock_expander_context = MagicMock()
            mock_expander_context.__enter__ = Mock(return_value=mock_expander_context)
            mock_expander_context.__exit__ = Mock(return_value=None)

            # Set up all attributes
            mock_st.file_uploader = Mock(return_value=None)
            mock_st.button = Mock(return_value=False)
            # Create mock columns that support context manager protocol
            mock_col1 = Mock()
            mock_col1.__enter__ = Mock(return_value=mock_col1)
            mock_col1.__exit__ = Mock(return_value=None)
            mock_col2 = Mock()
            mock_col2.__enter__ = Mock(return_value=mock_col2)
            mock_col2.__exit__ = Mock(return_value=None)
            mock_col3 = Mock()
            mock_col3.__enter__ = Mock(return_value=mock_col3)
            mock_col3.__exit__ = Mock(return_value=None)

            # Different return values for different column calls
            def columns_side_effect(arg):
                if arg == 2:
                    return [mock_col1, mock_col2]
                else:
                    return [mock_col1, mock_col2, mock_col3]

            mock_st.columns = Mock(side_effect=columns_side_effect)
            mock_st.expander = Mock(return_value=mock_expander_context)
            mock_st.write = Mock()
            mock_st.code = Mock()
            mock_st.success = Mock()
            mock_st.error = Mock()
            mock_st.warning = Mock()
            mock_st.download_button = Mock()
            mock_st.subheader = Mock()
            mock_st.info = Mock()

            yield mock_st

    @pytest.fixture
    def mock_state_value(self):
        """Mock get_state_value function."""
        with patch("coda.web.components.file_manager.get_state_value") as mock:
            yield mock

    def test_render_file_upload_widget_no_files(self, mock_streamlit):
        """Test rendering with no uploaded files."""
        mock_streamlit.file_uploader.return_value = None

        result = render_file_upload_widget()

        # Verify file uploader is rendered
        mock_streamlit.file_uploader.assert_called_once()
        assert result is None

    def test_render_file_upload_widget_single_file(self, mock_streamlit, mock_uploaded_file):
        """Test uploading a single file."""
        mock_streamlit.file_uploader.return_value = [mock_uploaded_file]

        result = render_file_upload_widget()

        # Verify success message
        mock_streamlit.success.assert_called_once_with("Uploaded 1 file(s)")

        # Verify result
        assert result is not None
        assert len(result) == 1
        assert result[0]["name"] == "test_document.txt"
        assert result[0]["size"] == 1024
        assert result[0]["type"] == "text/plain"
        assert result[0]["content"] == b"This is test file content"

    def test_render_file_upload_widget_multiple_files(self, mock_streamlit):
        """Test uploading multiple files."""
        files = []
        for i in range(3):
            file = Mock()
            file.name = f"file_{i}.txt"
            file.size = 1024 * (i + 1)
            file.type = "text/plain"
            file.read = Mock(return_value=f"Content {i}".encode())
            files.append(file)

        mock_streamlit.file_uploader.return_value = files

        result = render_file_upload_widget()

        # Verify success message
        mock_streamlit.success.assert_called_once_with("Uploaded 3 file(s)")

        # Verify result
        assert len(result) == 3
        for i, file_data in enumerate(result):
            assert file_data["name"] == f"file_{i}.txt"
            assert file_data["size"] == 1024 * (i + 1)

    def test_render_file_upload_widget_text_file_preview(self, mock_streamlit, mock_uploaded_file):
        """Test text file preview."""
        mock_streamlit.file_uploader.return_value = [mock_uploaded_file]

        render_file_upload_widget()

        # Verify code preview was called
        mock_streamlit.code.assert_called()

    def test_render_file_upload_widget_binary_file(self, mock_streamlit):
        """Test binary file handling."""
        binary_file = Mock()
        binary_file.name = "image.jpg"
        binary_file.size = 2048
        binary_file.type = "image/jpeg"
        binary_file.read = Mock(return_value=b"\xff\xd8\xff\xe0")  # JPEG header

        mock_streamlit.file_uploader.return_value = [binary_file]

        result = render_file_upload_widget()

        assert result is not None
        assert result[0]["type"] == "image/jpeg"

    def test_render_file_download_section(self, mock_streamlit):
        """Test download section rendering."""
        render_file_download_section()

        # Verify subheader and buttons
        mock_streamlit.subheader.assert_called_once_with("💾 Download Options")
        assert mock_streamlit.button.call_count == 2

    def test_download_chat_history_empty(self, mock_streamlit, mock_state_value):
        """Test downloading empty chat history."""
        mock_state_value.return_value = []

        download_chat_history()

        mock_streamlit.warning.assert_called_once_with("No chat history to download")

    def test_download_chat_history_with_messages(self, mock_streamlit, mock_state_value):
        """Test downloading chat history with messages."""
        messages = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        mock_state_value.return_value = messages

        download_chat_history()

        # Verify download buttons were created
        assert mock_streamlit.download_button.call_count == 2

        # Check markdown download
        markdown_call = mock_streamlit.download_button.call_args_list[0]
        assert markdown_call[1]["label"] == "Download as Markdown"
        assert markdown_call[1]["mime"] == "text/markdown"

        # Check JSON download
        json_call = mock_streamlit.download_button.call_args_list[1]
        assert json_call[1]["label"] == "Download as JSON"
        assert json_call[1]["mime"] == "application/json"

    def test_download_session_data(self, mock_streamlit, mock_state_value):
        """Test downloading session data."""
        # Create mock session and messages
        mock_session = Mock()
        mock_session.id = "session-123"
        mock_session.name = "Test Session"
        mock_session.provider = "openai"
        mock_session.model = "gpt-4"
        mock_session.created_at = Mock(isoformat=Mock(return_value="2024-01-01T00:00:00"))
        mock_session.updated_at = Mock(isoformat=Mock(return_value="2024-01-01T00:01:00"))

        mock_message = Mock()
        mock_message.id = "msg-1"
        mock_message.role = "user"
        mock_message.content = "Test"
        mock_message.timestamp = Mock(isoformat=Mock(return_value="2024-01-01T00:00:30"))

        mock_session_manager = Mock()
        mock_session_manager.get_active_sessions.return_value = [mock_session]
        mock_session_manager.get_messages.return_value = [mock_message]

        mock_state_value.side_effect = lambda key, default=None: {
            "session_manager": mock_session_manager
        }.get(key, default)

        download_session_data()

        # Verify download button was called
        mock_streamlit.download_button.assert_called_once()
        download_call = mock_streamlit.download_button.call_args
        assert download_call[1]["label"] == "Download All Sessions"
        assert download_call[1]["mime"] == "application/json"

    def test_generate_markdown_history(self):
        """Test markdown history generation."""
        messages = [
            {"role": "user", "content": "What is Python?", "timestamp": "2024-01-01T10:00:00"},
            {
                "role": "assistant",
                "content": "Python is a programming language.",
                "timestamp": "2024-01-01T10:00:30",
            },
        ]

        result = generate_markdown_history(messages)

        assert "# Chat History" in result
        assert "What is Python?" in result
        assert "Python is a programming language." in result
        assert "User" in result
        assert "Assistant" in result

    def test_format_file_size(self):
        """Test file size formatting."""
        # Import format_file_size directly from the module

        assert format_file_size(500) == "500.0 B"
        assert format_file_size(1024) == "1.0 KB"
        assert format_file_size(1024 * 1024) == "1.0 MB"
        assert format_file_size(1024 * 1024 * 1024) == "1.0 GB"

    def test_is_text_file(self):
        """Test text file detection."""
        assert is_text_file("text/plain")
        assert is_text_file("text/html")
        assert is_text_file("application/json")
        assert is_text_file("application/javascript")
        assert not is_text_file("image/jpeg")
        assert not is_text_file("video/mp4")

    def test_get_language_from_filename(self):
        """Test language detection from filename."""
        assert get_language_from_filename("script.py") == "python"
        assert get_language_from_filename("code.js") == "javascript"
        assert get_language_from_filename("styles.css") == "css"
        assert get_language_from_filename("page.html") == "html"
        assert get_language_from_filename("data.json") == "json"
        assert get_language_from_filename("notes.txt") == "text"

    def test_create_file_context_prompt(self):
        """Test file context prompt generation."""
        files_data = [
            {"name": "script.py", "type": "text/plain", "content": b"print('hello')", "size": 14},
            {
                "name": "data.json",
                "type": "application/json",
                "content": b'{"key": "value"}',
                "size": 16,
            },
        ]

        result = create_file_context_prompt(files_data)

        assert "Here are the files you uploaded:" in result
        assert "script.py" in result
        assert "data.json" in result
        assert "print('hello')" in result
        assert '{"key": "value"}' in result

    def test_create_file_context_prompt_with_binary(self):
        """Test file context with binary files."""
        files_data = [
            {"name": "image.jpg", "type": "image/jpeg", "content": b"\xff\xd8\xff\xe0", "size": 4},
            {"name": "text.txt", "type": "text/plain", "content": b"Text content", "size": 12},
        ]

        result = create_file_context_prompt(files_data)

        assert "image.jpg" in result
        assert "[Binary file - cannot display]" in result
        assert "Text content" in result

    def test_render_file_upload_widget_unicode_error(self, mock_streamlit):
        """Test handling of Unicode decode errors."""
        file = Mock()
        file.name = "bad_encoding.txt"
        file.size = 100
        file.type = "text/plain"
        file.read = Mock(return_value=b"\xff\xfe\x00\x00")  # Invalid UTF-8

        mock_streamlit.file_uploader.return_value = [file]

        result = render_file_upload_widget()

        # Should still return the file data
        assert result is not None
        assert len(result) == 1

        # Should show warning for preview
        mock_streamlit.warning.assert_called_with("Cannot preview binary file")
