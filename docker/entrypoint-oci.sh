#!/bin/bash
set -e

echo "Starting Coda for OCI GenAI usage..."

# Check if OCI config exists
if [ ! -f "$HOME/.oci/config" ]; then
    echo "⚠️  OCI configuration not found at $HOME/.oci/config"
    echo "   Please mount your OCI config directory or set up OCI configuration."
    echo "   Example: -v ~/.oci:/home/coda/.oci:ro"
    echo ""
fi

# Check if OCI environment variables are set
if [ -z "$OCI_CONFIG_FILE" ] && [ -z "$OCI_CLI_USER" ]; then
    echo "ℹ️  OCI configuration options:"
    echo "   1. Mount OCI config: -v ~/.oci:/home/coda/.oci:ro"
    echo "   2. Set environment variables: OCI_CLI_USER, OCI_CLI_FINGERPRINT, etc."
    echo "   3. Use instance principal (if running on OCI)"
    echo ""
fi

# Display available providers
echo "🚀 Coda is ready!"
echo "   Available providers: OCI GenAI, LiteLLM, Mock"
echo "   Default provider: OCI GenAI"
echo ""

# Execute the main command
if [ $# -eq 0 ]; then
    exec coda
else
    exec "$@"
fi