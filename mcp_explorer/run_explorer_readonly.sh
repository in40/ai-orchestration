#!/bin/bash
# Script to run the MCP Explorer Read-Only version from local virtual environment

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Activate the virtual environment
source "$SCRIPT_DIR/venv/bin/activate"

echo "Starting MCP Explorer Read-Only from local environment..."
mcp-explorer-readonly