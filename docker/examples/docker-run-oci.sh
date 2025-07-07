#!/bin/bash
# Example script to run Coda with OCI GenAI configuration

# Build the OCI-focused image
docker build -f Dockerfile.oci -t coda-code-assistant:oci .

# Run with OCI configuration mounted
docker run -it --rm \
  --name coda-oci \
  -v ~/.oci:/home/coda/.oci:ro \
  -v coda-oci-config:/home/coda/.config/coda \
  -v coda-oci-cache:/home/coda/.cache/coda \
  -v coda-oci-data:/home/coda/.local/share/coda \
  -e OCI_CLI_COMPARTMENT_ID="${OCI_CLI_COMPARTMENT_ID}" \
  -e OCI_CLI_REGION="${OCI_CLI_REGION:-us-ashburn-1}" \
  coda-code-assistant:oci "$@"