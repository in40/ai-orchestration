#!/bin/bash

# MCP Server Startup Script
# This script starts the Model Context Protocol (MCP) server with configurable options

set -e  # Exit on any error

# Default configuration
TRANSPORT="http"
HOST="127.0.0.1"
PORT="3030"
MAX_CONCURRENT_REQUESTS="10"
ENABLE_REGISTRY=false
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

# Function to display usage
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  -t, --transport TYPE    Transport type: 'stdio' or 'http' (default: http)"
    echo "  -h, --host HOST         Host to bind to (default: 127.0.0.1)"
    echo "  -p, --port PORT         Port to listen on (default: 3030)"
    echo "  -c, --concurrent-reqs N Maximum number of concurrent requests (default: 10)"
    echo "  -r, --enable-registry   Enable registry functionality"
    echo "  -R, --register-with-reg Register with a registry server"
    echo "  --registry-host HOST    Registry host to register with (default: 127.0.0.1)"
    echo "  --registry-port PORT    Registry port to register with (default: 3031)"
    echo "  --use-postgres          Use PostgreSQL for registry storage instead of SQLite"
    echo "  --postgres-host HOST    PostgreSQL host (default: 127.0.0.1)"
    echo "  --postgres-port PORT    PostgreSQL port (default: 5432)"
    echo "  --postgres-db DB        PostgreSQL database name (default: mcp_registry)"
    echo "  --postgres-user USER    PostgreSQL username (default: postgres)"
    echo "  --postgres-password PW  PostgreSQL password (default: empty)"
    echo "  --python CMD            Python command to use (default: python)"
    echo "  --log-to-file           Redirect all output to log file instead of console"
    echo "  --log-file FILE         Specify log file name (default: mcp_server_YYYYMMDD_HHMMSS.log)"
    echo "  --background            Run server in background (implies --log-to-file)"
    echo "  -H, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Start with defaults (HTTP on port 3030)"
    echo "  $0 -p 9000                           # Start on port 9000"
    echo "  $0 -c 20                             # Start with max 20 concurrent requests"
    echo "  $0 -r -p 5000                        # Start registry server on port 5000"
    echo "  $0 -t stdio                          # Start with stdio transport"
    echo "  $0 --python python3.11 -p 8080       # Use specific Python version"
    echo "  $0 -R                                  # Start and register with registry"
    echo "  $0 -R --registry-port 4000           # Start and register with registry on port 4000"
    echo "  $0 -r --use-postgres                 # Start registry with PostgreSQL backend"
    echo "  $0 --log-to-file                       # Start with logging to file"
    echo "  $0 --background --log-file myserver.log  # Start in background with custom log file"
    exit 1
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -t|--transport)
            TRANSPORT="$2"
            shift 2
            ;;
        -h|--host)
            HOST="$2"
            shift 2
            ;;
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -c|--concurrent-reqs)
            MAX_CONCURRENT_REQUESTS="$2"
            shift 2
            ;;
        -r|--enable-registry)
            ENABLE_REGISTRY=true
            shift
            ;;
        -R|--register-with-reg)
            REGISTER_WITH_REGISTRY=true
            shift
            ;;
        --registry-host)
            REGISTRY_HOST="$2"
            shift 2
            ;;
        --registry-port)
            REGISTRY_PORT="$2"
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
        --background)
            BACKGROUND=true
            LOG_TO_FILE=true
            shift
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

# Validate transport type
if [[ "$TRANSPORT" != "stdio" && "$TRANSPORT" != "http" ]]; then
    echo "Error: Transport must be 'stdio' or 'http'"
    usage
fi

# Validate port number
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "Error: Port must be a number between 1 and 65535"
    usage
fi

# Validate max concurrent requests
if ! [[ "$MAX_CONCURRENT_REQUESTS" =~ ^[0-9]+$ ]] || [ "$MAX_CONCURRENT_REQUESTS" -lt 1 ]; then
    echo "Error: Max concurrent requests must be a positive number"
    usage
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
CMD="$PYTHON_CMD -m mcp_server.server --transport $TRANSPORT --host $HOST --port $PORT --max-concurrent-requests $MAX_CONCURRENT_REQUESTS"

if [[ "$ENABLE_REGISTRY" == true ]]; then
    CMD="$CMD --enable-registry"
fi

if [[ "$REGISTER_WITH_REGISTRY" == true ]]; then
    CMD="$CMD --register-with-registry --registry-host $REGISTRY_HOST --registry-port $REGISTRY_PORT"
fi

if [[ "$USE_POSTGRES" == true ]]; then
    CMD="$CMD --use-postgres --postgres-host $POSTGRES_HOST --postgres-port $POSTGRES_PORT --postgres-db $POSTGRES_DB --postgres-user $POSTGRES_USER --postgres-password $POSTGRES_PASSWORD"
fi

# Display startup information
echo "Starting MCP Server..."
echo "Configuration:"
echo "  Transport: $TRANSPORT"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Max Concurrent Requests: $MAX_CONCURRENT_REQUESTS"
echo "  Registry (local): $(if [[ $ENABLE_REGISTRY == true ]]; then echo "enabled"; else echo "disabled"; fi)"
echo "  Register with registry: $(if [[ $REGISTER_WITH_REGISTRY == true ]]; then echo "yes ($REGISTRY_HOST:$REGISTRY_PORT)"; else echo "no"; fi)"
echo "  Use PostgreSQL: $(if [[ $USE_POSTGRES == true ]]; then echo "yes ($POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB)"; else echo "no (using SQLite)"; fi)"
echo ""

echo "Running command: $CMD"
echo ""

# Start the server
if [[ "$LOG_TO_FILE" == true ]]; then
    if [[ -z "$LOG_FILE" ]]; then
        LOG_FILE="mcp_server_$(date +%Y%m%d_%H%M%S).log"
    fi
    
    if [[ "$BACKGROUND" == true ]]; then
        echo "Starting MCP Server in background with logging to $LOG_FILE..."
        $CMD > "$LOG_FILE" 2>&1 &
        echo "MCP Server started in background with PID $!"
    else
        echo "Starting MCP Server with logging to $LOG_FILE..."
        $CMD > "$LOG_FILE" 2>&1
    fi
else
    # Display startup information
    echo "Starting MCP Server..."
    echo "Configuration:"
    echo "  Transport: $TRANSPORT"
    echo "  Host: $HOST"
    echo "  Port: $PORT"
    echo "  Max Concurrent Requests: $MAX_CONCURRENT_REQUESTS"
    echo "  Registry (local): $(if [[ $ENABLE_REGISTRY == true ]]; then echo "enabled"; else echo "disabled"; fi)"
    echo "  Register with registry: $(if [[ $REGISTER_WITH_REGISTRY == true ]]; then echo "yes ($REGISTRY_HOST:$REGISTRY_PORT)"; else echo "no"; fi)"
    echo "  Use PostgreSQL: $(if [[ $USE_POSTGRES == true ]]; then echo "yes ($POSTGRES_HOST:$POSTGRES_PORT/$POSTGRES_DB)"; else echo "no (using SQLite)"; fi)"
    echo ""
    echo "Running command: $CMD"
    echo ""
    
    exec $CMD
fi