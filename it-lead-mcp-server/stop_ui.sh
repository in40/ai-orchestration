#!/bin/bash

# Script to stop the Web UI components (backend and frontend)
# Usage: ./stop_ui.sh

echo "Stopping MCP Agent Web UI..."

# Find and kill the Web UI backend process (uvicorn)
echo "Stopping Web UI backend..."
UVICORN_PIDS=$(pgrep -f "uvicorn.*main:app")
if [ -n "$UVICORN_PIDS" ]; then
    echo "Found uvicorn processes: $UVICORN_PIDS"
    kill $UVICORN_PIDS
    echo "Web UI backend stopped."
else
    echo "No Web UI backend processes found."
fi

# Find and kill the Web UI frontend process (npm run dev)
echo "Stopping Web UI frontend..."
NPM_PIDS=$(pgrep -f "npm.*run.*dev.*--.*--port")
if [ -n "$NPM_PIDS" ]; then
    echo "Found npm dev processes: $NPM_PIDS"
    kill $NPM_PIDS
    echo "Web UI frontend stopped."
else
    echo "No Web UI frontend processes found."
fi

# Alternative: kill any remaining node processes that might be related to the frontend
NODE_PIDS=$(pgrep -f "node.*vite" | grep -v $$)
if [ -n "$NODE_PIDS" ]; then
    echo "Found additional node processes: $NODE_PIDS"
    kill $NODE_PIDS
    echo "Additional node processes stopped."
fi

echo "MCP Agent Web UI stopped successfully!"