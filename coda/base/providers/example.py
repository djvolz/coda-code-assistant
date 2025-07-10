#!/usr/bin/env python3
"""Standalone example showing the providers module works without other Coda modules.

This example demonstrates that the providers module:
1. Has minimal external dependencies
2. Can be used in any project
3. Provides comprehensive LLM provider abstraction

When using this module standalone:
- Copy the entire providers directory to your project
- Import directly: from providers import BaseProvider, Message, ProviderRegistry
- Or run this example: python example.py
"""

import asyncio
from typing import Any

# Standalone imports - use these when copying this module to another project
try:
    # When running as standalone module
    from base import BaseProvider, Message, Role
    from constants import PROVIDERS
    from registry import ProviderFactory, ProviderRegistry
except ImportError:
    # When running from coda package
    from coda.base.providers import (
        PROVIDERS,
        BaseProvider,
        Message,
        ProviderFactory,
        ProviderRegistry,
        Role,
    )


def print_section(title: str) -> None:
    """Print a section header."""
    print(f"\n{'=' * 60}")
    print(f" {title}")
    print(f"{'=' * 60}\n")


def demonstrate_registry() -> None:
    """Demonstrate the provider registry."""
    print_section("Provider Registry")

    # List available providers
    print("Available providers:")
    for provider_name in ProviderRegistry.list_providers():
        provider_class = ProviderRegistry.get_provider_class(provider_name)
        print(f"  - {provider_name}: {provider_class.__name__}")

    # Show provider constants
    print("\nProvider identifiers (PROVIDERS):")
    print(f"  OCI_GENAI: {PROVIDERS.OCI_GENAI}")
    print(f"  LITELLM: {PROVIDERS.LITELLM}")
    print(f"  OLLAMA: {PROVIDERS.OLLAMA}")
    print(f"  MOCK: {PROVIDERS.MOCK}")


def demonstrate_mock_provider() -> None:
    """Demonstrate using the mock provider."""
    print_section("Mock Provider Demo")

    # Create a mock provider
    provider = ProviderRegistry.create_provider(PROVIDERS.MOCK)
    print(f"Created provider: {provider.__class__.__name__}")
    print(f"Provider name: {provider.name}")

    # List available models
    print("\nAvailable models:")
    models = provider.list_models()
    for model in models[:3]:  # Show first 3
        print(f"  - {model.name} ({model.provider})")
        print(f"    Context: {model.context_length}, Streaming: {model.supports_streaming}")

    # Create a chat completion
    messages = [
        Message(role=Role.SYSTEM, content="You are a helpful assistant."),
        Message(role=Role.USER, content="Hello! What's 2+2?"),
    ]

    print("\nSending chat completion request...")
    completion = provider.chat(
        model="gpt-4",
        messages=messages,
        temperature=0.7,
        max_tokens=100,
    )

    print(f"Response: {completion.content}")
    print(f"Model used: {completion.model}")
    if completion.usage:
        print(f"Usage: {completion.usage}")


async def demonstrate_streaming() -> None:
    """Demonstrate streaming responses."""
    print_section("Streaming Demo (Mock Provider)")

    # Create provider
    provider = ProviderRegistry.create_provider(PROVIDERS.MOCK)

    # Create messages
    messages = [
        Message(role=Role.USER, content="Tell me a short story about a robot."),
    ]

    print("Streaming response:")
    print("-" * 40)

    # Stream the response
    full_content = ""
    async for chunk in provider.achat_stream(
        model="gpt-4",
        messages=messages,
        temperature=0.8,
    ):
        if chunk.content:
            print(chunk.content, end="", flush=True)
            full_content += chunk.content

    print("\n" + "-" * 40)
    print(f"\nTotal chunks received: {len(full_content.split())}")


def demonstrate_factory() -> None:
    """Demonstrate the provider factory with configuration."""
    print_section("Provider Factory Demo")

    # Create factory with global config
    config = {
        "providers": {
            "mock": {
                "default_model": "gpt-4",
                "timeout": 30,
            },
            "litellm": {
                "api_key": "your-api-key-here",
                "api_base": "https://api.openai.com/v1",
            },
        }
    }

    factory = ProviderFactory(config)
    print("Created factory with configuration")

    # Create provider using factory
    provider = factory.create("mock")
    print(f"\nCreated provider via factory: {provider.__class__.__name__}")

    # List available providers through factory
    print("\nAvailable providers via factory:")
    for name in factory.list_available():
        print(f"  - {name}")


def demonstrate_custom_provider() -> None:
    """Demonstrate creating a custom provider."""
    print_section("Custom Provider Demo")

    class CustomProvider(BaseProvider):
        """A simple custom provider example."""

        @property
        def name(self) -> str:
            return "custom"

        def list_models(self) -> list:
            """List available models."""
            from base import Model

            return [
                Model(
                    id="custom-model-v1",
                    name="custom-model-v1",
                    provider="custom",
                    context_length=2048,
                    supports_streaming=True,
                )
            ]

        def chat(self, messages: list, model: str, **kwargs) -> Any:
            """Simple chat implementation."""
            from base import ChatCompletion

            # Simple echo response
            last_message = messages[-1].content if messages else "Hello"
            response = f"Echo: {last_message}"

            return ChatCompletion(
                content=response,
                model=model,
                usage={
                    "prompt_tokens": len(str(messages)),
                    "completion_tokens": len(response.split()),
                    "total_tokens": len(str(messages)) + len(response.split()),
                },
            )

        def chat_stream(self, messages: list, model: str, **kwargs):
            """Simple streaming implementation."""
            from base import ChatCompletionChunk

            response = "This is a streaming response from custom provider."
            for word in response.split():
                yield ChatCompletionChunk(
                    content=word + " ",
                    model=model,
                )

        async def achat(self, messages: list, model: str, **kwargs) -> Any:
            """Async chat implementation."""
            # Simply call sync version for this example
            return self.chat(messages, model, **kwargs)

        async def achat_stream(self, messages: list, model: str, **kwargs):
            """Async streaming implementation."""
            from base import ChatCompletionChunk

            response = "This is an async streaming response from custom provider."
            for word in response.split():
                yield ChatCompletionChunk(
                    content=word + " ",
                    model=model,
                )
                await asyncio.sleep(0.1)  # Simulate delay

    # Register custom provider
    ProviderRegistry.register("custom", CustomProvider)
    print("Registered custom provider")

    # Create and use custom provider
    provider = ProviderRegistry.create_provider("custom")
    print(f"\nCreated custom provider: {provider.name}")

    # Test custom provider
    messages = [Message(role=Role.USER, content="Test message")]
    response = provider.chat(messages, "custom-model-v1")
    print(f"Custom provider response: {response.content}")


def main():
    """Run all demonstrations."""
    print("=== Coda Providers Module Demo ===")
    print("\nThis demonstrates the providers module working standalone")
    print("with minimal external dependencies.\n")

    # Run demonstrations
    demonstrate_registry()
    demonstrate_mock_provider()
    demonstrate_factory()
    demonstrate_custom_provider()

    # Run async demonstration
    print("\n" + "=" * 60)
    print(" Running async streaming demo...")
    print("=" * 60)
    asyncio.run(demonstrate_streaming())

    # Summary
    print_section("Summary")
    print("✓ Providers module works standalone!")
    print("✓ Minimal external dependencies (only standard library + provider SDKs)")
    print("✓ Can be copy-pasted to any project")
    print("✓ Provides complete LLM provider abstraction")
    print("✓ Supports sync and async operations")
    print("✓ Extensible with custom providers")


if __name__ == "__main__":
    main()
