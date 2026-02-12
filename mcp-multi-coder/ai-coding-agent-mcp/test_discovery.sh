#!/bin/bash

# Test script to verify that the AI Coding Agent server appears in the registry
# Assumes registry server is running on port 3031

echo "Testing AI Coding Agent server discovery in registry..."

# Check if registry server is running
if ! curl -s http://localhost:3031/ping > /dev/null 2>&1; then
    echo "ERROR: Registry server not found on http://localhost:3031"
    exit 1
fi

echo "Registry server found, querying for services..."

# Query registry using the proper client
python query_registry_client_proper_fixed.py --registry-url "http://localhost:3031" --timeout 10

if [ $? -eq 0 ]; then
    echo "SUCCESS: Registry query completed"
else
    echo "ERROR: Registry query failed"
    exit 1
fi

echo "Test completed successfully!"