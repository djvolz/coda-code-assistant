#!/usr/bin/env python3
"""Demo the Textual interface with a simple mock provider."""

from coda.cli.textual_integrated import IntegratedTextualCLI
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
    
    async def chat(self, messages, model, stream=True):
        """Mock chat method."""
        # Simulate streaming response
        response = "Hello! This is a mock response from the AI. I received your message and I'm responding in a simulated streaming fashion."
        
        class MockChunk:
            def __init__(self, content):
                self.content = content
        
        # Stream the response word by word
        words = response.split()
        for i, word in enumerate(words):
            await asyncio.sleep(0.1)  # Simulate delay
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
    print("Starting Textual CLI demo with mock provider...")
    print("Type 'hi' and press Enter to test.")
    print("Use Ctrl+C to exit.")
    
    # Create mock factory
    factory = MockFactory()
    
    # Run the app
    app = IntegratedTextualCLI(
        provider_factory=factory,
        provider_name="mock",
        model="mock-model-1"
    )
    
    app.run()

if __name__ == "__main__":
    run_demo()