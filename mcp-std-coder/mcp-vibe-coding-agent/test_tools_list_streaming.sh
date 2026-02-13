#!/bin/bash

# Shell script to call tools/list via streaming HTTP
# This script sends a JSON-RPC request to the MCP server and handles the response

SERVER_URL="http://127.0.0.1:3060/mcp"

echo "Calling tools/list via streaming HTTP..."
echo "Server URL: $SERVER_URL"
echo ""

# Send the JSON-RPC request using curl with streaming
curl -X POST "$SERVER_URL" \
  -H "Content-Type: application/json" \
  -H "Accept: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "tools-list-request-'$(date +%s)'",
    "method": "tools/list"
  }' \
  --no-buffer

echo ""
echo ""
echo "Request completed."