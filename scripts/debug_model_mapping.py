#!/usr/bin/env python3
"""Debug script to check model discovery and mapping."""

import os
import sys
from pprint import pprint

# Add project to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from coda.providers import OCIGenAIProvider

def main():
    """Debug model discovery and mapping."""
    print("OCI GenAI Model Discovery Debug\n" + "="*50)
    
    try:
        # Initialize provider
        provider = OCIGenAIProvider()
        print("✓ Provider initialized\n")
        
        # Force refresh models to ensure we get fresh data
        models = provider.refresh_models()
        print(f"✓ Discovered {len(models)} models\n")
        
        # Show model ID mapping
        print("Model ID Mapping (_model_id_map):")
        print("-" * 50)
        for friendly_name, oci_id in provider._model_id_map.items():
            print(f"{friendly_name:<40} -> {oci_id}")
        
        print("\n\nDetailed Model Information:")
        print("-" * 50)
        
        # Check for duplicates
        seen_ids = {}
        for model in models:
            if model.id in seen_ids:
                print(f"⚠️  DUPLICATE MODEL ID: {model.id}")
                print(f"   Previous: {seen_ids[model.id].name}")
                print(f"   Current:  {model.name}")
            else:
                seen_ids[model.id] = model
            
            print(f"\nModel: {model.id}")
            print(f"  Name: {model.name}")
            print(f"  Provider: {model.provider}")
            print(f"  OCI Model ID: {model.metadata.get('oci_model_id', 'N/A')}")
            print(f"  Vendor: {model.metadata.get('vendor', 'N/A')}")
            print(f"  Capabilities: {model.metadata.get('capabilities', [])}")
            
            # Check if this model is in the mapping
            if model.id in provider._model_id_map:
                print(f"  ✓ Has mapping to: {provider._model_id_map[model.id]}")
            else:
                print(f"  ✗ NO MAPPING FOUND!")
        
        # Test specific model
        test_model = "cohere.command-r-plus"
        print(f"\n\nTesting model: {test_model}")
        print("-" * 50)
        
        if test_model in provider._model_id_map:
            print(f"✓ Model {test_model} found in mapping")
            print(f"  Maps to OCI ID: {provider._model_id_map[test_model]}")
        else:
            print(f"✗ Model {test_model} NOT found in mapping")
            
            # Check if any similar models exist
            similar = [m for m in provider._model_id_map.keys() if "command-r-plus" in m.lower()]
            if similar:
                print(f"  Similar models found: {similar}")
        
        # Check if model is valid
        if provider.validate_model(test_model):
            print(f"✓ Model {test_model} passes validation")
        else:
            print(f"✗ Model {test_model} fails validation")
            
    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())