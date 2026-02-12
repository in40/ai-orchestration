#!/bin/bash
# Script to start the MCP Explorer test server

PORT=${1:-3031}
echo "Starting MCP Streamable HTTP test server on port $PORT..."

cd /root/qwen/base/mcp_explorer && python test_server.py --port $PORT