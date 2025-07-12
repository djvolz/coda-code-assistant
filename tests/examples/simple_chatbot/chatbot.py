#!/usr/bin/env python3
"""
Simple chatbot using Coda modules.

This example demonstrates:
- Basic configuration usage
- Provider initialization
- Simple chat loop
"""

import sys
from pathlib import Path

# Add the project root to the path so we can import coda modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from coda.base.config import Config
from coda.base.providers import ProviderFactory


def main():
    print("=== Coda Simple Chatbot ===\n")

    # Initialize configuration
    try:
        config = Config()
    except Exception as e:
        print(f"Failed to load configuration: {e}")
        print("\nMake sure you have a config file at ~/.config/coda/config.toml")
        print("or set environment variables like CODA_OPENAI_API_KEY")
        return 1

    # Create provider factory
    factory = ProviderFactory(config.to_dict())

    # List available providers
    available = factory.list_available()
    if not available:
        print("No providers available. Please configure at least one provider.")
        return 1

    print("Available providers:", ", ".join(available))

    # Let user choose provider or use default
    if len(available) == 1:
        provider_name = available[0]
        print(f"Using {provider_name}")
    else:
        provider_name = input("Choose provider (or press Enter for first available): ").strip()
        if not provider_name:
            provider_name = available[0]
        elif provider_name not in available:
            print(f"Provider '{provider_name}' not available")
            return 1

    # Create provider
    try:
        provider = factory.create(provider_name)
    except Exception as e:
        print(f"Failed to create provider: {e}")
        return 1

    # Get available models
    try:
        models = provider.list_models()
        if not models:
            print("No models available for this provider")
            return 1

        model_id = models[0].id
        print(f"Using model: {model_id}")
    except Exception as e:
        print(f"Failed to get models: {e}")
        return 1

    # Chat loop
    print(f"\nChatting with {provider_name}. Commands:")
    print("  'quit' or 'exit' - Exit the chatbot")
    print("  'clear' - Clear conversation history")
    print("  'model' - Change model")
    print()

    messages = []

    while True:
        # Get user input
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n\nGoodbye!")
            break

        # Handle commands
        if user_input.lower() in ["quit", "exit"]:
            print("\nGoodbye!")
            break

        if user_input.lower() == "clear":
            messages = []
            print("\nConversation cleared.\n")
            continue

        if user_input.lower() == "model":
            print("\nAvailable models:")
            for i, model in enumerate(models):
                print(f"  {i + 1}. {model.id} - {model.name}")
            try:
                choice = int(input("Choose model number: ")) - 1
                if 0 <= choice < len(models):
                    model_id = models[choice].id
                    print(f"Switched to model: {model_id}\n")
                else:
                    print("Invalid choice\n")
            except ValueError:
                print("Invalid input\n")
            continue

        if not user_input:
            continue

        # Add user message
        messages.append({"role": "user", "content": user_input})

        # Get AI response
        try:
            print("\nThinking...", end="", flush=True)

            response = provider.chat(messages=messages, model=model_id, temperature=0.7)

            # Clear "Thinking..." and show response
            print("\r" + " " * 20 + "\r", end="")  # Clear the line

            assistant_response = response["content"]
            messages.append({"role": "assistant", "content": assistant_response})

            print(f"Assistant: {assistant_response}\n")

            # Show token usage if available
            if "usage" in response:
                usage = response["usage"]
                total = usage.get("total_tokens", 0)
                if total > 0:
                    print(f"[Tokens used: {total}]\n")

        except Exception as e:
            print(f"\rError: {e}\n")
            # Remove the failed user message
            messages.pop()

    return 0


if __name__ == "__main__":
    sys.exit(main())
