# Testing the TUI Interface

This document describes how to test the Terminal User Interface (TUI) for CODA.

## Test Structure

We have two types of tests for the TUI interface:

1. **Smoke Tests** (`tests/test_tui_smoke.py`) - Unit tests that don't require a terminal
2. **Interactive Tests** (`tests/test_tui_interface.py`) - Integration tests using pexpect

## Running Tests

### Quick Smoke Tests (CI-friendly)
```bash
make test-tui
# or
uv run pytest tests/test_tui_smoke.py -v
```

### Interactive Tests (Manual)
```bash
make test-tui-interactive
# or
uv run pytest tests/test_tui_interface.py -v -s
```

### All Tests
```bash
uv run pytest -m tui -v
```

## Test Coverage

### Smoke Tests Cover:
- App initialization
- Component creation
- Command providers
- Completion helper
- Mode switching
- Error handling

### Interactive Tests Cover:
- App startup and shutdown
- Text input functionality
- Ctrl+P command palette
- Tab completion
- Slash commands
- Keyboard shortcuts
- Scrolling behavior
- Error recovery

## Writing New Tests

### For Smoke Tests:
```python
def test_new_component(self):
    """Test description."""
    app = IntegratedTUICLI()
    # Test component behavior without running the app
    assert app.some_method() == expected_value
```

### For Interactive Tests:
```python
def test_new_interaction(self, tui_app):
    """Test description."""
    # Send input
    tui_app.send("test input\r")
    time.sleep(0.5)
    
    # Check output
    tui_app.expect("expected output", timeout=2)
```

## CI/CD Integration

The tests are automatically run in GitHub Actions when:
- Files matching `coda/cli/tui_*.py` are changed
- Test files are updated
- The workflow file is modified

Interactive tests are automatically skipped in CI environments.

## Manual Testing

For manual testing during development:

```bash
# Run the TUI interface
uv run coda --tui

# Run with specific provider
uv run coda --tui --provider oci_genai

# Run test helper
uv run python tests/test_tui_interface.py
```

## Debugging

To debug TUI apps:

```bash
# Run with Textual dev mode (TUI is built with Textual)
textual run --dev coda.cli.tui_integrated:IntegratedTUICLI

# Disable animations for testing
export TEXTUAL_ANIMATIONS=false
uv run coda --tui
```

## Known Issues

1. Some terminal emulators may not support all key sequences
2. Interactive tests require a real terminal (not redirected output)
3. F-key shortcuts may be intercepted by the terminal emulator

## Test Markers

- `@pytest.mark.tui` - All TUI-related tests
- `@pytest.mark.interactive` - Tests requiring terminal interaction
- `@pytest.mark.unit` - Unit tests (no external dependencies)