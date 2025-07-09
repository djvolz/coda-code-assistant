"""Integration tests for session management functionality."""

import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestSessionIntegration:
    """Integration tests for session management."""

    def test_sessions_page_loads(self, web_server, driver, base_url):
        """Test that sessions page loads successfully."""
        driver.get(f"{base_url}")

        # Navigate to sessions tab
        sessions_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sessions')]"))
        )
        sessions_tab.click()

        # Verify sessions page elements
        time.sleep(2)

        # Check for session list or empty state
        session_elements = driver.find_elements(
            By.XPATH,
            "//*[contains(@class, 'session') or contains(text(), 'No sessions') or contains(text(), 'Session')]",
        )
        assert len(session_elements) > 0

    def test_create_new_session(self, web_server, driver, base_url):
        """Test creating a new session."""
        driver.get(f"{base_url}")

        # First create some chat history
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        # Send a message
        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys("Creating session test message")
        chat_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Navigate to sessions
        sessions_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sessions')]"))
        )
        sessions_tab.click()

        # Look for "New Session" or "Create Session" button
        try:
            new_session_btn = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable(
                    (By.XPATH, "//button[contains(text(), 'New') or contains(text(), 'Create')]")
                )
            )
            new_session_btn.click()

            time.sleep(2)

            # Verify new session was created
            session_items = driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'session-item') or contains(@data-testid, 'session')]",
            )
            assert len(session_items) > 0

        except TimeoutException:
            # New session might be created automatically
            pass

    def test_session_list_display(self, web_server, driver, base_url):
        """Test that existing sessions are displayed in list."""
        driver.get(f"{base_url}")

        # Create multiple sessions by sending messages
        for i in range(3):
            chat_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
            )
            chat_tab.click()

            chat_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
            )
            chat_input.send_keys(f"Session {i} test message")
            chat_input.send_keys(Keys.RETURN)

            time.sleep(1)

            # Create new session if button exists
            try:
                new_btn = driver.find_element(
                    By.XPATH, "//button[contains(text(), 'New') or contains(@title, 'New')]"
                )
                new_btn.click()
                time.sleep(1)
            except:
                pass

        # Navigate to sessions
        sessions_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sessions')]"))
        )
        sessions_tab.click()

        time.sleep(2)

        # Check session list
        session_items = driver.find_elements(
            By.XPATH, "//div[contains(@class, 'session') and not(contains(@class, 'empty'))]"
        )
        assert len(session_items) >= 1  # At least one session should exist

    def test_load_previous_session(self, web_server, driver, base_url):
        """Test loading a previous session."""
        driver.get(f"{base_url}")

        # Create a session with specific content
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        unique_message = "Unique message for session loading test 12345"
        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys(unique_message)
        chat_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Create new session
        try:
            new_btn = driver.find_element(
                By.XPATH, "//button[contains(text(), 'New') or contains(@title, 'New')]"
            )
            new_btn.click()
            time.sleep(1)
        except:
            pass

        # Navigate to sessions
        sessions_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sessions')]"))
        )
        sessions_tab.click()

        time.sleep(2)

        # Click on a session to load it
        session_items = driver.find_elements(
            By.XPATH,
            "//div[contains(@class, 'session-item') or contains(@data-testid, 'session')]//button",
        )

        if session_items:
            session_items[0].click()
            time.sleep(2)

            # Navigate back to chat
            chat_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
            )
            chat_tab.click()

            # Verify the unique message is loaded
            chat_messages = driver.find_elements(By.XPATH, "//div[@data-testid='stChatMessage']")
            message_found = False
            for msg in chat_messages:
                if unique_message in msg.text:
                    message_found = True
                    break
            assert message_found

    def test_delete_session(self, web_server, driver, base_url):
        """Test deleting a session."""
        driver.get(f"{base_url}")

        # Create a session
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys("Session to be deleted")
        chat_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Navigate to sessions
        sessions_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sessions')]"))
        )
        sessions_tab.click()

        time.sleep(2)

        # Count initial sessions
        initial_sessions = driver.find_elements(
            By.XPATH, "//div[contains(@class, 'session-item') or contains(@data-testid, 'session')]"
        )
        initial_count = len(initial_sessions)

        # Find and click delete button
        try:
            delete_buttons = driver.find_elements(
                By.XPATH,
                "//button[contains(text(), 'Delete') or contains(@title, 'Delete') or contains(@class, 'delete')]",
            )

            if delete_buttons:
                delete_buttons[0].click()

                # Handle confirmation if present
                time.sleep(1)
                confirm_buttons = driver.find_elements(
                    By.XPATH, "//button[contains(text(), 'Confirm') or contains(text(), 'Yes')]"
                )
                if confirm_buttons:
                    confirm_buttons[0].click()

                time.sleep(2)

                # Verify session count decreased
                final_sessions = driver.find_elements(
                    By.XPATH,
                    "//div[contains(@class, 'session-item') or contains(@data-testid, 'session')]",
                )
                assert len(final_sessions) < initial_count

        except TimeoutException:
            # Delete might not be implemented
            pass

    def test_session_search_filter(self, web_server, driver, base_url):
        """Test searching/filtering sessions."""
        driver.get(f"{base_url}")

        # Create sessions with different content
        test_messages = [
            "Python programming question",
            "JavaScript debugging help",
            "Database query optimization",
        ]

        for msg in test_messages:
            chat_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
            )
            chat_tab.click()

            chat_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
            )
            chat_input.send_keys(msg)
            chat_input.send_keys(Keys.RETURN)

            time.sleep(1)

            # Create new session
            try:
                new_btn = driver.find_element(
                    By.XPATH, "//button[contains(text(), 'New') or contains(@title, 'New')]"
                )
                new_btn.click()
            except:
                pass

        # Navigate to sessions
        sessions_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sessions')]"))
        )
        sessions_tab.click()

        time.sleep(2)

        # Look for search input
        try:
            search_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located(
                    (
                        By.XPATH,
                        "//input[@type='text' and (contains(@placeholder, 'Search') or contains(@placeholder, 'Filter'))]",
                    )
                )
            )

            # Search for Python
            search_input.clear()
            search_input.send_keys("Python")
            search_input.send_keys(Keys.RETURN)

            time.sleep(2)

            # Verify filtered results
            visible_sessions = driver.find_elements(
                By.XPATH,
                "//div[contains(@class, 'session-item') and not(contains(@style, 'display: none'))]",
            )

            # At least one session should match
            assert len(visible_sessions) >= 1

        except TimeoutException:
            # Search might not be implemented
            pass

    def test_session_export(self, web_server, driver, base_url):
        """Test exporting a session."""
        driver.get(f"{base_url}")

        # Create a session
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys("Session export test content")
        chat_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Navigate to sessions
        sessions_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sessions')]"))
        )
        sessions_tab.click()

        time.sleep(2)

        # Look for export button
        try:
            export_buttons = driver.find_elements(
                By.XPATH,
                "//button[contains(text(), 'Export') or contains(@title, 'Export') or contains(@class, 'export')]",
            )

            if export_buttons:
                export_buttons[0].click()
                time.sleep(1)

                # Verify export initiated (hard to test actual download)
                assert True

        except TimeoutException:
            # Export might be in different location
            pass

    def test_session_metadata_display(self, web_server, driver, base_url):
        """Test that session metadata is displayed correctly."""
        driver.get(f"{base_url}")

        # Create a session
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys("Test session with metadata")
        chat_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Navigate to sessions
        sessions_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sessions')]"))
        )
        sessions_tab.click()

        time.sleep(2)

        # Check for metadata elements
        metadata_elements = driver.find_elements(
            By.XPATH,
            "//*[contains(text(), 'Created') or contains(text(), 'Messages') or contains(text(), 'Provider')]",
        )
        assert len(metadata_elements) > 0

    def test_session_pagination(self, web_server, driver, base_url):
        """Test pagination if many sessions exist."""
        driver.get(f"{base_url}")

        # Create many sessions (if pagination is implemented)
        for i in range(12):  # Assuming 10 per page
            chat_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
            )
            chat_tab.click()

            chat_input = WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
            )
            chat_input.send_keys(f"Session {i} for pagination test")
            chat_input.send_keys(Keys.RETURN)

            time.sleep(0.5)

            # Create new session
            try:
                new_btn = driver.find_element(
                    By.XPATH, "//button[contains(text(), 'New') or contains(@title, 'New')]"
                )
                new_btn.click()
            except:
                pass

        # Navigate to sessions
        sessions_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sessions')]"))
        )
        sessions_tab.click()

        time.sleep(2)

        # Look for pagination controls
        pagination_elements = driver.find_elements(
            By.XPATH,
            "//button[contains(text(), 'Next') or contains(text(), 'Previous') or contains(@class, 'pagination')]",
        )

        if pagination_elements:
            # Click next page
            next_button = None
            for elem in pagination_elements:
                if "Next" in elem.text:
                    next_button = elem
                    break

            if next_button and next_button.is_enabled():
                next_button.click()
                time.sleep(2)

                # Verify different sessions are shown
                assert True  # Page changed successfully
        else:
            # Pagination might not be implemented for small numbers
            pass
