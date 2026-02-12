#!/bin/bash
# Stop AI Coding Agent MCP Server
# This script stops the AI Coding Agent server instances

set -e  # Exit on any error

echo "Stopping AI Coding Agent MCP Server..."

# Kill processes running the AI Coding Agent server
pids=$(ps aux | grep "ai_coding_agent_server.py" | grep -v grep | awk '{print $2}')

if [ -z "$pids" ]; then
    # Alternative: look for processes that include our specific server characteristics
    pids=$(ps aux | grep "python" | grep "ai_coding_agent" | grep -v grep | awk '{print $2}')

    if [ -z "$pids" ]; then
        # Try to find any Python process running on port 3050 that could be our server
        pids=$(lsof -i :3050 -t 2>/dev/null || true)
        
        if [ -z "$pids" ]; then
            echo "No AI Coding Agent MCP Server processes found"
            exit 0
        fi
    fi
fi

echo "Found processes to stop: $pids"
kill $pids
echo "Sent SIGTERM to AI Coding Agent MCP Server processes"

# Wait a moment for graceful shutdown
sleep 2

# Check if any processes are still running and force kill if necessary
remaining_pids=$(ps aux | grep "ai_coding_agent_server.py" | grep -v grep | awk '{print $2}')
if [ -z "$remaining_pids" ]; then
    # If not found by name, check port again
    remaining_pids=$(lsof -i :3050 -t 2>/dev/null || true)
fi

if [ -n "$remaining_pids" ]; then
    echo "Some processes still running, sending SIGKILL: $remaining_pids"
    kill -9 $remaining_pids
fi

echo "AI Coding Agent MCP Server stopped"