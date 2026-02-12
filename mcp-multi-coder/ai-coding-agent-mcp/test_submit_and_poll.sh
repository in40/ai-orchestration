#!/bin/bash

# Test script to submit a coding task and poll for completion

echo "Testing submit and poll functionality..."

# Submit a simple coding task
TASK_RESPONSE=$(curl -s -X POST http://localhost:3050/send \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "submit-test",
    "method": "tools/call",
    "params": {
      "name": "submit_coding_task",
      "arguments": {
        "task": "Write a Python function to add two numbers",
        "language": "Python"
      }
    }
  }')

echo "Submit response: $TASK_RESPONSE"

# Extract task ID from response
TASK_ID=$(echo "$TASK_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['result']['task_id'])" 2>/dev/null)

if [ -z "$TASK_ID" ]; then
    echo "ERROR: Could not extract task ID from response"
    echo "Response was: $TASK_RESPONSE"
    exit 1
fi

echo "Submitted task with ID: $TASK_ID"

# Poll for task completion
MAX_POLLS=30
POLL_COUNT=0
STATUS="unknown"

while [ "$STATUS" != "completed" ] && [ "$STATUS" != "failed" ] && [ $POLL_COUNT -lt $MAX_POLLS ]; do
    sleep 2
    
    STATUS_RESPONSE=$(curl -s -X POST http://localhost:3050/send \
      -H "Content-Type: application/json" \
      -d "{
        \"jsonrpc\": \"2.0\",
        \"id\": \"status-$POLL_COUNT\",
        \"method\": \"tools/call\",
        \"params\": {
          \"name\": \"get_task_status\",
          \"arguments\": {
            \"task_id\": \"$TASK_ID\"
          }
        }
      }")
    
    echo "Poll response: $STATUS_RESPONSE"
    
    STATUS=$(echo "$STATUS_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['result']['status'])" 2>/dev/null)
    
    echo "Task status: $STATUS"
    POLL_COUNT=$((POLL_COUNT + 1))
done

if [ "$STATUS" = "completed" ]; then
    echo "SUCCESS: Task completed successfully"
    
    # Get the result
    RESULT=$(echo "$STATUS_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['result']['result'])" 2>/dev/null)
    echo "Task result preview: ${RESULT:0:100}..."
    
    exit 0
elif [ "$STATUS" = "failed" ]; then
    echo "ERROR: Task failed"
    ERROR_MSG=$(echo "$STATUS_RESPONSE" | python -c "import sys, json; print(json.load(sys.stdin)['result']['error'])" 2>/dev/null)
    echo "Error message: $ERROR_MSG"
    exit 1
else
    echo "ERROR: Task did not complete within expected time ($MAX_POLLS polls)"
    exit 1
fi