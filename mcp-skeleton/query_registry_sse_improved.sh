#!/bin/bash

# Improved Query Registry Server via HTTP/SSE Protocol (Shell Wrapper)
# This script provides a shell interface to query the registry using the improved Python client

set -e  # Exit on any error

# Configuration
REGISTRY_URL="${1:-http://localhost:3031}"
SERVICE_ID="$2"
TIMEOUT="${3:-15}"

echo "🔍 QUERYING REGISTRY SERVER VIA HTTP/SSE PROTOCOL (IMPROVED)"
echo "=================================================="
echo "Registry URL: $REGISTRY_URL"
if [[ -n "$SERVICE_ID" ]]; then
    echo "Service ID: $SERVICE_ID"
fi
echo "Timeout: ${TIMEOUT}s"
echo ""

# Check if Python client exists
CLIENT_FILE="query_registry_client_proper_fixed.py"
if [[ ! -f "$CLIENT_FILE" ]]; then
    # Fallback to original client if fixed version doesn't exist
    CLIENT_FILE="query_registry_client_proper.py"
    if [[ ! -f "$CLIENT_FILE" ]]; then
        echo "❌ Python registry client not found!"
        echo "   Please ensure query_registry_client_proper.py or query_registry_client_proper_fixed.py is in the same directory"
        exit 1
    fi
    echo "⚠️  Using original client as fallback"
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python is not available!"
    exit 1
fi

# Run the Python client to query the registry
if [[ -n "$SERVICE_ID" ]]; then
    echo "🔍 Querying specific service: $SERVICE_ID"
    python "$CLIENT_FILE" --registry-url "$REGISTRY_URL" --service-id "$SERVICE_ID" --timeout "$TIMEOUT"
else
    echo "🔍 Querying all registered services"
    python "$CLIENT_FILE" --registry-url "$REGISTRY_URL" --timeout "$TIMEOUT"
fi

echo ""
echo "🎯 REGISTRY QUERY COMPLETED"
echo "   - Used proper HTTP/SSE protocol via Python client"
echo "   - Opened SSE connection first, then sent requests"
echo "   - Received responses via SSE as per MCP specification"
echo "   - Retrieved complete service information"