#!/bin/bash

# Script to start the Vibe Coding AI Agent MCP server with various options
# Usage: ./start_server.sh [options]

echo "Starting Vibe Coding AI Agent MCP Server..."

# Create logs directory if it doesn't exist
mkdir -p ./logs

# Set environment variables
export PYTHONPATH=".:./mcp-std-skeleton:${PYTHONPATH}:$(pwd)"

# Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
    echo "Virtual environment activated"
else
    echo "Error: Virtual environment not found. Please run 'python3 -m venv .venv' first."
    exit 1
fi

# Check if required environment variables are set
if [ -z "$LM_STUDIO_URL" ]; then
    export LM_STUDIO_URL="http://asus-tus:1234/v1"
    echo "LM_STUDIO_URL not set, using default: $LM_STUDIO_URL"
fi

if [ -z "$LM_STUDIO_MODEL" ]; then
    export LM_STUDIO_MODEL="qwen3-4b"
    echo "LM_STUDIO_MODEL not set, using default: $LM_STUDIO_MODEL"
fi

# Default values
TRANSPORT="streamable-http"
HOST="0.0.0.0"
PORT=3050
ENABLE_REGISTRY=true
REGISTER_WITH_REGISTRY=false
REGISTRY_HOST="127.0.0.1"
REGISTRY_PORT=3031
USE_POSTGRES=false
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
    --disable-registry)
      ENABLE_REGISTRY=false
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
      echo "  --host HOST               Host for HTTP transport [default: 0.0.0.0]"
      echo "  --port PORT               Port for HTTP transport [default: 3050]"
      echo "  --enable-registry         Enable registry functionality [default: true]"
      echo "  --disable-registry        Disable registry functionality"
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

echo "Starting Vibe Coding AI Agent MCP Server..."
echo "Transport: $TRANSPORT"
echo "Host: $HOST"
echo "Port: $PORT"
echo "Registry: $ENABLE_REGISTRY"
echo "LM Studio URL: $LM_STUDIO_URL"
echo "LM Studio Model: $LM_STUDIO_MODEL"

# Create a temporary Python script to start the server
TEMP_SCRIPT="./temp_server_start.py"
cat > "$TEMP_SCRIPT" << EOF
import sys
import os
sys.path.insert(0, '.')
sys.path.insert(0, './mcp-std-skeleton')

from vibe_coding_agent.mcp_server import VibeCodingMcpServer

server = VibeCodingMcpServer(
    host='$HOST',
    port=$PORT,
    enable_registry=$ENABLE_REGISTRY,
    register_with_registry=$REGISTER_WITH_REGISTRY,
    registry_host='$REGISTRY_HOST',
    registry_port=$REGISTRY_PORT,
    use_postgres=$USE_POSTGRES,
    max_concurrent_requests=$MAX_CONCURRENT_REQUESTS
)

try:
    server.start()
except KeyboardInterrupt:
    print('Server stopped by user')
except Exception as e:
    print(f'Server error: {e}')
    import traceback
    traceback.print_exc()
EOF

echo "Executing server startup script..."
echo "Server is starting... Check logs/server-$(date +%Y%m%d).log for detailed output"

# Start the server in a fully detached background process
nohup python "$TEMP_SCRIPT" >> "./logs/server-$(date +%Y%m%d).log" 2>&1 < /dev/null &
SERVER_PID=$!

# Disown the process so it's not affected by shell termination
disown $SERVER_PID

# Clean up the temporary script
rm -f "$TEMP_SCRIPT"

if kill -0 $SERVER_PID 2>/dev/null; then
    echo "✓ Vibe Coding AI Agent MCP Server started successfully!"
    echo "✓ Server PID: $SERVER_PID"
    echo "✓ Access the server at: http://$HOST:$PORT/mcp"
    echo "✓ View logs with: tail -f ./logs/server-$(date +%Y%m%d).log"
    echo ""
    echo "NOTE: Server is running in the background. Use './stop_server.sh' to stop it."
else
    echo "✗ Failed to start server"
    exit 1
fi