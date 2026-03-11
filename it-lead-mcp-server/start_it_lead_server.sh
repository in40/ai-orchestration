#!/bin/bash

# Script to start the IT Lead MCP server with PostgreSQL for task storage
# Usage: ./start_it_lead_server.sh [options]

echo "Starting IT Lead MCP Server with PostgreSQL..."

# Default values
TRANSPORT="streamable-http"
HOST="127.0.0.1"
PORT=3061
ENABLE_REGISTRY=true
REGISTER_WITH_REGISTRY=true
REGISTRY_HOST="127.0.0.1"
REGISTRY_PORT=3031
USE_POSTGRES=false  # Changed to false to use SQLite by default (matching Registry Server)
POSTGRES_HOST="127.0.0.1"
POSTGRES_PORT=5432
POSTGRES_DB="mcp_registry"
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"  # You should change this to a secure password in production
MAX_CONCURRENT_REQUESTS=10

# Load configuration from .env file if it exists
if [ -f "/root/qwen/base/.env" ]; then
    source /root/qwen/base/.env
    echo "✅ Loaded configuration from /root/qwen/base/.env"
fi

# LLM Configuration - MUST come from .env, NO fallback
LLM_PROVIDER_URL="${LLM_PROVIDER_URL}"
LLM_MODEL="${LLM_MODEL}"
PROMPTS_DIR="."

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
    --use-sqlite)
      USE_POSTGRES=false
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
    --prompts-dir)
      PROMPTS_DIR="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --transport TYPE          Transport type (stdio, http, streamable-http) [default: streamable-http]"
      echo "  --host HOST               Host for HTTP transport [default: 127.0.0.1]"
      echo "  --port PORT               Port for HTTP transport [default: 3061]"
      echo "  --enable-registry         Enable registry functionality [default: true]"
      echo "  --register-with-registry  Register this server with a registry server [default: true]"
      echo "  --registry-host HOST      Registry server host [default: 127.0.0.1]"
      echo "  --registry-port PORT      Registry server port [default: 3031]"
      echo "  --use-postgres            Use PostgreSQL for registry storage instead of SQLite [default: true]"
      echo "  --use-sqlite              Use SQLite for registry storage (alias for --no-postgres) [default: false]"
      echo "  --postgres-host HOST      PostgreSQL host [default: 127.0.0.1]"
      echo "  --postgres-port PORT      PostgreSQL port [default: 5432]"
      echo "  --postgres-db DB          PostgreSQL database name [default: mcp_registry]"
      echo "  --postgres-user USER      PostgreSQL username [default: postgres]"
      echo "  --postgres-password PASS  PostgreSQL password [default: postgres]"
      echo "  --max-concurrent-requests NUM  Maximum number of concurrent requests [default: 10]"
      echo "  --llm-provider-url URL    URL for the LLM provider [default: from .env]"
      echo "  --llm-model MODEL         LLM model name [MUST be set in .env file]"
      echo "  --prompts-dir DIR         Directory to keep prompts [default: current directory]"
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

# Build the command arguments
CMD_ARGS=""

if [ "$TRANSPORT" != "stdio" ]; then
  CMD_ARGS="$CMD_ARGS --transport $TRANSPORT"
fi

if [ "$HOST" != "127.0.0.1" ]; then
  CMD_ARGS="$CMD_ARGS --host $HOST"
fi

if [ "$PORT" != "3061" ]; then
  CMD_ARGS="$CMD_ARGS --port $PORT"
fi

if [ "$ENABLE_REGISTRY" = true ]; then
  CMD_ARGS="$CMD_ARGS --enable-registry"
fi

if [ "$REGISTER_WITH_REGISTRY" = true ]; then
  CMD_ARGS="$CMD_ARGS --register-with-registry"
fi

if [ "$REGISTRY_HOST" != "127.0.0.1" ]; then
  CMD_ARGS="$CMD_ARGS --registry-host $REGISTRY_HOST"
fi

if [ "$REGISTRY_PORT" != "3031" ]; then
  CMD_ARGS="$CMD_ARGS --registry-port $REGISTRY_PORT"
fi

if [ "$USE_POSTGRES" = true ]; then
  CMD_ARGS="$CMD_ARGS --use-postgres"
fi

echo "Configured to use PostgreSQL for task storage"

# Add postgres-specific args when using postgres (always pass them, even if default)
if [ "$USE_POSTGRES" = true ]; then
  CMD_ARGS="$CMD_ARGS --postgres-host $POSTGRES_HOST"
  CMD_ARGS="$CMD_ARGS --postgres-port $POSTGRES_PORT"
  CMD_ARGS="$CMD_ARGS --postgres-db $POSTGRES_DB"
  CMD_ARGS="$CMD_ARGS --postgres-user $POSTGRES_USER"
  if [ -n "$POSTGRES_PASSWORD" ]; then
    CMD_ARGS="$CMD_ARGS --postgres-password $POSTGRES_PASSWORD"
  fi
fi

if [ "$MAX_CONCURRENT_REQUESTS" != "10" ]; then
  CMD_ARGS="$CMD_ARGS --max-concurrent-requests $MAX_CONCURRENT_REQUESTS"
fi

# ALWAYS pass LLM configuration from .env (no hardcoded defaults)
CMD_ARGS="$CMD_ARGS --llm-provider-url $LLM_PROVIDER_URL"
CMD_ARGS="$CMD_ARGS --llm-model $LLM_MODEL"

if [ "$PROMPTS_DIR" != "." ]; then
  CMD_ARGS="$CMD_ARGS --prompts-dir $PROMPTS_DIR"
fi

echo "Executing: python -c \"import sys; sys.path.insert(0, '.'); from it_lead_mcp_server.server import main; import sys; import shlex; sys.argv = ['server.py'] + shlex.split('$CMD_ARGS'); main()\""
export PYTHONPATH=".:$PYTHONPATH"

# Set PostgreSQL password via environment variable for authentication
if [ "$USE_POSTGRES" = true ] && [ -n "$POSTGRES_PASSWORD" ]; then
  export PGPASSWORD="$POSTGRES_PASSWORD"
fi

python -c "import sys; sys.path.insert(0, '.'); from it_lead_mcp_server.server import main; import sys; import shlex; sys.argv = ['server.py'] + shlex.split('$CMD_ARGS'); main()"