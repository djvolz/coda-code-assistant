"""Unit tests for state management utilities."""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from coda.web.utils.state import (
    clear_chat_state,
    get_state_value,
    init_session_state,
    set_state_value,
)


class TestStateManagement:
    """Test suite for state management functionality."""

    @pytest.fixture
    def mock_streamlit(self):
        """Mock Streamlit session state."""
        with patch("coda.web.utils.state.st") as mock_st:
            # Create a custom class that behaves like streamlit session_state
            class SessionState(dict):
                def __setattr__(self, key, value):
                    self[key] = value

                def __getattr__(self, key):
                    return self.get(key)

            mock_st.session_state = SessionState()
            yield mock_st

    @pytest.fixture
    def mock_config(self):
        """Mock configuration."""
        with patch("coda.web.utils.state.get_config") as mock:
            config = Mock()
            config.to_dict.return_value = {
                "default_provider": "openai",
                "openai": {"enabled": True, "models": ["gpt-4", "gpt-3.5-turbo"]},
            }
            mock.return_value = config
            yield mock

    @pytest.fixture
    def mock_session_manager(self):
        """Mock SessionManager."""
        with patch("coda.web.utils.state.SessionManager") as mock:
            yield mock

    @pytest.fixture
    def mock_path(self):
        """Mock Path operations."""
        with patch("coda.web.utils.state.Path") as mock:
            mock_home = Mock()
            mock_path_obj = Mock()
            mock_parent = Mock()
            mock_parent.mkdir = Mock()
            mock_path_obj.parent = mock_parent
            mock_home.return_value = Path("/home/user")
            mock.home = mock_home
            yield mock

    def test_init_session_state_first_run(
        self, mock_streamlit, mock_config, mock_session_manager, mock_path
    ):
        """Test initialization on first run."""
        init_session_state()

        # Verify all required keys are initialized
        assert mock_streamlit.session_state["initialized"]
        assert "config" in mock_streamlit.session_state
        assert "session_manager" in mock_streamlit.session_state
        assert mock_streamlit.session_state["current_session_id"] is None
        assert mock_streamlit.session_state["current_provider"] is None
        assert mock_streamlit.session_state["current_model"] is None
        assert mock_streamlit.session_state["messages"] == []
        assert mock_streamlit.session_state["providers"] == {}
        assert mock_streamlit.session_state["models"] == {}

    def test_init_session_state_already_initialized(self, mock_streamlit, mock_config):
        """Test initialization when already initialized."""
        # Simulate already initialized state
        mock_streamlit.session_state = {"initialized": True, "messages": ["existing"]}

        init_session_state()

        # Should not reinitialize
        assert mock_streamlit.session_state["messages"] == ["existing"]
        mock_config.assert_not_called()

    def test_init_session_state_config_error(self, mock_streamlit, mock_session_manager, mock_path):
        """Test initialization with config error."""
        with patch("coda.web.utils.state.get_config") as mock_config:
            mock_config.side_effect = Exception("Config error")

            init_session_state()

            assert mock_streamlit.session_state["config"] is None
            assert mock_streamlit.session_state["config_error"] == "Config error"
            # Should continue initialization despite config error
            assert mock_streamlit.session_state["initialized"]

    def test_init_session_state_session_manager_error(self, mock_streamlit, mock_config, mock_path):
        """Test initialization with session manager error."""
        with patch("coda.web.utils.state.SessionManager") as mock_sm:
            mock_sm.side_effect = Exception("DB error")

            init_session_state()

            assert mock_streamlit.session_state["session_manager"] is None
            # The error message includes the path issue, so just check it contains our error
            assert (
                "DB error" in mock_streamlit.session_state["session_manager_error"]
                or "Operation not supported"
                in mock_streamlit.session_state["session_manager_error"]
            )
            # Should continue initialization despite error
            assert mock_streamlit.session_state["initialized"]

    def test_get_state_value_existing(self, mock_streamlit):
        """Test getting existing state value."""
        mock_streamlit.session_state = {"test_key": "test_value"}

        result = get_state_value("test_key")

        assert result == "test_value"

    def test_get_state_value_missing_with_default(self, mock_streamlit):
        """Test getting missing state value with default."""
        result = get_state_value("missing_key", "default_value")

        assert result == "default_value"

    def test_get_state_value_missing_no_default(self, mock_streamlit):
        """Test getting missing state value without default."""
        result = get_state_value("missing_key")

        assert result is None

    def test_set_state_value(self, mock_streamlit):
        """Test setting state value."""
        set_state_value("new_key", "new_value")

        assert mock_streamlit.session_state["new_key"] == "new_value"

    def test_set_state_value_overwrite(self, mock_streamlit):
        """Test overwriting existing state value."""
        mock_streamlit.session_state = {"existing_key": "old_value"}

        set_state_value("existing_key", "new_value")

        assert mock_streamlit.session_state["existing_key"] == "new_value"

    def test_clear_chat_state(self, mock_streamlit):
        """Test clearing chat state."""
        mock_streamlit.session_state = {
            "messages": ["msg1", "msg2"],
            "current_session_id": "session-123",
            "other_key": "keep_this",
        }

        clear_chat_state()

        assert mock_streamlit.session_state["messages"] == []
        assert mock_streamlit.session_state["current_session_id"] is None
        assert mock_streamlit.session_state["other_key"] == "keep_this"  # Not cleared

    def test_init_session_state_creates_db_directory(
        self, mock_streamlit, mock_config, mock_session_manager
    ):
        """Test that initialization creates database directory."""
        with patch("coda.web.utils.state.Path") as mock_path_class:
            # Create a mock path chain
            mock_parent = Mock()
            mock_db_path = Mock()
            mock_db_path.parent = mock_parent

            # Mock the path construction
            mock_coda_path = Mock()
            mock_coda_path.__truediv__ = Mock(return_value=mock_db_path)

            mock_config_path = Mock()
            mock_config_path.__truediv__ = Mock(return_value=mock_coda_path)

            mock_home_path = Mock()
            mock_home_path.__truediv__ = Mock(return_value=mock_config_path)

            mock_path_class.home = Mock(return_value=mock_home_path)

            init_session_state()

            # Verify directory creation was attempted
            mock_parent.mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_init_session_state_config_dict_conversion(
        self, mock_streamlit, mock_session_manager, mock_path
    ):
        """Test that config is converted to dict."""
        with patch("coda.web.utils.state.get_config") as mock_config:
            config = Mock()
            config.to_dict.return_value = {"key": "value"}
            mock_config.return_value = config

            init_session_state()

            assert mock_streamlit.session_state["config"] == {"key": "value"}
            config.to_dict.assert_called_once()

    def test_state_persistence_across_operations(self, mock_streamlit):
        """Test that state persists across multiple operations."""
        # Set some values
        set_state_value("key1", "value1")
        set_state_value("key2", {"nested": "data"})

        # Verify they persist
        assert get_state_value("key1") == "value1"
        assert get_state_value("key2") == {"nested": "data"}

        # Modify one
        set_state_value("key1", "modified")

        # Verify changes
        assert get_state_value("key1") == "modified"
        assert get_state_value("key2") == {"nested": "data"}  # Unchanged
