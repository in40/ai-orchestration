#!/bin/bash

# Comprehensive Stop Script for MCP and Registry Servers
# This script stops all Model Context Protocol (MCP) server and registry instances

set -e  # Exit on any error

echo "Stopping all MCP and Registry server instances..."

# First, try to stop registry servers specifically
echo "Looking for registry server processes..."
REGISTRY_PIDS=$(pgrep -f "python.*mcp_server.server.*--enable-registry\|--port.*3031\|--port.*3032" 2>/dev/null) || true

if [ -n "$REGISTRY_PIDS" ]; then
    echo "Found registry server processes with PIDs: $REGISTRY_PIDS"
    echo "Terminating registry server processes..."
    kill $REGISTRY_PIDS 2>/dev/null || true
    
    # Wait a moment for graceful shutdown
    sleep 2
    
    # Check if registry processes are still running and force kill if necessary
    STILL_RUNNING=$(pgrep -f "python.*mcp_server.server.*--enable-registry\|--port.*3031\|--port.*3032" 2>/dev/null) || true
    if [ -n "$STILL_RUNNING" ]; then
        echo "Some registry processes still running, forcing termination..."
        kill -9 $STILL_RUNNING 2>/dev/null || true
    fi
    echo "Registry server processes stopped."
else
    echo "No registry server processes found running."
fi

# Then, stop any remaining MCP server processes
echo "Looking for remaining MCP server processes..."
MCP_SERVER_PIDS=$(pgrep -f "python.*mcp_server.server" 2>/dev/null) || true

if [ -n "$MCP_SERVER_PIDS" ]; then
    # Filter out any registry processes that might be included
    MCP_ONLY_PIDS=""
    for pid in $MCP_SERVER_PIDS; do
        if ! ps -p $pid -o args= 2>/dev/null | grep -q "\--enable-registry\|3031\|3032"; then
            MCP_ONLY_PIDS="$MCP_ONLY_PIDS $pid"
        fi
    done
    
    if [ -n "$MCP_ONLY_PIDS" ]; then
        echo "Found MCP server processes with PIDs: $MCP_ONLY_PIDS"
        echo "Terminating MCP server processes..."
        kill $MCP_ONLY_PIDS 2>/dev/null || true
        
        # Wait a moment for graceful shutdown
        sleep 2
        
        # Check if MCP processes are still running and force kill if necessary
        # Exclude registry processes from this check
        MCP_STILL_RUNNING=$(pgrep -f "python.*mcp_server.server" 2>/dev/null) || true
        if [ -n "$MCP_STILL_RUNNING" ]; then
            # Filter out registry processes again
            MCP_TO_KILL=""
            for pid in $MCP_STILL_RUNNING; do
                if ! ps -p $pid -o args= 2>/dev/null | grep -q "\--enable-registry\|3031\|3032"; then
                    MCP_TO_KILL="$MCP_TO_KILL $pid"
                fi
            done
            
            if [ -n "$MCP_TO_KILL" ]; then
                echo "Some MCP server processes still running, forcing termination..."
                kill -9 $MCP_TO_KILL 2>/dev/null || true
            fi
        fi
        echo "MCP server processes stopped."
    fi
else
    echo "No additional MCP server processes found running."
fi

# Final check to ensure no processes remain
ALL_MCP_PROCESSES=$(pgrep -f "python.*mcp_server.server" 2>/dev/null) || true
if [ -n "$ALL_MCP_PROCESSES" ]; then
    echo "Warning: Some MCP processes may still be running with PIDs: $ALL_MCP_PROCESSES"
    echo "Force killing remaining processes..."
    kill -9 $ALL_MCP_PROCESSES 2>/dev/null || true
    sleep 1
fi

# Clean up any leftover PID files
for pidfile in *.pid mcp_*.pid registry_*.pid; do
    if [ -f "$pidfile" ]; then
        echo "Removing PID file: $pidfile"
        rm -f "$pidfile"
    fi
done

echo "All MCP and Registry server instances have been stopped."