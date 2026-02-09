#!/bin/bash

# Script to start the MCP JSON-RPC Registry in the background

echo "Starting MCP JSON-RPC Registry..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Error: Virtual environment not found."
    echo "Please run setup_env.sh first to create the virtual environment."
    exit 1
fi

# Activate virtual environment
source venv/bin/activate

# Check if required packages are installed
if ! python -c "import mcp" &> /dev/null; then
    echo "Required packages not found in virtual environment."
    echo "Running setup script to install dependencies..."
    ./setup_env.sh
    source venv/bin/activate
fi

# Load environment variables from .env file if it exists
if [ -f ".env" ]; then
    export $(grep -v '^#' .env | xargs)
fi

# Use environment variables for configuration, with defaults
HOST=${HTTP_HOST:-"0.0.0.0"}
PORT=${HTTP_PORT:-"6000"}

# Check if a previous instance is running on this port
if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
    echo "Stopping existing registry server on port $PORT..."
    lsof -ti:$PORT | xargs kill -9 2>/dev/null || true
    sleep 2
fi

# Start the registry server in the background
echo "Starting registry server on http://$HOST:$PORT..."
nohup python -m src.registry.main --transport streamable-http --host $HOST --port $PORT > registry.log 2>&1 &

# Get the PID of the background process
SERVER_PID=$!

if [ $? -eq 0 ]; then
    echo "Registry server started successfully with PID $SERVER_PID"
    echo "Server is running on http://$HOST:$PORT"
    echo "Logs are being written to registry.log"
else
    echo "Failed to start registry server"
    exit 1
fi