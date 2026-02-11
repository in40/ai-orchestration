#!/bin/bash

# Registry-Based Concurrent Request Load Test for MCP Server
# Queries the registry for available services and tests their capabilities

set -e  # Exit on any error

# Default configuration
REGISTRY_URL="${1:-http://127.0.0.1:3031}"
NUM_REQUESTS_PER_SERVICE="${2:-3}"
PYTHON_CMD="python"

# Function to display usage
usage() {
    echo "Usage: $0 [REGISTRY_URL] [NUM_REQUESTS_PER_SERVICE]"
    echo ""
    echo "Arguments:"
    echo "  REGISTRY_URL              Registry server URL (default: http://127.0.0.1:3031)"
    echo "  NUM_REQUESTS_PER_SERVICE  Number of concurrent requests per service (default: 3)"
    echo ""
    echo "Examples:"
    echo "  $0                                      # Test with defaults (3 concurrent requests per service)"
    echo "  $0 http://127.0.0.1:3031 5             # 5 concurrent requests per service"
    echo "  $0 http://my-registry:3031 10          # 10 concurrent requests per service"
    exit 1
}

# Check if Python command exists
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "Error: Python command '$PYTHON_CMD' not found"
    exit 1
fi

# Check if test script exists
if [[ ! -f "test_registry_concurrent.py" ]]; then
    echo "Error: test_registry_concurrent.py not found"
    exit 1
fi

echo "🚀 REGISTRY-BASED CONCURRENT REQUEST LOAD TEST"
echo "================================================================"
echo "Registry URL: $REGISTRY_URL"
echo "Number of concurrent requests per service: $NUM_REQUESTS_PER_SERVICE"
echo ""

# Run the registry-based concurrent load test
echo "🧪 Running registry-based concurrent request tests..."
echo ""

"$PYTHON_CMD" test_registry_concurrent.py --registry-url "$REGISTRY_URL" --requests-per-service "$NUM_REQUESTS_PER_SERVICE"

echo ""
echo "🎯 REGISTRY-BASED CONCURRENT REQUEST TEST COMPLETED"
echo "   - Queried registry for available services"
echo "   - Tested capabilities of each discovered service"
echo "   - Verified concurrent request handling via SSE transport"
echo "   - Measured performance metrics and success rates"