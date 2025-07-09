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
        with patch("coda.cli.interactive_cli.ModelManager"):
            cli = InteractiveCLI()
            cli.session_manager = Mock()
            cli.chat_session = Mock()
            return cli

    def test_initial_interrupt_state(self, cli):
        """Test initial state of interrupt flag."""
        assert cli.interrupted is False
        assert cli.original_sigint_handler is None

    def test_reset_interrupt(self, cli):
        """Test reset_interrupt clears the flag."""
        cli.interrupted = True

        cli.reset_interrupt()

        assert cli.interrupted is False

    def test_handle_interrupt_sets_flag(self, cli):
        """Test interrupt handler sets the flag."""
        assert cli.interrupted is False

        cli._handle_interrupt(signal.SIGINT, None)

        assert cli.interrupted is True

    def test_handle_interrupt_with_print(self, cli):
        """Test interrupt handler with print output."""
        with patch("coda.cli.interactive_cli.print") as mock_print:
            cli._handle_interrupt(signal.SIGINT, None)

            # Should print interrupt message
            mock_print.assert_called_once()
            assert "Interrupt received" in str(mock_print.call_args)

    @patch("coda.cli.interactive_cli.signal")
    def test_start_interrupt_listener(self, mock_signal, cli):
        """Test starting interrupt listener registers handler."""
        # Mock the current handler
        mock_signal.getsignal.return_value = signal.default_int_handler

        cli.start_interrupt_listener()

        # Should store original handler
        assert cli.original_sigint_handler == signal.default_int_handler

        # Should register new handler
        mock_signal.signal.assert_called_with(signal.SIGINT, cli._handle_interrupt)

    @patch("coda.cli.interactive_cli.signal")
    def test_stop_interrupt_listener(self, mock_signal, cli):
        """Test stopping interrupt listener restores handler."""
        cli.original_sigint_handler = signal.default_int_handler

        cli.stop_interrupt_listener()

        # Should restore original handler
        mock_signal.signal.assert_called_with(signal.SIGINT, signal.default_int_handler)

        # Should clear stored handler
        assert cli.original_sigint_handler is None

    @patch("coda.cli.interactive_cli.signal")
    def test_stop_interrupt_listener_no_original(self, mock_signal, cli):
        """Test stopping listener when no original handler stored."""
        cli.original_sigint_handler = None

        cli.stop_interrupt_listener()

        # Should not call signal.signal
        mock_signal.signal.assert_not_called()

    def test_interrupt_flag_thread_safety(self, cli):
        """Test interrupt flag is thread-safe."""
        results = []

        def set_interrupt():
            cli._handle_interrupt(signal.SIGINT, None)
            results.append(cli.interrupted)

        def reset_interrupt():
            time.sleep(0.01)  # Small delay to ensure ordering
            cli.reset_interrupt()
            results.append(cli.interrupted)

        # Run in threads
        t1 = threading.Thread(target=set_interrupt)
        t2 = threading.Thread(target=reset_interrupt)

        t1.start()
        t2.start()
        t1.join()
        t2.join()

        # Should have set then reset
        assert results[0] is True
        assert results[1] is False

    def test_multiple_interrupts(self, cli):
        """Test handling multiple interrupts."""
        cli._handle_interrupt(signal.SIGINT, None)
        assert cli.interrupted is True

        # Second interrupt should still leave flag set
        cli._handle_interrupt(signal.SIGINT, None)
        assert cli.interrupted is True

    def test_interrupt_during_input(self, cli):
        """Test interrupt handling during get_input."""
        with patch("coda.cli.interactive_cli.PromptSession"):
            # Set interrupt flag before input
            cli.interrupted = True

            result = cli.get_input()

            # Should return None and reset flag
            assert result is None
            assert cli.interrupted is False

    def test_interrupt_cleanup_on_exit(self, cli):
        """Test interrupt handler cleanup on CLI exit."""
        with patch("coda.cli.interactive_cli.signal") as mock_signal:
            cli.original_sigint_handler = signal.default_int_handler

            # Simulate cleanup
            cli.stop_interrupt_listener()

            # Handler should be restored
            mock_signal.signal.assert_called_with(signal.SIGINT, signal.default_int_handler)

    @patch("coda.cli.interactive_cli.signal")
    def test_interrupt_listener_idempotent(self, mock_signal, cli):
        """Test starting interrupt listener multiple times is safe."""
        mock_signal.getsignal.return_value = signal.default_int_handler

        cli.start_interrupt_listener()
        first_handler = cli.original_sigint_handler

        # Start again
        cli.start_interrupt_listener()

        # Should not change stored handler
        assert cli.original_sigint_handler == first_handler

        # Should register handler twice (not ideal but safe)
        assert mock_signal.signal.call_count == 2

    def test_interrupt_with_custom_handler(self, cli):
        """Test interrupt with custom signal handler."""
        custom_handler = Mock()

        with patch("coda.cli.interactive_cli.signal") as mock_signal:
            mock_signal.getsignal.return_value = custom_handler

            cli.start_interrupt_listener()

            # Should store custom handler
            assert cli.original_sigint_handler == custom_handler

    def test_interrupt_flag_persistence(self, cli):
        """Test interrupt flag persists until reset."""
        cli._handle_interrupt(signal.SIGINT, None)
        assert cli.interrupted is True

        # Flag should persist
        assert cli.interrupted is True
        assert cli.interrupted is True

        # Until explicitly reset
        cli.reset_interrupt()
        assert cli.interrupted is False

    @pytest.mark.parametrize(
        "signal_num,frame",
        [
            (signal.SIGINT, None),
            (signal.SIGINT, Mock()),
            (2, None),  # SIGINT numeric value
        ],
    )
    def test_handle_interrupt_parameters(self, cli, signal_num, frame):
        """Test interrupt handler with different parameters."""
        cli._handle_interrupt(signal_num, frame)
        assert cli.interrupted is True

    def test_interrupt_integration_with_chat(self, cli):
        """Test interrupt handling integration with chat flow."""
        with patch("coda.cli.interactive_cli.PromptSession") as mock_session:
            # Simulate interrupt during chat
            def side_effect(*args, **kwargs):
                if mock_session.prompt.call_count == 1:
                    cli._handle_interrupt(signal.SIGINT, None)
                    raise KeyboardInterrupt()
                return "follow-up input"

            mock_session.prompt.side_effect = side_effect

            # First call should be interrupted
            result = cli.get_input()
            assert result is None

            # Flag should be reset for next input
            assert cli.interrupted is False

    def test_concurrent_interrupt_handling(self, cli):
        """Test concurrent interrupt signal handling."""
        interrupt_count = 0

        def counting_handler(signum, frame):
            nonlocal interrupt_count
            interrupt_count += 1
            cli._handle_interrupt(signum, frame)

        cli._handle_interrupt = counting_handler

        # Simulate multiple concurrent interrupts
        threads = []
        for _ in range(5):
            t = threading.Thread(target=lambda: cli._handle_interrupt(signal.SIGINT, None))
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # All interrupts should be handled
        assert interrupt_count == 5
        assert cli.interrupted is True

    def test_interrupt_listener_error_handling(self, cli):
        """Test error handling in interrupt listener setup."""
        with patch("coda.cli.interactive_cli.signal.signal") as mock_signal:
            mock_signal.side_effect = OSError("Cannot set signal handler")

            # Should not crash
            try:
                cli.start_interrupt_listener()
            except OSError:
                pass  # Expected in test

            # Flag should remain unset
            assert cli.interrupted is False
