#!/bin/bash

# Script to start the Web UI components (backend and frontend)
# Usage: ./start_ui.sh [options]

echo "Starting MCP Agent Web UI..."

# Load configuration from .env file if it exists
if [ -f "/root/qwen/base/.env" ]; then
    source /root/qwen/base/.env
    echo "✅ Loaded configuration from /root/qwen/base/.env"
fi

# Default values (from .env or fallback)
WEB_BACKEND_HOST="${WEB_UI_HOST:-0.0.0.0}"
WEB_BACKEND_PORT="${WEB_UI_BACKEND_PORT:-8000}"
WEB_FRONTEND_PORT="${WEB_UI_FRONTEND_PORT:-5173}"
IT_LEAD_HOST="${IT_LEAD_HOST:-127.0.0.1}"
IT_LEAD_PORT="${IT_LEAD_PORT:-3061}"
REGISTRY_HOST="${REGISTRY_HOST:-127.0.0.1}"
REGISTRY_PORT="${REGISTRY_PORT:-3031}"
# LLM Configuration - MUST come from .env, NO fallback
LLM_PROVIDER_URL="${LLM_PROVIDER_URL}"
LLM_MODEL="${LLM_MODEL}"

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
      echo "  --llm-provider-url URL   URL for the LLM provider [default: from .env]"
      echo "  --llm-model MODEL        LLM model name [default: from .env (qwen3-coder-next@q5_k_xl)]"
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

# Trap ONLY Ctrl+C (SIGINT), NOT SIGTERM - allow nohup to protect from shell exit
# This prevents cleanup from running when shell exits, allowing disowned processes to survive
trap cleanup INT

# Check if port 8000 is already in use
if ss -tlnp | grep -q ":${WEB_BACKEND_PORT} "; then
    echo "⚠️  Port ${WEB_BACKEND_PORT} is already in use!"
    echo "Checking for existing Web UI backend process..."
    
    # Find existing uvicorn process on our port
    EXISTING_PID=$(lsof -t -i :${WEB_BACKEND_PORT} 2>/dev/null | head -1)
    
    if [ -n "$EXISTING_PID" ]; then
        echo "Found existing backend process (PID: $EXISTING_PID)"
        echo "Killing existing process..."
        kill -9 $EXISTING_PID 2>/dev/null || true
        sleep 2
    fi
fi

# Check if port 5173 is already in use
if ss -tlnp | grep -q ":${WEB_FRONTEND_PORT} "; then
    echo "⚠️  Port ${WEB_FRONTEND_PORT} is already in use!"
    echo "Checking for existing Web UI frontend process..."
    
    # Find existing vite process on our port
    EXISTING_VITE_PID=$(lsof -t -i :${WEB_FRONTEND_PORT} 2>/dev/null | head -1)
    
    if [ -n "$EXISTING_VITE_PID" ]; then
        echo "Found existing frontend process (PID: $EXISTING_VITE_PID)"
        echo "Killing existing process..."
        kill -9 $EXISTING_VITE_PID 2>/dev/null || true
        sleep 2
    fi
fi

# Start Web UI backend in the background with nohup to protect from signals
echo "Starting Web UI backend on ${WEB_BACKEND_HOST}:${WEB_BACKEND_PORT}..."
cd /root/qwen/base/it-lead-mcp-server/web-ui/backend
source venv/bin/activate
nohup uvicorn main:app --host "${WEB_BACKEND_HOST}" --port "${WEB_BACKEND_PORT}" > /tmp/web_ui_backend.log 2>&1 &
WEB_BACKEND_PID=$!

echo "Web Backend PID: ${WEB_BACKEND_PID}"

# Wait a moment for the backend to start
sleep 3

# Verify backend started
if ! ps -p $WEB_BACKEND_PID > /dev/null 2>&1; then
    echo "❌ Web UI backend failed to start!"
    echo "Check /tmp/web_ui_backend.log for details"
    exit 1
fi

# Start Web UI frontend in the background with nohup to protect from signals
echo "Starting Web UI frontend on port ${WEB_FRONTEND_PORT}..."
cd /root/qwen/base/it-lead-mcp-server/web-ui/frontend
nohup npm run dev -- --port "${WEB_FRONTEND_PORT}" > /tmp/web_ui_frontend.log 2>&1 &
WEB_FRONTEND_PID=$!

echo "Web Frontend PID: ${WEB_FRONTEND_PID}"

# Wait a moment for the frontend to start
sleep 3

# Verify frontend started
if ! ps -p $WEB_FRONTEND_PID > /dev/null 2>&1; then
    echo "❌ Web UI frontend failed to start!"
    echo "Check /tmp/web_ui_frontend.log for details"
    exit 1
fi

# Disown processes to prevent them from being killed when shell exits
disown $WEB_BACKEND_PID 2>/dev/null || true
disown $WEB_FRONTEND_PID 2>/dev/null || true

echo ""
echo "✅ MCP Agent Web UI started successfully!"
echo "Web Backend: http://${WEB_BACKEND_HOST}:${WEB_BACKEND_PORT}"
echo "Web Frontend: http://localhost:${WEB_FRONTEND_PORT}"
echo ""
echo "Web UI is configured to connect to IT Lead Server at: http://${IT_LEAD_HOST}:${IT_LEAD_PORT}"
echo ""
echo "Backend logs: /tmp/web_ui_backend.log"
echo "Frontend logs: /tmp/web_ui_frontend.log"
echo ""
echo "PIDs: Backend=$WEB_BACKEND_PID, Frontend=$WEB_FRONTEND_PID"
echo ""