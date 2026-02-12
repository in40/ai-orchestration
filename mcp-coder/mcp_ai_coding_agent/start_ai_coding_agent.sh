#!/bin/bash
# Start AI Coding Agent MCP Server
# This script starts the AI Coding Agent server with the appropriate configuration

set -e  # Exit on any error

# Default values
PORT=3050
HOST="127.0.0.1"
TRANSPORT="http"
ENABLE_REGISTRY=false
REGISTER_WITH_REGISTRY=true
REGISTRY_HOST="127.0.0.1"
REGISTRY_PORT=3031
MAX_CONCURRENT_REQUESTS=10
PYTHON_CMD="python3"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --port)
            PORT="$2"
            shift 2
            ;;
        --host)
            HOST="$2"
            shift 2
            ;;
        --transport)
            TRANSPORT="$2"
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
        --max-concurrent-requests)
            MAX_CONCURRENT_REQUESTS="$2"
            shift 2
            ;;
        --python)
            PYTHON_CMD="$2"
            shift 2
            ;;
        --help)
            echo "Usage: $0 [OPTIONS]"
            echo "Start the AI Coding Agent MCP Server"
            echo ""
            echo "Options:"
            echo "  --port PORT                    Port to listen on (default: 3050)"
            echo "  --host HOST                    Host to bind to (default: 127.0.0.1)"
            echo "  --transport TYPE               Transport type (stdio or http, default: http)"
            echo "  --enable-registry              Enable registry functionality to act as a registry server"
            echo "  --register-with-registry       Register this server with a registry server"
            echo "  --registry-host HOST           Registry server host to register with (default: 127.0.0.1)"
            echo "  --registry-port PORT           Registry server port to register with (default: 3031)"
            echo "  --max-concurrent-requests NUM  Max concurrent requests (default: 10)"
            echo "  --python CMD                   Python command to use (default: python3)"
            echo "  --help                         Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Activate the virtual environment
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_PATH="$SCRIPT_DIR/../mcp_ai_agent_env"
if [[ -d "$VENV_PATH" ]]; then
    source "$VENV_PATH/bin/activate"
elif [[ -d "$SCRIPT_DIR/../venv" ]]; then
    source "$SCRIPT_DIR/../venv/bin/activate"
else
    echo "Error: Virtual environment not found. Please create it first."
    exit 1
fi

# Check if Python command exists
if ! command -v "$PYTHON_CMD" &> /dev/null; then
    echo "Error: $PYTHON_CMD is not available"
    exit 1
fi

# Check if the server module exists
if [[ ! -f "ai_coding_agent_server.py" ]]; then
    echo "Error: ai_coding_agent_server.py not found"
    exit 1
fi

# Display configuration
echo "Starting AI Coding Agent MCP Server..."
echo "Configuration:"
echo "  Host: $HOST"
echo "  Port: $PORT"
echo "  Transport: $TRANSPORT"
if [ "$ENABLE_REGISTRY" = true ]; then
    echo "  Registry: enabled (acts as registry server)"
elif [ "$REGISTER_WITH_REGISTRY" = true ]; then
    echo "  Registry: register with registry at $REGISTRY_HOST:$REGISTRY_PORT"
else
    echo "  Registry: disabled"
fi
echo "  Max Concurrent Requests: $MAX_CONCURRENT_REQUESTS"
echo ""

# Start the server
if [ "$ENABLE_REGISTRY" = true ]; then
    # Enable registry functionality (this server acts as a registry)
    # Note: AI Coding Agent doesn't support registry server mode, so we'll warn the user
    echo "Warning: AI Coding Agent doesn't support registry server mode. Starting normally."
    LLM_BASE_URL="${LLM_BASE_URL:-http://asus-tus:1234/v1}" LLM_API_KEY="${LLM_API_KEY:-not-needed-for-local-llm}" LLM_MODEL_NAME="${LLM_MODEL_NAME:-qwen3-4b}" exec "$PYTHON_CMD" ai_coding_agent_server.py --transport "$TRANSPORT" --host "$HOST" --port "$PORT" --max-concurrent-requests "$MAX_CONCURRENT_REQUESTS"
elif [ "$REGISTER_WITH_REGISTRY" = true ]; then
    # Register this server with an existing registry
    LLM_BASE_URL="${LLM_BASE_URL:-http://asus-tus:1234/v1}" LLM_API_KEY="${LLM_API_KEY:-not-needed-for-local-llm}" LLM_MODEL_NAME="${LLM_MODEL_NAME:-qwen3-4b}" exec "$PYTHON_CMD" ai_coding_agent_server.py --transport "$TRANSPORT" --host "$HOST" --port "$PORT" --register-with-registry --registry-host "$REGISTRY_HOST" --registry-port "$REGISTRY_PORT" --max-concurrent-requests "$MAX_CONCURRENT_REQUESTS"
else
    # Run normally without registry functionality
    LLM_BASE_URL="${LLM_BASE_URL:-http://asus-tus:1234/v1}" LLM_API_KEY="${LLM_API_KEY:-not-needed-for-local-llm}" LLM_MODEL_NAME="${LLM_MODEL_NAME:-qwen3-4b}" exec "$PYTHON_CMD" ai_coding_agent_server.py --transport "$TRANSPORT" --host "$HOST" --port "$PORT" --max-concurrent-requests "$MAX_CONCURRENT_REQUESTS"
fi