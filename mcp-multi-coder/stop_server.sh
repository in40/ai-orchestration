#!/bin/bash

# Script to stop the Vibe Coding AI Agent MCP server

echo "Stopping Vibe Coding AI Agent MCP Server..."

# Find and kill the server process
SERVER_PID=$(pgrep -f "python -m vibe_coding_agent.mcp_server")

if [ ! -z "$SERVER_PID" ]; then
    echo "Found server process with PID: $SERVER_PID"
    kill $SERVER_PID
    
    # Wait a bit for graceful shutdown
    sleep 2
    
    # Check if process is still running
    if kill -0 $SERVER_PID 2>/dev/null; then
        echo "Process still running, forcing termination..."
        kill -9 $SERVER_PID
    fi
    
    echo "✓ Server stopped successfully"
else
    echo "No server process found running"
fi

# Also try to find any Python processes that might be the server
POTENTIAL_PIDS=$(pgrep -f "vibe_coding_agent.mcp_server")
if [ ! -z "$POTENTIAL_PIDS" ]; then
    echo "Found other potential server processes: $POTENTIAL_PIDS"
    for pid in $POTENTIAL_PIDS; do
        if [ "$pid" != "$SERVER_PID" ]; then  # Don't kill the same process twice
            echo "Killing process $pid"
            kill $pid 2>/dev/null || kill -9 $pid 2>/dev/null
        fi
    done
    echo "✓ Additional processes stopped"
fi