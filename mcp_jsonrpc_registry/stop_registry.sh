#!/bin/bash

# Script to stop the MCP JSON-RPC Registry

echo "Stopping MCP JSON-RPC Registry..."

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Use environment variables for configuration, with defaults
PORT=${HTTP_PORT:-"6000"}

# Check if a registry instance is running on this port
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Stopping registry server on port $PORT..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
    sleep 2
    
    if ! lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        echo "Registry server stopped successfully."
    else
        echo "Failed to stop registry server on port $PORT."
        exit 1
    fi
else
    echo "No registry server found running on port $PORT."
fi