#!/bin/bash

# Vibe Coding AI Agent - Task Queue Manager
# Simple utility for submitting tasks and managing the queue

set -e

SERVER_URL="http://localhost:3050/mcp"
QUEUE_FILE="./task_queue.json"

# Initialize queue file
initialize_queue() {
    if [ ! -f "$QUEUE_FILE" ]; then
        echo '{"pending": [], "processing": [], "completed": []}' > "$QUEUE_FILE"
    fi
}

# Send MCP request
send_request() {
    local method=$1
    local params=$2
    local req_id=${3:-"req-$(date +%s)-$$"}
    
    curl -s -X POST "$SERVER_URL" \
        -H "Content-Type: application/json" \
        -d "{
            \"jsonrpc\": \"2.0\",
            \"id\": \"$req_id\",
            \"method\": \"tools/call\",
            \"params\": {
                \"name\": \"$method\",
                \"arguments\": $params
            }
        }"
}

# Add task to local queue
add_to_queue() {
    local task_desc=$1
    local plan_id=$2
    local timestamp=$(date -Iseconds)
    
    if command -v jq >/dev/null 2>&1; then
        jq --arg desc "$task_desc" --arg pid "$plan_id" --arg ts "$timestamp" \
           '.pending += [{"id": $pid, "description": $desc, "timestamp": $ts, "status": "pending"}]' \
           "$QUEUE_FILE" > "$QUEUE_FILE.tmp" && mv "$QUEUE_FILE.tmp" "$QUEUE_FILE"
    fi
}

# Update task status in queue
update_queue_status() {
    local plan_id=$1
    local new_status=$2
    
    if command -v jq >/dev/null 2>&1; then
        # Move from pending to appropriate status list
        jq --arg pid "$plan_id" --arg status "$new_status" '
            .pending |= map(select(.id != $pid)) |
            if $status == "processing" then
                .processing += [.pending[] | select(.id == $pid)]
            elif $status == "completed" then
                .completed += [.pending[] | select(.id == $pid)]
            elif $status == "failed" then
                .completed += ([.pending[] | select(.id == $pid)] | map(.status = "failed"))
            else
                .
            end
        ' "$QUEUE_FILE" > "$QUEUE_FILE.tmp" && mv "$QUEUE_FILE.tmp" "$QUEUE_FILE"
    fi
}

# Show queue status
show_queue() {
    if command -v jq >/dev/null 2>&1; then
        echo "📊 Task Queue Status:"
        echo "Pending: $(jq '.pending | length' "$QUEUE_FILE") tasks"
        jq -r '.pending[] | "  - \(.id): \(.description)"' "$QUEUE_FILE" 2>/dev/null || echo "  (none)"
        
        echo "Processing: $(jq '.processing | length' "$QUEUE_FILE") tasks"
        jq -r '.processing[] | "  - \(.id): \(.description)"' "$QUEUE_FILE" 2>/dev/null || echo "  (none)"
        
        echo "Completed: $(jq '.completed | length' "$QUEUE_FILE") tasks"
        jq -r '.completed[] | "  - \(.id): \(.description) [\(.status)]"' "$QUEUE_FILE" 2>/dev/null || echo "  (none)"
    else
        echo "Queue file: $QUEUE_FILE"
        cat "$QUEUE_FILE"
    fi
}

# Main script
initialize_queue

if [ ! -f "$SERVER_URL" ]; then
    # Check if server is running
    if ! curl -s "$SERVER_URL" >/dev/null 2>&1; then
        echo "❌ Error: Server not reachable at $SERVER_URL"
        echo "Start server with: ./start_server.sh"
        exit 1
    fi
fi

ACTION=${1:-"status"}
TASK_DESC=${2:-""}

case "$ACTION" in
    "submit"|"add"|"enqueue")
        if [ -z "$TASK_DESC" ]; then
            echo "❌ Usage: $0 submit \"task description\""
            exit 1
        fi
        
        echo "📥 Submitting task: $TASK_DESC"
        
        RESPONSE=$(send_request "accept_task" "{\"task_description\":\"$TASK_DESC\"}")
        
        PLAN_ID=$(echo "$RESPONSE" | jq -r '.result.plan_id // empty' 2>/dev/null)
        if [ -n "$PLAN_ID" ] && [ "$PLAN_ID" != "null" ]; then
            echo "✅ Task submitted! Plan ID: $PLAN_ID"
            add_to_queue "$TASK_DESC" "$PLAN_ID"
            echo "📋 Added to queue"
        else
            echo "⚠️  Task submitted but no plan ID returned"
            echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
        fi
        ;;
    
    "list"|"show"|"status"|"queue")
        show_queue
        ;;
    
    "check"|"get")
        if [ -z "$TASK_DESC" ]; then
            echo "❌ Usage: $0 check <plan_id>"
            exit 1
        fi
        
        PLAN_ID="$TASK_DESC"
        echo "🔍 Checking status for: $PLAN_ID"
        
        RESPONSE=$(send_request "get_plan_status" "{\"plan_id\":\"$PLAN_ID\"}")
        
        echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
        
        # Update local status
        STATUS=$(echo "$RESPONSE" | jq -r '.result.status // empty' 2>/dev/null)
        if [ -n "$STATUS" ] && [ "$STATUS" != "null" ]; then
            update_queue_status "$PLAN_ID" "$STATUS"
        fi
        ;;
    
    "health")
        echo "🏥 Server health check..."
        RESPONSE=$(send_request "health" "{}")
        echo "$RESPONSE" | jq '.' 2>/dev/null || echo "$RESPONSE"
        ;;
    
    "clear"|"reset")
        echo '{"pending": [], "processing": [], "completed": []}' > "$QUEUE_FILE"
        echo "🗑️  Queue cleared"
        ;;
    
    "help"|"-h"|"--help"|*)
        echo "Usage: $0 [action] [parameters]"
        echo ""
        echo "Actions:"
        echo "  submit \"task\"     Submit a new task to the queue"
        echo "  list | status     Show current queue status"
        echo "  check <plan_id>   Check status of specific task"
        echo "  health            Check server health"
        echo "  clear             Clear local queue tracking"
        echo "  help              Show this help"
        echo ""
        echo "Example: $0 submit \"Create a Python calculator app\""
        exit 0
        ;;
esac