"""Functional tests for end-to-end user workflows."""

import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


class TestUserWorkflows:
    """Test complete user workflows from start to finish."""

    def test_new_user_onboarding_workflow(self, web_server, driver, base_url):
        """Test the complete workflow for a new user setting up the application."""
        driver.get(f"{base_url}")

        # Step 1: Navigate to Settings to configure provider
        settings_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Settings')]"))
        )
        settings_tab.click()

        time.sleep(2)

        # Step 2: Enter API key for a provider
        api_key_inputs = driver.find_elements(
            By.XPATH, "//input[@type='password' or contains(@placeholder, 'API')]"
        )

        if api_key_inputs:
            # Enter test API key for OpenAI
            api_key_inputs[0].clear()
            api_key_inputs[0].send_keys("test-openai-api-key")

            # Save settings
            save_buttons = driver.find_elements(
                By.XPATH, "//button[contains(text(), 'Save') or contains(text(), 'Apply')]"
            )
            if save_buttons:
                save_buttons[0].click()
                time.sleep(1)

        # Step 3: Navigate to Chat
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        time.sleep(2)

        # Step 4: Select provider and model
        try:
            # Select provider
            provider_selector = driver.find_element(
                By.XPATH, "//div[@data-testid='stSelectbox'][1]"
            )
            provider_selector.click()

            openai_option = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'openai')]"))
            )
            openai_option.click()

            time.sleep(1)

            # Select model
            model_selector = driver.find_element(By.XPATH, "//div[@data-testid='stSelectbox'][2]")
            model_selector.click()

            gpt_option = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//li[contains(text(), 'gpt')]"))
            )
            gpt_option.click()

        except TimeoutException:
            pass

        # Step 5: Send first message
        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys("Hello! This is my first message.")
        chat_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Verify message appears
        chat_messages = driver.find_elements(By.XPATH, "//div[@data-testid='stChatMessage']")
        assert len(chat_messages) > 0

        # Step 6: Check Dashboard
        dashboard_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Dashboard')]"))
        )
        dashboard_tab.click()

        time.sleep(2)

        # Verify dashboard shows activity
        dashboard_elements = driver.find_elements(
            By.XPATH,
            "//*[contains(@class, 'metric') or contains(text(), 'Total') or contains(text(), 'Usage')]",
        )
        assert len(dashboard_elements) > 0

    def test_complete_chat_workflow(self, web_server, driver, base_url, tmp_path):
        """Test complete chat workflow with file upload and export."""
        driver.get(f"{base_url}")

        # Step 1: Navigate to Chat
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        time.sleep(2)

        # Step 2: Upload a file
        test_file = tmp_path / "code_sample.py"
        test_file.write_text(
            """
def calculate_fibonacci(n):
    if n <= 1:
        return n
    return calculate_fibonacci(n-1) + calculate_fibonacci(n-2)

# Test the function
print(calculate_fibonacci(10))
"""
        )

        try:
            file_input = WebDriverWait(driver, 5).until(
                EC.presence_of_element_located((By.XPATH, "//input[@type='file']"))
            )
            file_input.send_keys(str(test_file))
            time.sleep(2)
        except TimeoutException:
            pass

        # Step 3: Send message about the code
        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys(
            "Can you explain this Fibonacci implementation and suggest improvements?"
        )
        chat_input.send_keys(Keys.RETURN)

        time.sleep(3)

        # Step 4: Send follow-up message
        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys("Can you show me an iterative version?")
        chat_input.send_keys(Keys.RETURN)

        time.sleep(3)

        # Step 5: Export chat history
        export_buttons = driver.find_elements(
            By.XPATH, "//button[contains(text(), 'Export') or contains(text(), 'Download')]"
        )

        if export_buttons:
            export_buttons[0].click()
            time.sleep(1)

        # Verify multiple messages exist
        chat_messages = driver.find_elements(By.XPATH, "//div[@data-testid='stChatMessage']")
        assert len(chat_messages) >= 2

    def test_session_management_workflow(self, web_server, driver, base_url):
        """Test complete session management workflow."""
        driver.get(f"{base_url}")

        # Step 1: Create first session with specific content
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys("First session: Python programming help")
        chat_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Step 2: Create new session
        try:
            new_session_btn = driver.find_element(
                By.XPATH, "//button[contains(text(), 'New') or contains(@title, 'New Session')]"
            )
            new_session_btn.click()
            time.sleep(1)
        except:
            # Navigate to sessions and create new
            sessions_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sessions')]"))
            )
            sessions_tab.click()

            time.sleep(2)

            new_btn = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, "//button[contains(text(), 'New')]"))
            )
            new_btn.click()

        # Step 3: Create second session with different content
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys("Second session: JavaScript debugging")
        chat_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Step 4: Navigate to sessions
        sessions_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Sessions')]"))
        )
        sessions_tab.click()

        time.sleep(2)

        # Step 5: Verify both sessions exist
        session_items = driver.find_elements(
            By.XPATH, "//div[contains(@class, 'session-item') or contains(@data-testid, 'session')]"
        )
        assert len(session_items) >= 2

        # Step 6: Load first session
        if session_items:
            session_items[0].click()
            time.sleep(2)

            # Go back to chat
            chat_tab = WebDriverWait(driver, 10).until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
            )
            chat_tab.click()

            # Verify correct session loaded
            chat_messages = driver.find_elements(By.XPATH, "//div[@data-testid='stChatMessage']")
            messages_text = " ".join([msg.text for msg in chat_messages])
            assert "Python" in messages_text or "First session" in messages_text

    def test_configuration_change_workflow(self, web_server, driver, base_url):
        """Test changing configuration and using new settings."""
        driver.get(f"{base_url}")

        # Step 1: Start with one provider
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        # Note current provider
        initial_provider = None
        try:
            provider_text = driver.find_element(
                By.XPATH, "//div[@data-testid='stSelectbox'][1]//div[contains(@class, 'selected')]"
            ).text
            initial_provider = provider_text
        except:
            pass

        # Step 2: Go to settings and change configuration
        settings_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Settings')]"))
        )
        settings_tab.click()

        time.sleep(2)

        # Change some settings (e.g., add new API key, change defaults)
        api_key_inputs = driver.find_elements(
            By.XPATH, "//input[@type='password' or contains(@placeholder, 'API')]"
        )

        # Add API key for different provider
        if len(api_key_inputs) > 1:
            api_key_inputs[1].clear()
            api_key_inputs[1].send_keys("test-anthropic-api-key")

        # Save changes
        save_buttons = driver.find_elements(
            By.XPATH, "//button[contains(text(), 'Save') or contains(text(), 'Apply')]"
        )
        if save_buttons:
            save_buttons[0].click()
            time.sleep(1)

        # Step 3: Go back to chat and use new provider
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        time.sleep(2)

        # Change provider
        try:
            provider_selector = driver.find_element(
                By.XPATH, "//div[@data-testid='stSelectbox'][1]"
            )
            provider_selector.click()

            # Select different provider
            provider_options = driver.find_elements(By.XPATH, "//li[@role='option']")
            for option in provider_options:
                if initial_provider and option.text != initial_provider:
                    option.click()
                    break

            time.sleep(1)

        except TimeoutException:
            pass

        # Step 4: Send message with new provider
        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys("Testing with new provider configuration")
        chat_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Verify message was sent
        chat_messages = driver.find_elements(By.XPATH, "//div[@data-testid='stChatMessage']")
        assert len(chat_messages) > 0

    def test_error_recovery_workflow(self, web_server, driver, base_url):
        """Test error recovery and fallback workflow."""
        driver.get(f"{base_url}")

        # Step 1: Intentionally cause an error (no API key)
        settings_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Settings')]"))
        )
        settings_tab.click()

        # Clear API keys
        api_key_inputs = driver.find_elements(By.XPATH, "//input[@type='password']")
        for input_field in api_key_inputs:
            input_field.clear()

        # Save empty configuration
        save_buttons = driver.find_elements(
            By.XPATH, "//button[contains(text(), 'Save') or contains(text(), 'Apply')]"
        )
        if save_buttons:
            save_buttons[0].click()
            time.sleep(1)

        # Step 2: Try to use chat
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys("This should fail")
        chat_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Step 3: Verify error message
        error_elements = driver.find_elements(
            By.XPATH,
            "//*[contains(text(), 'Error') or contains(text(), 'API key') or contains(@class, 'error')]",
        )
        assert len(error_elements) > 0

        # Step 4: Fix configuration
        settings_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Settings')]"))
        )
        settings_tab.click()

        # Add valid API key
        api_key_inputs = driver.find_elements(By.XPATH, "//input[@type='password']")
        if api_key_inputs:
            api_key_inputs[0].send_keys("valid-test-api-key")

            save_buttons = driver.find_elements(
                By.XPATH, "//button[contains(text(), 'Save') or contains(text(), 'Apply')]"
            )
            if save_buttons:
                save_buttons[0].click()
                time.sleep(1)

        # Step 5: Verify chat works again
        chat_tab = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "//span[contains(text(), 'Chat')]"))
        )
        chat_tab.click()

        chat_input = WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.XPATH, "//textarea[@data-testid='stChatInput']"))
        )
        chat_input.send_keys("This should work now")
        chat_input.send_keys(Keys.RETURN)

        time.sleep(2)

        # Verify recovery
        new_messages = driver.find_elements(By.XPATH, "//div[@data-testid='stChatMessage'][last()]")
        assert len(new_messages) > 0
