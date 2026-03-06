#!/bin/bash

# DevOps Release Engineer MCP Server Simulation Test
# Tests the DevOps Release Engineer server functionality by simulating an AI agent interacting with it

set +e  # Don't exit on error - we want to run all tests and report results

echo "=========================================="
echo "DevOps Release Engineer MCP Server Simulation Test"
echo "=========================================="

# Configuration
SERVER_URL="http://localhost:3071"
TESTS_PASSED=0
TESTS_FAILED=0

# Function to run a test
run_test() {
    local test_name="$1"
    local test_description="$2"
    local endpoint="$3"
    local request_body="$4"
    local expected_pattern="$5"
    
    echo ""
    echo "Test: $test_name"
    echo "Description: $test_description"
    
    response=$(curl -s -X POST "$SERVER_URL$endpoint" \
        -H "Content-Type: application/json" \
        -d "$request_body" 2>/dev/null)
    
    if echo "$response" | grep -q "$expected_pattern"; then
        echo "✓ PASSED"
        echo "Response: $response"
        ((TESTS_PASSED++))
    else
        echo "✗ FAILED"
        echo "Response: $response"
        echo "Expected pattern: $expected_pattern"
        ((TESTS_FAILED++))
    fi
}

# Test 1: Initialize connection
run_test \
    "Initialize" \
    "Test server initialization" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {"clientInfo": {"name": "test-agent", "version": "1.0.0"}}}' \
    "serverInfo"

# Test 2: Health check
run_test \
    "Health Check (ping)" \
    "Test server health check endpoint" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "2", "method": "ping", "params": {}}' \
    "healthy"

# Test 3: List tools
run_test \
    "List Tools" \
    "Test listing available tools" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "3", "method": "tools/list", "params": {}}' \
    "git_commit_and_push"

# Test 4: List resources
run_test \
    "List Resources" \
    "Test listing available resources" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "4", "method": "resources/list", "params": {}}' \
    "deployment-status"

# Test 5: List prompts
run_test \
    "List Prompts" \
    "Test listing available prompts" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "5", "method": "prompts/list", "params": {}}' \
    "deployment_prompt"

# Test 6: Get resource
run_test \
    "Read Resource" \
    "Test reading deployment status resource" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "6", "method": "resources/read", "params": {"uri": "devops://resource/deployment-status"}}' \
    "contents"

# Test 7: Get prompt
run_test \
    "Get Prompt" \
    "Test getting a specific prompt" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "7", "method": "prompts/get", "params": {"name": "deployment_prompt", "arguments": {"application_name": "myapp", "target_environment": "production", "deployment_strategy": "blue-green"}}}' \
    "contents"

# Test 8: Test git_commit_and_push tool
run_test \
    "Git Commit and Push Tool" \
    "Test the git_commit_and_push tool" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "8", "method": "tools/call", "params": {"name": "git_commit_and_push", "arguments": {"repository_path": "/tmp/test-repo", "files_to_commit": ["file1.txt", "file2.txt"], "commit_message": "Add new features"}}}' \
    "result"

# Test 9: Test configure_ci_cd_pipeline tool
run_test \
    "Configure CI/CD Pipeline Tool" \
    "Test the configure_ci_cd_pipeline tool" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "9", "method": "tools/call", "params": {"name": "configure_ci_cd_pipeline", "arguments": {"source_repository": "https://github.com/example/app", "target_platform": "github", "build_requirements": ["npm install", "npm test"], "deployment_targets": ["staging", "production"]}}}' \
    "result"

# Test 10: Test orchestrate_deployments tool
run_test \
    "Orchestrate Deployments Tool" \
    "Test the orchestrate_deployments tool" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "10", "method": "tools/call", "params": {"name": "orchestrate_deployments", "arguments": {"application_artifacts": "myapp:latest", "target_environments": ["staging", "production"], "deployment_strategy": "blue-green", "rollback_procedures": {"staging": "docker-compose down", "production": "docker-compose down"}}}}' \
    "result"

# Test 11: Test monitor_deployment_health tool
run_test \
    "Monitor Deployment Health Tool" \
    "Test the monitor_deployment_health tool" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "11", "method": "tools/call", "params": {"name": "monitor_deployment_health", "arguments": {"deployed_application": "myapp", "target_environment": "production", "health_metrics": ["cpu_usage", "memory_usage", "request_rate", "error_rate"], "failure_thresholds": {"cpu_usage": 90, "error_rate": 5}}}}' \
    "result"

# Test 12: Test manage_infrastructure_provisioning tool
run_test \
    "Manage Infrastructure Provisioning Tool" \
    "Test the manage_infrastructure_provisioning tool" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "12", "method": "tools/call", "params": {"name": "manage_infrastructure_provisioning", "arguments": {"infrastructure_requirements": [{"type": "ec2", "count": 3, "instance_type": "t3.medium"}], "target_platform": "aws", "iac_tool": "terraform"}}}' \
    "result"

# Test 13: Test optimize_build_processes tool
run_test \
    "Optimize Build Processes Tool" \
    "Test the optimize_build_processes tool" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "13", "method": "tools/call", "params": {"name": "optimize_build_processes", "arguments": {"build_configuration": "webpack", "build_metrics": {"avg_time": 300, "failures": 5}, "optimization_goals": ["speed", "reliability"]}}}' \
    "result"

# Test 14: Test generate_terraform_config tool
run_test \
    "Generate Terraform Config Tool" \
    "Test the generate_terraform_config tool" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "14", "method": "tools/call", "params": {"name": "generate_terraform_config", "arguments": {"resource_type": "aws_instance", "resource_config": {"ami": "ami-12345", "instance_type": "t3.medium"}, "output_file": "main.tf"}}}' \
    "result"

# Test 15: Test generate_pipeline_config tool
run_test \
    "Generate Pipeline Config Tool" \
    "Test the generate_pipeline_config tool" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "15", "method": "tools/call", "params": {"name": "generate_pipeline_config", "arguments": {"platform": "github", "stages": ["build", "test", "deploy"], "trigger_branch": "main", "docker_image": "node:18", "test_command": "npm test"}}}' \
    "result"

# Test 16: Test shutdown
run_test \
    "Shutdown" \
    "Test server shutdown" \
    "/mcp" \
    '{"jsonrpc": "2.0", "id": "16", "method": "shutdown", "params": {}}' \
    "result"

echo ""
echo "=========================================="
echo "Test Results Summary"
echo "=========================================="
echo "Tests Passed: $TESTS_PASSED"
echo "Tests Failed: $TESTS_FAILED"
echo "Total Tests: $((TESTS_PASSED + TESTS_FAILED))"
echo "=========================================="

if [ $TESTS_FAILED -gt 0 ]; then
    echo "Some tests failed!"
    exit 1
else
    echo "All tests passed!"
    exit 0
fi
