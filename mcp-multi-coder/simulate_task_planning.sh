#!/bin/bash

# Simulation script for task planning
# Tests the accept_task and get_plan_status tools

set -e  # Exit on any error

echo "=== Task Planning Simulation ==="
echo "Testing accept_task and get_plan_status tools..."

# Test accept_task
echo "1. Testing accept_task with a sample development task..."
TASK_RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-plan-1",
    "method": "tools/call",
    "params": {
      "name": "accept_task",
      "arguments": {
        "task_description": "Create a Python function that calculates the factorial of a number using recursion"
      }
    }
  }')

echo "Response:"
echo "$TASK_RESPONSE" | jq '.' || echo "$TASK_RESPONSE"

# Extract plan_id from response
PLAN_ID=$(echo "$TASK_RESPONSE" | jq -r '.result.plan_id // empty' 2>/dev/null || echo "")
if [ -n "$PLAN_ID" ] && [ "$PLAN_ID" != "null" ]; then
    echo "2. Testing get_plan_status with plan_id: $PLAN_ID"
    STATUS_RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
      -H "Content-Type: application/json" \
      -d "{
        \"jsonrpc\": \"2.0\",
        \"id\": \"test-status-1\",
        \"method\": \"tools/call\",
        \"params\": {
          \"name\": \"get_plan_status\",
          \"arguments\": {
            \"plan_id\": \"$PLAN_ID\"
          }
        }
      }")
    
    echo "Status Response:"
    echo "$STATUS_RESPONSE" | jq '.' || echo "$STATUS_RESPONSE"
else
    echo "Warning: Could not extract plan_id from response"
fi

echo "=== Task Planning Simulation Complete ==="