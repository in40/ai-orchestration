#!/bin/bash

# Simple MCP Server Startup Script with Registry Option
# This script starts the Model Context Protocol (MCP) server with default settings

set -e  # Exit on any error

# Default configuration
TRANSPORT="http"
HOST="127.0.0.1"
PORT="3030"
REGISTER_WITH_REGISTRY=false
REGISTRY_HOST="127.0.0.1"
REGISTRY_PORT="3031"

# Check if Python command exists
if ! command -v python &> /dev/null; then
    echo "Error: Python command not found"
    exit 1
fi

# Check if we're in the correct directory
if [[ ! -f "mcp_server/server.py" ]]; then
    echo "Error: Cannot find mcp_server/server.py"
    echo "Make sure you're running this script from the MCP server root directory"
    exit 1
fi

echo "Starting MCP Server with default settings..."
echo "Transport: $TRANSPORT"
echo "Host: $HOST"
echo "Port: $PORT"
echo "Register with registry: $(if [[ $REGISTER_WITH_REGISTRY == true ]]; then echo "yes ($REGISTRY_HOST:$REGISTRY_PORT)"; else echo "no"; fi)"
echo ""

# Build the command
CMD="python -m mcp_server.server --transport $TRANSPORT --host $HOST --port $PORT"

if [[ "$REGISTER_WITH_REGISTRY" == true ]]; then
    CMD="$CMD --register-with-registry --registry-host $REGISTRY_HOST --registry-port $REGISTRY_PORT"
fi

# Start the server
exec $CMD