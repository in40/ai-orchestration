#!/bin/bash

# Script to start the Requirement Engineer MCP server with various options
# Usage: ./start_requirement_engineer_server.sh [options]

echo "Starting Requirement Engineer MCP Server..."

# Load configuration from .env file if it exists
if [ -f "/root/qwen/base/.env" ]; then
    source /root/qwen/base/.env
    echo "✅ Loaded configuration from /root/qwen/base/.env"
fi

# Default values from .env or fallback
TRANSPORT="streamable-http"
HOST="${WEB_UI_HOST:-0.0.0.0}"
PORT="${REQUIREMENTS_PORT:-3062}"
ENABLE_REGISTRY=false
REGISTER_WITH_REGISTRY=true
REGISTRY_HOST="${REGISTRY_HOST:-127.0.0.1}"
REGISTRY_PORT="${REGISTRY_PORT:-3031}"
USE_POSTGRES="${USE_POSTGRES:-true}"
POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
POSTGRES_DB="${POSTGRES_DB:-mcp_registry}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
MAX_CONCURRENT_REQUESTS="${MAX_CONCURRENT_REQUESTS:-10}"
# LLM configuration MUST come from .env - no fallbacks
LLM_PROVIDER_URL="${LLM_PROVIDER_URL}"
LLM_MODEL="${LLM_MODEL}"

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
    --llm-provider-url)
      LLM_PROVIDER_URL="$2"
      shift 2
      ;;
    --llm-model)
      LLM_MODEL="$2"
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
      echo "  --llm-provider-url URL    LLM provider URL [default: http://192.168.51.237:1234/v1/chat/completions]"
      echo "  --llm-model MODEL         LLM model name [default: qwen3-coder-next@q5_k_xl]"
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
  CMD="$CMD --use-postgres --postgres-host $POSTGRES_HOST --postgres-db $POSTGRES_DB --postgres-user $POSTGRES_USER --postgres-password $POSTGRES_PASSWORD"
fi

if [ "$MAX_CONCURRENT_REQUESTS" != "10" ]; then
  CMD="$CMD --max-concurrent-requests $MAX_CONCURRENT_REQUESTS"
fi

# LLM configuration
if [ -n "$LLM_PROVIDER_URL" ]; then
  CMD="$CMD --llm-provider-url $LLM_PROVIDER_URL"
fi

if [ -n "$LLM_MODEL" ]; then
  CMD="$CMD --llm-model $LLM_MODEL"
fi

echo "Executing: $CMD"
exec $CMD
