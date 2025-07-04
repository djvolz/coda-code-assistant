#!/usr/bin/env python3
"""
Enhanced OCI GenAI Model Discovery with LiteLLM Integration

This script demonstrates:
1. How to discover available models from OCI GenAI
2. How to format model names for use with LiteLLM
3. How to validate model compatibility with different capabilities
4. How to create a dynamic model registry

Requirements:
- OCI Python SDK: pip install oci
- LiteLLM: pip install litellm
- Configured OCI credentials (~/.oci/config)
- Appropriate IAM permissions for GenAI service
"""

import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any

import oci


@dataclass
class ModelInfo:
    """Structured model information for easier handling."""

    id: str
    display_name: str
    vendor: str
    version: str
    capabilities: list[str]
    lifecycle_state: str
    type: str
    is_long_term_supported: bool
    time_created: datetime
    compartment_id: str | None = None
    litellm_name: str | None = None
    is_available: bool = True


class OCIGenAIModelDiscovery:
    """Class to handle OCI GenAI model discovery and registry management."""

    def __init__(self, config_profile: str = "DEFAULT"):
        """
        Initialize the model discovery client.

        Args:
            config_profile: OCI configuration profile name
        """
        self.config = oci.config.from_file(profile_name=config_profile)
        self.client = oci.generative_ai.GenerativeAiClient(self.config)
        self.models_cache: list[ModelInfo] = []
        self.last_refresh: datetime | None = None

    def discover_models(self, compartment_id: str, force_refresh: bool = False) -> list[ModelInfo]:
        """
        Discover available GenAI models from OCI.

        Args:
            compartment_id: The OCID of the compartment to search in
            force_refresh: Force refresh of cached models

        Returns:
            List of ModelInfo objects
        """
        # Use cache if available and not forcing refresh
        if self.models_cache and not force_refresh and self.last_refresh:
            return self.models_cache

        try:
            response = self.client.list_models(compartment_id=compartment_id)

            models = []
            for model in response.data.items:
                # Generate LiteLLM compatible model name
                litellm_name = self._generate_litellm_model_name(model)

                model_info = ModelInfo(
                    id=model.id,
                    display_name=model.display_name,
                    vendor=model.vendor,
                    version=model.version,
                    capabilities=model.capabilities,
                    lifecycle_state=model.lifecycle_state,
                    type=model.type,
                    is_long_term_supported=model.is_long_term_supported,
                    time_created=model.time_created,
                    compartment_id=model.compartment_id,
                    litellm_name=litellm_name,
                    is_available=(model.lifecycle_state == "ACTIVE"),
                )
                models.append(model_info)

            # Cache the results
            self.models_cache = models
            self.last_refresh = datetime.now()

            return models

        except Exception as e:
            print(f"Error discovering models: {e}")
            return []

    def _generate_litellm_model_name(self, model) -> str:
        """
        Generate a LiteLLM compatible model name from OCI model info.

        Args:
            model: OCI model object

        Returns:
            LiteLLM compatible model name
        """
        # For OCI GenAI, the model name format is typically:
        # oci_genai/{model_id}
        return f"oci_genai/{model.id}"

    def get_models_by_capability(self, compartment_id: str, capability: str) -> list[ModelInfo]:
        """
        Get models that support a specific capability.

        Args:
            compartment_id: The OCID of the compartment
            capability: The capability to filter by

        Returns:
            List of ModelInfo objects with the specified capability
        """
        all_models = self.discover_models(compartment_id)
        return [
            model for model in all_models if capability in model.capabilities and model.is_available
        ]

    def get_chat_models(self, compartment_id: str) -> list[ModelInfo]:
        """Get models that support chat/conversation capabilities."""
        return self.get_models_by_capability(compartment_id, "CHAT")

    def get_text_generation_models(self, compartment_id: str) -> list[ModelInfo]:
        """Get models that support text generation."""
        return self.get_models_by_capability(compartment_id, "TEXT_GENERATION")

    def get_embedding_models(self, compartment_id: str) -> list[ModelInfo]:
        """Get models that support text embeddings."""
        return self.get_models_by_capability(compartment_id, "TEXT_EMBEDDINGS")

    def generate_litellm_model_config(
        self, compartment_id: str, service_endpoint: str = None
    ) -> dict[str, Any]:
        """
        Generate a LiteLLM model configuration for all available models.

        Args:
            compartment_id: The OCID of the compartment
            service_endpoint: Optional custom service endpoint

        Returns:
            Dictionary containing LiteLLM model configuration
        """
        models = self.discover_models(compartment_id)

        config = {"model_list": [], "litellm_settings": {"drop_params": True, "set_verbose": False}}

        for model in models:
            if not model.is_available:
                continue

            model_config = {
                "model_name": model.litellm_name,
                "litellm_params": {
                    "model": model.litellm_name,
                    "compartment_id": compartment_id,
                    "api_base": service_endpoint
                    or f"https://inference.generativeai.{self.config.get('region', 'us-ashburn-1')}.oci.oraclecloud.com",
                },
                "model_info": {
                    "id": model.id,
                    "display_name": model.display_name,
                    "vendor": model.vendor,
                    "version": model.version,
                    "capabilities": model.capabilities,
                    "type": model.type,
                    "is_long_term_supported": model.is_long_term_supported,
                },
            }

            config["model_list"].append(model_config)

        return config

    def export_model_registry(
        self, compartment_id: str, output_file: str = "oci_genai_models.json"
    ) -> None:
        """
        Export discovered models to a JSON file.

        Args:
            compartment_id: The OCID of the compartment
            output_file: Output file path
        """
        config = self.generate_litellm_model_config(compartment_id)

        with open(output_file, "w") as f:
            json.dump(config, f, indent=2, default=str)

        print(f"Model registry exported to {output_file}")

    def print_model_summary(self, compartment_id: str) -> None:
        """Print a comprehensive summary of available models."""
        models = self.discover_models(compartment_id)

        if not models:
            print("No models found.")
            return

        print("\n🤖 OCI GenAI Model Discovery Summary")
        print(f"Found {len(models)} models")
        print("=" * 80)

        # Group by capability
        capabilities_map = {}
        for model in models:
            for capability in model.capabilities:
                if capability not in capabilities_map:
                    capabilities_map[capability] = []
                capabilities_map[capability].append(model)

        for capability, cap_models in capabilities_map.items():
            print(f"\n📋 {capability} Models ({len(cap_models)}):")
            print("-" * 40)

            for model in cap_models:
                status = "✅ Available" if model.is_available else "❌ Unavailable"
                lts = "🔒 LTS" if model.is_long_term_supported else "📅 Standard"

                print(f"  • {model.display_name} ({model.vendor})")
                print(f"    ID: {model.id}")
                print(f"    LiteLLM: {model.litellm_name}")
                print(f"    Status: {status} | {lts}")
                print(f"    Version: {model.version}")
                print()


def main():
    """Demonstrate model discovery functionality."""
    # You need to replace this with your actual compartment OCID
    compartment_id = "ocid1.compartment.oc1..example"

    # Check if compartment ID is set
    if "example" in compartment_id:
        print("ERROR: Please update the compartment_id variable with your actual compartment OCID")
        return

    # Create model discovery client
    discovery = OCIGenAIModelDiscovery()

    # Print comprehensive model summary
    discovery.print_model_summary(compartment_id)

    # Get specific model types
    print("\n🔍 Filtering by capability:")

    chat_models = discovery.get_chat_models(compartment_id)
    print(f"Chat models: {len(chat_models)}")
    for model in chat_models:
        print(f"  - {model.litellm_name}")

    text_gen_models = discovery.get_text_generation_models(compartment_id)
    print(f"Text generation models: {len(text_gen_models)}")
    for model in text_gen_models:
        print(f"  - {model.litellm_name}")

    embedding_models = discovery.get_embedding_models(compartment_id)
    print(f"Embedding models: {len(embedding_models)}")
    for model in embedding_models:
        print(f"  - {model.litellm_name}")

    # Export model registry
    print("\n📄 Exporting model registry...")
    discovery.export_model_registry(compartment_id)

    # Show sample LiteLLM usage
    print("\n💡 Sample LiteLLM usage:")
    if chat_models:
        sample_model = chat_models[0]
        print(
            f"""
import litellm
import os

# Set your OCI compartment ID
os.environ['OCI_COMPARTMENT_ID'] = '{compartment_id}'

# Use the model with LiteLLM
response = litellm.completion(
    model="{sample_model.litellm_name}",
    messages=[
        {{"role": "user", "content": "Hello, how are you?"}}
    ]
)
print(response.choices[0].message.content)
"""
        )


if __name__ == "__main__":
    main()
