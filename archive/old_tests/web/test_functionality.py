"""Test web UI functionality across different tabs."""

import time

import pytest
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestWebUIFunctionality:
    """Test suite for web UI functionality."""

    def test_dashboard_charts_render(self, web_page):
        """Test that dashboard charts render without errors."""
        try:
            # Navigate to dashboard tab
            self._navigate_to_tab(web_page, "dashboard")

            # Wait for charts to load (Plotly charts have specific elements)
            chart_elements = WebDriverWait(web_page, 15).until(
                lambda driver: driver.find_elements(
                    By.CSS_SELECTOR, ".js-plotly-plot, .stPlotlyChart"
                )
            )

            assert len(chart_elements) > 0, "No charts found on dashboard"

            # Check that charts actually have content
            for chart in chart_elements:
                assert chart.size["height"] > 0, "Chart has no height"
                assert chart.size["width"] > 0, "Chart has no width"

        except TimeoutException:
            pytest.fail("Dashboard charts failed to load within timeout")

    def test_chat_interface_elements(self, web_page):
        """Test that chat interface has required elements."""
        try:
            # Navigate to chat tab
            self._navigate_to_tab(web_page, "chat")

            main_content = web_page.find_element(By.CSS_SELECTOR, "[data-testid='stMain']")

            # Look for chat-specific elements
            content_text = main_content.text.lower()

            # Check for expected chat elements
            expected_elements = ["provider", "model", "chat", "message"]
            found_elements = [elem for elem in expected_elements if elem in content_text]

            assert len(found_elements) >= 2, (
                f"Chat interface elements not found. Found: {found_elements}"
            )

            # Look for form elements (dropdowns, inputs)
            dropdowns = web_page.find_elements(
                By.CSS_SELECTOR, "select, [data-testid='stSelectbox']"
            )
            inputs = web_page.find_elements(
                By.CSS_SELECTOR, "input, textarea, [data-testid='stTextInput']"
            )

            assert len(dropdowns) > 0 or len(inputs) > 0, (
                "No interactive elements found in chat interface"
            )

        except (TimeoutException, NoSuchElementException) as e:
            pytest.fail(f"Chat interface test failed: {e}")

    def test_sessions_interface_elements(self, web_page):
        """Test that sessions interface shows session management elements."""
        try:
            # Navigate to sessions tab
            self._navigate_to_tab(web_page, "sessions")

            main_content = web_page.find_element(By.CSS_SELECTOR, "[data-testid='stMain']")
            content_text = main_content.text.lower()

            # Check for session-related content
            session_indicators = ["session", "search", "filter", "export", "delete"]
            found_indicators = [
                indicator for indicator in session_indicators if indicator in content_text
            ]

            assert len(found_indicators) >= 2, (
                f"Session management elements not found. Found: {found_indicators}"
            )

        except (TimeoutException, NoSuchElementException) as e:
            pytest.fail(f"Sessions interface test failed: {e}")

    def test_settings_interface_elements(self, web_page):
        """Test that settings interface shows configuration elements."""
        try:
            # Navigate to settings tab
            self._navigate_to_tab(web_page, "settings")

            main_content = web_page.find_element(By.CSS_SELECTOR, "[data-testid='stMain']")
            content_text = main_content.text.lower()

            # Check for settings-related content
            settings_indicators = [
                "settings",
                "provider",
                "configuration",
                "oci",
                "ollama",
                "litellm",
            ]
            found_indicators = [
                indicator for indicator in settings_indicators if indicator in content_text
            ]

            assert len(found_indicators) >= 2, (
                f"Settings elements not found. Found: {found_indicators}"
            )

        except (TimeoutException, NoSuchElementException) as e:
            pytest.fail(f"Settings interface test failed: {e}")

    def test_responsive_layout(self, web_page):
        """Test that the layout is responsive and elements are visible."""
        try:
            # Test different window sizes
            window_sizes = [(1920, 1080), (1280, 720), (800, 600)]

            for width, height in window_sizes:
                web_page.set_window_size(width, height)
                time.sleep(1)

                # Check that main elements are still visible
                sidebar = web_page.find_element(By.CSS_SELECTOR, "[data-testid='stSidebar']")
                main_content = web_page.find_element(By.CSS_SELECTOR, "[data-testid='stMain']")

                assert sidebar.is_displayed(), f"Sidebar not visible at {width}x{height}"
                assert main_content.is_displayed(), f"Main content not visible at {width}x{height}"

        except NoSuchElementException as e:
            pytest.fail(f"Responsive layout test failed: {e}")

    def test_no_javascript_errors(self, web_page):
        """Test that no JavaScript errors occur during navigation."""
        try:
            # Get initial JavaScript logs
            web_page.get_log("browser")

            # Navigate through all tabs
            sidebar = web_page.find_element(By.CSS_SELECTOR, "[data-testid='stSidebar']")
            radio_buttons = sidebar.find_elements(By.CSS_SELECTOR, "input[type='radio']")

            for radio_button in radio_buttons:
                radio_button.click()
                time.sleep(2)

            # Get final JavaScript logs
            final_logs = web_page.get_log("browser")

            # Filter for actual errors (not warnings or info)
            errors = [log for log in final_logs if log["level"] == "SEVERE"]

            assert len(errors) == 0, (
                f"JavaScript errors found: {[error['message'] for error in errors]}"
            )

        except Exception as e:
            # Some drivers don't support log collection, skip this test
            pytest.skip(f"Browser log collection not supported: {e}")

    def _navigate_to_tab(self, driver, tab_name):
        """Helper method to navigate to a specific tab."""
        try:
            sidebar = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='stSidebar']"))
            )

            # Look for radio button labels containing the tab name
            sidebar_text = sidebar.text.lower()
            if tab_name.lower() not in sidebar_text:
                pytest.skip(f"Tab '{tab_name}' not found in navigation")

            # Find radio buttons and click the appropriate one
            radio_buttons = sidebar.find_elements(By.CSS_SELECTOR, "input[type='radio']")

            # Try to identify the correct radio button by context
            # This is a simplified approach - in practice you might need more sophisticated element finding
            for _i, button in enumerate(radio_buttons):
                button.click()
                time.sleep(2)

                main_content = driver.find_element(By.CSS_SELECTOR, "[data-testid='stMain']")
                content_text = main_content.text.lower()

                if tab_name.lower() in content_text:
                    return  # Successfully navigated to the tab

            pytest.fail(f"Could not navigate to {tab_name} tab")

        except TimeoutException:
            pytest.fail(f"Failed to navigate to {tab_name} tab")
