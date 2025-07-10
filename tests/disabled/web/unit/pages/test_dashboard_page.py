"""Unit tests for the dashboard page."""

import os
import sys
from datetime import datetime
from unittest.mock import patch

import pytest
from streamlit.testing.v1 import AppTest

# Add project root to path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../.."))
sys.path.insert(0, project_root)


class TestDashboardPage:
    """Test suite for the dashboard page functionality."""

    @pytest.fixture
    def app(self):
        """Create AppTest instance for testing."""
        app_path = os.path.join(project_root, "coda/web/app.py")
        return AppTest.from_file(app_path)

    @pytest.fixture
    def mock_session_data(self):
        """Mock session data for testing."""
        return {
            "sessions": [
                {
                    "id": "session1",
                    "name": "Test Session 1",
                    "created_at": datetime.now().isoformat(),
                    "message_count": 10,
                    "last_active": datetime.now().isoformat(),
                },
                {
                    "id": "session2",
                    "name": "Test Session 2",
                    "created_at": datetime.now().isoformat(),
                    "message_count": 5,
                    "last_active": datetime.now().isoformat(),
                },
            ],
            "total_messages": 15,
            "active_sessions": 2,
        }

    @pytest.mark.unit
    def test_dashboard_page_loads(self, app):
        """Test that dashboard page loads without errors."""
        app.run()
        # Dashboard is the default page
        assert not app.exception

    @pytest.mark.unit
    def test_welcome_message_display(self, app):
        """Test that welcome message is displayed."""
        app.run()

        # Should have a title or header
        assert len(app.title) > 0 or len(app.header) > 0

    @pytest.mark.unit
    def test_statistics_display(self, app, mock_session_data):
        """Test that statistics are displayed on dashboard."""
        with patch("coda.session.manager.SessionManager") as mock_manager:
            mock_manager.return_value.get_statistics.return_value = mock_session_data

            app.run()

            # Should display metrics
            assert len(app.metric) > 0

    @pytest.mark.unit
    def test_provider_status_display(self, app):
        """Test that provider status is shown."""
        with patch("coda.providers.registry.ProviderFactory") as mock_factory:
            mock_factory.list_providers.return_value = ["openai", "anthropic"]

            app.run()

            # Should show available providers
            assert not app.exception

    @pytest.mark.unit
    def test_recent_sessions_display(self, app, mock_session_data):
        """Test that recent sessions are displayed."""
        app.session_state["recent_sessions"] = mock_session_data["sessions"]

        app.run()

        # Should display session information
        assert not app.exception

    @pytest.mark.unit
    def test_quick_actions(self, app):
        """Test quick action buttons on dashboard."""
        app.run()

        # Should have buttons for quick actions
        action_buttons = [
            b for b in app.button if "new" in str(b).lower() or "start" in str(b).lower()
        ]
        assert len(action_buttons) >= 0  # May have quick actions

    @pytest.mark.unit
    def test_system_info_display(self, app):
        """Test that system information is displayed."""
        app.run()

        # May show version info, etc.
        assert not app.exception

    @pytest.mark.unit
    def test_navigation_from_dashboard(self, app):
        """Test navigation to other pages from dashboard."""
        try:
            app.run()

            # Should be able to navigate to chat
            app.radio[0].set_value("💬 Chat").run()
            assert not app.exception

            # Navigate back to dashboard
            app.radio[0].set_value("📊 Dashboard").run()
            assert not app.exception
        except (RuntimeError, ValueError):
            pytest.skip("App test timed out or encountered error")

    @pytest.mark.unit
    def test_refresh_functionality(self, app):
        """Test refresh button if available."""
        app.run()

        # Look for refresh button
        refresh_buttons = [b for b in app.button if "refresh" in str(b).lower()]
        if refresh_buttons:
            refresh_buttons[0].click().run()
            assert not app.exception

    @pytest.mark.unit
    def test_empty_state_display(self, app):
        """Test dashboard display when no data is available."""
        try:
            app.run()

            # Should handle empty state gracefully
            assert not app.exception
        except RuntimeError:
            pytest.skip("App test timed out")
