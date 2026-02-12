#!/bin/bash

# Test script to verify LM Studio health check functionality

echo "Testing LM Studio health check functionality..."

HEALTH_RESPONSE=$(curl -s -X POST http://localhost:3050/send \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "health-test",
    "method": "tools/call",
    "params": {
      "name": "lmstudio_health",
      "arguments": {}
    }
  }')

echo "Health response: $HEALTH_RESPONSE"

# Check if the response contains the expected health information
if echo "$HEALTH_RESPONSE" | grep -q '"status"'; then
    echo "SUCCESS: LM Studio health check worked correctly"
    exit 0
else
    echo "ERROR: LM Studio health check failed"
    exit 1
fi