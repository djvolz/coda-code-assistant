#!/usr/bin/env python3
"""
Example showing how to integrate OCI GenAI model discovery with LiteLLM.

This demonstrates how the model discovery API can be used to:
1. Dynamically discover available models
2. Create LiteLLM-compatible model configurations
3. Validate model availability before making requests

Requirements:
- OCI Python SDK: pip install oci
- LiteLLM: pip install litellm
- Configured OCI credentials (~/.oci/config)
"""

from typing import Any

import oci


class LiteLLMOCIModelManager:
    """Manager for OCI GenAI models with LiteLLM integration."""

    def __init__(self, compartment_id: str, config_profile: str = "DEFAULT"):
        """
        Initialize the model manager.

        Args:
            compartment_id: OCI compartment OCID
            config_profile: OCI configuration profile name
        """
        self.compartment_id = compartment_id
        self.config = oci.config.from_file(profile_name=config_profile)
        self.client = oci.generative_ai.GenerativeAiClient(self.config)
        self._models_cache: list[dict[str, Any]] | None = None

    def discover_available_models(self, force_refresh: bool = False) -> list[dict[str, Any]]:
        """
        Discover available GenAI models from OCI.

        Args:
            force_refresh: Force refresh of cached models

        Returns:
            List of model information dictionaries
        """
        if self._models_cache and not force_refresh:
            return self._models_cache

        try:
            response = self.client.list_models(
                compartment_id=self.compartment_id,
                lifecycle_state="ACTIVE",  # Only get active models
            )

            models = []
            for model in response.data.items:
                model_info = {
                    "id": model.id,
                    "display_name": model.display_name,
                    "vendor": model.vendor,
                    "version": model.version,
                    "capabilities": model.capabilities,
                    "lifecycle_state": model.lifecycle_state,
                    "type": model.type,
                    "is_long_term_supported": model.is_long_term_supported,
                    "litellm_name": f"oci_genai/{model.id}",
                    "is_available": model.lifecycle_state == "ACTIVE",
                }
                models.append(model_info)

            self._models_cache = models
            return models

        except Exception as e:
            print(f"Error discovering models: {e}")
            return []

    def get_available_model_names(self) -> list[str]:
        """Get list of available model names for LiteLLM."""
        models = self.discover_available_models()
        return [model["litellm_name"] for model in models if model["is_available"]]

    def get_models_by_capability(self, capability: str) -> list[dict[str, Any]]:
        """
        Get models that support a specific capability.

        Args:
            capability: The capability to filter by (CHAT, TEXT_GENERATION, etc.)

        Returns:
            List of model information dictionaries
        """
        models = self.discover_available_models()
        return [
            model
            for model in models
            if capability in model["capabilities"] and model["is_available"]
        ]

    def validate_model_for_litellm(self, model_name: str) -> bool:
        """
        Validate that a model is available for use with LiteLLM.

        Args:
            model_name: The model name to validate

        Returns:
            True if the model is available, False otherwise
        """
        available_models = self.get_available_model_names()
        return model_name in available_models

    def create_litellm_model_config(self, service_endpoint: str = None) -> dict[str, Any]:
        """
        Create a LiteLLM model configuration for all available models.

        Args:
            service_endpoint: Optional custom service endpoint

        Returns:
            Dictionary containing LiteLLM model configuration
        """
        models = self.discover_available_models()

        if not service_endpoint:
            region = self.config.get("region", "us-ashburn-1")
            service_endpoint = f"https://inference.generativeai.{region}.oci.oraclecloud.com"

        config = {"model_list": [], "litellm_settings": {"drop_params": True, "set_verbose": False}}

        for model in models:
            if not model["is_available"]:
                continue

            model_config = {
                "model_name": model["litellm_name"],
                "litellm_params": {
                    "model": model["litellm_name"],
                    "compartment_id": self.compartment_id,
                    "api_base": service_endpoint,
                },
                "model_info": {
                    "id": model["id"],
                    "display_name": model["display_name"],
                    "vendor": model["vendor"],
                    "capabilities": model["capabilities"],
                    "type": model["type"],
                },
            }

            config["model_list"].append(model_config)

        return config

    def print_available_models(self) -> None:
        """Print a formatted list of available models."""
        models = self.discover_available_models()

        if not models:
            print("No models found.")
            return

        print("\n🔍 Available OCI GenAI Models")
        print("=" * 60)

        for model in models:
            if not model["is_available"]:
                continue

            print(f"📋 {model['display_name']} ({model['vendor']})")
            print(f"   ID: {model['id']}")
            print(f"   LiteLLM: {model['litellm_name']}")
            print(f"   Capabilities: {', '.join(model['capabilities'])}")
            print(f"   Version: {model['version']}")
            print(f"   LTS: {'Yes' if model['is_long_term_supported'] else 'No'}")
            print()


def demonstrate_litellm_integration():
    """Demonstrate how to use the model discovery with LiteLLM."""

    # You need to replace this with your actual compartment OCID
    compartment_id = "ocid1.compartment.oc1..example"

    if "example" in compartment_id:
        print("ERROR: Please update the compartment_id variable with your actual compartment OCID")
        return

    # Create model manager
    manager = LiteLLMOCIModelManager(compartment_id)

    # Show available models
    manager.print_available_models()

    # Get specific model types
    chat_models = manager.get_models_by_capability("CHAT")
    print(f"🗨️  Chat models available: {len(chat_models)}")

    text_gen_models = manager.get_models_by_capability("TEXT_GENERATION")
    print(f"📝 Text generation models available: {len(text_gen_models)}")

    embedding_models = manager.get_models_by_capability("TEXT_EMBEDDINGS")
    print(f"🔍 Embedding models available: {len(embedding_models)}")

    # Show how to validate models
    print("\n✅ Model validation:")
    available_models = manager.get_available_model_names()
    for model_name in available_models[:3]:  # Show first 3
        is_valid = manager.validate_model_for_litellm(model_name)
        print(f"   {model_name}: {'✅ Valid' if is_valid else '❌ Invalid'}")

    # Show sample LiteLLM usage
    print("\n💡 Sample LiteLLM usage:")
    if chat_models:
        sample_model = chat_models[0]
        print(
            f"""
# Set environment variables
os.environ['OCI_COMPARTMENT_ID'] = '{compartment_id}'

# Import LiteLLM
import litellm

# Use the model
response = litellm.completion(
    model="{sample_model["litellm_name"]}",
    messages=[
        {{"role": "user", "content": "Hello, how are you?"}}
    ],
    # Optional parameters
    temperature=0.7,
    max_tokens=100
)
print(response.choices[0].message.content)
"""
        )

    # Show model configuration export
    print("\n📄 LiteLLM Model Configuration:")
    config = manager.create_litellm_model_config()
    print(f"Found {len(config['model_list'])} models ready for LiteLLM")

    # Show how this integrates with existing LiteLLM OCI implementation
    print("\n🔧 Integration with existing LiteLLM OCI implementation:")
    print(
        """
The discovered models can be used with the existing LiteLLM OCI GenAI implementation:

1. Models are automatically formatted with 'oci_genai/' prefix
2. Compartment ID is included in the configuration
3. Service endpoint is dynamically determined based on region
4. Model capabilities are preserved for proper routing

This enables:
- Dynamic model discovery instead of hardcoded model lists
- Automatic validation of model availability
- Capability-based model selection
- Region-aware endpoint configuration
"""
    )


if __name__ == "__main__":
    demonstrate_litellm_integration()
