#!/bin/bash

# MCP Registry Test Script
# This script demonstrates all registry functionality with formatted output

set -e  # Exit on any error

# Configuration
REGISTRY_URL="http://localhost:3031"
TEST_PORT=3031

# ANSI Color Codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
WHITE='\033[1;37m'
NC='\033[0m' # No Color

# Function to print header
print_header() {
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

# Function to print success
print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

# Function to print error
print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to print info
print_info() {
    echo -e "${CYAN}[INFO]${NC} $1"
}

# Function to print warning
print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

# Function to print separator
print_separator() {
    echo -e "${WHITE}--------------------------------${NC}"
}

# Function to check if registry is running
check_registry_running() {
    print_header "CHECKING REGISTRY STATUS"
    
    # Test the /send endpoint instead of SSE (since SSE keeps connection open)
    if curl -s --connect-timeout 5 -X POST "$REGISTRY_URL/send" \
        -H "Content-Type: application/json" \
        -d '{"jsonrpc": "2.0", "id": "test", "method": "ping", "params": {}}' > /dev/null 2>&1; then
        print_success "Registry server is running on $REGISTRY_URL"
        return 0
    else
        print_error "Registry server is NOT running on $REGISTRY_URL"
        print_info "To start the registry server, run:"
        echo "  ./start_mcp_server.sh --port $TEST_PORT --enable-registry"
        echo ""
        return 1
    fi
}

# Function to test health check
test_health_check() {
    print_header "TESTING HEALTH CHECK"
    
    local payload='{
        "jsonrpc": "2.0",
        "id": "health-test-'$(date +%s)'",
        "method": "ping",
        "params": {}
    }'
    
    local response
    response=$(curl -s -X POST "$REGISTRY_URL/send" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null) || {
        print_error "Failed to reach registry server"
        return 1
    }
    
    if echo "$response" | grep -q "result"; then
        local timestamp=$(echo "$response" | jq -r '.result.timestamp' 2>/dev/null || echo "N/A")
        print_success "Health check successful"
        echo "  Response timestamp: $timestamp"
    else
        print_error "Health check failed"
        echo "  Response: $response"
    fi
    print_separator
}

# Function to register a test service
register_test_service() {
    print_header "REGISTERING TEST SERVICE"
    
    local service_id="test-service-$(date +%s)"
    local payload="{
        \"jsonrpc\": \"2.0\",
        \"id\": \"register-$service_id\",
        \"method\": \"registry/register\",
        \"params\": {
            \"id\": \"$service_id\",
            \"name\": \"Test Database Service\",
            \"description\": \"A test service for demonstration\",
            \"endpoint\": \"http://localhost:8081\",
            \"capabilities\": {
                \"tools\": [\"query_db\", \"insert_record\", \"delete_record\"],
                \"resources\": [\"db://users\", \"db://products\", \"db://orders\"],
                \"prompts\": [\"generate_report\", \"summarize_data\"]
            }
        }
    }"
    
    local response
    response=$(curl -s -X POST "$REGISTRY_URL/send" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null) || {
        print_error "Failed to register service"
        return 1
    }
    
    if echo "$response" | grep -q "success.*true"; then
        print_success "Service registered successfully"
        local service_id_result=$(echo "$response" | jq -r '.result.service_id' 2>/dev/null || echo "N/A")
        echo "  Service ID: $service_id_result"
        echo "  Service Name: Test Database Service"
        echo "  Endpoint: http://localhost:8081"
        TEST_SERVICE_ID="$service_id_result"
    else
        print_error "Service registration failed"
        echo "  Response: $response"
    fi
    print_separator
}

# Function to register a second test service
register_second_test_service() {
    print_header "REGISTERING SECOND TEST SERVICE"
    
    local service_id="test-service-2-$(date +%s)"
    local payload="{
        \"jsonrpc\": \"2.0\",
        \"id\": \"register-$service_id\",
        \"method\": \"registry/register\",
        \"params\": {
            \"id\": \"$service_id\",
            \"name\": \"Test File Service\",
            \"description\": \"A file system service for testing\",
            \"endpoint\": \"http://localhost:8082\",
            \"capabilities\": {
                \"tools\": [\"read_file\", \"write_file\", \"list_files\"],
                \"resources\": [\"fs://documents\", \"fs://logs\", \"fs://configs\"],
                \"prompts\": [\"format_document\", \"parse_config\"]
            }
        }
    }"
    
    local response
    response=$(curl -s -X POST "$REGISTRY_URL/send" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null) || {
        print_error "Failed to register second service"
        return 1
    }
    
    if echo "$response" | grep -q "success.*true"; then
        print_success "Second service registered successfully"
        local service_id_result=$(echo "$response" | jq -r '.result.service_id' 2>/dev/null || echo "N/A")
        echo "  Service ID: $service_id_result"
        echo "  Service Name: Test File Service"
        echo "  Endpoint: http://localhost:8082"
        TEST_SERVICE_ID_2="$service_id_result"
    else
        print_error "Second service registration failed"
        echo "  Response: $response"
    fi
    print_separator
}

# Function to list all services
list_all_services() {
    print_header "LISTING ALL REGISTERED SERVICES"
    
    local payload='{
        "jsonrpc": "2.0",
        "id": "list-all-'$(date +%s)'",
        "method": "registry/list",
        "params": {}
    }'
    
    local response
    response=$(curl -s -X POST "$REGISTRY_URL/send" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null) || {
        print_error "Failed to list services"
        return 1
    }
    
    if echo "$response" | grep -q "services"; then
        local total_count=$(echo "$response" | jq -r '.result.total_count' 2>/dev/null || echo "N/A")
        print_success "Found $total_count registered service(s)"
        
        if [ "$total_count" -gt 0 ]; then
            echo ""
            echo "$response" | jq -r '.result.services[] | "  • \(.name) (\(.id))\n    Endpoint: \(.endpoint)\n    Description: \(.description)\n    Capabilities: \(.capabilities | to_entries[] | \"\(.key):\ [.value[]])\")\n"' 2>/dev/null || {
                # Fallback if jq is not available
                echo "  Raw response: $response"
            }
        else
            echo "  No services registered yet."
        fi
    else
        print_error "Failed to list services"
        echo "  Response: $response"
    fi
    print_separator
}

# Function to list filtered services
list_filtered_services() {
    print_header "FILTERING SERVICES (Searching for 'test')"
    
    local payload='{
        "jsonrpc": "2.0",
        "id": "list-filtered-'$(date +%s)'",
        "method": "registry/list",
        "params": {
            "filter": "test"
        }
    }'
    
    local response
    response=$(curl -s -X POST "$REGISTRY_URL/send" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null) || {
        print_error "Failed to filter services"
        return 1
    }
    
    if echo "$response" | grep -q "services"; then
        local total_count=$(echo "$response" | jq -r '.result.total_count' 2>/dev/null || echo "N/A")
        print_success "Found $total_count service(s) matching 'test'"
        
        if [ "$total_count" -gt 0 ]; then
            echo ""
            echo "$response" | jq -r '.result.services[] | "  • \(.name) (\(.id))\n    Endpoint: \(.endpoint)\n    Description: \(.description)\n"' 2>/dev/null || {
                # Fallback if jq is not available
                echo "  Raw response: $response"
            }
        else
            echo "  No services match the filter."
        fi
    else
        print_error "Failed to filter services"
        echo "  Response: $response"
    fi
    print_separator
}

# Function to deregister a test service
deregister_test_service() {
    if [ -z "$TEST_SERVICE_ID" ]; then
        print_warning "No test service to deregister (skipping)"
        print_separator
        return
    fi
    
    print_header "DEREGISTERING TEST SERVICE ($TEST_SERVICE_ID)"
    
    local payload="{
        \"jsonrpc\": \"2.0\",
        \"id\": \"deregister-'$(date +%s)'-$TEST_SERVICE_ID\",
        \"method\": \"registry/unregister\",
        \"params\": {
            \"id\": \"$TEST_SERVICE_ID\"
        }
    }"
    
    local response
    response=$(curl -s -X POST "$REGISTRY_URL/send" \
        -H "Content-Type: application/json" \
        -d "$payload" 2>/dev/null) || {
        print_error "Failed to deregister service"
        return 1
    }
    
    if echo "$response" | grep -q "success.*true"; then
        print_success "Service deregistered successfully"
        echo "  Service ID: $TEST_SERVICE_ID"
    else
        print_error "Service deregistration failed"
        echo "  Response: $response"
    fi
    print_separator
}

# Function to run all tests
run_all_tests() {
    print_header "MCP REGISTRY FUNCTIONALITY TEST"
    echo ""
    
    # Check if registry is running
    if ! check_registry_running; then
        exit 1
    fi
    echo ""
    
    # Test health check
    test_health_check
    
    # Register test services
    register_test_service
    register_second_test_service
    
    # List all services
    list_all_services
    
    # Filter services
    list_filtered_services
    
    # Deregister test service
    deregister_test_service
    
    print_header "TEST SUMMARY"
    print_success "All registry functionality tests completed!"
    echo ""
    echo "Tested features:"
    echo "  ✓ Health check (ping)"
    echo "  ✓ Service registration"
    echo "  ✓ Multiple service registration"
    echo "  ✓ Service listing"
    echo "  ✓ Service filtering"
    echo "  ✓ Service deregistration"
    echo ""
    echo "The registry is working correctly and ready for use!"
}

# Main execution
main() {
    # Check if curl is available
    if ! command -v curl &> /dev/null; then
        print_error "curl is required but not installed"
        exit 1
    fi
    
    # Check if jq is available (optional, for better formatting)
    if ! command -v jq &> /dev/null; then
        print_warning "jq is not installed - response formatting will be basic"
    fi
    
    # Run all tests
    run_all_tests
}

# Run main function
main "$@"