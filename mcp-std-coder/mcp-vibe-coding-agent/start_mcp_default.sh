#!/bin/bash

# Simple startup script for the standard MCP server with default settings
# Usage: ./start_mcp_default.sh

echo "Starting MCP Server with default settings..."

# Start with Streamable HTTP transport on port 3060 (updated as required)
python -m mcp_std_server.server --transport streamable-http --port 3060 --enable-registry --register-with-registry