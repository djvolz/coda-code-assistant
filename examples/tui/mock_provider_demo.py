#!/usr/bin/env python3
"""Demo the TUI interface with a simple mock provider."""

from coda.cli.tui_integrated import IntegratedTUICLI
from coda.providers import Message, Role
import asyncio

class MockProvider:
    """Mock provider for testing."""
    
    def list_models(self):
        """Return mock models."""
        class MockModel:
            def __init__(self, id):
                self.id = id
        return [MockModel("mock-model-1"), MockModel("mock-model-2")]
    
    def chat_stream(self, messages, model, temperature=0.7, max_tokens=2000):
        """Mock chat_stream method that returns an iterator."""
        # Simulate streaming response
        response = "Hello! This is a mock response from the AI. I received your message and I'm responding in a simulated streaming fashion. Each word appears progressively to demonstrate the streaming capability of the TUI interface. You can see how the text builds up character by character, creating a smooth streaming experience similar to real AI responses."
        
        class MockChunk:
            def __init__(self, content):
                self.content = content
        
        import time
        
        # Stream the response word by word with realistic timing
        words = response.split()
        for i, word in enumerate(words):
            time.sleep(0.2)  # Simulate network delay
            if i == 0:
                yield MockChunk(word)
            else:
                yield MockChunk(" " + word)

class MockFactory:
    """Mock factory for testing."""
    
    def create(self, provider_name):
        return MockProvider()

def run_demo():
    """Run the demo."""
    print("Starting TUI CLI demo with mock provider...")
    print("Type 'hi' and press Enter to test.")
    print("Use Ctrl+C to exit.")
    
    # Create mock factory
    factory = MockFactory()
    
    # Run the app
    app = IntegratedTUICLI(
        provider_factory=factory,
        provider_name="mock",
        model="mock-model-1"
    )
    
    app.run()

if __name__ == "__main__":
    run_demo()