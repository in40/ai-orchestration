#!/bin/bash

# Script to start the complete MCP system (IT Lead server and Web UI)
# Usage: ./start_system.sh [options]

echo "Starting MCP System (IT Lead Server + Web UI)..."

# Default values
START_IT_LEAD_SERVER=true
START_WEB_UI=true

# Parse command line options
while [[ $# -gt 0 ]]; do
  case $1 in
    --no-it-lead-server)
      START_IT_LEAD_SERVER=false
      shift
      ;;
    --no-web-ui)
      START_WEB_UI=false
      shift
      ;;
    -h|--help)
      echo "Usage: $0 [OPTIONS]"
      echo ""
      echo "Options:"
      echo "  --no-it-lead-server    Skip starting the IT Lead server"
      echo "  --no-web-ui           Skip starting the Web UI"
      echo "  -h, --help           Show this help message"
      exit 0
      ;;
    *)
      echo "Unknown option: $1"
      echo "Use --help for usage information"
      exit 1
      ;;
  esac
done

# Function to stop all processes on Ctrl+C
cleanup() {
    echo ""
    echo "Shutting down MCP System..."
    
    # Kill all background processes
    jobs -p | xargs -r kill 2>/dev/null
    
    # Also try to stop specific services if they're running
    pkill -f "it_lead_mcp_server.server" 2>/dev/null || true
    pkill -f "uvicorn" 2>/dev/null || true
    pkill -f "npm run dev" 2>/dev/null || true
    
    echo "MCP System has been shut down."
    exit 0
}

# Trap SIGINT and SIGTERM
trap cleanup INT TERM

# Start IT Lead Server first (if requested)
if [ "$START_IT_LEAD_SERVER" = true ]; then
    echo ""
    echo "Starting IT Lead MCP Server..."
    cd /root/qwen/base/it-lead-mcp-server
    ./start_it_lead_server.sh &
    IT_LEAD_PID=$!
    
    echo "IT Lead Server PID: ${IT_LEAD_PID}"
    
    # Wait a moment for the IT Lead server to start
    echo "Waiting for IT Lead Server to be ready..."
    sleep 5
    
    # Check if the server is running on port 3061
    timeout 10 bash -c 'until nc -z localhost 3061; do sleep 1; done' 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "IT Lead Server is ready on port 3061"
    else
        echo "Warning: IT Lead Server may not be ready on port 3061"
    fi
else
    echo "Skipping IT Lead Server startup (as requested)"
fi

# Start Web UI (if requested)
if [ "$START_WEB_UI" = true ]; then
    echo ""
    echo "Starting Web UI..."
    cd /root/qwen/base/it-lead-mcp-server
    ./start_ui.sh &
    WEB_UI_PID=$!
    
    echo "Web UI PID: ${WEB_UI_PID}"
    
    # Wait a moment for the Web UI to start
    echo "Waiting for Web UI to be ready..."
    sleep 5
    
    # Check if the web backend is running on port 8000
    timeout 10 bash -c 'until nc -z localhost 8000; do sleep 1; done' 2>/dev/null
    if [ $? -eq 0 ]; then
        echo "Web UI Backend is ready on port 8000"
    else
        echo "Warning: Web UI Backend may not be ready on port 8000"
    fi
else
    echo "Skipping Web UI startup (as requested)"
fi

echo ""
echo "MCP System startup complete!"
echo ""
if [ "$START_IT_LEAD_SERVER" = true ]; then
    echo "IT Lead Server should be available at: http://127.0.0.1:3061/mcp"
fi
if [ "$START_WEB_UI" = true ]; then
    echo "Web UI should be available at: http://localhost:5173"
fi
echo ""
echo "Press Ctrl+C to shut down the entire MCP System"
echo ""

# Wait for all processes
wait