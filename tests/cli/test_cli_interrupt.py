"""Tests for CLI interrupt handling."""

import signal
import threading
import time
from unittest.mock import Mock, patch

import pytest

from coda.cli.interactive_cli import InteractiveCLI


class TestInterruptHandling:
    """Test cases for interrupt handling in InteractiveCLI."""

    @pytest.fixture
    def cli(self):
        """Create an InteractiveCLI instance for testing."""
        # Mock the console to avoid terminal issues in tests
        with patch("coda.themes.get_themed_console"):
            cli = InteractiveCLI()
            cli.session_manager = Mock()
            cli.chat_session = Mock()
            return cli

    def test_initial_interrupt_state(self, cli):
        """Test initial state of interrupt event."""
        assert hasattr(cli, "interrupt_event")
        assert not cli.interrupt_event.is_set()
        assert cli.escape_count == 0
        assert cli.ctrl_c_count == 0

    def test_reset_interrupt(self, cli):
        """Test reset_interrupt clears the event and counters."""
        # Set the interrupt event and counters
        cli.interrupt_event.set()
        cli.escape_count = 5
        cli.ctrl_c_count = 3

        cli.reset_interrupt()

        assert not cli.interrupt_event.is_set()
        assert cli.escape_count == 0
        assert cli.ctrl_c_count == 0

    def test_interrupt_event_thread_safety(self, cli):
        """Test interrupt event is thread-safe."""
        results = []

        def set_interrupt():
            cli.interrupt_event.set()
            results.append(cli.interrupt_event.is_set())

        def clear_interrupt():
            time.sleep(0.01)  # Small delay to ensure ordering
            cli.interrupt_event.clear()
            results.append(cli.interrupt_event.is_set())

        # Run in threads
        t1 = threading.Thread(target=set_interrupt)
        t2 = threading.Thread(target=clear_interrupt)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Should have set then cleared
        assert results[0] is True
        assert results[1] is False

    def test_multiple_interrupt_sets(self, cli):
        """Test handling multiple interrupt event sets."""
        cli.interrupt_event.set()
        assert cli.interrupt_event.is_set()

        # Second set should still leave event set
        cli.interrupt_event.set()
        assert cli.interrupt_event.is_set()

    def test_interrupt_event_persistence(self, cli):
        """Test interrupt event persists until cleared."""
        cli.interrupt_event.set()
        assert cli.interrupt_event.is_set()

        # Event should persist
        assert cli.interrupt_event.is_set()
        assert cli.interrupt_event.is_set()

        # Until explicitly cleared
        cli.interrupt_event.clear()
        assert not cli.interrupt_event.is_set()

    @patch("signal.signal")
    def test_start_interrupt_listener(self, mock_signal, cli):
        """Test starting interrupt listener registers handler."""
        # Mock the current handler
        mock_signal.return_value = signal.default_int_handler

        cli.start_interrupt_listener()

        # Should register new handler
        mock_signal.assert_called_once()
        call_args = mock_signal.call_args[0]
        assert call_args[0] == signal.SIGINT
        # The handler should be a function
        assert callable(call_args[1])

        # Should store old handler
        assert hasattr(cli, "old_sigint_handler")

    @patch("signal.signal")
    def test_stop_interrupt_listener(self, mock_signal, cli):
        """Test stopping interrupt listener restores handler."""
        cli.old_sigint_handler = signal.default_int_handler

        cli.stop_interrupt_listener()

        # Should restore original handler
        mock_signal.assert_called_with(signal.SIGINT, signal.default_int_handler)

    @patch("signal.signal")
    def test_stop_interrupt_listener_no_old_handler(self, mock_signal, cli):
        """Test stopping listener when no old handler stored."""
        # Ensure no old_sigint_handler attribute
        if hasattr(cli, "old_sigint_handler"):
            delattr(cli, "old_sigint_handler")

        cli.stop_interrupt_listener()

        # Should not call signal.signal
        mock_signal.assert_not_called()

    @patch("signal.signal")
    def test_interrupt_handler_sets_event(self, mock_signal, cli):
        """Test that the interrupt handler sets the interrupt event."""
        # Start the listener to get the handler
        cli.start_interrupt_listener()

        # Get the handler that was registered
        handler = mock_signal.call_args[0][1]

        # Ensure event is not set
        cli.interrupt_event.clear()
        assert not cli.interrupt_event.is_set()

        # Call the handler
        handler(signal.SIGINT, None)

        # Event should now be set
        assert cli.interrupt_event.is_set()

    def test_escape_and_ctrl_c_counters(self, cli):
        """Test escape and ctrl-c counter attributes."""
        assert hasattr(cli, "escape_count")
        assert hasattr(cli, "ctrl_c_count")
        assert hasattr(cli, "last_escape_time")
        assert hasattr(cli, "last_ctrl_c_time")

        # Initial values
        assert cli.escape_count == 0
        assert cli.ctrl_c_count == 0
        assert cli.last_escape_time == 0
        assert cli.last_ctrl_c_time == 0

    def test_concurrent_interrupt_handling(self, cli):
        """Test concurrent interrupt event handling."""
        set_count = 0
        clear_count = 0

        def set_event():
            nonlocal set_count
            cli.interrupt_event.set()
            if cli.interrupt_event.is_set():
                set_count += 1

        def clear_event():
            nonlocal clear_count
            cli.interrupt_event.clear()
            if not cli.interrupt_event.is_set():
                clear_count += 1

        # Simulate multiple concurrent sets and clears
        threads = []
        for i in range(5):
            if i % 2 == 0:
                t = threading.Thread(target=set_event)
            else:
                t = threading.Thread(target=clear_event)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All operations should have completed
        assert set_count + clear_count == 5

    @patch("signal.signal")
    def test_interrupt_listener_error_handling(self, mock_signal, cli):
        """Test error handling in interrupt listener setup."""
        mock_signal.side_effect = OSError("Cannot set signal handler")

        # Should not crash even if signal setup fails
        with pytest.raises(OSError):
            cli.start_interrupt_listener()

        # Event should remain unset
        assert not cli.interrupt_event.is_set()
