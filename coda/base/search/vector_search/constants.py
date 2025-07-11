"""Constants for the search module.

All search-related constants are defined here to make the module self-contained.
"""

# Default chunking parameters
DEFAULT_CHUNK_SIZE: int = 1000
DEFAULT_CHUNK_OVERLAP: int = 200
MIN_CHUNK_SIZE: int = 100

# Default embedding dimensions
DEFAULT_EMBEDDING_DIMENSION: int = 768

# Vector store defaults
DEFAULT_INDEX_TYPE: str = "Flat"  # FAISS index type
DEFAULT_SIMILARITY_METRIC: str = "cosine"

# Search defaults
DEFAULT_SEARCH_K: int = 5  # Number of results to return
DEFAULT_SIMILARITY_THRESHOLD: float = 0.7

# File processing
SUPPORTED_TEXT_EXTENSIONS: list[str] = [
    ".txt",
    ".md",
    ".rst",
    ".doc",
    ".docx",
    ".pdf",
    ".html",
    ".xml",
    ".json",
    ".yaml",
    ".yml",
]

SUPPORTED_CODE_EXTENSIONS: list[str] = [
    ".py",
    ".js",
    ".ts",
    ".jsx",
    ".tsx",
    ".java",
    ".cpp",
    ".c",
    ".h",
    ".hpp",
    ".go",
    ".rs",
    ".rb",
    ".php",
    ".swift",
    ".kt",
    ".scala",
    ".r",
    ".m",
    ".cs",
    ".sh",
    ".bash",
    ".zsh",
    ".fish",
]

# Embedding provider types
PROVIDER_MOCK: str = "mock"
PROVIDER_OCI: str = "oci"
PROVIDER_OLLAMA: str = "ollama"
PROVIDER_SENTENCE_TRANSFORMERS: str = "sentence_transformers"

# Cache and storage
DEFAULT_CACHE_TTL: int = 3600  # 1 hour in seconds
MAX_CACHE_SIZE: int = 1000  # Maximum cached items

# Batch processing
DEFAULT_BATCH_SIZE: int = 100
MAX_BATCH_SIZE: int = 1000

# Error handling
MAX_RETRIES: int = 3
RETRY_DELAY: float = 1.0  # seconds
