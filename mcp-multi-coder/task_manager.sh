#!/bin/bash

# Vibe Coding AI Agent - Complete Task Management Suite
# Full utility for submitting tasks, managing queues, and tracking completion

set -e

SERVER_URL="http://localhost:3050/mcp"
TASK_STORAGE_FILE="./tasks.json"
LOG_FILE="./task_operations.log"

# Initialize storage files
initialize_storage() {
    if [ ! -f "$TASK_STORAGE_FILE" ]; then
        echo '{"tasks": {}, "queue": [], "completed": [], "failed": []}' > "$TASK_STORAGE_FILE"
    fi
    touch "$LOG_FILE"
}

# Log function
log() {
    echo "[$(date -Iseconds)] $*" >> "$LOG_FILE"
    echo "📝 $*"
}

# Function to send MCP request
send_mcp_request() {
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

# Function to save task to local storage
save_task() {
    local plan_id=$1
    local task_desc=$2
    local status=${3:-"pending"}
    local timestamp=$(date -Iseconds)
    
    if command -v jq >/dev/null 2>&1; then
        jq --arg pid "$plan_id" --arg desc "$task_desc" --arg stat "$status" --arg ts "$timestamp" \
           '.tasks[$pid] = {"description": $desc, "status": $stat, "timestamp": $ts}' \
           "$TASK_STORAGE_FILE" > "$TASK_STORAGE_FILE.tmp" && mv "$TASK_STORAGE_FILE.tmp" "$TASK_STORAGE_FILE"
        
        # Add to appropriate queue
        if [ "$status" = "pending" ]; then
            jq --arg pid "$plan_id" '.queue += [$pid]' "$TASK_STORAGE_FILE" > "$TASK_STORAGE_FILE.tmp" && mv "$TASK_STORAGE_FILE.tmp" "$TASK_STORAGE_FILE"
        fi
    fi
}

# Function to update task status
update_task_status() {
    local plan_id=$1
    local status=$2
    local timestamp=$(date -Iseconds)
    
    if command -v jq >/dev/null 2>&1; then
        # Update task status
        jq --arg pid "$plan_id" --arg stat "$status" --arg ts "$timestamp" \
           'if .tasks[$pid] then .tasks[$pid].status = $stat | .tasks[$pid].updated = $ts else . end' \
           "$TASK_STORAGE_FILE" > "$TASK_STORAGE_FILE.tmp" && mv "$TASK_STORAGE_FILE.tmp" "$TASK_STORAGE_FILE"
        
        # Move from queue to appropriate list
        if [ "$status" = "completed" ]; then
            jq --arg pid "$plan_id" '.queue -= [$pid] | .completed += [$pid]' "$TASK_STORAGE_FILE" > "$TASK_STORAGE_FILE.tmp" && mv "$TASK_STORAGE_FILE.tmp" "$TASK_STORAGE_FILE"
        elif [ "$status" = "failed" ]; then
            jq --arg pid "$plan_id" '.queue -= [$pid] | .failed += [$pid]' "$TASK_STORAGE_FILE" > "$TASK_STORAGE_FILE.tmp" && mv "$TASK_STORAGE_FILE.tmp" "$TASK_STORAGE_FILE"
        fi
    fi
}

# Function to show queue status
show_queue_status() {
    if command -v jq >/dev/null 2>&1; then
        echo "📊 QUEUE STATUS"
        echo "============="
        echo "Pending Tasks: $(jq '.queue | length' "$TASK_STORAGE_FILE")"
        jq -r '.queue[] as $id | .tasks[$id] | "  • \($id): \(.description) (\(.status))"' "$TASK_STORAGE_FILE" 2>/dev/null || echo "  (none)"
        
        echo ""
        echo "Completed Tasks: $(jq '.completed | length' "$TASK_STORAGE_FILE")"
        jq -r '.completed[] as $id | .tasks[$id] | "  • \($id): \(.description)"' "$TASK_STORAGE_FILE" 2>/dev/null || echo "  (none)"
        
        echo ""
        echo "Failed Tasks: $(jq '.failed | length' "$TASK_STORAGE_FILE")"
        jq -r '.failed[] as $id | .tasks[$id] | "  • \($id): \(.description)"' "$TASK_STORAGE_FILE" 2>/dev/null || echo "  (none)"
    else
        echo "Task storage file: $TASK_STORAGE_FILE"
        cat "$TASK_STORAGE_FILE"
    fi
}

# Function to submit a new task
submit_task() {
    local task_desc=$1
    log "Submitting task: $task_desc"
    
    # Check if server is reachable
    if ! curl -s "$SERVER_URL" >/dev/null 2>&1; then
        log "❌ Server not reachable at $SERVER_URL"
        log "Please start the server with: ./start_server.sh"
        exit 1
    fi
    
    # Submit the task
    local response
    response=$(send_mcp_request "accept_task" "{\"task_description\":\"$task_desc\"}")
    
    log "Server Response:"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
    
    # Extract plan ID and save task
    if command -v jq >/dev/null 2>&1; then
        local plan_id
        plan_id=$(echo "$response" | jq -r '.result.plan_id // empty' 2>/dev/null)
        if [ -n "$plan_id" ] && [ "$plan_id" != "null" ]; then
            log "✅ Task submitted successfully! Plan ID: $plan_id"
            save_task "$plan_id" "$task_desc" "pending"
        else
            log "⚠️  Task submitted but could not extract plan ID"
        fi
    fi
}

# Function to check task status
check_task_status() {
    local plan_id=$1
    log "Checking status for plan: $plan_id"
    
    local response
    response=$(send_mcp_request "get_plan_status" "{\"plan_id\":\"$plan_id\"}")
    
    log "Status Response:"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
    
    # Update local status
    if command -v jq >/dev/null 2>&1; then
        local status
        status=$(echo "$response" | jq -r '.result.status // empty' 2>/dev/null)
        if [ -n "$status" ] && [ "$status" != "null" ]; then
            update_task_status "$plan_id" "$status"
        fi
    fi
}

# Function to check server health
check_health() {
    log "🏥 Checking server health..."
    
    local response
    response=$(send_mcp_request "health" "{}")
    
    log "Health Response:"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
}

# Function to analyze code
analyze_code() {
    local code=$1
    log "🔍 Analyzing code: ${code:0:50}..."
    
    local response
    response=$(send_mcp_request "analyze_code" "{\"analysis_type\":\"bugs\", \"code_snippet\":\"$code\"}")
    
    log "Analysis Response:"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
}

# Function to generate code
generate_code() {
    local spec=$1
    log "⚡ Generating code for: $spec"
    
    local response
    response=$(send_mcp_request "generate_code" "{\"specification\":\"$spec\"}")
    
    log "Generation Response:"
    echo "$response" | jq '.' 2>/dev/null || echo "$response"
}

# Main execution
initialize_storage

ACTION=${1:-"help"}
PARAM1=${2:-""}
PARAM2=${3:-""}

case "$ACTION" in
    "submit"|"create"|"add")
        if [ -z "$PARAM1" ]; then
            log "❌ Usage: $0 submit \"task description\""
            exit 1
        fi
        submit_task "$PARAM1"
        ;;
    
    "list"|"queue"|"status"|"show")
        show_queue_status
        ;;
    
    "check"|"get"|"status-of")
        if [ -z "$PARAM1" ]; then
            log "❌ Usage: $0 check <plan_id>"
            exit 1
        fi
        check_task_status "$PARAM1"
        ;;
    
    "health"|"server-status")
        check_health
        ;;
    
    "analyze"|"code-analyze")
        if [ -z "$PARAM1" ]; then
            log "❌ Usage: $0 analyze \"code to analyze\""
            exit 1
        fi
        analyze_code "$PARAM1"
        ;;
    
    "generate"|"code-generate")
        if [ -z "$PARAM1" ]; then
            log "❌ Usage: $0 generate \"code specification\""
            exit 1
        fi
        generate_code "$PARAM1"
        ;;
    
    "clear"|"reset")
        echo '{"tasks": {}, "queue": [], "completed": [], "failed": []}' > "$TASK_STORAGE_FILE"
        log "🗑️  Task storage cleared"
        ;;
    
    "logs"|"log")
        log "📋 Recent logs:"
        tail -20 "$LOG_FILE"
        ;;
    
    "help"|"-h"|"--help"|*)
        echo "🚀 Vibe Coding AI Agent - Task Management Suite"
        echo ""
        echo "Usage: $0 [action] [parameters]"
        echo ""
        echo "Task Management:"
        echo "  submit \"task\" | create \"task\"    Submit a new coding task"
        echo "  list | queue | status             Show queue status"
        echo "  check <plan_id> | get <plan_id>   Check specific task status"
        echo "  clear | reset                     Clear local task storage"
        echo ""
        echo "Development Tools:"
        echo "  health | server-status            Check server health"
        echo "  analyze \"code\"                    Analyze code for issues"
        echo "  generate \"spec\"                   Generate code from spec"
        echo ""
        echo "Utilities:"
        echo "  logs                              Show recent operation logs"
        echo "  help                              Show this help message"
        echo ""
        echo "Examples:"
        echo "  $0 submit \"Create a Python function to calculate fibonacci numbers\""
        echo "  $0 list"
        echo "  $0 check plan_a1b2c3d4"
        echo "  $0 analyze \"def bad_func(x): return x/0\""
        echo "  $0 generate \"Create a React component for a counter\""
        echo "  $0 health"
        exit 0
        ;;
esac

log "✅ Operation completed!"