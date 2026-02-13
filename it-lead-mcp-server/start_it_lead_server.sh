#!/bin/bash

# Script to start the IT Lead MCP server with various options
# Usage: ./start_it_lead_server.sh [options]

echo "Starting IT Lead MCP Server..."

# Default values
TRANSPORT="streamable-http"
HOST="127.0.0.1"
PORT=3061
ENABLE_REGISTRY=true
REGISTER_WITH_REGISTRY=true
REGISTRY_HOST="127.0.0.1"
REGISTRY_PORT=3031
USE_POSTGRES=true
MAX_CONCURRENT_REQUESTS=10
LLM_PROVIDER_URL="http://asus-tus:1234/v1/chat/completions"
LLM_MODEL="qwen3-4b"
PROMPTS_DIR="."
POSTGRES_USER="postgres"
POSTGRES_PASSWORD="postgres"

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
    --postgres-user)
      POSTGRES_USER="$2"
      shift 2
      ;;
    --postgres-password)
      POSTGRES_PASSWORD="$2"
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
      echo "  --max-concurrent-requests NUM  Maximum number of concurrent requests [default: 10]"
      echo "  --llm-provider-url URL    URL for the LLM provider [default: http://asus-tus:1234/v1/chat/completions]"
      echo "  --llm-model MODEL         LLM model name [default: qwen3-4b]"
      echo "  --prompts-dir DIR         Directory to keep prompts [default: current directory]"
      echo "  --postgres-user USER      PostgreSQL username [default: postgres]"
      echo "  --postgres-password PASS  PostgreSQL password [default: postgres]"
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
  CMD_ARGS="$CMD_ARGS --use-postgres --postgres-user $POSTGRES_USER --postgres-password $POSTGRES_PASSWORD"
fi

if [ "$MAX_CONCURRENT_REQUESTS" != "10" ]; then
  CMD_ARGS="$CMD_ARGS --max-concurrent-requests $MAX_CONCURRENT_REQUESTS"
fi

if [ "$LLM_PROVIDER_URL" != "http://asus-tus:1234/v1/chat/completions" ]; then
  CMD_ARGS="$CMD_ARGS --llm-provider-url $LLM_PROVIDER_URL"
fi

if [ "$LLM_MODEL" != "qwen3-4b" ]; then
  CMD_ARGS="$CMD_ARGS --llm-model $LLM_MODEL"
fi

if [ "$PROMPTS_DIR" != "." ]; then
  CMD_ARGS="$CMD_ARGS --prompts-dir $PROMPTS_DIR"
fi

echo "Executing: python -m it_lead_mcp_server.server $CMD_ARGS"
export PYTHONPATH=.
exec python -m it_lead_mcp_server.server $CMD_ARGS