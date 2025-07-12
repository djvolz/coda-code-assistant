"""Provider management and initialization for CLI."""

from rich.console import Console

from coda.base.providers import BaseProvider, Model, ProviderFactory
from coda.services.config import AppConfig

# Theme is now passed in via constructor


class ProviderManager:
    """Manages provider initialization and model discovery."""

    def __init__(self, config: AppConfig, console: Console):
        self.config = config
        self.console = console
        self.factory = ProviderFactory(config.to_dict())
        self.theme = config.theme_manager.get_console_theme()

    def initialize_provider(self, provider_name: str | None = None) -> BaseProvider:
        """Initialize and connect to a provider."""
        # Use default provider if not specified
        provider_name = provider_name or self.config.default_provider

        self.console.print(
            f"\n[{self.theme.success}]Provider:[/{self.theme.success}] {provider_name}"
        )
        self.console.print(
            f"[{self.theme.warning}]Initializing {provider_name}...[/{self.theme.warning}]"
        )

        # Create provider instance
        provider_instance = self.factory.create(provider_name)
        self.console.print(
            f"[{self.theme.success}]✓ Connected to {provider_name}[/{self.theme.success}]"
        )

        return provider_instance

    def get_chat_models(self, provider: BaseProvider) -> tuple[list[Model], list[Model]]:
        """Get available chat models from provider.

        Returns:
            Tuple of (all_models, unique_chat_models)
        """
        # List all models
        models = provider.list_models()
        self.console.print(
            f"[{self.theme.success}]✓ Found {len(models)} available models[/{self.theme.success}]"
        )

        # Filter for chat models - different providers use different indicators
        chat_models = [
            m
            for m in models
            if "CHAT" in m.metadata.get("capabilities", [])  # OCI GenAI
            or m.provider in ["ollama", "litellm"]  # These providers only list chat models
        ]

        # If no chat models found, use all models
        if not chat_models:
            chat_models = models

        # Deduplicate models by ID
        seen = set()
        unique_models = []
        for m in chat_models:
            if m.id not in seen:
                seen.add(m.id)
                unique_models.append(m)

        return models, unique_models

    def select_model(
        self, unique_models: list[Model], model: str | None = None, one_shot: bool = False
    ) -> str:
        """Select a model for chat.

        Args:
            unique_models: List of unique chat models
            model: Pre-selected model ID
            one_shot: Whether in one-shot mode (auto-select first model)

        Returns:
            Selected model ID
        """
        if model:
            return model

        if one_shot:
            # For one-shot, use the first available chat model
            selected = unique_models[0].id
            self.console.print(
                f"[{self.theme.success}]Auto-selected model:[/{self.theme.success}] {selected}"
            )
            return selected

        # Use interactive model selector
        import asyncio

        from .completion_selector import CompletionModelSelector

        selector = CompletionModelSelector(unique_models, self.console)
        # Run the async selector in a new event loop
        return asyncio.run(selector.select_interactive())

    def get_provider_error_message(
        self, error: Exception, provider_name: str
    ) -> tuple[str, str | None]:
        """Get user-friendly error message for provider errors.

        Returns:
            Tuple of (error_message, help_text)
        """
        error_str = str(error)

        if "compartment_id is required" in error_str:
            return (
                "OCI compartment ID not configured",
                "Please set it via one of these methods:\n"
                "1. Environment variable: [cyan]export OCI_COMPARTMENT_ID='your-compartment-id'[/cyan]\n"
                "2. Coda config file: [cyan]~/.config/coda/config.toml[/cyan]",
            )
        elif "Unknown provider" in error_str:
            available = ", ".join(self.factory.list_available())
            return (f"Provider '{provider_name}' not found", f"Available providers: {available}")
        else:
            return (str(error), None)
