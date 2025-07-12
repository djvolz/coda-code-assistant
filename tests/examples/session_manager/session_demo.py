#!/usr/bin/env python3
"""
Session management example.

This example demonstrates:
- Creating and loading sessions
- Conversation persistence
- Session branching
- History management
"""

import sys
from pathlib import Path

# Add the project root to the path so we can import coda modules
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

import json
from datetime import datetime

from coda.base.config import Config
from coda.base.providers import ProviderFactory
from coda.base.session import SessionManager


class SessionDemo:
    def __init__(self):
        print("Initializing Session Demo...")

        # Load configuration
        self.config = Config()

        # Create provider
        self.factory = ProviderFactory(self.config.to_dict())
        available = self.factory.list_available()

        if not available:
            raise RuntimeError("No providers available")

        # Use first available provider
        self.provider_name = available[0]
        self.provider = self.factory.create(self.provider_name)
        self.model_id = self.provider.list_models()[0].id

        # Initialize session manager
        self.session_manager = SessionManager(self.config.to_dict())

        print(f"Using provider: {self.provider_name}")
        print(f"Using model: {self.model_id}")
        print()

    def list_sessions(self):
        """Show all available sessions."""
        sessions = self.session_manager.list_sessions()

        if not sessions:
            print("No sessions found.\n")
            return

        print("\nAvailable sessions:")
        print("-" * 60)

        for session in sessions:
            name = session.get("name", "unnamed")
            message_count = session.get("message_count", 0)
            created = session.get("created_at", "unknown")
            updated = session.get("updated_at", "unknown")

            # Format timestamps
            if created != "unknown":
                try:
                    created_dt = datetime.fromisoformat(created)
                    created = created_dt.strftime("%Y-%m-%d %H:%M")
                except ValueError:
                    pass

            print(f"  Name: {name}")
            print(f"  Messages: {message_count}")
            print(f"  Created: {created}")
            print(f"  Updated: {updated}")
            print("-" * 60)

    def start_session(self, name: str):
        """Start or resume a session."""
        # Load or create session
        session = self.session_manager.create_session(name)
        messages = session.get_messages()

        print(f"\nSession '{name}' loaded with {len(messages)} messages")

        if messages:
            print("\nLast 3 messages:")
            for msg in messages[-3:]:
                role = msg["role"].capitalize()
                content = msg["content"]
                if len(content) > 80:
                    content = content[:77] + "..."
                print(f"  {role}: {content}")

        print("\nCommands:")
        print("  'quit' - Save and exit session")
        print("  'history' - Show conversation history")
        print("  'save' - Save session")
        print("  'stats' - Show session statistics")
        print("  'export' - Export session to JSON")
        print("  'clear' - Clear session (requires confirmation)")
        print()

        while True:
            try:
                user_input = input("You: ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\n")
                break

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() == "quit":
                break

            elif user_input.lower() == "history":
                self.show_history(session)
                continue

            elif user_input.lower() == "save":
                self.session_manager.save_session(session)
                print("Session saved.\n")
                continue

            elif user_input.lower() == "stats":
                self.show_stats(session)
                continue

            elif user_input.lower() == "export":
                self.export_session(session, name)
                continue

            elif user_input.lower() == "clear":
                confirm = input("Are you sure you want to clear this session? (yes/no): ")
                if confirm.lower() == "yes":
                    session.messages = []
                    print("Session cleared.\n")
                else:
                    print("Clear cancelled.\n")
                continue

            # Add user message
            session.add_message({"role": "user", "content": user_input})

            # Get AI response
            try:
                print("\nThinking...", end="", flush=True)

                response = self.provider.chat(
                    messages=session.get_messages(), model=self.model_id, temperature=0.7
                )

                print("\r" + " " * 20 + "\r", end="")  # Clear thinking message

                assistant_response = response["content"]
                session.add_message(
                    {
                        "role": "assistant",
                        "content": assistant_response,
                        "model": self.model_id,
                        "provider": self.provider_name,
                    }
                )

                print(f"Assistant: {assistant_response}\n")

                # Show token usage
                if "usage" in response:
                    tokens = response["usage"].get("total_tokens", 0)
                    if tokens > 0:
                        print(f"[Tokens: {tokens}]\n")

            except Exception as e:
                print(f"\rError: {e}\n")
                # Remove the failed user message
                session.messages.pop()

        # Auto-save on exit
        print("Saving session...")
        self.session_manager.save_session(session)
        print(f"Session '{name}' saved.\n")

    def show_history(self, session):
        """Display conversation history."""
        messages = session.get_messages()

        if not messages:
            print("\nNo messages in session.\n")
            return

        print(f"\n--- Conversation History ({len(messages)} messages) ---")

        for i, msg in enumerate(messages, 1):
            role = msg["role"].capitalize()
            content = msg["content"]

            # Show metadata for assistant messages
            if role == "Assistant" and "model" in msg:
                print(f"\n[{i}] {role} ({msg.get('model', 'unknown')})")
            else:
                print(f"\n[{i}] {role}:")

            # Wrap long messages
            if len(content) > 200:
                print(content[:200] + "...")
                print(f"    [... {len(content) - 200} more characters]")
            else:
                print(content)

        print("\n--- End History ---\n")

    def show_stats(self, session):
        """Show session statistics."""
        messages = session.get_messages()

        if not messages:
            print("\nNo messages in session.\n")
            return

        # Calculate statistics
        user_messages = [m for m in messages if m["role"] == "user"]
        assistant_messages = [m for m in messages if m["role"] == "assistant"]

        total_user_chars = sum(len(m["content"]) for m in user_messages)
        total_assistant_chars = sum(len(m["content"]) for m in assistant_messages)

        # Model usage
        model_usage = {}
        for msg in assistant_messages:
            model = msg.get("model", "unknown")
            model_usage[model] = model_usage.get(model, 0) + 1

        print("\n--- Session Statistics ---")
        print(f"Total messages: {len(messages)}")
        print(f"User messages: {len(user_messages)}")
        print(f"Assistant messages: {len(assistant_messages)}")
        print(f"User characters: {total_user_chars:,}")
        print(f"Assistant characters: {total_assistant_chars:,}")

        if user_messages:
            avg_user = total_user_chars / len(user_messages)
            print(f"Avg user message: {avg_user:.0f} chars")

        if assistant_messages:
            avg_assistant = total_assistant_chars / len(assistant_messages)
            print(f"Avg assistant message: {avg_assistant:.0f} chars")

        print("\nModels used:")
        for model, count in model_usage.items():
            print(f"  {model}: {count} responses")

        print("--- End Statistics ---\n")

    def export_session(self, session, name: str):
        """Export session to JSON file."""
        filename = f"session_{name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"

        export_data = {
            "session_name": name,
            "exported_at": datetime.now().isoformat(),
            "provider": self.provider_name,
            "model": self.model_id,
            "message_count": len(session.get_messages()),
            "messages": session.get_messages(),
        }

        try:
            with open(filename, "w") as f:
                json.dump(export_data, f, indent=2)
            print(f"Session exported to: {filename}\n")
        except Exception as e:
            print(f"Export failed: {e}\n")

    def branch_session(self, source_name: str, target_name: str):
        """Create a new session branched from an existing one."""
        # Load source session
        source = self.session_manager.create_session(source_name)
        source_messages = source.get_messages()

        if not source_messages:
            print(f"Source session '{source_name}' has no messages.\n")
            return

        # Create target session with copied messages
        target = self.session_manager.create_session(target_name)
        target.messages = source_messages.copy()

        # Save the new session
        self.session_manager.save_session(target)

        print(f"Created branch '{target_name}' from '{source_name}'")
        print(f"Copied {len(source_messages)} messages\n")


def main():
    try:
        demo = SessionDemo()
    except Exception as e:
        print(f"Failed to initialize: {e}")
        return 1

    while True:
        print("\n=== Session Manager Demo ===")
        print("1. List sessions")
        print("2. Start/resume session")
        print("3. Branch session")
        print("4. Delete session")
        print("5. Quit")

        try:
            choice = input("\nChoice: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n")
            break

        if choice == "1":
            demo.list_sessions()

        elif choice == "2":
            name = input("Session name: ").strip()
            if name:
                demo.start_session(name)

        elif choice == "3":
            source = input("Source session name: ").strip()
            target = input("Target session name: ").strip()
            if source and target:
                demo.branch_session(source, target)

        elif choice == "4":
            name = input("Session name to delete: ").strip()
            if name:
                confirm = input(f"Delete session '{name}'? (yes/no): ")
                if confirm.lower() == "yes":
                    # Note: SessionManager doesn't have delete method in base,
                    # but we can demonstrate the concept
                    print(f"Session '{name}' would be deleted (not implemented in base)\n")

        elif choice == "5":
            print("Goodbye!")
            break

        else:
            print("Invalid choice")

    return 0


if __name__ == "__main__":
    sys.exit(main())
