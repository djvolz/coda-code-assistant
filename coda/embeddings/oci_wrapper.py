"""
Example wrapper showing how Coda would use the self-contained embedding provider
while maintaining backward compatibility with CodaConfig.
"""

from typing import Optional
from .oci_standalone import StandaloneOCIEmbeddingProvider
from ..configuration import CodaConfig
from ..constants import MODEL_CACHE_DURATION


class CodaOCIEmbeddingProvider(StandaloneOCIEmbeddingProvider):
    """Wrapper that adapts StandaloneOCIEmbeddingProvider to use CodaConfig.
    
    This demonstrates how to maintain Coda's configuration system while
    using self-contained components underneath.
    """
    
    def __init__(self, model_id: str = "multilingual-e5", config: Optional[CodaConfig] = None):
        """Initialize from CodaConfig.
        
        Args:
            model_id: Model to use
            config: Coda configuration object
        """
        config = config or CodaConfig()
        
        # Extract OCI configuration from CodaConfig
        oci_config = config.providers.get("oci_genai", {})
        compartment_id = oci_config.get("compartment_id")
        
        if not compartment_id:
            raise ValueError(
                "OCI compartment_id not found in configuration. "
                "Set it in providers.oci_genai.compartment_id"
            )
            
        # Convert cache duration from seconds to hours
        cache_hours = MODEL_CACHE_DURATION // 3600
        
        # Initialize the standalone provider with extracted values
        super().__init__(
            compartment_id=compartment_id,
            model_id=model_id,
            oci_config_file=oci_config.get("config_file", "~/.oci/config"),
            oci_profile=oci_config.get("profile", "DEFAULT"),
            region=oci_config.get("region"),
            cache_duration_hours=cache_hours
        )


# This pattern allows:
# 1. Coda to continue using its configuration system
# 2. External users to use StandaloneOCIEmbeddingProvider directly
# 3. Clean separation between Coda-specific and generic code
# 4. Easy testing of both versions