#!/bin/bash
# Script to start the MCP Explorer test server

PORT=${1:-3031}
echo "Starting MCP Streamable HTTP test server on port $PORT..."

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate the virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

cd "$SCRIPT_DIR" && python test_server.py --port $PORT