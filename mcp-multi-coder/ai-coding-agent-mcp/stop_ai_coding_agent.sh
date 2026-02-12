#!/bin/bash

# AI Coding Agent MCP Server stop script
# Kills the Python process running on port 3050

echo "Stopping AI Coding Agent MCP Server..."

# Find and kill the Python process running on port 3050
pids=$(lsof -ti:3060 -c python)

if [ -z "$pids" ]; then
    echo "No Python process found running on port 3050"
else
    echo "Killing processes: $pids"
    kill -9 $pids
    echo "AI Coding Agent MCP Server stopped."
fi