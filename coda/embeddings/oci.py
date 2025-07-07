"""
OCI GenAI embedding provider implementation.

This module is designed to be self-contained and usable as a library
by external projects without Coda dependencies.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
import numpy as np
from datetime import datetime, timedelta
import logging
from pathlib import Path

from oci.generative_ai_inference import GenerativeAiInferenceClient
from oci.generative_ai_inference.models import (
    EmbedTextDetails,
    OnDemandServingMode,
)
import oci

from .base import BaseEmbeddingProvider, EmbeddingResult

logger = logging.getLogger(__name__)


class OCIEmbeddingProvider(BaseEmbeddingProvider):
    """OCI GenAI embedding provider.
    
    Supports multilingual-e5 and cohere-embed-multilingual-v3.0 models.
    """
    
    # OCI embedding model mappings
    MODEL_MAPPING = {
        "multilingual-e5": "multilingual-e5-base",
        "cohere-embed": "cohere.embed-multilingual-v3.0",
        "cohere-embed-english": "cohere.embed-english-v3.0",
    }
    
    # Model information
    MODEL_INFO = {
        "multilingual-e5-base": {
            "dimension": 768,
            "max_tokens": 512,
            "multilingual": True,
        },
        "cohere.embed-multilingual-v3.0": {
            "dimension": 1024,
            "max_tokens": 512,
            "multilingual": True,
        },
        "cohere.embed-english-v3.0": {
            "dimension": 1024,
            "max_tokens": 512,
            "multilingual": False,
        },
    }
    
    def __init__(
        self,
        compartment_id: str,
        model_id: str = "multilingual-e5",
        oci_config: Optional[Dict[str, Any]] = None,
        oci_config_file: Optional[Union[str, Path]] = None,
        oci_profile: str = "DEFAULT",
        region: Optional[str] = None,
        cache_duration_hours: int = 24
    ):
        """Initialize OCI embedding provider.
        
        Args:
            compartment_id: OCI compartment ID (required)
            model_id: Short model name or full OCI model ID
            oci_config: OCI configuration dictionary (if not provided, uses config_file)
            oci_config_file: Path to OCI config file (default: ~/.oci/config)
            oci_profile: Profile to use from config file
            region: OCI region (if not provided, uses config file)
            cache_duration_hours: How long to cache model lists (default: 24)
        """
        # Map short names to full model IDs
        if model_id in self.MODEL_MAPPING:
            model_id = self.MODEL_MAPPING[model_id]
            
        super().__init__(model_id)
        
        self.compartment_id = compartment_id
        self.cache_duration = timedelta(hours=cache_duration_hours)
        self._client = None
        self._models_cache = None
        self._cache_timestamp = None
        
        # Store OCI config for client initialization
        if oci_config is None:
            if oci_config_file:
                self._oci_config = oci.config.from_file(
                    file_location=str(oci_config_file),
                    profile_name=oci_profile
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
            self._client = GenerativeAiInferenceClient(self._oci_config)
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
        
    async def embed_batch(self, texts: List[str]) -> List[EmbeddingResult]:
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
                None,
                lambda: self.client.embed_text(embed_details)
            )
            
            # Extract embeddings
            results = []
            for i, text in enumerate(texts):
                embedding = np.array(response.data.embeddings[i])
                results.append(EmbeddingResult(
                    text=text,
                    embedding=embedding,
                    model=self.model_id,
                    metadata={
                        "provider": "oci",
                        "truncated": len(text.split()) > self.MODEL_INFO.get(self.model_id, {}).get("max_tokens", 512)
                    }
                ))
                
            return results
            
        except Exception as e:
            logger.error(f"Error embedding texts with OCI: {str(e)}")
            raise
            
    async def list_models(self) -> List[Dict[str, Any]]:
        """List available OCI embedding models.
        
        Returns:
            List of model information
        """
        # Check cache
        if self._models_cache and self._cache_timestamp:
            if datetime.now() - self._cache_timestamp < self.cache_duration:
                return self._models_cache
                
        # For now, return static list
        # TODO: Query OCI API for dynamic model list when available
        models = []
        for short_name, full_name in self.MODEL_MAPPING.items():
            info = self.MODEL_INFO.get(full_name, {})
            models.append({
                "id": full_name,
                "short_name": short_name,
                "provider": "oci",
                "dimension": info.get("dimension", 768),
                "max_tokens": info.get("max_tokens", 512),
                "multilingual": info.get("multilingual", True),
            })
            
        self._models_cache = models
        self._cache_timestamp = datetime.now()
        
        return models
        
    def get_model_info(self) -> Dict[str, Any]:
        """Get information about the current model.
        
        Returns:
            Model information dictionary
        """
        info = self.MODEL_INFO.get(self.model_id, {})
        return {
            "id": self.model_id,
            "provider": "oci",
            "dimension": info.get("dimension", 768),
            "max_tokens": info.get("max_tokens", 512),
            "multilingual": info.get("multilingual", True),
        }