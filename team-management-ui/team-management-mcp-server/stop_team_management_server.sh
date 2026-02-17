#!/bin/bash

# Team Management MCP Server stop script
# Stops only the team management server, not other servers

echo "Stopping Team Management MCP Server..."

# Find and kill the team management server process
TEAM_MGMT_PID=$(ps aux | grep "team_management_server" | grep -v grep | awk '{print $2}')

if [ -n "$TEAM_MGMT_PID" ]; then
    echo "Found Team Management Server process with PID: $TEAM_MGMT_PID"
    kill -TERM $TEAM_MGMT_PID
    
    # Wait a few seconds for graceful shutdown
    sleep 3
    
    # Check if process is still running and force kill if necessary
    if ps -p $TEAM_MGMT_PID > /dev/null; then
        echo "Process still running, forcing kill..."
        kill -9 $TEAM_MGMT_PID
    fi
    
    echo "Team Management MCP Server stopped."
else
    echo "Team Management MCP Server is not running."
fi