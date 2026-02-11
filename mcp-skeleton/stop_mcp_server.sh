#!/bin/bash

# Stop MCP Server Script
# This script stops the Model Context Protocol (MCP) server instances

set -e  # Exit on any error

echo "Stopping MCP Server instances..."

# Kill any processes running the MCP server
# Look for processes running mcp_server.server module
MCP_SERVER_PIDS=$(pgrep -f "python.*mcp_server.server" 2>/dev/null) || true

if [ -n "$MCP_SERVER_PIDS" ]; then
    echo "Found MCP server processes with PIDs: $MCP_SERVER_PIDS"
    echo "Terminating MCP server processes..."
    kill $MCP_SERVER_PIDS 2>/dev/null || true
    
    # Wait a moment for graceful shutdown
    sleep 2
    
    # Check if processes are still running and force kill if necessary
    STILL_RUNNING=$(pgrep -f "python.*mcp_server.server" 2>/dev/null) || true
    if [ -n "$STILL_RUNNING" ]; then
        echo "Some MCP server processes still running, forcing termination..."
        kill -9 $STILL_RUNNING 2>/dev/null || true
    fi
    echo "MCP server processes stopped."
else
    echo "No MCP server processes found running."
fi

echo "MCP Server stop procedure completed."