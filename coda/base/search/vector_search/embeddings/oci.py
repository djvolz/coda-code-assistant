"""
OCI GenAI embedding provider implementation.

This module is designed to be self-contained and usable as a library
by external projects without Coda dependencies.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import numpy as np
import oci
from oci.generative_ai_inference import GenerativeAiInferenceClient
from oci.generative_ai_inference.models import (
    EmbedTextDetails,
    OnDemandServingMode,
)

from .base import BaseEmbeddingProvider, EmbeddingResult
from .oci_constants import DEFAULT_COMPARTMENT_ID, DEFAULT_MODEL, MODEL_INFO, MODEL_MAPPING

logger = logging.getLogger(__name__)


class OCIEmbeddingProvider(BaseEmbeddingProvider):
    """OCI GenAI embedding provider.

    Supports multilingual-e5 and cohere-embed-multilingual-v3.0 models.
    """

    # Additional model aliases for backward compatibility
    ALIASES = {
        "multilingual-e5": "cohere.embed-multilingual-v3.0",
        "cohere-embed": "cohere.embed-multilingual-v3.0",
        "cohere-embed-english": "cohere.embed-english-v3.0",
    }

    def __init__(
        self,
        compartment_id: str | None = None,
        model_id: str | None = None,
        oci_config: dict[str, Any] | None = None,
        oci_config_file: str | Path | None = None,
        oci_profile: str = "DEFAULT",
        region: str | None = None,
        service_endpoint: str | None = None,
        cache_duration_hours: int = 24,
    ):
        """Initialize OCI embedding provider.

        Args:
            compartment_id: OCI compartment ID (uses default if not provided)
            model_id: Short model name or full OCI model ID (uses default if not provided)
            oci_config: OCI configuration dictionary (if not provided, uses config_file)
            oci_config_file: Path to OCI config file (default: ~/.oci/config)
            oci_profile: Profile to use from config file
            region: OCI region (if not provided, uses config file)
            service_endpoint: OCI service endpoint (optional)
            cache_duration_hours: How long to cache model lists (default: 24)
        """
        # Use defaults if not provided
        if compartment_id is None:
            compartment_id = DEFAULT_COMPARTMENT_ID
        if model_id is None:
            model_id = DEFAULT_MODEL

        # Map short names and aliases to full model IDs
        if model_id in self.ALIASES:
            model_id = self.ALIASES[model_id]
        elif model_id in MODEL_MAPPING:
            model_id = MODEL_MAPPING[model_id]

        super().__init__(model_id)

        self.compartment_id = compartment_id
        self.service_endpoint = service_endpoint
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self._client = None
        self._models_cache = None
        self._cache_timestamp = None

        # Store OCI config for client initialization
        if oci_config is None:
            if oci_config_file:
                self._oci_config = oci.config.from_file(
                    file_location=str(oci_config_file), profile_name=oci_profile
                )
            else:
                self._oci_config = oci.config.from_file(profile_name=oci_profile)
        else:
            self._oci_config = oci_config

        if region:
            self._oci_config["region"] = region

    @property
    def client(self) -> GenerativeAiInferenceClient:
        """Get or create OCI client."""
        if self._client is None:
            self._client = GenerativeAiInferenceClient(
                self._oci_config, service_endpoint=self.service_endpoint
            )
        return self._client

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Embed a single text using OCI GenAI.

        Args:
            text: The text to embed

        Returns:
            EmbeddingResult with the embedding
        """
        results = await self.embed_batch([text])
        return results[0]

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Embed a batch of texts using OCI GenAI.

        Args:
            texts: List of texts to embed

        Returns:
            List of EmbeddingResults
        """
        try:
            # Create request
            embed_details = EmbedTextDetails(
                inputs=texts,
                serving_mode=OnDemandServingMode(
                    model_id=f"ocid1.generativeaimodel.oc1.us-chicago-1.{self.model_id}"
                ),
                compartment_id=self.compartment_id,
                # Add truncate parameter to handle long texts
                truncate="END",
            )

            # Make request
            response = await asyncio.get_event_loop().run_in_executor(
                None, lambda: self.client.embed_text(embed_details)
            )

            # Extract embeddings
            results = []
            for i, text in enumerate(texts):
                embedding = np.array(response.data.embeddings[i])
                results.append(
                    EmbeddingResult(
                        text=text,
                        embedding=embedding,
                        model=self.model_id,
                        metadata={
                            "provider": "oci",
                            "truncated": len(text.split())
                            > MODEL_INFO.get(self.model_id, {}).get("max_tokens", 512),
                        },
                    )
                )

            return results

        except Exception as e:
            logger.error(f"Error embedding texts with OCI: {str(e)}")
            raise

    async def list_models(self) -> list[dict[str, Any]]:
        """List available OCI embedding models.

        Returns:
            List of model information
        """
        # Check cache
        if self._models_cache and self._cache_timestamp:
            if datetime.now() - self._cache_timestamp < self.cache_duration:
                return self._models_cache

        # Return all available models from constants
        models = []
        for model_id, info in MODEL_INFO.items():
            models.append(
                {
                    "id": model_id,
                    "provider": "oci",
                    "dimensions": info.get("dimensions", 768),
                    "max_tokens": info.get("max_tokens", 512),
                    "languages": info.get("languages", ["multilingual"]),
                    "description": info.get("description", ""),
                }
            )

        self._models_cache = models
        self._cache_timestamp = datetime.now()

        return models

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current model.

        Returns:
            Model information dictionary
        """
        info = MODEL_INFO.get(self.model_id, {})
        return {
            "id": self.model_id,
            "provider": "oci",
            "dimensions": info.get("dimensions", 768),
            "max_tokens": info.get("max_tokens", 512),
            "languages": info.get("languages", ["multilingual"]),
            "description": info.get("description", ""),
        }


# Factory functions for easier instantiation
def create_oci_provider_from_coda_config(
    coda_config: dict[str, Any], model_id: str | None = None
) -> OCIEmbeddingProvider:
    """Create OCI provider from Coda configuration.

    Args:
        coda_config: Coda configuration dictionary
        model_id: Optional model ID override

    Returns:
        Configured OCIEmbeddingProvider instance
    """
    oci_config = coda_config.get("oci", {})
    return OCIEmbeddingProvider(
        compartment_id=oci_config.get("compartment_id"),
        model_id=model_id or oci_config.get("embedding_model_id"),
        oci_config_file=oci_config.get("config_file_path"),
        oci_profile=oci_config.get("profile", "DEFAULT"),
        region=oci_config.get("region"),
        service_endpoint=oci_config.get("endpoint"),
    )


def create_standalone_oci_provider(
    compartment_id: str | None = None, model_id: str | None = None, **kwargs
) -> OCIEmbeddingProvider:
    """Create standalone OCI provider with minimal configuration.

    Args:
        compartment_id: OCI compartment ID (uses default if not provided)
        model_id: Model ID (uses default if not provided)
        **kwargs: Additional arguments passed to OCIEmbeddingProvider

    Returns:
        Configured OCIEmbeddingProvider instance
    """
    return OCIEmbeddingProvider(compartment_id=compartment_id, model_id=model_id, **kwargs)
