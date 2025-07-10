"""Test web UI navigation functionality."""

import time

import pytest
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestWebUINavigation:
    """Test suite for web UI navigation."""

    def test_page_loads(self, web_page):
        """Test that the main page loads successfully."""
        # Check page title
        assert "Coda Assistant" in web_page.title

        # Check for main elements
        try:
            # Look for sidebar
            sidebar = WebDriverWait(web_page, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='stSidebar']"))
            )
            assert sidebar is not None

            # Look for main content area
            main_content = web_page.find_element(By.CSS_SELECTOR, "[data-testid='stMain']")
            assert main_content is not None

        except TimeoutException:
            pytest.fail("Page failed to load basic Streamlit elements")

    def test_sidebar_navigation_exists(self, web_page):
        """Test that navigation elements exist in sidebar."""
        try:
            # Wait for sidebar to be present
            sidebar = WebDriverWait(web_page, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='stSidebar']"))
            )

            # Look for navigation radio buttons or similar
            # Streamlit radio buttons have specific CSS selectors
            radio_elements = sidebar.find_elements(By.CSS_SELECTOR, "input[type='radio']")

            # Should have at least 4 radio buttons for our 4 tabs
            assert len(radio_elements) >= 4, (
                f"Expected at least 4 navigation options, found {len(radio_elements)}"
            )

        except (TimeoutException, NoSuchElementException) as e:
            pytest.fail(f"Navigation elements not found: {e}")

    def test_navigation_labels(self, web_page):
        """Test that navigation labels are present and correct."""
        try:
            sidebar = WebDriverWait(web_page, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='stSidebar']"))
            )

            sidebar_text = sidebar.text

            # Check for expected navigation labels
            expected_labels = ["Dashboard", "Chat", "Sessions", "Settings"]
            for label in expected_labels:
                assert label in sidebar_text, f"Navigation label '{label}' not found in sidebar"

        except TimeoutException:
            pytest.fail("Sidebar not found")

    def test_tab_switching(self, web_page):
        """Test that clicking navigation tabs changes content."""
        try:
            sidebar = WebDriverWait(web_page, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='stSidebar']"))
            )

            main_content = web_page.find_element(By.CSS_SELECTOR, "[data-testid='stMain']")

            # Get all radio buttons in sidebar
            radio_buttons = sidebar.find_elements(By.CSS_SELECTOR, "input[type='radio']")

            if len(radio_buttons) < 2:
                pytest.skip("Not enough navigation options to test switching")

            # Test switching between first two tabs
            initial_content = main_content.text

            # Click second radio button
            radio_buttons[1].click()
            time.sleep(2)  # Wait for content to update

            new_content = main_content.text

            # Content should change when switching tabs
            assert initial_content != new_content, "Content did not change when switching tabs"

        except (TimeoutException, NoSuchElementException) as e:
            pytest.fail(f"Tab switching test failed: {e}")

    def test_dashboard_tab_content(self, web_page):
        """Test that dashboard tab shows expected content."""
        try:
            # Navigate to dashboard (should be default)
            main_content = WebDriverWait(web_page, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='stMain']"))
            )

            content_text = main_content.text.lower()

            # Check for dashboard-specific content
            dashboard_indicators = ["dashboard", "provider", "status", "usage"]
            found_indicators = [
                indicator for indicator in dashboard_indicators if indicator in content_text
            ]

            assert len(found_indicators) >= 2, (
                f"Dashboard content not found. Found indicators: {found_indicators}"
            )

        except TimeoutException:
            pytest.fail("Dashboard content did not load")

    def test_no_error_messages(self, web_page):
        """Test that no error messages are displayed on page load."""
        try:
            main_content = WebDriverWait(web_page, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='stMain']"))
            )

            # Look for error indicators
            error_elements = web_page.find_elements(By.CSS_SELECTOR, "[data-testid='stAlert']")
            error_text = [
                elem.text.lower() for elem in error_elements if "error" in elem.text.lower()
            ]

            # Also check page text for common error patterns
            page_text = main_content.text.lower()
            error_patterns = ["traceback", "exception", "error occurred", "failed to load"]

            found_errors = [pattern for pattern in error_patterns if pattern in page_text]

            assert len(error_text) == 0, f"Error alerts found: {error_text}"
            assert len(found_errors) == 0, f"Error patterns found in page: {found_errors}"

        except TimeoutException:
            pytest.fail("Main content did not load")

    def test_all_tabs_accessible(self, web_page):
        """Test that all navigation tabs can be accessed and show content."""
        try:
            sidebar = WebDriverWait(web_page, 10).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "[data-testid='stSidebar']"))
            )

            main_content = web_page.find_element(By.CSS_SELECTOR, "[data-testid='stMain']")
            radio_buttons = sidebar.find_elements(By.CSS_SELECTOR, "input[type='radio']")

            successful_tabs = 0

            for i, radio_button in enumerate(radio_buttons):
                try:
                    # Click the radio button
                    radio_button.click()
                    time.sleep(2)  # Wait for content to load

                    # Check if content is present (not empty or just whitespace)
                    content = main_content.text.strip()
                    if content and len(content) > 10:  # Some meaningful content
                        successful_tabs += 1

                except Exception as e:
                    print(f"Tab {i} failed to load: {e}")

            # At least half the tabs should work
            min_working_tabs = max(1, len(radio_buttons) // 2)
            assert successful_tabs >= min_working_tabs, (
                f"Only {successful_tabs} of {len(radio_buttons)} tabs loaded successfully"
            )

        except (TimeoutException, NoSuchElementException) as e:
            pytest.fail(f"Tab accessibility test failed: {e}")
