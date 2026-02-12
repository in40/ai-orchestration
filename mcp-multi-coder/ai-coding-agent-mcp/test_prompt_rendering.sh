#!/bin/bash

# Test script to verify prompt rendering functionality

echo "Testing prompt rendering functionality..."

# Create a temporary prompt file for testing
cat > ./prompts/test_prompt.txt << EOF
This is a test prompt with variables:
Task: {task_description}
Language: {language}
Priority: {priority}
EOF

# Test rendering the prompt
RENDER_RESPONSE=$(curl -s -X POST http://localhost:3050/send \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "render-test",
    "method": "tools/call",
    "params": {
      "name": "render_prompt",
      "arguments": {
        "template_name": "test_prompt",
        "variables": {
          "task_description": "Implement a sorting algorithm",
          "language": "Python",
          "priority": "high"
        }
      }
    }
  }')

echo "Render response: $RENDER_RESPONSE"

# Check if the response contains the expected rendered prompt
if echo "$RENDER_RESPONSE" | grep -q "sorting algorithm"; then
    echo "SUCCESS: Prompt rendering worked correctly"
    rm -f ./prompts/test_prompt.txt
    exit 0
else
    echo "ERROR: Prompt rendering failed"
    rm -f ./prompts/test_prompt.txt
    exit 1
fi