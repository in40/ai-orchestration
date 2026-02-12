#!/bin/bash

# AI Coding Agent MCP Server startup script
# Starts the server with default settings and registers with registry

echo "Starting AI Coding Agent MCP Server..."

# Set default values
TRANSPORT="${TRANSPORT:-http}"
HOST="${HOST:-127.0.0.1}"
PORT="${PORT:-3060}"
MAX_CONCURRENT_REQUESTS="${MAX_CONCURRENT_REQUESTS:-10}"
REGISTER_WITH_REGISTRY="${REGISTER_WITH_REGISTRY:-true}"
REGISTRY_HOST="${REGISTRY_HOST:-127.0.0.1}"
REGISTRY_PORT="${REGISTRY_PORT:-3031}"

# Start the server with registry registration
if [ "$REGISTER_WITH_REGISTRY" = "true" ]; then
    echo "Registering with registry at $REGISTRY_HOST:$REGISTRY_PORT"
    python -m mcp_server.server \
        --transport "$TRANSPORT" \
        --host "$HOST" \
        --port "$PORT" \
        --register-with-registry \
        --registry-host "$REGISTRY_HOST" \
        --registry-port "$REGISTRY_PORT" \
        --max-concurrent-requests "$MAX_CONCURRENT_REQUESTS"
else
    python -m mcp_server.server \
        --transport "$TRANSPORT" \
        --host "$HOST" \
        --port "$PORT" \
        --max-concurrent-requests "$MAX_CONCURRENT_REQUESTS"
fi

echo "AI Coding Agent MCP Server stopped."