#!/bin/bash

# Stop Registry Server Script
# This script stops the Model Context Protocol (MCP) registry server

set -e  # Exit on any error

echo "Stopping MCP Registry Server..."

# Kill any processes running the registry server (typically on port 3031)
# Look for processes with --enable-registry flag or running on registry port
REGISTRY_PIDS=$(pgrep -f "python.*mcp_server.server.*--enable-registry\|--port.*3031\|--port.*3032" 2>/dev/null) || true

if [ -n "$REGISTRY_PIDS" ]; then
    echo "Found registry server processes with PIDs: $REGISTRY_PIDS"
    echo "Terminating registry server processes..."
    kill $REGISTRY_PIDS 2>/dev/null || true
    
    # Wait a moment for graceful shutdown
    sleep 2
    
    # Check if processes are still running and force kill if necessary
    STILL_RUNNING=$(pgrep -f "python.*mcp_server.server.*--enable-registry\|--port.*3031\|--port.*3032" 2>/dev/null) || true
    if [ -n "$STILL_RUNNING" ]; then
        echo "Some registry processes still running, forcing termination..."
        kill -9 $STILL_RUNNING 2>/dev/null || true
    fi
    echo "Registry server processes stopped."
else
    echo "No registry server processes found running."
fi

echo "MCP Registry Server stop procedure completed."