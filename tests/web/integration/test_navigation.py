"""Integration tests for navigation between pages."""

import time

import pytest
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@pytest.mark.integration
@pytest.mark.requires_browser
class TestNavigation:
    """Test suite for page navigation."""

    def test_initial_page_load(self, driver, streamlit_server):
        """Test that the app loads successfully."""
        driver.get(streamlit_server)

        # Wait for app to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Dashboard')]"))
        )

        # Verify title
        assert "Coda Assistant" in driver.title

    def test_navigate_to_chat(self, driver, streamlit_server):
        """Test navigation to chat page."""
        driver.get(streamlit_server)

        # Wait for app to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Dashboard')]"))
        )

        # Click on Chat navigation
        chat_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), '💬 Chat')]"))
        )
        chat_link.click()

        # Verify chat page loaded
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[@placeholder='Type your message here...']")
            )
        )

    def test_navigate_to_sessions(self, driver, streamlit_server):
        """Test navigation to sessions page."""
        driver.get(streamlit_server)

        # Wait for app to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Dashboard')]"))
        )

        # Click on Sessions navigation
        sessions_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), '📁 Sessions')]"))
        )
        sessions_link.click()

        # Verify sessions page loaded
        time.sleep(2)  # Allow page to render
        page_content = driver.find_element(By.TAG_NAME, "body").text
        assert "Sessions" in page_content or "Session" in page_content

    def test_navigate_to_settings(self, driver, streamlit_server):
        """Test navigation to settings page."""
        driver.get(streamlit_server)

        # Wait for app to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Dashboard')]"))
        )

        # Click on Settings navigation
        settings_link = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), '⚙️ Settings')]"))
        )
        settings_link.click()

        # Verify settings page loaded
        time.sleep(2)  # Allow page to render
        page_content = driver.find_element(By.TAG_NAME, "body").text
        assert "Settings" in page_content or "Configuration" in page_content

    def test_sidebar_persistence(self, driver, streamlit_server):
        """Test that sidebar remains accessible across pages."""
        driver.get(streamlit_server)

        # Wait for app to load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Dashboard')]"))
        )

        # Navigate through all pages
        pages = ["💬 Chat", "📁 Sessions", "⚙️ Settings", "📊 Dashboard"]

        for page in pages:
            # Click on page
            page_link = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, f"//span[contains(text(), '{page}')]"))
            )
            page_link.click()

            time.sleep(1)  # Brief pause between navigations

            # Verify sidebar still visible
            sidebar = driver.find_element(By.CSS_SELECTOR, "[data-testid='stSidebar']")
            assert sidebar.is_displayed()

    def test_navigation_speed(self, driver, streamlit_server):
        """Test that navigation between pages is responsive."""
        driver.get(streamlit_server)

        # Wait for initial load
        WebDriverWait(driver, 30).until(
            EC.presence_of_element_located((By.XPATH, "//span[contains(text(), 'Dashboard')]"))
        )

        # Time navigation to chat
        start_time = time.time()

        chat_link = driver.find_element(By.XPATH, "//span[contains(text(), '💬 Chat')]")
        chat_link.click()

        # Wait for chat page to load
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located(
                (By.XPATH, "//input[@placeholder='Type your message here...']")
            )
        )

        end_time = time.time()
        navigation_time = end_time - start_time

        # Navigation should be reasonably fast (under 5 seconds)
        assert navigation_time < 5.0

    def test_direct_url_navigation(self, driver, streamlit_server):
        """Test that direct URLs work (if supported)."""
        # Try navigating directly to chat page
        driver.get(f"{streamlit_server}?page=chat")

        # Wait for app to load
        time.sleep(3)

        # App should still load successfully
        assert "Coda Assistant" in driver.title
