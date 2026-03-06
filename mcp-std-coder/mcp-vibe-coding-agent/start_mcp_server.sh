#!/bin/bash

# Script to start the MCP server with various options
# Usage: ./start_mcp_server.sh [options]

echo "Starting Vibe Coding MCP Server..."

# Load configuration from .env file if it exists
if [ -f "/root/qwen/base/.env" ]; then
    source /root/qwen/base/.env
    echo "✅ Loaded configuration from /root/qwen/base/.env"
fi

# Set PostgreSQL password from environment or default
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
export PGPASSWORD="${POSTGRES_PASSWORD}"

# Default values from .env or fallback
TRANSPORT="streamable-http"
HOST="${WEB_UI_HOST:-0.0.0.0}"
PORT="${IMPLEMENTATION_PORT:-3060}"
ENABLE_REGISTRY=false
REGISTER_WITH_REGISTRY=true
REGISTRY_HOST="${REGISTRY_HOST:-127.0.0.1}"
REGISTRY_PORT="${REGISTRY_PORT:-3031}"
USE_POSTGRES="${USE_POSTGRES:-true}"
MAX_CONCURRENT_REQUESTS="${MAX_CONCURRENT_REQUESTS:-10}"
LLM_PROVIDER_URL="${LLM_PROVIDER_URL:-http://192.168.51.237:1234/v1/chat/completions}"
LLM_MODEL="${LLM_MODEL:-qwen3-coder-next@q5_k_xl}"

# Export LLM configuration for Python process
export LLM_PROVIDER_URL
export LLM_MODEL

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
      echo "  --port PORT               Port for HTTP transport [default: 3060 for vibe coding server]"
      echo "  --enable-registry         Enable registry functionality"
      echo "  --register-with-registry  Register this server with a registry server"
      echo "  --registry-host HOST      Registry server host [default: 127.0.0.1]"
      echo "  --registry-port PORT      Registry server port [default: 3031]"
      echo "  --use-postgres            Use PostgreSQL for registry storage instead of SQLite"
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


# If you want to use an environment variable instead, set it before running this script:
if [ -z "$POSTGRES_PASSWORD" ]; then
  echo "POSTGRES_PASSWORD environment variable not set. Using empty password."
  echo "To set it, uncomment and update the export line in this script, or run:"
  echo "  export POSTGRES_PASSWORD='your_actual_password_here'"
else
  echo "Using PostgreSQL password from environment variable."
fi

# Enable PostgreSQL by default for persistent task storage
USE_POSTGRES=true

# Build the command
CMD="python -m mcp_std_server.server"

if [ "$TRANSPORT" != "stdio" ]; then
  CMD="$CMD --transport $TRANSPORT"
fi

if [ "$HOST" != "127.0.0.1" ]; then
  CMD="$CMD --host $HOST"
fi

CMD="$CMD --port $PORT"

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
fi

# Always enable PostgreSQL for persistent task storage
if [ "$USE_POSTGRES" = true ]; then
  if [ -n "$POSTGRES_PASSWORD" ]; then
    CMD="$CMD --use-postgres --postgres-password $POSTGRES_PASSWORD"
  else
    CMD="$CMD --use-postgres"
  fi
fi

if [ "$MAX_CONCURRENT_REQUESTS" != "10" ]; then
  CMD="$CMD --max-concurrent-requests $MAX_CONCURRENT_REQUESTS"
fi

# Note: Implementation Engineer uses LLM internally via vibe_coder, doesn't accept CLI args

echo "Executing: $CMD"
# Ensure the PostgreSQL password environment variable is available to the Python process
export POSTGRES_PASSWORD
exec $CMD
