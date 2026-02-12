#!/bin/bash

# DNS Resolving MCP Server startup script
# Starts the DNS Resolving MCP Server with configurable options

set -e  # Exit on any error

# Default values
TRANSPORT="http"
HOST="127.0.0.1"
PORT="3040"  # Changed from default 3030 to 3040
ENABLE_REGISTRY=false
REGISTER_WITH_REGISTRY=true
REGISTRY_HOST="127.0.0.1"
REGISTRY_PORT="3031"
USE_POSTGRES=false
POSTGRES_HOST="127.0.0.1"
POSTGRES_PORT="5432"
POSTGRES_DB="mcp_registry"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD=""
PYTHON_CMD="python3"
LOG_TO_FILE=false
LOG_FILE=""
BACKGROUND=false

# Print usage information
usage() {
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --transport TYPE        Transport type: stdio or http (default: http)"
    echo "  --host HOST             Host for HTTP transport (default: 127.0.0.1)"
    echo "  --port PORT             Port for HTTP transport (default: 3040)"
    echo "  --enable-registry       Enable registry functionality"
    echo "  --register-with-registry Register this server with a registry server"
    echo "  --registry-host HOST    Registry server host (default: 127.0.0.1)"
    echo "  --registry-port PORT    Registry server port (default: 3031)"
    echo "  --use-postgres          Use PostgreSQL for registry storage instead of SQLite"
    echo "  --postgres-host HOST    PostgreSQL host (default: 127.0.0.1)"
    echo "  --postgres-port PORT    PostgreSQL port (default: 5432)"
    echo "  --postgres-db DB        PostgreSQL database name (default: mcp_registry)"
    echo "  --postgres-user USER    PostgreSQL username (default: postgres)"
    echo "  --postgres-password PASS PostgreSQL password (default: empty)"
    echo "  --python CMD            Python command to use (default: python3)"
    echo "  --log-to-file           Redirect all output to log file instead of console"
    echo "  --log-file FILE         Specify log file name (default: dns_server_YYYYMMDD_HHMMSS.log)"
    echo "  --background            Run server in background (implies --log-to-file)"
    echo "  -h, --help              Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0                                    # Start DNS server on port 3040"
    echo "  $0 --port 8080                       # Start on custom port"
    echo "  $0 --enable-registry --port 3041     # Start as registry server"
    echo "  $0 --register-with-registry          # Start and register with registry"
    echo "  $0 --background                      # Start in background"
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --transport)
            TRANSPORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --port)
            PORT="$2"
            shift 2
            ;;
        --enable-registry)
            ENABLE_REGISTRY=true
            shift
            ;;
        --register-with-registry)
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
            shift 2
            ;;
        --background)
            BACKGROUND=true
            LOG_TO_FILE=true
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
    esac
done

# Validate transport type
if [[ "$TRANSPORT" != "stdio" && "$TRANSPORT" != "http" ]]; then
    echo "Error: Invalid transport type '$TRANSPORT'. Must be 'stdio' or 'http'."
    exit 1
fi

# Validate port number
if ! [[ "$PORT" =~ ^[0-9]+$ ]] || [ "$PORT" -lt 1 ] || [ "$PORT" -gt 65535 ]; then
    echo "Error: Invalid port number '$PORT'. Must be between 1 and 65535."
    exit 1
fi

# Validate registry port number
if ! [[ "$REGISTRY_PORT" =~ ^[0-9]+$ ]] || [ "$REGISTRY_PORT" -lt 1 ] || [ "$REGISTRY_PORT" -gt 65535 ]; then
    echo "Error: Invalid registry port number '$REGISTRY_PORT'. Must be between 1 and 65535."
    exit 1
fi

# Generate log file name if not specified and logging to file
if [ "$LOG_TO_FILE" = true ] && [ -z "$LOG_FILE" ]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    LOG_FILE="dns_server_$TIMESTAMP.log"
fi

# Display configuration
echo "DNS Resolving MCP Server Configuration:"
echo "  Transport: $TRANSPORT"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Enable Registry: $ENABLE_REGISTRY"
if [ "$REGISTER_WITH_REGISTRY" = true ]; then
    echo "  Register with Registry: Yes"
    echo "  Registry Host: $REGISTRY_HOST"
    echo "  Registry Port: $REGISTRY_PORT"
fi
if [ "$USE_POSTGRES" = true ]; then
    echo "  Use PostgreSQL: Yes"
    echo "  PostgreSQL Host: $POSTGRES_HOST"
    echo "  PostgreSQL Port: $POSTGRES_PORT"
    echo "  PostgreSQL DB: $POSTGRES_DB"
    echo "  PostgreSQL User: $POSTGRES_USER"
fi
echo ""

# Prepare command line arguments
ARGS="--transport $TRANSPORT --host $HOST --port $PORT"
if [ "$ENABLE_REGISTRY" = true ]; then
    ARGS="$ARGS --enable-registry"
fi
if [ "$REGISTER_WITH_REGISTRY" = true ]; then
    ARGS="$ARGS --register-with-registry --registry-host $REGISTRY_HOST --registry-port $REGISTRY_PORT"
fi
if [ "$USE_POSTGRES" = true ]; then
    ARGS="$ARGS --use-postgres --postgres-host $POSTGRES_HOST --postgres-port $POSTGRES_PORT --postgres-db $POSTGRES_DB --postgres-user $POSTGRES_USER"
    if [ -n "$POSTGRES_PASSWORD" ]; then
        ARGS="$ARGS --postgres-password '$POSTGRES_PASSWORD'"
    fi
fi

# Execute the server
if [ "$BACKGROUND" = true ]; then
    echo "Starting DNS Resolving MCP Server in background..."
    if [ -n "$LOG_FILE" ]; then
        echo "Logging to: $LOG_FILE"
        nohup bash -c "source mcp_dns_env/bin/activate && $PYTHON_CMD dns_mcp_server.py $ARGS" > "$LOG_FILE" 2>&1 &
    else
        nohup bash -c "source mcp_dns_env/bin/activate && $PYTHON_CMD dns_mcp_server.py $ARGS" > /dev/null 2>&1 &
    fi
    echo "DNS Resolving MCP Server started in background with PID $!"
elif [ "$LOG_TO_FILE" = true ]; then
    echo "Starting DNS Resolving MCP Server..."
    echo "Logging to: $LOG_FILE"
    bash -c "source mcp_dns_env/bin/activate && $PYTHON_CMD dns_mcp_server.py $ARGS" 2>&1 | tee "$LOG_FILE"
else
    echo "Starting DNS Resolving MCP Server..."
    exec bash -c "source mcp_dns_env/bin/activate && $PYTHON_CMD dns_mcp_server.py $ARGS"
fi