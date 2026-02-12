#!/bin/bash
# AI Agent Simulation Test for DNS Resolving MCP Server
# This script simulates how an AI agent would interact with the DNS server

set -e  # Exit on any error

echo "🧪 Starting AI Agent Simulation Test for DNS Resolving MCP Server..."

# Configuration
SERVER_URL="http://localhost:3040"  # DNS server runs on port 3040
TEST_ID="dns-agent-test-$(date +%s)"

echo "Test ID: $TEST_ID"
echo "----------------------------------------"

# Function to send JSON-RPC request and capture response
send_request() {
    local method=$1
    local params=$2
    local request_id=${3:-$(date +%s)}
    
    local payload="{\"jsonrpc\": \"2.0\", \"id\": \"$request_id\", \"method\": \"$method\", \"params\": $params}"
    
    # Send request and capture the response ID
    echo "Sending: $payload"
    curl -s -X POST "$SERVER_URL/send" \
         -H "Content-Type: application/json" \
         -d "$payload" \
         --connect-timeout 5 \
         --max-time 10
    
    echo ""
}

# Function to start SSE listener in background
start_sse_listener() {
    local sse_output_file="sse_output_${TEST_ID}.txt"
    echo "Starting SSE listener, output to: $sse_output_file"
    
    # Start SSE listener in background
    curl -N -s "$SERVER_URL/sse" --connect-timeout 5 > "$sse_output_file" &
    SSE_PID=$!
    
    # Give it a moment to establish connection
    sleep 2
    
    echo $SSE_PID
}

# Function to stop SSE listener
stop_sse_listener() {
    local pid=$1
    if kill -0 $pid 2>/dev/null; then
        kill $pid
        echo "SSE listener stopped (PID: $pid)"
    fi
}

# Start SSE listener to capture responses
SSE_PID=$(start_sse_listener)

# Test 1: Initialize connection
echo "📋 Test 1: Initializing connection to DNS server"
send_request "initialize" "{\"clientInfo\": {\"name\": \"dns-agent-simulation\", \"version\": \"1.0\"}}" "${TEST_ID}_init"
sleep 2

# Test 2: List available DNS tools
echo "🔍 Test 2: Listing available DNS tools"
send_request "tools/list" "{}" "${TEST_ID}_tools"
sleep 2

# Test 3: Resolve a domain (A record)
echo "🌐 Test 3: Resolving A record for google.com"
send_request "tools/call" "{\"name\": \"dns_resolve\", \"arguments\": {\"domain\": \"google.com\", \"record_type\": \"A\"}}" "${TEST_ID}_resolve_a"
sleep 3

# Test 4: Resolve a domain (MX record)
echo "📧 Test 4: Resolving MX record for google.com"
send_request "tools/call" "{\"name\": \"dns_resolve\", \"arguments\": {\"domain\": \"google.com\", \"record_type\": \"MX\"}}" "${TEST_ID}_resolve_mx"
sleep 3

# Test 5: Reverse DNS lookup
echo "🔍 Test 5: Performing reverse DNS lookup for 8.8.8.8"
send_request "tools/call" "{\"name\": \"dns_reverse_lookup\", \"arguments\": {\"ip_address\": \"8.8.8.8\"}}" "${TEST_ID}_reverse"
sleep 3

# Test 6: Check domain availability
echo "📋 Test 6: Checking domain availability for non-existent-domain-$TEST_ID.com"
send_request "tools/call" "{\"name\": \"dns_check_domain_availability\", \"arguments\": {\"domain\": \"non-existent-domain-$TEST_ID.com\"}}" "${TEST_ID}_availability"
sleep 3

# Test 7: Health check
echo "🩺 Test 7: Performing health check"
send_request "ping" "{}" "${TEST_ID}_health"
sleep 2

# Test 8: List resources
echo "📚 Test 8: Listing available resources"
send_request "resources/list" "{}" "${TEST_ID}_resources"
sleep 2

# Test 9: Read DNS configuration resource
echo "⚙️ Test 9: Reading DNS configuration resource"
send_request "tools/call" "{\"name\": \"dns_resolve\", \"arguments\": {\"domain\": \"google.com\", \"record_type\": \"A\"}}" "${TEST_ID}_config"
sleep 2

# Wait a bit more to capture all responses
sleep 5

# Stop SSE listener
stop_sse_listener $SSE_PID

# Check SSE output for expected responses
SSE_OUTPUT_FILE="sse_output_${TEST_ID}.txt"
echo "----------------------------------------"
echo "📊 SSE Response Summary:"
if [ -f "$SSE_OUTPUT_FILE" ]; then
    cat "$SSE_OUTPUT_FILE" | grep -v "^: " | grep -v "^$" | head -20
    echo "..."
    echo "(See full output in $SSE_OUTPUT_FILE)"
else
    echo "❌ SSE output file not found: $SSE_OUTPUT_FILE"
fi

# Verify that we got responses for our key requests
echo "----------------------------------------"
echo "✅ Verification Results:"

KEY_RESPONSES=("resolve_a" "reverse" "availability")
for resp in "${KEY_RESPONSES[@]}"; do
    if grep -q "$resp" "$SSE_OUTPUT_FILE" 2>/dev/null; then
        echo "  ✓ Found response for $resp request"
    else
        echo "  ❌ Missing response for $resp request"
    fi
done

# Check if DNS resolution worked by looking for IP addresses in responses
if grep -qE '\b([0-9]{1,3}\.){3}[0-9]{1,3}\b' "$SSE_OUTPUT_FILE" 2>/dev/null; then
    echo "  ✓ Found IP addresses in responses (DNS resolution working)"
else
    echo "  ⚠️  No IP addresses found in responses"
fi

echo "----------------------------------------"
echo "🧪 AI Agent Simulation Test Completed!"
echo "Test ID: $TEST_ID"
echo "Results stored in: $SSE_OUTPUT_FILE"

# Clean up
rm -f "sse_output_${TEST_ID}.txt" 2>/dev/null || true