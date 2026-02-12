#!/bin/bash

# Registry-Based Concurrent Request Load Test for MCP Server
# Discovers services from registry and tests their capabilities

set -e  # Exit on any error

# Default configuration - only need registry URL now
REGISTRY_URL="${1:-http://127.0.0.1:3031}"
NUM_REQUESTS="${2:-5}"
PYTHON_CMD="python"

# Function to display usage
usage() {
    echo "Usage: $0 [REGISTRY_URL] [NUM_REQUESTS_PER_SERVICE]"
    echo ""
    echo "Arguments:"
    echo "  REGISTRY_URL              Registry server URL (default: http://127.0.0.1:3031)"
    echo "  NUM_REQUESTS_PER_SERVICE  Number of concurrent requests per service (default: 5)"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Test with defaults (5 concurrent requests per service)"
    echo "  $0 http://127.0.0.1:3031 10         # 10 concurrent requests per service"
    echo "  $0 http://my-registry:3031 3        # 3 concurrent requests per service"
    exit 1
}

# Check if Python command exists
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "Error: Python command '$PYTHON_CMD' not found"
    exit 1
fi

# Check if test script exists
if [[ ! -f "test_simple_registry_concurrent.py" ]]; then
    echo "Error: test_simple_registry_concurrent.py not found"
    exit 1
fi

echo "🚀 REGISTRY-BASED CONCURRENT REQUEST LOAD TEST FOR MCP SERVER"
echo "================================================================"
echo "Registry URL: $REGISTRY_URL"
echo "Number of concurrent requests per service: $NUM_REQUESTS"
echo ""

# Run the registry-based concurrent load test
echo "🧪 Running registry-based concurrent request tests..."
echo ""

"$PYTHON_CMD" test_simple_registry_concurrent.py --registry-url "$REGISTRY_URL" --requests-per-service "$NUM_REQUESTS"

echo ""
echo "🎯 REGISTRY-BASED CONCURRENT REQUEST TEST COMPLETED"
echo "   - Discovered services from registry automatically"
echo "   - Tested concurrent calls to all discovered services"
echo "   - Verified multiple simultaneous requests handling via SSE"
echo "   - Measured performance metrics and success rates"
echo "   - Confirmed concurrent request processing on all services"