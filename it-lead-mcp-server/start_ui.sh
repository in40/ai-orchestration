#!/bin/bash

# Script to start the Web UI components (backend and frontend)
# Usage: ./start_ui.sh [options]

echo "Starting MCP Agent Web UI..."

# Default values
WEB_BACKEND_HOST="0.0.0.0"
WEB_BACKEND_PORT=8000
WEB_FRONTEND_PORT=5173
IT_LEAD_HOST="127.0.0.1"
IT_LEAD_PORT=3061
REGISTRY_HOST="127.0.0.1"
REGISTRY_PORT=3031
LLM_PROVIDER_URL="http://asus-tus:1234/v1/chat/completions"
LLM_MODEL="qwen3.5-35b-a3b@q5_k_xl"

# Parse command line options
while [[ $# -gt 0 ]]; do
  case $1 in
    --web-backend-host)
      WEB_BACKEND_HOST="$2"
      shift 2
      ;;
    --web-backend-port)
      WEB_BACKEND_PORT="$2"
      shift 2
      ;;
    --web-frontend-port)
      WEB_FRONTEND_PORT="$2"
      shift 2
      ;;
    --it-lead-host)
      IT_LEAD_HOST="$2"
      shift 2
      ;;
    --it-lead-port)
      IT_LEAD_PORT="$2"
      shift 2
      ;;
    --registry-host)
      REGISTRY_HOST="$2"
      shift 2
      ;;
    --registry-port)
      REGISTRY_PORT="$2"
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
      echo "  --web-backend-host HOST  Host for web backend server [default: 0.0.0.0]"
      echo "  --web-backend-port PORT  Port for web backend server [default: 8000]"
      echo "  --web-frontend-port PORT Port for web frontend server [default: 5173]"
      echo "  --it-lead-host HOST      Host for IT Lead server [default: 127.0.0.1]"
      echo "  --it-lead-port PORT      Port for IT Lead server [default: 3061]"
      echo "  --registry-host HOST     Host for registry server [default: 127.0.0.1]"
      echo "  --registry-port PORT     Port for registry server [default: 3031]"
      echo "  --llm-provider-url URL   URL for the LLM provider [default: http://asus-tus:1234/v1/chat/completions]"
      echo "  --llm-model MODEL        LLM model name [default: qwen3.5-35b-a3b@q5_k_xl]"
      echo "  -h, --help              Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

echo "Configuration:"
echo "  Web Backend: ${WEB_BACKEND_HOST}:${WEB_BACKEND_PORT}"
echo "  Web Frontend: ${WEB_FRONTEND_PORT}"
echo "  IT Lead Server: ${IT_LEAD_HOST}:${IT_LEAD_PORT}"
echo "  Registry: ${REGISTRY_HOST}:${REGISTRY_PORT}"
echo ""

# Function to stop all processes on Ctrl+C
cleanup() {
    echo ""
    echo "Shutting down Web UI..."
    # Kill backend process if it's still running
    if kill -0 $WEB_BACKEND_PID 2>/dev/null; then
        kill -TERM $WEB_BACKEND_PID 2>/dev/null || true
        wait $WEB_BACKEND_PID 2>/dev/null || true
    fi
    # Kill frontend process if it's still running
    if kill -0 $WEB_FRONTEND_PID 2>/dev/null; then
        kill -TERM $WEB_FRONTEND_PID 2>/dev/null || true
        wait $WEB_FRONTEND_PID 2>/dev/null || true
    fi
    exit 0
}

# Trap SIGINT and SIGTERM
trap cleanup INT TERM

# Start Web UI backend in the background with nohup to protect from signals
echo "Starting Web UI backend on ${WEB_BACKEND_HOST}:${WEB_BACKEND_PORT}..."
cd /root/qwen/base/it-lead-mcp-server/web-ui/backend
source venv/bin/activate
nohup uvicorn main:app --host "${WEB_BACKEND_HOST}" --port "${WEB_BACKEND_PORT}" > /tmp/backend.log 2>&1 &
WEB_BACKEND_PID=$!

echo "Web Backend PID: ${WEB_BACKEND_PID}"

# Wait a moment for the backend to start
sleep 3

# Start Web UI frontend in the background with nohup to protect from signals
echo "Starting Web UI frontend on port ${WEB_FRONTEND_PORT}..."
cd /root/qwen/base/it-lead-mcp-server/web-ui/frontend
nohup npm run dev -- --port "${WEB_FRONTEND_PORT}" > /tmp/frontend.log 2>&1 &
WEB_FRONTEND_PID=$!

echo "Web Frontend PID: ${WEB_FRONTEND_PID}"

echo ""
echo "MCP Agent Web UI started successfully!"
echo "Web Backend: http://${WEB_BACKEND_HOST}:${WEB_BACKEND_PORT}"
echo "Web Frontend: http://localhost:${WEB_FRONTEND_PORT}"
echo ""
echo "Web UI is configured to connect to IT Lead Server at: http://${IT_LEAD_HOST}:${IT_LEAD_PORT}"
echo ""
echo "Press Ctrl+C to shut down the Web UI"
echo ""

# Wait for all processes
wait $WEB_BACKEND_PID $WEB_FRONTEND_PID