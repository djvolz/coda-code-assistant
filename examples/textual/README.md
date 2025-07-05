# Textual UI Examples

This directory contains examples and tests for the Textual-based CLI interface.

## Files

- `mock_provider_demo.py` - Demo the Textual interface with a mock AI provider that simulates streaming responses
- `connection_test.py` - Test script to verify the Textual interface connects properly to real providers
- `basic_interface_test.py` - Basic test of interface creation without provider integration

## Usage

### Mock Provider Demo
```bash
uv run python examples/textual/mock_provider_demo.py
```
Shows the Textual interface with a simulated AI provider. Type messages to see streaming responses.

### Connection Test
```bash
uv run python examples/textual/connection_test.py
```
Tests that the interface can connect to the real OCI provider without errors.

### Basic Interface Test
```bash
uv run python examples/textual/basic_interface_test.py
```
Verifies the basic interface components can be created successfully.

## Running the Real Interface

To use the actual Textual interface with a real provider:

```bash
# With OCI GenAI
uv run coda --textual --provider oci_genai

# With any configured provider
uv run coda --textual
```

## Features Demonstrated

- Dynamic terminal UI with real-time updates
- Command palette (Ctrl+P)
- Streaming AI responses
- Provider integration
- Error handling
- Message history
- Mode switching