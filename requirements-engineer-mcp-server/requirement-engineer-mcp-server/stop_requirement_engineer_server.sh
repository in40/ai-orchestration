#!/bin/bash

# Script to stop the Requirement Engineer MCP server
# This script finds and kills only the requirement engineer server process

echo "Stopping Requirement Engineer MCP Server..."

# Find the PID of the requirement engineer server process
SERVER_PID=$(pgrep -f "requirement_engineer_server.py")

if [ -z "$SERVER_PID" ]; then
    echo "Requirement Engineer MCP Server is not running or could not be found."
    exit 0
else
    echo "Found Requirement Engineer MCP Server with PID: $SERVER_PID"
    kill $SERVER_PID
    
    # Wait a moment for the process to terminate
    sleep 2
    
    # Check if the process is still running
    if pgrep -f "requirement_engineer_server.py" > /dev/null; then
        echo "Process still running, force killing..."
        kill -9 $SERVER_PID
    fi
    
    echo "Requirement Engineer MCP Server stopped."
fi