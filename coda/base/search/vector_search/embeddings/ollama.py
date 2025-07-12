"""
Ollama embedding provider for local embeddings.

This provider uses Ollama's embedding models to generate embeddings
locally without requiring external API calls.
"""

import asyncio
import logging
from typing import Any

import httpx
import numpy as np

from .base import BaseEmbeddingProvider, EmbeddingResult

logger = logging.getLogger(__name__)


class OllamaEmbeddingProvider(BaseEmbeddingProvider):
    """Embedding provider using Ollama's local models."""

    # Known Ollama embedding models with their typical dimensions
    MODELS = {
        "mxbai-embed-large": {
            "dimension": 1024,
            "description": "High-quality embedding model from MixedBread AI",
            "max_tokens": 512,
        },
        "nomic-embed-text": {
            "dimension": 768,
            "description": "Nomic's embedding model optimized for text",
            "max_tokens": 8192,
        },
        "all-minilm": {
            "dimension": 384,
            "description": "Sentence-transformers MiniLM model via Ollama",
            "max_tokens": 256,
        },
        "bge-small": {
            "dimension": 384,
            "description": "BAAI General Embedding small model",
            "max_tokens": 512,
        },
        "bge-base": {
            "dimension": 768,
            "description": "BAAI General Embedding base model",
            "max_tokens": 512,
        },
        "bge-large": {
            "dimension": 1024,
            "description": "BAAI General Embedding large model",
            "max_tokens": 512,
        },
    }

    def __init__(
        self,
        model_id: str = "mxbai-embed-large",
        base_url: str = "http://localhost:11434",
        timeout: float = 30.0,
        keep_alive: str | None = "5m",
    ):
        """Initialize Ollama embedding provider.

        Args:
            model_id: Model name available in Ollama
            base_url: Ollama API base URL
            timeout: Request timeout in seconds
            keep_alive: How long to keep model in memory (e.g., "5m", "1h")
        """
        super().__init__(model_id)
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.keep_alive = keep_alive
        self._client: httpx.AsyncClient | None = None
        self._model_info = self.MODELS.get(
            model_id,
            {
                "dimension": None,  # Will be detected
                "description": f"Custom Ollama model: {model_id}",
                "max_tokens": 2048,
            },
        )
        self._dimension_cache: dict[str, int] = {}

    def _get_client(self) -> httpx.AsyncClient:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.AsyncClient(base_url=self.base_url, timeout=self.timeout)
        return self._client

    async def _detect_dimension(self, model: str) -> int:
        """Detect embedding dimension by generating a test embedding."""
        if model in self._dimension_cache:
            return self._dimension_cache[model]

        client = self._get_client()

        try:
            response = await client.post(
                "/api/embeddings",
                json={"model": model, "prompt": "test", "keep_alive": self.keep_alive},
            )
            response.raise_for_status()

            data = response.json()
            embedding = data.get("embedding", [])
            dimension = len(embedding)

            # Cache the dimension
            self._dimension_cache[model] = dimension
            return dimension

        except Exception as e:
            logger.warning(f"Failed to detect dimension for {model}: {e}")
            # Return a default if detection fails
            return 768

    async def embed_text(self, text: str) -> EmbeddingResult:
        """Embed a single text using Ollama.

        Args:
            text: The text to embed

        Returns:
            EmbeddingResult containing the text and its embedding
        """
        client = self._get_client()

        try:
            response = await client.post(
                "/api/embeddings",
                json={"model": self.model_id, "prompt": text, "keep_alive": self.keep_alive},
            )
            response.raise_for_status()

            data = response.json()
            embedding = np.array(data["embedding"], dtype=np.float32)

            # Update dimension if not known
            if self._model_info["dimension"] is None:
                self._model_info["dimension"] = len(embedding)

            return EmbeddingResult(
                text=text,
                embedding=embedding,
                model=self.model_id,
                metadata={"provider": "ollama", "dimension": len(embedding)},
            )

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 404:
                raise ValueError(
                    f"Model '{self.model_id}' not found in Ollama. "
                    f"Pull it with: ollama pull {self.model_id}"
                ) from e
            raise
        except httpx.ConnectError:
            raise ConnectionError(
                f"Cannot connect to Ollama at {self.base_url}. Make sure Ollama is running."
            ) from None

    async def embed_batch(self, texts: list[str]) -> list[EmbeddingResult]:
        """Embed a batch of texts.

        Note: Ollama doesn't have native batch support, so we process
        texts concurrently for better performance.

        Args:
            texts: List of texts to embed

        Returns:
            List of EmbeddingResults
        """
        # Process texts concurrently with semaphore to limit parallel requests
        semaphore = asyncio.Semaphore(5)  # Limit to 5 concurrent requests

        async def embed_with_semaphore(text: str) -> EmbeddingResult:
            async with semaphore:
                return await self.embed_text(text)

        # Create tasks for all texts
        tasks = [embed_with_semaphore(text) for text in texts]

        # Wait for all embeddings
        results = await asyncio.gather(*tasks)

        return results

    def get_model_info(self) -> dict[str, Any]:
        """Get information about the current model.

        Returns:
            Dictionary with model information
        """
        return {
            "id": self.model_id,
            "provider": "ollama",
            "dimension": self._model_info["dimension"],
            "description": self._model_info["description"],
            "max_tokens": self._model_info.get("max_tokens", 2048),
            "base_url": self.base_url,
            "keep_alive": self.keep_alive,
        }

    async def list_models(self) -> list[dict[str, Any]]:
        """List available Ollama embedding models.

        This lists both known models and attempts to detect
        what's actually available in the local Ollama instance.

        Returns:
            List of model information dictionaries
        """
        models = []

        # First, add known models
        for model_id, info in self.MODELS.items():
            models.append(
                {
                    "id": model_id,
                    "provider": "ollama",
                    "dimension": info["dimension"],
                    "description": info["description"],
                    "max_tokens": info["max_tokens"],
                    "status": "known",
                }
            )

        # Try to get actual models from Ollama
        try:
            client = self._get_client()
            response = await client.get("/api/tags")
            response.raise_for_status()

            data = response.json()
            ollama_models = data.get("models", [])

            # Add any embedding models not in our known list
            known_names = set(self.MODELS.keys())
            for model in ollama_models:
                name = model.get("name", "").split(":")[0]  # Remove tag

                # Skip if already in known models or not an embedding model
                if name in known_names:
                    continue

                # Try to detect if it's an embedding model by name patterns
                if any(pattern in name.lower() for pattern in ["embed", "bge", "e5", "minilm"]):
                    # Try to detect dimension
                    try:
                        dimension = await self._detect_dimension(name)
                    except Exception:
                        dimension = None

                    models.append(
                        {
                            "id": name,
                            "provider": "ollama",
                            "dimension": dimension or "unknown",
                            "description": f"Detected Ollama model: {name}",
                            "max_tokens": "unknown",
                            "status": "available",
                        }
                    )

        except Exception as e:
            logger.warning(f"Could not list Ollama models: {e}")
            # Add a note about the connection issue
            models.append(
                {
                    "id": "error",
                    "provider": "ollama",
                    "dimension": "N/A",
                    "description": f"Could not connect to Ollama at {self.base_url}",
                    "max_tokens": "N/A",
                    "status": "error",
                }
            )

        return models

    async def __aenter__(self):
        """Async context manager entry."""
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit - cleanup client."""
        if self._client:
            await self._client.aclose()
            self._client = None
