#!/bin/bash

# Simulation script for health check
# Tests the health tool

set -e  # Exit on any error

echo "=== Health Check Simulation ==="
echo "Testing health tool..."

# Test health check
echo "1. Testing health tool..."
HEALTH_RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-health-1",
    "method": "tools/call",
    "params": {
      "name": "health"
    }
  }')

echo "Health Check Response:"
echo "$HEALTH_RESPONSE" | jq '.' || echo "$HEALTH_RESPONSE"

# Check if response indicates healthy status
if echo "$HEALTH_RESPONSE" | jq -e '.result.status // empty' | grep -q "healthy"; then
    echo "✓ Server is healthy"
    EXIT_CODE=0
else
    echo "✗ Server health check failed"
    EXIT_CODE=1
fi

echo "=== Health Check Simulation Complete ==="
exit $EXIT_CODE