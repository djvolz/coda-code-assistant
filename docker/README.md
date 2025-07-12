# Docker Setup for Coda

This directory contains all Docker-related files for building and running Coda in containers.

## 📁 Directory Structure

```
docker/
├── Dockerfile              # Main production Dockerfile
├── Dockerfile.dev          # Development Dockerfile with hot reload
├── Dockerfile.oci          # OCI-specific Dockerfile
├── docker-compose.yml      # Main compose configuration
├── docker-compose.dev.yml  # Development compose overrides
├── docker-compose.test.yml # Testing compose configuration
├── entrypoint.sh          # Main container entrypoint
├── entrypoint-dev.sh      # Development entrypoint
├── entrypoint-oci.sh      # OCI-specific entrypoint
├── config/                # Docker-specific configurations
│   ├── dev-config.toml    # Development config
│   └── oci-config.toml    # OCI config
└── examples/              # Example configurations
    ├── docker-compose-oci.yml
    └── docker-run-oci.sh
```

**Note**: The `.dockerignore` file remains in the project root as required by Docker.

## Quick Start

### Production Usage

Build and run the production container:

```bash
# Build the image
make docker-build

# Run Coda with Ollama
make docker-run
```

### Development Usage

Start the development environment:

```bash
# Start all services
make docker-dev-up

# Access the container
docker-compose exec coda bash

# Run Coda inside the container
coda

# Stop the environment
make docker-dev-down
```

## Architecture

### Multi-Stage Build

The production Dockerfile uses a multi-stage build:

1. **Builder Stage**: Compiles dependencies and builds the application
2. **Runtime Stage**: Minimal runtime environment with Ollama

### Services

- **coda**: Main application container with Ollama bundled
- **ollama-dev**: Separate Ollama service for development
- **postgres**: Optional database for advanced features
- **redis**: Optional caching layer

## Configuration

### Environment Variables

- `OLLAMA_HOST`: Ollama server address (default: `127.0.0.1:11434`)
- `OLLAMA_PULL_DEFAULT`: Auto-pull default model (default: `true`)
- `CODA_LOG_LEVEL`: Log level (default: `INFO`)
- `CODA_ENV`: Environment mode (default: `production`)

### Volumes

- `coda-config`: Configuration files
- `coda-cache`: Model cache and sessions
- `coda-data`: Session data and logs

## Multi-Architecture Support

The Docker images support both AMD64 and ARM64 architectures:

```bash
# Build for multiple architectures
make docker-build-multi

# Or use Docker Buildx directly
docker buildx build --platform linux/amd64,linux/arm64 -t coda:latest .
```

## Optimization Features

### Size Optimization

- Multi-stage builds reduce final image size
- Minimal base image (python:3.11-slim)
- Efficient layer caching
- Removed unnecessary packages and cache

### Performance Optimization

- UV for fast Python package management
- Optimized dependency installation
- Proper layer ordering for better caching
- Health checks for service monitoring

### Security

- Non-root user execution
- Minimal attack surface
- Security scanning in CI/CD
- Proper file permissions

## Development Workflow

### Local Development

1. **Start environment**: `make docker-dev-up`
2. **Access container**: `docker-compose exec coda bash`
3. **Install dependencies**: `uv sync --all-extras`
4. **Run tests**: `make test`
5. **Run application**: `coda`

### Testing

Run tests in Docker:

```bash
# Run all tests
make docker-test

# Run specific test suite
docker-compose exec coda uv run pytest tests/unit/ -v
```

### Building Images

```bash
# Production build
make docker-build

# Development build
make docker-dev

# Multi-architecture build
make docker-build-multi
```

## Profiles

Use Docker Compose profiles to start different service combinations:

```bash
# Start with standalone Ollama
docker-compose --profile standalone up -d

# Start with database
docker-compose --profile database up -d

# Start with caching
docker-compose --profile cache up -d

# Start everything
docker-compose --profile standalone --profile database --profile cache up -d
```

## Troubleshooting

### Common Issues

1. **Ollama not starting**: Check logs with `docker-compose logs coda`
2. **Permission errors**: Ensure volumes are properly mounted
3. **Port conflicts**: Change port mappings in docker-compose.yml
4. **Build failures**: Check Docker daemon and buildx setup

### Logs

```bash
# View all logs
docker-compose logs

# View specific service logs
docker-compose logs coda

# Follow logs in real-time
docker-compose logs -f coda
```

### Health Checks

```bash
# Check container health
docker ps

# Check Ollama API
curl http://localhost:11434/api/health

# Check container resources
docker stats coda-dev
```

## CI/CD Integration

The repository includes GitHub Actions workflow for:

- Multi-architecture builds
- Automated testing
- Security scanning
- Registry publishing

See `.github/workflows/docker-build.yml` for details.

## Best Practices

### Production

- Use specific version tags, not `latest`
- Set resource limits
- Use health checks
- Monitor container metrics
- Regular security updates

### Development

- Use bind mounts for code changes
- Set up proper debugging
- Use development-specific configuration
- Regular cleanup of unused images

### Security

- Scan images for vulnerabilities
- Use minimal base images
- Run as non-root user
- Keep dependencies updated
- Use secrets management

## Advanced Usage

### Custom Configuration

Create a custom config file:

```toml
# docker/config/custom-config.toml
[general]
debug = true
theme = "dark"

[providers.ollama]
base_url = "http://localhost:11434"
timeout = 60
```

Mount it in docker-compose.yml:

```yaml
volumes:
  - ./docker/config/custom-config.toml:/home/coda/.config/coda/config.toml:ro
```

### Model Management

Pre-pull models during build:

```dockerfile
# Add to Dockerfile
RUN ollama pull llama3.2:3b && ollama pull codellama:7b
```

### Resource Limits

Set resource limits in docker-compose.yml:

```yaml
services:
  coda:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          memory: 2G
```

## Support

For Docker-related issues:
- Check container logs
- Review Docker daemon logs
- Verify system requirements
- Check network connectivity

For Coda-specific issues:
- See main project documentation
- Check GitHub issues
- Review configuration files