"""Pytest configuration and fixtures for web UI testing."""

import pytest
import subprocess
import time
import requests
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from pathlib import Path
import tempfile
import os


@pytest.fixture(scope="session")
def web_server():
    """Start the Streamlit web server for testing."""
    port = 8600  # Use a dedicated test port
    
    # Start the web server
    proc = subprocess.Popen(
        ["uv", "run", "streamlit", "run", "coda/web/app.py", 
         "--server.port", str(port), "--server.headless", "true"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        cwd=Path(__file__).parent.parent.parent  # Project root
    )
    
    # Wait for server to start
    url = f"http://localhost:{port}"
    for _ in range(30):  # Wait up to 30 seconds
        try:
            response = requests.get(url, timeout=2)
            if response.status_code == 200:
                break
        except requests.RequestException:
            time.sleep(1)
    else:
        proc.terminate()
        proc.wait()
        pytest.fail("Web server failed to start")
    
    yield url
    
    # Cleanup
    proc.terminate()
    proc.wait()


@pytest.fixture
def chrome_driver():
    """Create a Chrome WebDriver instance."""
    options = ChromeOptions()
    options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    try:
        driver = webdriver.Chrome(options=options)
        yield driver
    except Exception as e:
        pytest.skip(f"Chrome driver not available: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()


@pytest.fixture
def firefox_driver():
    """Create a Firefox WebDriver instance."""
    options = FirefoxOptions()
    options.add_argument("--headless")
    options.add_argument("--width=1920")
    options.add_argument("--height=1080")
    
    try:
        driver = webdriver.Firefox(options=options)
        yield driver
    except Exception as e:
        pytest.skip(f"Firefox driver not available: {e}")
    finally:
        if 'driver' in locals():
            driver.quit()


@pytest.fixture(params=["chrome", "firefox"])
def browser_driver(request, chrome_driver, firefox_driver):
    """Parameterized fixture to test with multiple browsers."""
    if request.param == "chrome":
        return chrome_driver
    elif request.param == "firefox":
        return firefox_driver


@pytest.fixture
def web_page(browser_driver, web_server):
    """Load the web application in browser."""
    browser_driver.get(web_server)
    
    # Wait for page to load
    time.sleep(3)
    
    return browser_driver