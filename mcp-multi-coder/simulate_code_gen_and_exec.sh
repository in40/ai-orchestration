#!/bin/bash

# Simulation script for code generation and execution
# Tests generate_code, write_file_content, and execute_code tools

set -e  # Exit on any error

echo "=== Code Generation and Execution Simulation ==="
echo "Testing generate_code, write_file_content, and execute_code tools..."

# Test generate_code
echo "1. Testing generate_code for a factorial function..."
CODE_RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-gen-1",
    "method": "tools/call",
    "params": {
      "name": "generate_code",
      "arguments": {
        "specification": "Create a Python function that calculates factorial using recursion. Include proper error handling for negative numbers.",
        "language": "python",
        "file_path": "factorial.py"
      }
    }
  }')

echo "Generated Code Response:"
echo "$CODE_RESPONSE" | jq '.' || echo "$CODE_RESPONSE"

# Extract code and file path from response
CODE=$(echo "$CODE_RESPONSE" | jq -r '.result.code // empty' 2>/dev/null || echo "")
FILE_PATH=$(echo "$CODE_RESPONSE" | jq -r '.result.file_path // "test_factorial.py"' 2>/dev/null || echo "test_factorial.py")

if [ -n "$CODE" ] && [ "$CODE" != "null" ]; then
    echo "2. Testing write_file_content to save the generated code..."
    WRITE_RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
      -H "Content-Type: application/json" \
      -d "{
        \"jsonrpc\": \"2.0\",
        \"id\": \"test-write-1\",
        \"method\": \"tools/call\",
        \"params\": {
          \"name\": \"write_file_content\",
          \"arguments\": {
            \"file_path\": \"$FILE_PATH\",
            \"content\": $(printf '%s' "$CODE" | jq -sR '.'),
            \"confirm_write\": true
          }
        }
      }")
    
    echo "Write Response:"
    echo "$WRITE_RESPONSE" | jq '.' || echo "$WRITE_RESPONSE"
    
    echo "3. Testing execute_code to run the factorial function..."
    EXECUTE_RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
      -H "Content-Type: application/json" \
      -d "{
        \"jsonrpc\": \"2.0\",
        \"id\": \"test-exec-1\",
        \"method\": \"tools/call\",
        \"params\": {
          \"name\": \"execute_code\",
          \"arguments\": {
            \"code\": $(printf '%s' \"$CODE\" | jq -sR '.'),
            \"language\": \"python\",
            \"timeout\": 10
          }
        }
      }")
    
    echo "Execute Response:"
    echo "$EXECUTE_RESPONSE" | jq '.' || echo "$EXECUTE_RESPONSE"
else
    echo "Warning: Could not extract code from response"
fi

echo "=== Code Generation and Execution Simulation Complete ==="