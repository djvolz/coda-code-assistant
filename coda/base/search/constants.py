"""Constants for the search module.

All search-related constants are defined here to make the module self-contained.
"""

# === Repository Analysis Constants ===

# Supported file extensions for analysis
SUPPORTED_LANGUAGES = {
    ".py": "python",
    ".js": "javascript",
    ".ts": "typescript",
    ".jsx": "javascript",
    ".tsx": "typescript",
    ".java": "java",
    ".cpp": "cpp",
    ".c": "c",
    ".h": "c",
    ".hpp": "cpp",
    ".go": "go",
    ".rs": "rust",
    ".rb": "ruby",
    ".php": "php",
    ".swift": "swift",
    ".kt": "kotlin",
    ".scala": "scala",
    ".r": "r",
    ".m": "matlab",
    ".cs": "csharp",
    ".sh": "bash",
    ".bash": "bash",
    ".zsh": "bash",
    ".fish": "bash",
}

# Default analysis settings
DEFAULT_MAX_FILE_SIZE: int = 1024 * 1024  # 1MB
DEFAULT_MAX_FILES: int = 10000
DEFAULT_EXCLUDE_PATTERNS: list[str] = [
    "__pycache__",
    ".git",
    ".pytest_cache",
    "node_modules",
    ".mypy_cache",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".DS_Store",
    "Thumbs.db",
]

# Tree-sitter query directories
QUERIES_DIR: str = "queries"

# === Search and Embedding Constants ===

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

# File processing for search
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

SUPPORTED_CODE_EXTENSIONS: list[str] = list(SUPPORTED_LANGUAGES.keys())

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

# === Integration Constants ===

# Default index directory name
DEFAULT_INDEX_DIR: str = "search_index"


# Analysis modes
class AnalysisMode:
    STRUCTURE_ONLY: str = "structure"  # Just code structure
    SEMANTIC_ONLY: str = "semantic"  # Just semantic search
    FULL: str = "full"  # Both structure + semantic
