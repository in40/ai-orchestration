#!/bin/bash
# Script to run the MCP Explorer from local virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate the virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

echo "Starting MCP Explorer from local environment..."
mcp-explorer