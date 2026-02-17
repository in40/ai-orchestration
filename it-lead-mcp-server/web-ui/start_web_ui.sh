#!/bin/bash

# Script to start the MCP Agent Web UI
# Usage: ./start_web_ui.sh [options]

echo "Starting MCP Agent Web UI..."

# Default values
BACKEND_HOST="0.0.0.0"
BACKEND_PORT=8000
FRONTEND_PORT=5173
IT_LEAD_HOST="localhost"
IT_LEAD_PORT=3061

# Parse command line options
while [[ $# -gt 0 ]]; do
  case $1 in
    --backend-host)
      BACKEND_HOST="$2"
      shift 2
      ;;
    --backend-port)
      BACKEND_PORT="$2"
      shift 2
      ;;
    --frontend-port)
      FRONTEND_PORT="$2"
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
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --backend-host HOST    Host for backend server [default: 0.0.0.0]"
      echo "  --backend-port PORT    Port for backend server [default: 8000]"
      echo "  --frontend-port PORT   Port for frontend server [default: 5173]"
      echo "  --it-lead-host HOST    Host for IT Lead server [default: localhost]"
      echo "  --it-lead-port PORT    Port for IT Lead server [default: 3061]"
      echo "  -h, --help            Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Start the backend server in the background
echo "Starting backend server on ${BACKEND_HOST}:${BACKEND_PORT}..."
cd /root/qwen/base/it-lead-mcp-server/web-ui/backend
source venv/bin/activate
uvicorn main:app --host "${BACKEND_HOST}" --port "${BACKEND_PORT}" &
BACKEND_PID=$!

# Wait a moment for the backend to start
sleep 3

# Start the frontend server in the background
echo "Starting frontend server on port ${FRONTEND_PORT}..."
cd /root/qwen/base/it-lead-mcp-server/web-ui/frontend
npm run dev -- --port "${FRONTEND_PORT}" &
FRONTEND_PID=$!

echo "MCP Agent Web UI started successfully!"
echo "Backend: http://${BACKEND_HOST}:${BACKEND_PORT}"
echo "Frontend: http://localhost:${FRONTEND_PORT}"
echo "IT Lead Agent: http://${IT_LEAD_HOST}:${IT_LEAD_PORT}"

echo "Backend PID: ${BACKEND_PID}"
echo "Frontend PID: ${FRONTEND_PID}"

# Function to stop servers on Ctrl+C
cleanup() {
    echo "Shutting down MCP Agent Web UI..."
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null
    exit 0
}

# Trap SIGINT and SIGTERM
trap cleanup INT TERM

# Wait for both processes
wait $BACKEND_PID $FRONTEND_PID