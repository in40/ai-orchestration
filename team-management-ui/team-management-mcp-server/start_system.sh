#!/bin/bash

# Main startup script for Team Management System
# Starts the MCP server and the combined API/Web server

echo "Starting Team Management System..."

# Start the MCP server in the background
echo "Starting Team Management MCP Server..."
nohup ./start_team_management_server.sh > mcp_server.log 2>&1 &
MCP_SERVER_PID=$!
echo "MCP Server started with PID: $MCP_SERVER_PID"

# Wait a moment for the MCP server to start
sleep 3

# Start the combined API and Web server in the background
echo "Starting Team Management API and Web Server..."
cd team_management_app
source ../venv/bin/activate  # Activate virtual environment
nohup python api_server.py > api_server.log 2>&1 &
COMBINED_SERVER_PID=$!
echo "Combined API and Web Server started with PID: $COMBINED_SERVER_PID"

echo "Team Management System is running!"
echo "MCP Server: http://localhost:3063"
echo "Combined API/Web Server: http://localhost:5001"
echo ""
echo "Press Ctrl+C to stop the system..."

# Function to handle shutdown
cleanup() {
    echo ""
    echo "Shutting down Team Management System..."
    
    # Kill the combined API and Web server process
    if [ ! -z "$COMBINED_SERVER_PID" ]; then
        echo "Stopping Combined API and Web Server (PID: $COMBINED_SERVER_PID)..."
        kill $COMBINED_SERVER_PID 2>/dev/null
    fi
    
    # Stop the MCP server using the stop script
    echo "Stopping MCP Server..."
    ./stop_team_management_server.sh
    
    echo "Team Management System stopped."
    exit 0
}

# Trap SIGINT and SIGTERM to handle cleanup
trap cleanup SIGINT SIGTERM

# Wait for processes to finish (they run in background, so this waits indefinitely)
wait $MCP_SERVER_PID