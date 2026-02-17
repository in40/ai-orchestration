#!/bin/bash

# Team Management MCP Server startup script
# Sets up environment variables and starts the server

# Set default values
export TRANSPORT="${TRANSPORT:-streamable-http}"
export HOST="${HOST:-127.0.0.1}"
export PORT="${PORT:-3063}"  # Default to port 3063 as requested
export ENABLE_REGISTRY="${ENABLE_REGISTRY:-false}"  # Should be false as requested
export REGISTER_WITH_REGISTRY="${REGISTER_WITH_REGISTRY:-true}"  # Should be true as requested
export REGISTRY_HOST="${REGISTRY_HOST:-127.0.0.1}"
export REGISTRY_PORT="${REGISTRY_PORT:-3031}"
export USE_POSTGRES="${USE_POSTGRES:-false}"
export MAX_CONCURRENT_REQUESTS="${MAX_CONCURRENT_REQUESTS:-10}"

# PostgreSQL configuration (only used if USE_POSTGRES=true)
export POSTGRES_HOST="${POSTGRES_HOST:-localhost}"
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export POSTGRES_DB="${POSTGRES_DB:-mcp_registry}"
export POSTGRES_USER="${POSTGRES_USER:-postgres}"
export POSTGRES_PASSWORD="${POSTGRES_PASSWORD:-}"

# Start the team management server
echo "Starting Team Management MCP Server..."
echo "Transport: $TRANSPORT"
echo "Host: $HOST"
echo "Port: $PORT"
echo "Enable Registry: $ENABLE_REGISTRY"
echo "Register with Registry: $REGISTER_WITH_REGISTRY"
echo "Registry Host: $REGISTRY_HOST"
echo "Registry Port: $REGISTRY_PORT"
echo "Use PostgreSQL: $USE_POSTGRES"

# Activate virtual environment
source venv/bin/activate

# Start the server with the specified parameters
python -m mcp_std_server.team_management_server \
  --transport "$TRANSPORT" \
  --host "$HOST" \
  --port "$PORT" \
  $( [[ "$ENABLE_REGISTRY" == "true" ]] && echo "--enable-registry" ) \
  $( [[ "$REGISTER_WITH_REGISTRY" == "true" ]] && echo "--register-with-registry" ) \
  --registry-host "$REGISTRY_HOST" \
  --registry-port "$REGISTRY_PORT" \
  $( [[ "$USE_POSTGRES" == "true" ]] && echo "--use-postgres --postgres-host $POSTGRES_HOST --postgres-port $POSTGRES_PORT --postgres-db $POSTGRES_DB --postgres-user $POSTGRES_USER --postgres-password $POSTGRES_PASSWORD" ) \
  --max-concurrent-requests "$MAX_CONCURRENT_REQUESTS"

echo "Team Management MCP Server stopped."