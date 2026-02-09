#!/bin/bash

# DNS Resolver MCP Server Startup Script
# Loads configuration from .env, stops any running server, and starts a new instance in the background

set -e  # Exit immediately if a command exits with a non-zero status

# Default values
TAIL_LOGS=false

# Parse command-line options
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--tail-logs)
            TAIL_LOGS=true
            shift
            ;;
        *)
            echo "Unknown option: $1"
            echo "Usage: $0 [-t|--tail-logs]"
            exit 1
            ;;
    esac
done

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "Loading configuration from .env file..."

# Source environment variables from .env file
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
else
    echo "Error: .env file not found!"
    exit 1
fi

# Determine the transport type and port from environment variables
TRANSPORT="${MCP_TRANSPORT:-stdio}"
PORT="${MCP_PORT:-8080}"
HOST="${MCP_HOST:-0.0.0.0}"

echo "Configuration loaded:"
echo "  Transport: $TRANSPORT"
echo "  Host: $HOST"
echo "  Port: $PORT"

# Function to stop the server if it's running
stop_server() {
    echo "Stopping any running DNS resolver server..."

    # Find and kill processes running the DNS resolver server
    # This looks for Python processes running dns_resolver_server.src.main or src.main
    SERVER_PIDS=$(pgrep -f "python.*dns_resolver_server\.src\.main" 2>/dev/null || pgrep -f "python.*src\.main" 2>/dev/null || true)

    if [ -z "$SERVER_PIDS" ]; then
        echo "No running DNS resolver server found."
    else
        echo "Found running server processes: $SERVER_PIDS"
        kill $SERVER_PIDS 2>/dev/null || true

        # Wait a moment for graceful shutdown
        sleep 2

        # Force kill if still running
        SERVER_PIDS=$(pgrep -f "python.*dns_resolver_server\.src\.main" 2>/dev/null || pgrep -f "python.*src\.main" 2>/dev/null || true)
        if [ -n "$SERVER_PIDS" ]; then
            echo "Force killing remaining processes: $SERVER_PIDS"
            kill -9 $SERVER_PIDS 2>/dev/null || true
        fi

        echo "Server stopped."
    fi
}

# Stop any existing server
stop_server

# Wait a moment to ensure the port is free
sleep 2

echo "Starting DNS resolver server..."

# Activate virtual environment if it exists
if [ -d "venv" ] && [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
    echo "Virtual environment activated."
fi

# Prepare the command based on transport type
if [ "$TRANSPORT" = "http" ]; then
    STARTUP_CMD="python -m dns_resolver_server.src.main --transport http --host $HOST --port $PORT"
    # Start the HTTP server in the background
    eval "$STARTUP_CMD" >dns_resolver_server_http.log 2>&1 &
    SERVER_PID=$!
    LOG_FILE="dns_resolver_server_http.log"
else
    # For stdio transport, we'll run it with nohup to ensure it continues running after script exits
    # Stdio transport is typically used for MCP communication through stdin/stdout
    # If registry endpoint is stdio://, we don't need to register with external registry
    if [ "$MCP_REGISTRY_ENDPOINT" = "stdio://" ]; then
        STARTUP_CMD="python -m dns_resolver_server.src.main --transport stdio"
    else
        # If registry endpoint is not stdio, we may want to disable health monitoring for stdio transport
        STARTUP_CMD="python -m dns_resolver_server.src.main --transport stdio --disable-health-monitoring"
    fi
    nohup $STARTUP_CMD >dns_resolver_server_stdio.log 2>&1 &
    SERVER_PID=$!
    LOG_FILE="dns_resolver_server_stdio.log"
fi

# Wait a moment for the server to start
sleep 3

# Check if the server started successfully
if kill -0 $SERVER_PID 2>/dev/null; then
    echo "DNS resolver server started successfully with PID: $SERVER_PID"

    if [ "$TRANSPORT" = "http" ]; then
        echo "Server is listening on $HOST:$PORT"
        echo "Health check: curl http://$HOST:$PORT/health"
    else
        echo "Server is running with stdio transport (PID: $SERVER_PID)"
    fi
    
    echo "Recent server logs:"
    echo "-------------------"
    tail -n 10 "$LOG_FILE" 2>/dev/null || echo "Could not read log file: $LOG_FILE"
    echo "-------------------"
    echo "Check full logs at $LOG_FILE"
else
    echo "Failed to start the server. Check logs for details."
    echo "Log file: $LOG_FILE"
    if [ -f "$LOG_FILE" ]; then
        echo "Last 20 lines of log:"
        echo "-------------------"
        tail -n 20 "$LOG_FILE"
        echo "-------------------"
    fi
    exit 1
fi

if [ "$TAIL_LOGS" = true ]; then
    echo "Tailing server logs (press Ctrl+C to stop):"
    tail -f "$LOG_FILE" &
    TAIL_PID=$!
    
    # Wait for the tail process to finish (when interrupted)
    wait $TAIL_PID
else
    echo "Server startup script completed. Server is running in the background."
fi