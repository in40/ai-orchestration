#!/bin/bash

# Script to start the MCP Registry Server
# Usage: ./start_registry_server.sh [options]

echo "Starting MCP Registry Server..."

# Load configuration from .env file if it exists
if [ -f "/root/qwen/base/.env" ]; then
    source /root/qwen/base/.env
    echo "✅ Loaded configuration from /root/qwen/base/.env"
fi

# Default values from .env or fallback
TRANSPORT="streamable-http"
HOST="${REGISTRY_HOST:-127.0.0.1}"
PORT="${REGISTRY_PORT:-3031}"
USE_POSTGRES="${USE_POSTGRES:-true}"
POSTGRES_HOST="${POSTGRES_HOST:-127.0.0.1}"
POSTGRES_PORT="${POSTGRES_PORT:-5432}"
POSTGRES_DB="${POSTGRES_DB:-mcp_registry}"
POSTGRES_USER="${POSTGRES_USER:-postgres}"
POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-postgres}"
MAX_CONCURRENT_REQUESTS="${MAX_CONCURRENT_REQUESTS:-10}"

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
    --use-postgres)
      USE_POSTGRES=true
      shift
      ;;
    --max-concurrent-requests)
      MAX_CONCURRENT_REQUESTS="$2"
      shift 2
      ;;
    -b|--background)
      BACKGROUND=true
      shift
      ;;
    -l|--log-file)
      LOG_FILE="$2"
      shift 2
      ;;
    --pid-file)
      PID_FILE="$2"
      shift 2
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --transport TYPE          Transport type (http, streamable-http) [default: streamable-http]"
      echo "  --host HOST               Host for HTTP transport [default: 127.0.0.1]"
      echo "  --port PORT               Port for HTTP transport [default: 3031]"
      echo "  --use-postgres            Use PostgreSQL for registry storage instead of SQLite"
      echo "  --max-concurrent-requests NUM  Maximum number of concurrent requests [default: 10]"
      echo "  -b, --background         Run server in background"
      echo "  -l, --log-file FILE      Redirect output to log file"
      echo "  --pid-file FILE          Write process ID to file"
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

# Build the command
CMD="python -m mcp_std_server.server --enable-registry"

if [ "$TRANSPORT" != "streamable-http" ]; then
  CMD="$CMD --transport $TRANSPORT"
fi

if [ "$HOST" != "127.0.0.1" ]; then
  CMD="$CMD --host $HOST"
fi

CMD="$CMD --port $PORT"

if [ "$USE_POSTGRES" = true ]; then
  CMD="$CMD --use-postgres --postgres-host $POSTGRES_HOST --postgres-port $POSTGRES_PORT --postgres-db $POSTGRES_DB --postgres-user $POSTGRES_USER --postgres-password $POSTGRES_PASSWORD"
fi

if [ "$MAX_CONCURRENT_REQUESTS" != "10" ]; then
  CMD="$CMD --max-concurrent-requests $MAX_CONCURRENT_REQUESTS"
fi

# Handle background and logging options
if [ "$BACKGROUND" = true ] || [ -n "$LOG_FILE" ] || [ -n "$PID_FILE" ]; then
  # Generate timestamped log file if not specified
  if [ -z "$LOG_FILE" ]; then
    TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
    LOG_FILE="registry_${TIMESTAMP}.log"
  fi
  
  # Add output redirection
  FULL_CMD="$CMD >> $LOG_FILE 2>&1"
  
  if [ "$BACKGROUND" = true ]; then
    FULL_CMD="$FULL_CMD &"
    if [ -n "$PID_FILE" ]; then
      FULL_CMD="$FULL_CMD echo \$! > $PID_FILE"
    fi
  fi
  
  echo "Starting registry server in background..."
  echo "Command: $FULL_CMD"
  eval $FULL_CMD
  if [ "$BACKGROUND" = true ]; then
    if [ -n "$PID_FILE" ]; then
      echo "Registry server started in background with PID saved to $PID_FILE"
      echo "Check $LOG_FILE for output"
    else
      echo "Registry server started in background"
      echo "Check $LOG_FILE for output"
    fi
  else
    echo "Registry server started with output redirected to $LOG_FILE"
  fi
else
  # Run in foreground
  echo "Executing: $CMD"
  exec $CMD
fi