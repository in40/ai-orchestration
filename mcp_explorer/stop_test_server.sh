#!/bin/bash
# Script to stop the MCP Explorer test server

echo "Stopping MCP Streamable HTTP test server..."
pkill -f "test_server.py"
echo "MCP test server stopped."