"""
Coda-specific wrapper for OCI embedding provider.

This thin wrapper adapts the self-contained OCIEmbeddingProvider
to work with Coda's configuration system.
"""

from typing import Optional
from .oci import OCIEmbeddingProvider
from ..configuration import CodaConfig
from ..constants import MODEL_CACHE_DURATION


def create_oci_embedding_provider(
    model_id: str = "multilingual-e5",
    config: Optional[CodaConfig] = None
) -> OCIEmbeddingProvider:
    """Create an OCI embedding provider from Coda configuration.
    
    Args:
        model_id: Model to use
        config: Coda configuration object
        
    Returns:
        Configured OCIEmbeddingProvider instance
        
    Raises:
        ValueError: If OCI is not configured properly
    """
    config = config or CodaConfig()
    
    # Extract OCI configuration
    oci_config = config.providers.get("oci_genai", {})
    compartment_id = oci_config.get("compartment_id")
    
    if not compartment_id:
        raise ValueError(
            "OCI compartment_id not found in configuration. "
            "Set it in providers.oci_genai.compartment_id"
        )
    
    # Convert cache duration from seconds to hours
    cache_hours = MODEL_CACHE_DURATION // 3600
    
    # Create the provider with extracted configuration
    return OCIEmbeddingProvider(
        compartment_id=compartment_id,
        model_id=model_id,
        oci_config_file=oci_config.get("config_file", "~/.oci/config"),
        oci_profile=oci_config.get("profile", "DEFAULT"),
        region=oci_config.get("region"),
        cache_duration_hours=cache_hours
    )