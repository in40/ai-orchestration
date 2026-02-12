#!/bin/bash

# Vibe Coding AI Agent - Advanced Task Management Utility
# Allows submitting tasks, managing queues, and tracking completion

set -e

SERVER_URL="http://localhost:3050/mcp"
TASK_STORAGE_FILE="./task_storage.json"

echo "=== Vibe Coding AI Agent - Advanced Task Manager ==="

# Initialize task storage if it doesn't exist
if [ ! -f "$TASK_STORAGE_FILE" ]; then
    echo "{}" > "$TASK_STORAGE_FILE"
fi

# Function to send MCP request
send_mcp_request() {
    local method=$1
    local params=$2
    local id=${3:-"task-$(date +%s)-$$"}
    
    curl -s -X POST "$SERVER_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": \"$id\",
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"$method\",
                \"arguments\": $params
            }
        }"
}

# Function to save task info locally
save_task_info() {
    local plan_id=$1
    local task_desc=$2
    local status=${3:-"submitted"}
    local timestamp=$(date -Iseconds)
    
    # Use jq to update the JSON file
    if command -v jq >/dev/null 2>&1; then
        jq --arg pid "$plan_id" --arg desc "$task_desc" --arg stat "$status" --arg ts "$timestamp" \
           '.[$pid] = {"description": $desc, "status": $stat, "timestamp": $ts}' \
           "$TASK_STORAGE_FILE" > "$TASK_STORAGE_FILE.tmp" && mv "$TASK_STORAGE_FILE.tmp" "$TASK_STORAGE_FILE"
    else
        echo "Warning: jq not found, task tracking will be limited"
    fi
}

# Function to list tasks
list_tasks() {
    if command -v jq >/dev/null 2>&1; then
        if [ -s "$TASK_STORAGE_FILE" ] && [ "$(cat "$TASK_STORAGE_FILE" | tr -d ' \t\n\r')" != "{}" ]; then
            echo "Tracked Tasks:"
            jq -r 'to_entries[] | "ID: \(.key) | Description: \(.value.description) | Status: \(.value.status) | Time: \(.value.timestamp)"' "$TASK_STORAGE_FILE"
        else
            echo "No tracked tasks found."
        fi
    else
        echo "Task storage file: $TASK_STORAGE_FILE"
        cat "$TASK_STORAGE_FILE"
    fi
}

# Function to update task status
update_task_status() {
    local plan_id=$1
    local status=$2
    
    if command -v jq >/dev/null 2>&1; then
        if [ -f "$TASK_STORAGE_FILE" ] && jq empty "$TASK_STORAGE_FILE" 2>/dev/null; then
            jq --arg pid "$plan_id" --arg stat "$status" \
               'if has($pid) then .[$pid].status = $stat else . end' \
               "$TASK_STORAGE_FILE" > "$TASK_STORAGE_FILE.tmp" && mv "$TASK_STORAGE_FILE.tmp" "$TASK_STORAGE_FILE"
        fi
    fi
}

# Check if server is running
if ! curl -s "$SERVER_URL" >/dev/null 2>&1; then
    echo "❌ Error: Vibe Coding AI Agent server not reachable at $SERVER_URL"
    echo "Please start the server first using: ./start_server.sh"
    exit 1
fi

# Parse command line arguments
ACTION=${1:-"help"}
TASK_DESCRIPTION=${2:-""}
PLAN_ID=${2:-""}

case "$ACTION" in
    "submit"|"create")
        if [ -z "$TASK_DESCRIPTION" ]; then
            echo "❌ Error: Task description is required for submit action"
            echo "Usage: $0 submit \"your task description here\""
            exit 1
        fi
        
        echo "Submitting task: $TASK_DESCRIPTION"
        
        # Submit the task
        RESPONSE=$(send_mcp_request "accept_task" "{\"task_description\":\"$TASK_DESCRIPTION\"}")
        
        # Extract plan ID if available
        if command -v jq >/dev/null 2>&1; then
            PLAN_ID=$(echo "$RESPONSE" | jq -r '.result.plan_id // empty' 2>/dev/null)
            if [ -n "$PLAN_ID" ] && [ "$PLAN_ID" != "null" ]; then
                echo "✅ Task submitted successfully!"
                echo "📋 Plan ID: $PLAN_ID"
                save_task_info "$PLAN_ID" "$TASK_DESCRIPTION" "submitted"
                
                # Show the response
                echo "Response:"
                echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
            else
                echo "⚠️  Task submitted but could not extract plan ID"
                echo "Response:"
                echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
            fi
        else
            echo "Response:"
            echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
        fi
        ;;
    
    "list"|"queue"|"status")
        echo "📋 Listing all tracked tasks:"
        list_tasks
        
        echo ""
        echo "💡 Note: Real-time queue status depends on the agent's internal state."
        echo "   You can check individual plan status using: $0 check <plan_id>"
        ;;
    
    "check"|"get"|"status-of")
        if [ -z "$PLAN_ID" ]; then
            echo "❌ Error: Plan ID is required for check action"
            echo "Usage: $0 check <plan_id>"
            exit 1
        fi
        
        echo "Checking status for plan: $PLAN_ID"
        
        RESPONSE=$(send_mcp_request "get_plan_status" "{\"plan_id\":\"$PLAN_ID\"}")
        
        echo "Status Response:"
        echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
        
        # Update local status if possible
        if command -v jq >/dev/null 2>&1; then
            NEW_STATUS=$(echo "$RESPONSE" | jq -r '.result.status // empty' 2>/dev/null)
            if [ -n "$NEW_STATUS" ] && [ "$NEW_STATUS" != "null" ]; then
                update_task_status "$PLAN_ID" "$NEW_STATUS"
            fi
        fi
        ;;
    
    "health"|"server-status")
        echo "🏥 Checking server health..."
        
        RESPONSE=$(send_mcp_request "health" "{}")
        
        echo "Server Health Response:"
        echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
        ;;
    
    "analyze"|"code-analyze")
        if [ -z "$TASK_DESCRIPTION" ]; then
            echo "❌ Error: Code analysis requires a description or code snippet"
            echo "Usage: $0 analyze \"code to analyze\""
            exit 1
        fi
        
        echo "Analyzing code: $TASK_DESCRIPTION"
        
        RESPONSE=$(send_mcp_request "analyze_code" "{\"analysis_type\":\"bugs\", \"code_snippet\":\"$TASK_DESCRIPTION\"}")
        
        echo "Analysis Response:"
        echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
        ;;
    
    "generate"|"code-generate")
        if [ -z "$TASK_DESCRIPTION" ]; then
            echo "❌ Error: Code generation requires a specification"
            echo "Usage: $0 generate \"code specification\""
            exit 1
        fi
        
        echo "Generating code for: $TASK_DESCRIPTION"
        
        RESPONSE=$(send_mcp_request "generate_code" "{\"specification\":\"$TASK_DESCRIPTION\"}")
        
        echo "Generation Response:"
        echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
        ;;
    
    "help"|"-h"|"--help"|*)
        echo "Usage: $0 [action] [parameters]"
        echo ""
        echo "Actions:"
        echo "  submit \"task\" | create \"task\"    Submit a new coding task"
        echo "  list | queue | status             List all tracked tasks"
        echo "  check <plan_id> | get <plan_id>   Check status of specific task"
        echo "  health | server-status            Check server health"
        echo "  analyze \"code\"                    Analyze code for issues"
        echo "  generate \"spec\"                   Generate code from specification"
        echo "  help                              Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 submit \"Create a Python function to sort arrays\""
        echo "  $0 list"
        echo "  $0 check plan_a1b2c3d4"
        echo "  $0 health"
        echo "  $0 analyze \"def bad_func(x): return x/0\""
        echo "  $0 generate \"Create a React component for a counter\""
        exit 0
        ;;
esac

echo ""
echo "✅ Operation completed!"