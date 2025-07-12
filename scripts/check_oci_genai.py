#!/usr/bin/env python3
"""
Diagnostic script to check OCI GenAI service access.

This helps troubleshoot authorization and configuration issues.
"""

import os
import sys

# Add parent directory to path so we can import coda modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coda.base.providers import ProviderFactory


def main():
    print("OCI GenAI Service Diagnostic Check")
    print("=" * 50)

    # Create config for OCI
    config = {"provider": "oci_genai", "oci_genai": {}}

    # Check environment variables
    print("\n1. Checking environment variables:")
    compartment_id = os.environ.get("OCI_COMPARTMENT_ID")
    oci_config_file = os.environ.get("OCI_CONFIG_FILE", "~/.oci/config")
    oci_profile = os.environ.get("OCI_CONFIG_PROFILE", "DEFAULT")

    print(f"   OCI_COMPARTMENT_ID: {'✓ Set' if compartment_id else '✗ Not set'}")
    print(f"   OCI_CONFIG_FILE: {oci_config_file}")
    print(f"   OCI_CONFIG_PROFILE: {oci_profile}")

    if compartment_id:
        config["oci_genai"]["compartment_id"] = compartment_id

    # Try to create provider
    print("\n2. Initializing OCI GenAI provider:")
    try:
        factory = ProviderFactory(config)
        provider = factory.create("oci_genai")
        print("   ✓ Provider initialized successfully")

        # Run diagnostics
        print("\n3. Running service diagnostics:")
        diagnostics = provider.check_service_access()

        print(f"   Config valid: {'✓' if diagnostics['config_valid'] else '✗'}")
        print(f"   Service accessible: {'✓' if diagnostics['service_accessible'] else '✗'}")
        print(f"   Compartment ID: {diagnostics['compartment_id']}")
        print(f"   Region: {diagnostics['region']}")

        if diagnostics["errors"]:
            print("\n   Errors found:")
            for error in diagnostics["errors"]:
                print(f"   - {error}")

        # If service is accessible, try listing models
        if diagnostics["service_accessible"]:
            print("\n4. Attempting to list models:")
            try:
                models = provider.list_models()
                print(f"   ✓ Found {len(models)} models")
                if models:
                    print("\n   Available models:")
                    for model in models[:5]:  # Show first 5
                        print(f"   - {model.id}")
                    if len(models) > 5:
                        print(f"   ... and {len(models) - 5} more")
            except Exception as e:
                print(f"   ✗ Failed to list models: {e}")

    except Exception as e:
        print(f"   ✗ Failed to initialize: {e}")

    # Provide troubleshooting tips
    print("\n" + "=" * 50)
    print("Troubleshooting Tips:")
    print("=" * 50)

    if not compartment_id:
        print("\n1. Set your compartment ID:")
        print("   export OCI_COMPARTMENT_ID='ocid1.compartment.oc1...'")

    print("\n2. Verify your OCI CLI works:")
    print("   oci generative-ai model list --compartment-id <your-compartment-id>")

    print("\n3. Check IAM policies in OCI Console:")
    print("   - Go to Identity & Security > Policies")
    print("   - Ensure you have a policy like:")
    print("     Allow group <your-group> to use generative-ai-family in compartment <compartment>")

    print("\n4. Verify GenAI service availability in your region:")
    print("   https://docs.oracle.com/en-us/iaas/Content/generative-ai/overview.htm#regions")

    print("\n5. Check your OCI config file:")
    print(f"   cat {os.path.expanduser(oci_config_file)}")
    print("   Ensure the key_file path exists and is readable")


if __name__ == "__main__":
    main()
