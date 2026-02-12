#!/bin/bash

# Vibe Coding AI Agent - Task Submission Utility
# Allows submitting coding tasks to the agent via MCP protocol

set -e

echo "=== Vibe Coding AI Agent - Task Submission Utility ==="

# Check if server is running
if ! curl -s http://localhost:3050/mcp >/dev/null 2>&1; then
    echo "❌ Error: Vibe Coding AI Agent server not reachable at http://localhost:3050/mcp"
    echo "Please start the server first using: ./start_server.sh"
    exit 1
fi

# Parse command line arguments
ACTION=${1:-"submit"}
TASK_DESCRIPTION=${2:-""}

if [ "$ACTION" = "help" ] || [ "$ACTION" = "-h" ] || [ "$ACTION" = "--help" ]; then
    echo "Usage: $0 [action] [task_description]"
    echo ""
    echo "Actions:"
    echo "  submit \"task description\"    Submit a new coding task"
    echo "  list                        List all active tasks/plans"
    echo "  health                      Check server health"
    echo "  help                        Show this help message"
    echo ""
    echo "Examples:"
    echo "  $0 submit \"Create a Python function to calculate fibonacci numbers\""
    echo "  $0 list"
    echo "  $0 health"
    exit 0
fi

if [ "$ACTION" = "submit" ]; then
    if [ -z "$TASK_DESCRIPTION" ]; then
        echo "❌ Error: Task description is required for submit action"
        echo "Usage: $0 submit \"your task description here\""
        exit 1
    fi
    
    echo "Submitting task: $TASK_DESCRIPTION"
    
    # Submit the task using curl
    RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
        -H "Content-Type: application/json" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": \"task-\$(date +%s)-\$\$\",
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"accept_task\",
                \"arguments\": {
                    \"task_description\": \"$TASK_DESCRIPTION\"
                }
            }
        }")
    
    echo "Response:"
    echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
    
elif [ "$ACTION" = "list" ]; then
    echo "Listing active tasks/plans is not directly supported by the current tools."
    echo "However, you can check the server health and status:"
    echo ""
    
    # Check server health
    HEALTH_RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
        -H "Content-Type: application/json" \
        -d '{
            "jsonrpc": "2.0",
            "id": "health-check",
            "method": "tools/call",
            "params": {
                "name": "health"
            }
        }')
    
    echo "Server Health:"
    echo "$HEALTH_RESPONSE" | jq '.' 2>/dev/null || echo "$HEALTH_RESPONSE"
    
elif [ "$ACTION" = "health" ]; then
    echo "Checking server health..."
    
    HEALTH_RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
        -H "Content-Type: application/json" \
        -d '{
            "jsonrpc": "2.0",
            "id": "health-check",
            "method": "tools/call",
            "params": {
                "name": "health"
            }
        }')
    
    echo "Server Health Response:"
    echo "$HEALTH_RESPONSE" | jq '.' 2>/dev/null || echo "$HEALTH_RESPONSE"
    
else
    echo "❌ Unknown action: $ACTION"
    echo "Use '$0 help' for usage information"
    exit 1
fi

echo ""
echo "✅ Operation completed!"