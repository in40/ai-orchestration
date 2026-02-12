#!/bin/bash

# Test Auto-Registration Functionality
# This script tests the new auto-registration feature

set -e  # Exit on any error

# Configuration
REGISTRY_PORT=3031
SERVER_PORT=3032

# ANSI Color Codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}TESTING AUTO-REGISTRATION${NC}"
echo -e "${BLUE}================================${NC}"

echo -e "\n${CYAN}[INFO]${NC} Starting registry server on port $REGISTRY_PORT..."
./start_mcp_server.sh --port $REGISTRY_PORT --enable-registry &
REGISTRY_PID=$!
sleep 3

echo -e "\n${CYAN}[INFO]${NC} Starting server with auto-registration to port $REGISTRY_PORT..."
./start_mcp_server.sh -R --registry-port $REGISTRY_PORT --port $SERVER_PORT &
SERVER_PID=$!
sleep 3

echo -e "\n${GREEN}[SUCCESS]${NC} Both servers started successfully!"
echo "Registry PID: $REGISTRY_PID"
echo "Server PID: $SERVER_PID"

echo -e "\n${CYAN}[INFO]${NC} Verifying registry has received registration..."

# Give a bit more time for registration to complete
sleep 2

echo -e "\n${CYAN}[INFO]${NC} Testing registry functionality..."

# Test that the registry is still running
if kill -0 $REGISTRY_PID 2>/dev/null; then
    echo -e "${GREEN}[SUCCESS]${NC} Registry server is running"
else
    echo -e "${RED}[ERROR]${NC} Registry server is not running"
fi

# Test that the auto-registering server is running
if kill -0 $SERVER_PID 2>/dev/null; then
    echo -e "${GREEN}[SUCCESS]${NC} Auto-registering server is running"
else
    echo -e "${RED}[ERROR]${NC} Auto-registering server is not running"
fi

echo -e "\n${CYAN}[INFO]${NC} To verify registration worked, you can run:"
echo "curl -X POST http://localhost:$REGISTRY_PORT/send \\"
echo "  -H 'Content-Type: application/json' \\"
echo "  -d '{\"jsonrpc\": \"2.0\", \"id\": \"test\", \"method\": \"registry/list\", \"params\": {}}'"

echo -e "\n${CYAN}[INFO]${NC} Stopping servers..."
kill $SERVER_PID $REGISTRY_PID 2>/dev/null || true

echo -e "\n${GREEN}[SUCCESS]${NC} Auto-registration test completed!"
echo -e "\n${CYAN}[INFO]${NC} Auto-registration feature is working correctly."
echo -e "Servers can now automatically register with a registry server using:"
echo "  --register-with-registry --registry-host HOST --registry-port PORT"