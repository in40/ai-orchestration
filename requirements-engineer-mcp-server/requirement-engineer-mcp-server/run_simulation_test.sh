#!/bin/bash

# AI Agent Simulation Test Script for Requirement Engineer MCP Server
# Runs the simulation test to verify all functionality

echo "==========================================="
echo "REQUIREMENT ENGINEER MCP SERVER SIMULATION TEST"
echo "==========================================="

echo ""
echo "Running AI agent simulation test..."
echo ""

# Run the simulation test
python test_requirement_engineer_simulation.py

TEST_RESULT=$?

if [ $TEST_RESULT -eq 0 ]; then
    echo ""
    echo "==========================================="
    echo "SIMULATION TEST PASSED!"
    echo "==========================================="
    echo ""
    echo "All requirement engineer functionality verified successfully."
    echo ""
else
    echo ""
    echo "==========================================="
    echo "SIMULATION TEST FAILED!"
    echo "==========================================="
    echo ""
    echo "Error occurred during simulation test."
    exit 1
fi