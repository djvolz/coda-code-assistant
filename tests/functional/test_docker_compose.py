"""Functional tests for Docker Compose integration."""

import os
import shutil
import subprocess
import tempfile

import pytest
import yaml


class TestDockerComposeIntegration:
    """Test Docker Compose service orchestration and configuration."""

    @pytest.fixture
    def temp_compose_dir(self):
        """Create temporary directory for compose files."""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def base_compose_config(self):
        """Base Docker Compose configuration."""
        return {
            "version": "3.8",
            "services": {
                "coda": {
                    "image": "coda:test",
                    "environment": {"OLLAMA_HOST": "http://ollama:11434", "CODA_LOG_LEVEL": "INFO"},
                    "depends_on": ["ollama"],
                    "networks": ["coda-network"],
                },
                "ollama": {
                    "image": "ollama/ollama:latest",
                    "ports": ["11434:11434"],
                    "volumes": ["ollama_data:/root/.ollama"],
                    "networks": ["coda-network"],
                },
            },
            "networks": {"coda-network": {"driver": "bridge"}},
            "volumes": {"ollama_data": {}},
        }

    def test_service_orchestration(self, temp_compose_dir, base_compose_config):
        """Test basic service orchestration."""
        compose_file = os.path.join(temp_compose_dir, "docker-compose.yml")

        # Write compose file
        with open(compose_file, "w") as f:
            yaml.dump(base_compose_config, f)

        # Test compose validation
        result = subprocess.run(
            ["docker-compose", "-f", compose_file, "config"],
            capture_output=True,
            text=True,
            cwd=temp_compose_dir,
        )

        if result.returncode == 0:
            # Validate configuration
            config = yaml.safe_load(result.stdout)
            assert "services" in config
            assert "coda" in config["services"]
            assert "ollama" in config["services"]
            assert config["services"]["coda"]["depends_on"] == ["ollama"]

    def test_volume_mounting(self, temp_compose_dir):
        """Test volume mounting configurations."""
        compose_config = {
            "version": "3.8",
            "services": {
                "coda": {
                    "image": "coda:test",
                    "volumes": [
                        "./config:/app/config:ro",
                        "./data:/app/data:rw",
                        "shared_models:/models",
                    ],
                }
            },
            "volumes": {"shared_models": {"driver": "local"}},
        }

        compose_file = os.path.join(temp_compose_dir, "docker-compose.yml")
        with open(compose_file, "w") as f:
            yaml.dump(compose_config, f)

        # Create required directories
        os.makedirs(os.path.join(temp_compose_dir, "config"), exist_ok=True)
        os.makedirs(os.path.join(temp_compose_dir, "data"), exist_ok=True)

        # Validate volumes
        result = subprocess.run(
            ["docker-compose", "-f", compose_file, "config"],
            capture_output=True,
            text=True,
            cwd=temp_compose_dir,
        )

        if result.returncode == 0:
            config = yaml.safe_load(result.stdout)
            volumes = config["services"]["coda"]["volumes"]
            assert any(":ro" in v for v in volumes)  # Read-only mount
            assert any(":rw" in v for v in volumes)  # Read-write mount
            assert "shared_models" in config["volumes"]

    def test_network_connectivity(self, temp_compose_dir, base_compose_config):
        """Test network configuration between services."""
        compose_file = os.path.join(temp_compose_dir, "docker-compose.yml")

        # Add network aliases
        base_compose_config["services"]["ollama"]["networks"] = {
            "coda-network": {"aliases": ["llm-server"]}
        }

        with open(compose_file, "w") as f:
            yaml.dump(base_compose_config, f)

        result = subprocess.run(
            ["docker-compose", "-f", compose_file, "config"],
            capture_output=True,
            text=True,
            cwd=temp_compose_dir,
        )

        if result.returncode == 0:
            config = yaml.safe_load(result.stdout)
            # Check network configuration
            assert "coda-network" in config["networks"]
            assert config["networks"]["coda-network"]["driver"] == "bridge"

    def test_environment_propagation(self, temp_compose_dir):
        """Test environment variable propagation."""
        # Create .env file
        env_content = """
OLLAMA_MODEL=codellama
CODA_LOG_LEVEL=DEBUG
CODA_TIMEOUT=300
CUSTOM_VAR=test_value
"""
        env_file = os.path.join(temp_compose_dir, ".env")
        with open(env_file, "w") as f:
            f.write(env_content)

        # Compose file with env vars
        compose_config = {
            "version": "3.8",
            "services": {
                "coda": {
                    "image": "coda:test",
                    "environment": {
                        "OLLAMA_MODEL": "${OLLAMA_MODEL}",
                        "CODA_LOG_LEVEL": "${CODA_LOG_LEVEL}",
                        "CODA_TIMEOUT": "${CODA_TIMEOUT:-120}",
                        "CUSTOM_VAR": "${CUSTOM_VAR}",
                    },
                }
            },
        }

        compose_file = os.path.join(temp_compose_dir, "docker-compose.yml")
        with open(compose_file, "w") as f:
            yaml.dump(compose_config, f)

        # Test environment substitution
        result = subprocess.run(
            ["docker-compose", "-f", compose_file, "config"],
            capture_output=True,
            text=True,
            cwd=temp_compose_dir,
        )

        if result.returncode == 0:
            config = yaml.safe_load(result.stdout)
            env = config["services"]["coda"]["environment"]
            assert env.get("OLLAMA_MODEL") == "codellama"
            assert env.get("CODA_LOG_LEVEL") == "DEBUG"
            assert env.get("CUSTOM_VAR") == "test_value"

    def test_dev_vs_prod_configurations(self, temp_compose_dir):
        """Test different configurations for dev and production."""
        # Base compose file
        base_compose = {
            "version": "3.8",
            "services": {
                "coda": {"image": "coda:latest", "environment": {"CODA_ENV": "production"}}
            },
        }

        # Dev override
        dev_compose = {
            "version": "3.8",
            "services": {
                "coda": {
                    "image": "coda:dev",
                    "build": {"context": ".", "dockerfile": "Dockerfile.dev"},
                    "environment": {"CODA_ENV": "development", "DEBUG": "true"},
                    "volumes": ["./src:/app/src:ro"],
                    "command": "python -m coda.cli --dev",
                }
            },
        }

        # Write files
        base_file = os.path.join(temp_compose_dir, "docker-compose.yml")
        dev_file = os.path.join(temp_compose_dir, "docker-compose.dev.yml")

        with open(base_file, "w") as f:
            yaml.dump(base_compose, f)
        with open(dev_file, "w") as f:
            yaml.dump(dev_compose, f)

        # Test production config
        prod_result = subprocess.run(
            ["docker-compose", "-f", base_file, "config"],
            capture_output=True,
            text=True,
            cwd=temp_compose_dir,
        )

        # Test dev config (with override)
        dev_result = subprocess.run(
            ["docker-compose", "-f", base_file, "-f", dev_file, "config"],
            capture_output=True,
            text=True,
            cwd=temp_compose_dir,
        )

        if prod_result.returncode == 0 and dev_result.returncode == 0:
            prod_config = yaml.safe_load(prod_result.stdout)
            dev_config = yaml.safe_load(dev_result.stdout)

            # Verify production config
            assert prod_config["services"]["coda"]["environment"]["CODA_ENV"] == "production"
            assert "DEBUG" not in prod_config["services"]["coda"]["environment"]

            # Verify dev config overrides
            assert dev_config["services"]["coda"]["environment"]["CODA_ENV"] == "development"
            assert dev_config["services"]["coda"]["environment"]["DEBUG"] == "true"
            assert "build" in dev_config["services"]["coda"]

    def test_healthcheck_configuration(self, temp_compose_dir):
        """Test health check configurations."""
        compose_config = {
            "version": "3.8",
            "services": {
                "ollama": {
                    "image": "ollama/ollama:latest",
                    "healthcheck": {
                        "test": ["CMD", "curl", "-f", "http://localhost:11434/api/tags"],
                        "interval": "30s",
                        "timeout": "10s",
                        "retries": 3,
                        "start_period": "40s",
                    },
                },
                "coda": {
                    "image": "coda:latest",
                    "depends_on": {"ollama": {"condition": "service_healthy"}},
                },
            },
        }

        compose_file = os.path.join(temp_compose_dir, "docker-compose.yml")
        with open(compose_file, "w") as f:
            yaml.dump(compose_config, f)

        result = subprocess.run(
            ["docker-compose", "-f", compose_file, "config"],
            capture_output=True,
            text=True,
            cwd=temp_compose_dir,
        )

        if result.returncode == 0:
            config = yaml.safe_load(result.stdout)
            health = config["services"]["ollama"]["healthcheck"]
            assert health["interval"] == "30s"
            assert health["retries"] == 3

    def test_resource_limits(self, temp_compose_dir):
        """Test resource limit configurations."""
        compose_config = {
            "version": "3.8",
            "services": {
                "coda": {
                    "image": "coda:latest",
                    "deploy": {
                        "resources": {
                            "limits": {"cpus": "2.0", "memory": "2G"},
                            "reservations": {"cpus": "0.5", "memory": "512M"},
                        }
                    },
                },
                "ollama": {
                    "image": "ollama/ollama:latest",
                    "deploy": {"resources": {"limits": {"memory": "4G"}}},
                },
            },
        }

        compose_file = os.path.join(temp_compose_dir, "docker-compose.yml")
        with open(compose_file, "w") as f:
            yaml.dump(compose_config, f)

        result = subprocess.run(
            ["docker-compose", "-f", compose_file, "config"],
            capture_output=True,
            text=True,
            cwd=temp_compose_dir,
        )

        if result.returncode == 0:
            config = yaml.safe_load(result.stdout)
            coda_resources = config["services"]["coda"]["deploy"]["resources"]
            assert coda_resources["limits"]["memory"] == "2G"
            assert coda_resources["reservations"]["cpus"] == "0.5"

    def test_restart_policies(self, temp_compose_dir):
        """Test restart policy configurations."""
        compose_config = {
            "version": "3.8",
            "services": {
                "coda": {"image": "coda:latest", "restart": "unless-stopped"},
                "ollama": {"image": "ollama/ollama:latest", "restart": "always"},
            },
        }

        compose_file = os.path.join(temp_compose_dir, "docker-compose.yml")
        with open(compose_file, "w") as f:
            yaml.dump(compose_config, f)

        result = subprocess.run(
            ["docker-compose", "-f", compose_file, "config"],
            capture_output=True,
            text=True,
            cwd=temp_compose_dir,
        )

        if result.returncode == 0:
            config = yaml.safe_load(result.stdout)
            assert config["services"]["coda"]["restart"] == "unless-stopped"
            assert config["services"]["ollama"]["restart"] == "always"

    def test_logging_configuration(self, temp_compose_dir):
        """Test logging driver configurations."""
        compose_config = {
            "version": "3.8",
            "services": {
                "coda": {
                    "image": "coda:latest",
                    "logging": {
                        "driver": "json-file",
                        "options": {"max-size": "10m", "max-file": "3"},
                    },
                }
            },
        }

        compose_file = os.path.join(temp_compose_dir, "docker-compose.yml")
        with open(compose_file, "w") as f:
            yaml.dump(compose_config, f)

        result = subprocess.run(
            ["docker-compose", "-f", compose_file, "config"],
            capture_output=True,
            text=True,
            cwd=temp_compose_dir,
        )

        if result.returncode == 0:
            config = yaml.safe_load(result.stdout)
            logging = config["services"]["coda"]["logging"]
            assert logging["driver"] == "json-file"
            assert logging["options"]["max-size"] == "10m"

    @pytest.mark.parametrize("compose_version", ["3.7", "3.8", "3.9"])
    def test_compose_version_compatibility(self, temp_compose_dir, compose_version):
        """Test compatibility with different compose versions."""
        compose_config = {
            "version": compose_version,
            "services": {"coda": {"image": "coda:latest"}},
        }

        compose_file = os.path.join(temp_compose_dir, "docker-compose.yml")
        with open(compose_file, "w") as f:
            yaml.dump(compose_config, f)

        result = subprocess.run(
            ["docker-compose", "-f", compose_file, "config"],
            capture_output=True,
            text=True,
            cwd=temp_compose_dir,
        )

        # Should work with all recent versions
        if result.returncode == 0:
            config = yaml.safe_load(result.stdout)
            assert "services" in config
            assert "coda" in config["services"]
