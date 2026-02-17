#!/bin/bash

# Test script for Requirement Engineer MCP Server
# This script tests the basic functionality of the requirement engineer server

echo "Testing Requirement Engineer MCP Server..."

# Test 1: Check if the server can start with basic configuration
echo "Test 1: Checking server startup configuration..."
if python requirement_engineer_server.py --help; then
    echo "✓ Help command works"
else
    echo "✗ Help command failed"
    exit 1
fi

# Test 2: Check if the startup script works
echo "Test 2: Checking startup script..."
if bash start_requirement_engineer_server.sh --help; then
    echo "✓ Startup script help works"
else
    echo "✗ Startup script help failed"
    exit 1
fi

# Test 3: Check if the stop script exists
echo "Test 3: Checking stop script..."
if [ -f "stop_requirement_engineer_server.sh" ]; then
    echo "✓ Stop script exists"
else
    echo "✗ Stop script missing"
    exit 1
fi

# Test 4: Check if all required files exist
echo "Test 4: Checking required files..."
files=(
    "requirement_engineer_server.py"
    "requirement_engineer_handlers.py"
    "start_requirement_engineer_server.sh"
    "stop_requirement_engineer_server.sh"
    "AGENTS.md"
    "README.md"
    "requirements.txt"
)

missing_files=()
for file in "${files[@]}"; do
    if [ ! -f "$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -eq 0 ]; then
    echo "✓ All required files exist"
else
    echo "✗ Missing files: ${missing_files[*]}"
    exit 1
fi

# Test 5: Check if the server can be imported in Python
echo "Test 5: Checking Python import..."
if python -c "from requirement_engineer_server import RequirementEngineerMcpServer; print('✓ Import successful')"; then
    :
else
    echo "✗ Import failed"
    exit 1
fi

echo "All tests passed! ✓"
echo ""
echo "To run the server, use:"
echo "  ./start_requirement_engineer_server.sh"
echo ""
echo "To stop the server, use:"
echo "  ./stop_requirement_engineer_server.sh"