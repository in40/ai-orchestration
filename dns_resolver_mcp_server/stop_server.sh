#!/bin/bash

# DNS Resolver MCP Server Stop Script
# Stops the running DNS resolver server

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Stopping DNS resolver server..."

# Find and kill processes running the DNS resolver server
# This looks for Python processes running dns_resolver_server.src.main or src.main
SERVER_PIDS=$(pgrep -f "python.*dns_resolver_server\.src\.main" 2>/dev/null || pgrep -f "python.*src\.main" 2>/dev/null || true)

if [ -z "$SERVER_PIDS" ]; then
    echo "No running DNS resolver server found."
    exit 0
else
    echo "Found running server processes: $SERVER_PIDS"
    kill $SERVER_PIDS 2>/dev/null || true
    
    # Wait a moment for graceful shutdown
    sleep 2
    
    # Check if processes are still running
    REMAINING_PIDS=$(pgrep -f "python.*dns_resolver_server\.src\.main" 2>/dev/null || pgrep -f "python.*src\.main" 2>/dev/null || true)
    if [ -n "$REMAINING_PIDS" ]; then
        echo "Some processes still running, force killing: $REMAINING_PIDS"
        kill -9 $REMAINING_PIDS 2>/dev/null || true
    fi
    
    echo "Server stopped."
fi