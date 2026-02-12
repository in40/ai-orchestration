#!/bin/bash

# AI Coding Agent Client - Simple Shell Wrapper
# Just calls the Python client utility with proper arguments

# Check if Python client utility exists
if [ ! -f "client_utility.py" ]; then
    echo "Error: client_utility.py not found in current directory"
    exit 1
fi

# Set default server URL
SERVER_URL=${SERVER_URL:-"http://localhost:3060"}

# Extract the command and pass the URL as the first argument to the Python script
python3 client_utility.py --url "$SERVER_URL" "$@"