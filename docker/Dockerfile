# Multi-stage Dockerfile for Coda with Ollama (Optimized)
FROM python:3.11-slim-bullseye as builder

# OCI image labels
LABEL org.opencontainers.image.title="Coda Code Assistant" \
      org.opencontainers.image.description="AI-powered code assistant with local and cloud LLM support" \
      org.opencontainers.image.url="https://github.com/djvolz/coda-devops-automation" \
      org.opencontainers.image.documentation="https://github.com/djvolz/coda-devops-automation/blob/main/README.md" \
      org.opencontainers.image.licenses="MIT" \
      org.opencontainers.image.vendor="Coda Project"

# Install system dependencies needed for building
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# Install uv for fast Python package management
RUN pip install --no-cache-dir uv

# Set working directory
WORKDIR /app

# Copy dependency files first for better caching
COPY pyproject.toml uv.lock README.md ./

# Copy source code (needed for version resolution)
COPY coda/ ./coda/

# Install Python dependencies
RUN uv sync --no-dev --no-cache

# Copy rest of application code
COPY . .

# Build the application
RUN uv build --no-cache

# Runtime stage - Use distroless for minimal attack surface
FROM python:3.11-slim-bullseye

# Set labels with build args for versioning
ARG VERSION=latest
ARG BUILD_DATE
ARG VCS_REF
LABEL maintainer="Coda Development Team" \
      description="Coda CLI code assistant with Ollama bundled" \
      version="${VERSION}" \
      org.opencontainers.image.created="${BUILD_DATE}" \
      org.opencontainers.image.revision="${VCS_REF}" \
      org.opencontainers.image.source="https://github.com/djvolz/coda-code-assistant"

# Install runtime dependencies with minimal packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean \
    && rm -rf /tmp/* /var/tmp/*

# Install Ollama with verification
RUN curl -fsSL https://ollama.com/install.sh -o /tmp/install-ollama.sh \
    && chmod +x /tmp/install-ollama.sh \
    && /tmp/install-ollama.sh \
    && rm -rf /tmp/* /var/tmp/*

# Create non-root user with minimal permissions
RUN useradd -m -s /bin/bash -u 1000 coda \
    && mkdir -p /home/coda/.config/coda \
               /home/coda/.cache/coda \
               /home/coda/.local/share/coda \
    && chown -R coda:coda /home/coda

# Set working directory
WORKDIR /app

# Copy built application from builder stage
COPY --from=builder /app/dist/*.whl ./

# Install the application with dependencies
RUN pip install --no-cache-dir *.whl \
    && rm -rf *.whl /root/.cache

# Copy startup script with proper permissions
COPY --chown=coda:coda docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

# Switch to non-root user
USER coda

# Set environment variables
ENV HOME=/home/coda \
    PATH="$HOME/.local/bin:$PATH" \
    CODA_CONFIG_DIR="$HOME/.config/coda" \
    CODA_CACHE_DIR="$HOME/.cache/coda" \
    CODA_DATA_DIR="$HOME/.local/share/coda" \
    OLLAMA_HOST=127.0.0.1:11434 \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Expose Ollama port
EXPOSE 11434

# Health check with optimized intervals
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
    CMD curl -f http://localhost:11434/api/health || exit 1

# Default command
ENTRYPOINT ["/entrypoint.sh"]
CMD ["coda"]