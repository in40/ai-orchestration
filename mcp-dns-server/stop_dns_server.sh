#!/bin/bash

# DNS Resolving MCP Server stop script
# Stops all instances of the DNS Resolving MCP Server

set -e  # Exit on any error

echo "Stopping DNS Resolving MCP Server..."

# Kill all processes running dns_mcp_server.py
if pgrep -f "python.*dns_mcp_server.py" > /dev/null; then
    echo "Found DNS Resolving MCP Server processes, stopping them..."
    pkill -f "python.*dns_mcp_server.py"
    echo "Waiting for processes to stop..."
    sleep 3
    
    # Check if any processes are still running
    if pgrep -f "python.*dns_mcp_server.py" > /dev/null; then
        echo "Some processes still running, force killing..."
        pkill -9 -f "python.*dns_mcp_server.py"
        sleep 2
    fi
    echo "DNS Resolving MCP Server stopped."
else
    echo "No DNS Resolving MCP Server processes found."
fi

# Also kill any processes that might be started via the shell script
if pgrep -f "start_dns_server.sh" > /dev/null; then
    echo "Found start_dns_server.sh processes, stopping them..."
    pkill -f "start_dns_server.sh"
    sleep 1
fi

echo "Done."