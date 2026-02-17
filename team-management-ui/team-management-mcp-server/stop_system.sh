#!/bin/bash

# Stop script for the entire Team Management System
# Stops the MCP server and the combined API/Web server

echo "Stopping Team Management System..."

# Stop the MCP server
echo "Stopping Team Management MCP Server..."
./stop_team_management_server.sh

# Find and kill the combined API and Web server process
COMBINED_SERVER_PID=$(ps aux | grep "api_server.py" | grep -v grep | awk '{print $2}')

if [ -n "$COMBINED_SERVER_PID" ]; then
    echo "Found Combined API and Web Server process with PID: $COMBINED_SERVER_PID"
    kill -TERM $COMBINED_SERVER_PID
    
    # Wait a few seconds for graceful shutdown
    sleep 2
    
    # Check if process is still running and force kill if necessary
    if ps -p $COMBINED_SERVER_PID > /dev/null; then
        echo "Combined API and Web Server process still running, forcing kill..."
        kill -9 $COMBINED_SERVER_PID
    fi
    
    echo "Combined API and Web Server stopped."
else
    echo "Combined API and Web Server is not running."
fi

echo "Team Management System stopped."