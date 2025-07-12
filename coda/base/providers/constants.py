"""Constants for the providers module.

This module contains all constants needed by the providers module,
making it self-contained and independent of other Coda modules.
"""


class PROVIDERS:
    """Provider identifiers."""

    OCI_GENAI: str = "oci_genai"
    LITELLM: str = "litellm"
    OLLAMA: str = "ollama"
    MOCK: str = "mock"
    OPENAI: str = "openai"

    @property
    def ALL(self) -> list[str]:
        """Return all provider names."""
        return [
            self.OCI_GENAI,
            self.LITELLM,
            self.OLLAMA,
            self.MOCK,
            self.OPENAI,
        ]


# Model defaults
DEFAULT_CONTEXT_LENGTH: int = 4096
DEFAULT_TEMPERATURE: float = 0.7
DEFAULT_MAX_TOKENS: int = 2048
DEFAULT_TOP_P: float = 1.0

# Streaming defaults
DEFAULT_STREAM_CHUNK_SIZE: int = 1024
STREAM_TIMEOUT_SECONDS: int = 300

# Provider-specific defaults
OLLAMA_DEFAULT_HOST: str = "http://localhost:11434"
OCI_DEFAULT_ENDPOINT: str = "https://inference.generativeai.us-chicago-1.oci.oraclecloud.com"

# Retry settings
MAX_RETRIES: int = 3
RETRY_DELAY_SECONDS: float = 1.0
RETRY_BACKOFF_FACTOR: float = 2.0

# API timeouts and cache durations
API_TIMEOUT: int = 30  # seconds
MODEL_CACHE_DURATION: int = 24 * 60 * 60  # 24 hours
PROVIDER_CACHE_DURATION: int = 60 * 60  # 1 hour

# Token management ratios
CONTEXT_AGGRESSIVE_RATIO: float = 0.6
CONTEXT_BALANCED_RATIO: float = 0.75
CONTEXT_CONSERVATIVE_RATIO: float = 0.9
PRESERVE_LAST_N_MESSAGES: int = 10

# Environment variable names
ENV_OCI_COMPARTMENT_ID: str = "OCI_COMPARTMENT_ID"
