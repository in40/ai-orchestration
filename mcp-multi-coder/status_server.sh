#!/bin/bash

# Script to check the status of the Vibe Coding AI Agent MCP server

echo "Checking Vibe Coding AI Agent MCP Server status..."

SERVER_PID=$(pgrep -f "python -m vibe_coding_agent.mcp_server")

if [ ! -z "$SERVER_PID" ]; then
    echo "✓ Server is running with PID: $SERVER_PID"
    
    # Get more details about the process
    PROCESS_INFO=$(ps -p $SERVER_PID -o pid,ppid,cmd,etime,pcpu,pmem 2>/dev/null)
    if [ ! -z "$PROCESS_INFO" ]; then
        echo "$PROCESS_INFO"
    fi
    
    # Check if the port is listening
    PORT_LISTENING=$(netstat -tuln | grep ":3050 " | grep LISTEN)
    if [ ! -z "$PORT_LISTENING" ]; then
        echo "✓ Port 3050 is listening"
    else
        echo "! Port 3050 is not listening (server may be starting up)"
    fi
else
    echo "✗ Server is not running"
    
    # Check if there are any Python processes that might be related
    POTENTIAL_PROCESSES=$(pgrep -f "vibe_coding_agent" 2>/dev/null)
    if [ ! -z "$POTENTIAL_PROCESSES" ]; then
        echo "Found potential related processes:"
        ps -p $POTENTIAL_PROCESSES -o pid,cmd,etime 2>/dev/null
    fi
fi