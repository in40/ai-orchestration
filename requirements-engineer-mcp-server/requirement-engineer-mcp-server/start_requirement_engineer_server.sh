#!/bin/bash

# Script to start the Requirement Engineer MCP server with various options
# Usage: ./start_requirement_engineer_server.sh [options]

echo "Starting Requirement Engineer MCP Server..."

# Default values
TRANSPORT="streamable-http"
HOST="127.0.0.1"
PORT=3062  # Changed to 3062 as required
ENABLE_REGISTRY=false  # As per requirement: should not become a new registry
REGISTER_WITH_REGISTRY=true  # As per requirement: should connect to existing registry
REGISTRY_HOST="127.0.0.1"
REGISTRY_PORT=3031  # As per requirement: connect to existing registry on port 3031
USE_POSTGRES=false  # Use SQLite for task storage (matching Registry Server)
POSTGRES_HOST="127.0.0.1"  # PostgreSQL host
POSTGRES_DB="mcp_registry"  # Database name
MAX_CONCURRENT_REQUESTS=10

# Parse command line options
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
    --postgres-db)
      POSTGRES_DB="$2"
      shift 2
      ;;
    --max-concurrent-requests)
      MAX_CONCURRENT_REQUESTS="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --transport TYPE          Transport type (stdio, http, streamable-http) [default: streamable-http]"
      echo "  --host HOST               Host for HTTP transport [default: 127.0.0.1]"
      echo "  --port PORT               Port for HTTP transport [default: 3062]"
      echo "  --enable-registry         Enable registry functionality (should be false for requirement engineer server)"
      echo "  --register-with-registry  Register this server with a registry server [default: true]"
      echo "  --registry-host HOST      Registry server host [default: 127.0.0.1]"
      echo "  --registry-port PORT      Registry server port [default: 3031]"
      echo "  --use-postgres            Use PostgreSQL for registry storage instead of SQLite [default: true]"
      echo "  --max-concurrent-requests NUM  Maximum number of concurrent requests [default: 10]"
      echo "  -h, --help               Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Build the command to run our custom server
CMD="python requirement_engineer_server.py"

if [ "$TRANSPORT" != "stdio" ]; then
  CMD="$CMD --transport $TRANSPORT"
fi

if [ "$HOST" != "127.0.0.1" ]; then
  CMD="$CMD --host $HOST"
fi

if [ "$PORT" != "3062" ]; then
  CMD="$CMD --port $PORT"
else
  # Always specify the port since it's different from default
  CMD="$CMD --port $PORT"
fi

if [ "$ENABLE_REGISTRY" = true ]; then
  CMD="$CMD --enable-registry"
fi

if [ "$REGISTER_WITH_REGISTRY" = true ]; then
  CMD="$CMD --register-with-registry"
fi

if [ "$REGISTRY_HOST" != "127.0.0.1" ]; then
  CMD="$CMD --registry-host $REGISTRY_HOST"
fi

if [ "$REGISTRY_PORT" != "3031" ]; then
  CMD="$CMD --registry-port $REGISTRY_PORT"
else
  # Always specify the registry port since it's different from default
  CMD="$CMD --registry-port $REGISTRY_PORT"
fi

if [ "$USE_POSTGRES" = true ]; then
  CMD="$CMD --use-postgres --postgres-host $POSTGRES_HOST --postgres-db $POSTGRES_DB --postgres-user postgres --postgres-password postgres"
fi

if [ "$MAX_CONCURRENT_REQUESTS" != "10" ]; then
  CMD="$CMD --max-concurrent-requests $MAX_CONCURRENT_REQUESTS"
fi

echo "Executing: $CMD"
exec $CMD
