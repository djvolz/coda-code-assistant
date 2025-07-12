"""Test backend integration without browser automation."""

import subprocess
import time
from pathlib import Path

import pytest
import requests


class TestBackendIntegration:
    """Test backend functionality and API endpoints."""

    def test_web_server_starts(self):
        """Test that the web server starts successfully."""
        port = 8601
        proc = subprocess.Popen(
            [
                "uv",
                "run",
                "streamlit",
                "run",
                "coda/web/app.py",
                "--server.port",
                str(port),
                "--server.headless",
                "true",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent.parent.parent,
        )

        try:
            # Wait for server to start
            url = f"http://localhost:{port}"
            for _ in range(20):
                try:
                    response = requests.get(url, timeout=2)
                    if response.status_code == 200:
                        break
                except requests.RequestException:
                    time.sleep(1)
            else:
                pytest.fail("Web server failed to start within timeout")

            # Test basic connectivity
            response = requests.get(url, timeout=5)
            assert response.status_code == 200
            assert "streamlit" in response.text.lower()

        finally:
            proc.terminate()
            proc.wait()

    def test_streamlit_health_endpoint(self):
        """Test Streamlit health endpoint."""
        port = 8602
        proc = subprocess.Popen(
            [
                "uv",
                "run",
                "streamlit",
                "run",
                "coda/web/app.py",
                "--server.port",
                str(port),
                "--server.headless",
                "true",
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=Path(__file__).parent.parent.parent,
        )

        try:
            # Wait for server to start
            base_url = f"http://localhost:{port}"
            for _ in range(20):
                try:
                    response = requests.get(base_url, timeout=2)
                    if response.status_code == 200:
                        break
                except requests.RequestException:
                    time.sleep(1)
            else:
                pytest.fail("Web server failed to start within timeout")

            # Test health endpoint
            health_url = f"{base_url}/_stcore/health"
            response = requests.get(health_url, timeout=5)
            assert response.status_code == 200

        finally:
            proc.terminate()
            proc.wait()

    def test_configuration_loading(self):
        """Test that configuration loads without errors."""
        from coda.configuration import get_config

        config = get_config()
        assert config is not None

        config_dict = config.to_dict()
        assert isinstance(config_dict, dict)
        assert len(config_dict) > 0

    def test_session_manager_initialization(self):
        """Test that session manager initializes correctly."""
        from coda.session.manager import SessionManager

        session_manager = SessionManager()
        assert session_manager is not None

        # Test basic operations
        sessions = session_manager.get_active_sessions(limit=5)
        assert isinstance(sessions, list)

    def test_provider_registry_access(self):
        """Test that provider registry is accessible."""
        from coda.providers.registry import get_provider_registry

        registry = get_provider_registry()
        assert isinstance(registry, dict)
        assert len(registry) > 0

        # Check for expected providers
        expected_providers = ["oci_genai", "ollama", "litellm", "mock"]
        for provider in expected_providers:
            assert provider in registry

    def test_web_components_importable(self):
        """Test that all web components can be imported."""
        components = [
            "coda.web.app",
            "coda.web.pages.dashboard",
            "coda.web.pages.chat",
            "coda.web.pages.sessions",
            "coda.web.pages.settings",
            "coda.web.components.model_selector",
            "coda.web.components.chat_widget",
            "coda.web.components.file_manager",
            "coda.web.utils.state",
        ]

        for component in components:
            try:
                __import__(component)
            except ImportError as e:
                pytest.fail(f"Failed to import {component}: {e}")

    def test_cli_web_command(self):
        """Test that the CLI web command works."""
        result = subprocess.run(
            ["uv", "run", "coda", "web", "--help"],
            capture_output=True,
            text=True,
            timeout=10,
            cwd=Path(__file__).parent.parent.parent,
        )

        assert result.returncode == 0
        assert "web" in result.stdout.lower()
        assert "streamlit" in result.stdout.lower() or "launch" in result.stdout.lower()

    def test_minimal_streamlit_app(self):
        """Test a minimal Streamlit app to verify Streamlit works."""
        minimal_app_content = """
import streamlit as st

st.title("Test App")
page = st.radio("Navigation", ["Page 1", "Page 2"])
st.write(f"Current page: {page}")
"""

        # Write minimal app to temp file
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write(minimal_app_content)
            temp_app_path = f.name

        try:
            port = 8603
            proc = subprocess.Popen(
                [
                    "uv",
                    "run",
                    "streamlit",
                    "run",
                    temp_app_path,
                    "--server.port",
                    str(port),
                    "--server.headless",
                    "true",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=Path(__file__).parent.parent.parent,
            )

            try:
                # Wait for server to start
                url = f"http://localhost:{port}"
                for _ in range(15):
                    try:
                        response = requests.get(url, timeout=2)
                        if response.status_code == 200:
                            break
                    except requests.RequestException:
                        time.sleep(1)
                else:
                    pytest.fail("Minimal Streamlit app failed to start")

                # Test that it responds
                response = requests.get(url, timeout=5)
                assert response.status_code == 200

            finally:
                proc.terminate()
                proc.wait()

        finally:
            # Clean up temp file
            Path(temp_app_path).unlink(missing_ok=True)
