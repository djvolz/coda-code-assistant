"""Test suite for TUI CLI interface using pexpect."""

import os
import sys
import time
from pathlib import Path

import pexpect
import pytest

# Mark all tests in this module as tui and interactive
pytestmark = [pytest.mark.tui, pytest.mark.interactive]


class TestTUIInterface:
    """Test the TUI CLI interface functionality."""

    @pytest.fixture
    def tui_app(self):
        """Fixture to start the TUI app."""
        # Use the coda command with --tui flag
        cmd = f"{sys.executable} -m coda.cli.main --tui"
        child = pexpect.spawn(cmd, timeout=10, dimensions=(25, 80))
        
        # Wait for app to initialize
        try:
            child.expect("Ready! Type your message", timeout=5)
            yield child
        finally:
            # Clean shutdown
            try:
                child.sendcontrol('c')
                child.close(force=True)
            except:
                pass

    def test_app_startup(self, tui_app):
        """Test that the TUI app starts successfully."""
        # Check for key UI elements
        assert tui_app.isalive()
        
        # Look for status bar elements
        before = tui_app.before.decode('utf-8', errors='ignore')
        assert "Welcome to CODA TUI CLI" in before or "Ready!" in before

    def test_text_input(self, tui_app):
        """Test that text can be entered in the input field."""
        # Type some text
        tui_app.send("hello world")
        time.sleep(0.5)
        
        # The text should be visible in the terminal
        tui_app.send("\r")  # Press Enter
        time.sleep(0.5)
        
        # Should see "You" message with our text
        tui_app.expect("hello world", timeout=2)

    def test_ctrl_p_command_palette(self, tui_app):
        """Test that Ctrl+P opens command palette without crashing."""
        # Send Ctrl+P
        tui_app.sendcontrol('p')
        time.sleep(0.5)
        
        # Type a command search
        tui_app.send("mode")
        time.sleep(0.5)
        
        # Should see mode commands in palette
        # Look for mode-related text in the buffer
        tui_app.send("\x1b")  # Send Escape to close palette
        time.sleep(0.5)
        
        # App should still be running
        assert tui_app.isalive()

    def test_tab_completion(self, tui_app):
        """Test tab completion functionality."""
        # Type partial command
        tui_app.send("/mo")
        time.sleep(0.2)
        
        # Press Tab
        tui_app.send("\t")
        time.sleep(0.5)
        
        # Should complete to /mode
        tui_app.send(" general\r")
        time.sleep(0.5)
        
        # Should see mode switch message
        tui_app.expect("Switched to general mode", timeout=2)

    def test_slash_commands(self, tui_app):
        """Test various slash commands."""
        # Test /help command
        tui_app.send("/help\r")
        time.sleep(0.5)
        
        # Should see help text
        tui_app.expect("CODA TUI CLI Help", timeout=2)
        
        # Test /model command
        tui_app.send("/model\r")
        time.sleep(0.5)
        
        # Should see model info
        tui_app.expect("Current model:", timeout=2)

    def test_keyboard_shortcuts(self, tui_app):
        """Test keyboard shortcuts."""
        # Test F1 for help
        tui_app.send("\x1b[11~")  # F1 key sequence
        time.sleep(0.5)
        
        # Should see help text
        try:
            tui_app.expect("Keyboard Shortcuts", timeout=2)
        except:
            # Some terminals might not support F1
            pass
        
        # Test Ctrl+L for clear
        tui_app.sendcontrol('l')
        time.sleep(0.5)
        
        # Should see conversation cleared message
        tui_app.expect("Conversation cleared", timeout=2)

    def test_error_handling(self, tui_app):
        """Test that the app handles errors gracefully."""
        # Send invalid command
        tui_app.send("/invalid_command\r")
        time.sleep(0.5)
        
        # Should see error message but app continues
        tui_app.expect("Unknown command", timeout=2)
        
        # App should still be responsive
        tui_app.send("/help\r")
        time.sleep(0.5)
        tui_app.expect("CODA TUI CLI Help", timeout=2)

    def test_scrolling(self, tui_app):
        """Test scrolling functionality."""
        # Send multiple messages to create scrollable content
        for i in range(5):
            tui_app.send(f"Test message {i}\r")
            time.sleep(0.2)
        
        # Test Page Up
        tui_app.send("\x1b[5~")  # Page Up key sequence
        time.sleep(0.2)
        
        # Test Page Down
        tui_app.send("\x1b[6~")  # Page Down key sequence
        time.sleep(0.2)
        
        # App should still be running
        assert tui_app.isalive()

    @pytest.mark.parametrize("mode", ["code", "debug", "explain", "review", "refactor", "plan"])
    def test_mode_switching(self, tui_app, mode):
        """Test switching between different developer modes."""
        tui_app.send(f"/mode {mode}\r")
        time.sleep(0.5)
        
        # Should see mode switch confirmation
        tui_app.expect(f"Switched to {mode} mode", timeout=2)
        
        # Status bar should update
        assert tui_app.isalive()


class TestTUIIntegration:
    """Integration tests for TUI interface with providers."""

    @pytest.fixture
    def mock_provider_app(self, tmp_path):
        """Fixture for app with mock provider."""
        # Create a test config file
        config_file = tmp_path / "test_config.toml"
        config_file.write_text("""
[providers.mock]
type = "mock"
""")
        
        # Start app with test config
        env = os.environ.copy()
        env["CODA_CONFIG"] = str(config_file)
        
        cmd = f"{sys.executable} -m coda.cli.main --tui --provider mock"
        child = pexpect.spawn(cmd, timeout=10, dimensions=(25, 80), env=env)
        
        try:
            # Wait for initialization
            time.sleep(2)
            yield child
        finally:
            try:
                child.sendcontrol('c')
                child.close(force=True)
            except:
                pass

    @pytest.mark.skip(reason="Mock provider not yet implemented")
    def test_provider_interaction(self, mock_provider_app):
        """Test interaction with provider."""
        # Send a message
        mock_provider_app.send("Hello AI\r")
        time.sleep(1)
        
        # Should see response
        mock_provider_app.expect("Assistant", timeout=5)
        
        # Check streaming works
        assert mock_provider_app.isalive()


# Utility function for manual testing
def run_manual_test():
    """Run manual test of TUI interface."""
    print("Starting manual TUI interface test...")
    print("This will launch the app - test the following:")
    print("1. Type some text and press Enter")
    print("2. Press Ctrl+P and type 'mode'")
    print("3. Press Tab after typing '/mo'")
    print("4. Press Ctrl+C to exit")
    print()
    
    cmd = f"{sys.executable} -m coda.cli.main --tui"
    child = pexpect.spawn(cmd)
    child.interact()


if __name__ == "__main__":
    # Run manual test when executed directly
    run_manual_test()