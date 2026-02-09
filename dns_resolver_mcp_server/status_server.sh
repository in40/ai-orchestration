#!/bin/bash

# DNS Resolver MCP Server Status Script
# Checks if the DNS resolver server is currently running

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Checking DNS resolver server status..."

# Find processes running the DNS resolver server
SERVER_PIDS=$(pgrep -f "python.*dns_resolver_server\.src\.main" 2>/dev/null || pgrep -f "python.*src\.main" 2>/dev/null || true)

if [ -z "$SERVER_PIDS" ]; then
    echo "DNS resolver server is not running."
    exit 1
else
    echo "DNS resolver server is running with PID(s): $SERVER_PIDS"

    # Show additional info about the process
    for pid in $SERVER_PIDS; do
        echo "  PID $pid: $(ps -p $pid -o args= 2>/dev/null)"
    done

    exit 0
fi