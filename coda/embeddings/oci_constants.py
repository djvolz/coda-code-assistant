"""OCI Generative AI Embeddings constants."""

from typing import Any

# Mapping of model names to OCI model IDs
MODEL_MAPPING: dict[str, str] = {
    "embed-english-v3.0": "cohere.embed-english-v3.0",
    "embed-multilingual-v3.0": "cohere.embed-multilingual-v3.0",
    "embed-english-light-v3.0": "cohere.embed-english-light-v3.0",
    "embed-multilingual-light-v3.0": "cohere.embed-multilingual-light-v3.0",
    "embed-english-v2.0": "cohere.embed-english-v2.0",
    "embed-english-light-v2.0": "cohere.embed-english-light-v2.0",
}

# Model information including dimensions and context windows
MODEL_INFO: dict[str, dict[str, Any]] = {
    "cohere.embed-english-v3.0": {
        "dimensions": 1024,
        "max_tokens": 512,
        "languages": ["english"],
        "description": "English embedding model v3.0",
    },
    "cohere.embed-multilingual-v3.0": {
        "dimensions": 1024,
        "max_tokens": 512,
        "languages": ["multilingual"],
        "description": "Multilingual embedding model v3.0",
    },
    "cohere.embed-english-light-v3.0": {
        "dimensions": 384,
        "max_tokens": 512,
        "languages": ["english"],
        "description": "Lightweight English embedding model v3.0",
    },
    "cohere.embed-multilingual-light-v3.0": {
        "dimensions": 384,
        "max_tokens": 512,
        "languages": ["multilingual"],
        "description": "Lightweight multilingual embedding model v3.0",
    },
    "cohere.embed-english-v2.0": {
        "dimensions": 4096,
        "max_tokens": 512,
        "languages": ["english"],
        "description": "English embedding model v2.0",
    },
    "cohere.embed-english-light-v2.0": {
        "dimensions": 1024,
        "max_tokens": 512,
        "languages": ["english"],
        "description": "Lightweight English embedding model v2.0",
    },
}

# Default configuration
DEFAULT_MODEL = "cohere.embed-english-v3.0"
DEFAULT_COMPARTMENT_ID = (
    "ocid1.compartment.oc1..aaaaaaaauzqq5ybqlvshhpnhvhkmxrtvfx2ece5dnmn3iq5bgfsi7zb3n2q"
)
DEFAULT_SERVICE_ENDPOINT = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"
