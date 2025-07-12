#!/usr/bin/env python3
"""
Example script demonstrating how to list available GenAI models from OCI.

This script shows two approaches:
1. Using the OCI Python SDK directly
2. How litellm integrates with OCI GenAI

Requirements:
- OCI Python SDK: pip install oci
- Configured OCI credentials (~/.oci/config)
- Appropriate IAM permissions for GenAI service
"""

from typing import Any

import oci


def list_oci_genai_models_direct(
    compartment_id: str, region: str = "us-ashburn-1", config_profile: str = "DEFAULT"
) -> list[dict[str, Any]]:
    """
    List available GenAI models using OCI Python SDK directly.

    Args:
        compartment_id: The OCID of the compartment to search in
        region: OCI region (default: us-ashburn-1)
        config_profile: OCI config profile name (default: DEFAULT)

    Returns:
        List of model dictionaries with model information
    """
    # Load OCI configuration
    config = oci.config.from_file(profile_name=config_profile)

    # Create GenerativeAI client
    generative_ai_client = oci.generative_ai.GenerativeAiClient(config)

    try:
        # List all models in the compartment
        response = generative_ai_client.list_models(compartment_id=compartment_id)

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
                "time_created": model.time_created,
                "compartment_id": model.compartment_id,
            }
            models.append(model_info)

        return models

    except Exception as e:
        print(f"Error listing models: {e}")
        return []


def list_oci_genai_models_filtered(
    compartment_id: str,
    capability: str = None,
    vendor: str = None,
    lifecycle_state: str = "ACTIVE",
    config_profile: str = "DEFAULT",
) -> list[dict[str, Any]]:
    """
    List available GenAI models with filtering options.

    Args:
        compartment_id: The OCID of the compartment to search in
        capability: Filter by capability (TEXT_GENERATION, CHAT, TEXT_EMBEDDINGS, etc.)
        vendor: Filter by vendor (e.g., "cohere", "meta")
        lifecycle_state: Filter by lifecycle state (default: ACTIVE)
        config_profile: OCI config profile name (default: DEFAULT)

    Returns:
        List of model dictionaries with model information
    """
    # Load OCI configuration
    config = oci.config.from_file(profile_name=config_profile)

    # Create GenerativeAI client
    generative_ai_client = oci.generative_ai.GenerativeAiClient(config)

    try:
        # Build filter parameters
        list_params = {"compartment_id": compartment_id}

        if capability:
            list_params["capability"] = [capability]
        if vendor:
            list_params["vendor"] = vendor
        if lifecycle_state:
            list_params["lifecycle_state"] = lifecycle_state

        # List models with filters
        response = generative_ai_client.list_models(**list_params)

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
                "time_created": model.time_created,
                "compartment_id": model.compartment_id,
            }
            models.append(model_info)

        return models

    except Exception as e:
        print(f"Error listing models: {e}")
        return []


def print_models_summary(models: list[dict[str, Any]]) -> None:
    """Print a summary of available models."""
    if not models:
        print("No models found.")
        return

    print(f"\nFound {len(models)} models:")
    print("-" * 80)

    for model in models:
        print(f"Model ID: {model['id']}")
        print(f"Display Name: {model['display_name']}")
        print(f"Vendor: {model['vendor']}")
        print(f"Version: {model['version']}")
        print(f"Capabilities: {', '.join(model['capabilities'])}")
        print(f"State: {model['lifecycle_state']}")
        print(f"Type: {model['type']}")
        print(f"LTS: {model['is_long_term_supported']}")
        print("-" * 80)


def main():
    """Main function to demonstrate model listing."""
    # You need to replace this with your actual compartment OCID
    compartment_id = "ocid1.compartment.oc1..example"

    # Check if compartment ID is set
    if "example" in compartment_id:
        print("ERROR: Please update the compartment_id variable with your actual compartment OCID")
        return

    print("Listing all GenAI models in compartment...")
    all_models = list_oci_genai_models_direct(compartment_id)
    print_models_summary(all_models)

    print("\nListing only CHAT-capable models...")
    chat_models = list_oci_genai_models_filtered(compartment_id, capability="CHAT")
    print_models_summary(chat_models)

    print("\nListing only TEXT_GENERATION-capable models...")
    text_gen_models = list_oci_genai_models_filtered(compartment_id, capability="TEXT_GENERATION")
    print_models_summary(text_gen_models)


if __name__ == "__main__":
    main()
