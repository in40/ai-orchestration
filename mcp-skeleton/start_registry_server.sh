#!/bin/bash

# Default Registry Server Startup Script
# This script starts the Model Context Protocol (MCP) registry server with default settings
# Designed for quick startup of a registry server with common configuration

set -e  # Exit on any error

# Default configuration for registry server
TRANSPORT="http"
HOST="127.0.0.1"
PORT="3031"  # Default registry port
ENABLE_REGISTRY=true
REGISTER_WITH_REGISTRY=false
REGISTRY_HOST="127.0.0.1"
REGISTRY_PORT="3031"
USE_POSTGRES=false
POSTGRES_HOST="127.0.0.1"
POSTGRES_PORT="5432"
POSTGRES_DB="mcp_registry"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD=""
PYTHON_CMD="python"
LOG_TO_FILE=false
LOG_FILE=""
BACKGROUND=false
PID_FILE=""

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Quick-start script for MCP registry server with default settings."
    echo ""
    echo "Options:"
    echo "  -p, --port PORT         Port to listen on (default: 3031)"
    echo "  --use-postgres          Use PostgreSQL for registry storage instead of SQLite"
    echo "  --postgres-host HOST    PostgreSQL host (default: 127.0.0.1)"
    echo "  --postgres-port PORT    PostgreSQL port (default: 5432)"
    echo "  --postgres-db DB        PostgreSQL database name (default: mcp_registry)"
    echo "  --postgres-user USER    PostgreSQL username (default: postgres)"
    echo "  --postgres-password PW  PostgreSQL password (default: empty)"
    echo "  --python CMD            Python command to use (default: python)"
    echo "  --log-to-file           Redirect all output to log file instead of console"
    echo "  --log-file FILE         Specify log file name (default: registry_server_YYYYMMDD_HHMMSS.log)"
    echo "  -b, --background        Run server in background"
    echo "  --pid-file FILE         Write PID to specified file (implies background)"
    echo "  -H, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Start registry on default port 3031"
    echo "  $0 -p 4000                           # Start registry on port 4000"
    echo "  $0 --use-postgres                    # Start registry with PostgreSQL backend"
    echo "  $0 --background                      # Start registry in background"
    echo "  $0 --background --log-file reg.log   # Start registry in background with logging"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        --use-postgres)
            USE_POSTGRES=true
            shift
            ;;
        --postgres-host)
            POSTGRES_HOST="$2"
            shift 2
            ;;
        --postgres-port)
            POSTGRES_PORT="$2"
            shift 2
            ;;
        --postgres-db)
            POSTGRES_DB="$2"
            shift 2
            ;;
        --postgres-user)
            POSTGRES_USER="$2"
            shift 2
            ;;
        --postgres-password)
            POSTGRES_PASSWORD="$2"
            shift 2
            ;;
        --python)
            PYTHON_CMD="$2"
            shift 2
            ;;
        --log-to-file)
            LOG_TO_FILE=true
            shift
            ;;
        --log-file)
            LOG_FILE="$2"
            LOG_TO_FILE=true
            shift 2
            ;;
        -b|--background)
            BACKGROUND=true
            LOG_TO_FILE=true
            shift
            ;;
        --pid-file)
            PID_FILE="$2"
            BACKGROUND=true  # PID file implies background
            shift 2
            ;;
        -H|--help)
            usage
            ;;
        *)
            echo "Unknown option: $1"
            usage
            ;;
    esac
done

# Validate port number
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "Error: Port must be a number between 1 and 65535"
    exit 1
fi

# Check if Python command exists
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "Error: Python command '$PYTHON_CMD' not found"
    exit 1
fi

# Check if we're in the correct directory
if [[ ! -f "mcp_server/server.py" ]]; then
    echo "Error: Cannot find mcp_server/server.py"
    echo "Make sure you're running this script from the MCP server root directory"
    exit 1
fi

# Build the command
CMD="$PYTHON_CMD -m mcp_server.server --transport $TRANSPORT --host $HOST --port $PORT --enable-registry"

if [[ "$USE_POSTGRES" == true ]]; then
    CMD="$CMD --use-postgres --postgres-host $POSTGRES_HOST --postgres-port $POSTGRES_PORT --postgres-db $POSTGRES_DB --postgres-user $POSTGRES_USER --postgres-password $POSTGRES_PASSWORD"
fi

# Display startup information
echo "Starting MCP Registry Server..."
echo "Configuration:"
echo "  Transport: $TRANSPORT"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Registry: enabled"
echo "  Register with registry: no"
echo "  Use PostgreSQL: $(if [[ $USE_POSTGRES == true ]]; then echo "yes ($POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB)"; else echo "no (using SQLite)"; fi)"
echo "  Background: $BACKGROUND"
if [[ -n "$LOG_FILE" ]]; then
    echo "  Log file: $LOG_FILE"
fi
if [[ -n "$PID_FILE" ]]; then
    echo "  PID file: $PID_FILE"
fi
echo ""

echo "Running command: $CMD"
echo ""

# Start the server
if [[ "$BACKGROUND" == true ]]; then
    if [[ -n "$LOG_FILE" ]]; then
        echo "Starting MCP Registry Server in background with logging to $LOG_FILE..."
        if [[ -n "$PID_FILE" ]]; then
            $CMD --pid-file "$PID_FILE" > "$LOG_FILE" 2>&1 &
        else
            $CMD > "$LOG_FILE" 2>&1 &
        fi
        SERVER_PID=$!
        echo "MCP Registry Server started in background with PID: $SERVER_PID"
    else
        echo "Starting MCP Registry Server in background (output redirected to /dev/null)..."
        if [[ -n "$PID_FILE" ]]; then
            $CMD --pid-file "$PID_FILE" > /dev/null 2>&1 &
        else
            $CMD > /dev/null 2>&1 &
        fi
        SERVER_PID=$!
        echo "MCP Registry Server started in background with PID: $SERVER_PID"
    fi
else
    if [[ "$LOG_TO_FILE" == true ]]; then
        if [[ -z "$LOG_FILE" ]]; then
            LOG_FILE="registry_server_$(date +%Y%m%d_%H%M%S).log"
        fi
        echo "Starting MCP Registry Server with logging to $LOG_FILE..."
        $CMD > "$LOG_FILE" 2>&1
    else
        exec $CMD
    fi
fi