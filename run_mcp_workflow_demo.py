#!/usr/bin/env python3
"""
MCP System - Task Submission and Workflow Demonstration Script

This script demonstrates the complete MCP (Model Context Protocol) system workflow
by submitting tasks to the IT Lead server and tracking their execution through
all available agents.
"""

import requests
import json
from datetime import datetime

# Configuration
BASE_URL = "http://localhost:3061"
REGISTRY_URL = "http://localhost:3031"

def make_mcp_request(method, params=None, id="demo-task"):
    """Make an MCP request to the IT Lead server"""
    headers = {"Content-Type": "application/json"}
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params or {},
        "id": id
    }
    
    try:
        response = requests.post(f"{BASE_URL}/mcp", json=payload, timeout=30)
        return {"success": True, "data": response.json()}
    except Exception as e:
        return {"success": False, "error": str(e)}

def make_registry_request(payload):
    """Make an MCP request to the registry server"""
    headers = {"Content-Type": "application/json"}
    try:
        response = requests.post(f"{REGISTRY_URL}/mcp", json=payload)
        return response.json()
    except Exception as e:
        return {"error": str(e)}

def check_registry():
    """Check what services are registered in the registry"""
    payload = {
        "jsonrpc": "2.0",
        "method": "registry/list",
        "params": {},
        "id": "check-services"
    }
    
    result = make_registry_request(payload)
    services = result.get("result", {}).get("services", [])
    
    print(f"  📋 Registered Services: {len(services)}")
    for svc in services[:5]:
        endpoint = svc.get('endpoint', 'N/A').split(':')[0].replace('/mcp', '')
        caps = svc.get('capabilities', {})
        tools = caps.get('tools', [])[:2]
        print(f"     • {svc['name'].strip()}: {' '.join(tools)}...")
    return services

def submit_task(task_id, description, assignee="requirement-engineer", priority="medium"):
    """Submit a task to IT Lead for processing"""
    params = {
        "name": "assign_task",
        "arguments": {
            "task_id": task_id,
            "task_description": description,
            "assignee": assignee,
            "priority": priority
        }
    }
    
    result = make_mcp_request("tools/call", {"name": "assign_task", "arguments": {
        "task_id": task_id, "task_description": description, 
        "assignee": assignee, "priority": priority}}, f"submit-{task_id}")
    
    if result["success"]:
        task_result = result["data"].get("result", {})
        print(f"     ✅ Task '{task_id}' submitted - Status: {task_result.get('status', 'N/A')}")
        return task_result
    else:
        print(f"     ❌ Failed to submit task: {result.get('error', 'Unknown error')}")
        return None

def analyze_architecture(architecture, requirements):
    """Analyze system architecture with IT Lead"""
    params = {
        "name": "analyze_architecture",
        "arguments": {
            "current_architecture": architecture,
            "requirements": requirements
        }
    }
    
    result = make_mcp_request("tools/call", {"name": "analyze_architecture", "arguments": {
        "current_architecture": architecture, "requirements": requirements}}, "arch-analysis")
    
    if result["success"]:
        analysis = result["data"].get("result", {}).get("result", {})
        return analysis
    else:
        print(f"Error analyzing architecture: {result.get('error', 'Unknown')}")
        return None

def list_services():
    """List all services in the registry"""
    payload = {"jsonrpc": "2.0", "method": "registry/list", "params": {}, "id": "list-all"}
    
    result = make_registry_request(payload)
    services = result.get("result", {}).get("services", [])
    
    print("\n" + "="*70)
    print("SERVICES REGISTERED IN REGISTRY")
    print("="*70)
    
    for svc in sorted(services, key=lambda x: x['name']):
        endpoint = svc.get('endpoint', 'N/A').split(':')[0].replace('/mcp', '')
        caps = svc.get('capabilities', {})
        tools = caps.get('tools', [])[:2]
        print(f"  {svc['name'].strip():35s} | {endpoint:40s}")
    print("="*70)

def run_workflow_demo():
    """Run a complete workflow demonstration"""
    
    print("\n" + "="*70)
    print("MCP SYSTEM - WORKFLOW DEMONSTRATION")
    print("="*70)
    print(f"\nTimestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Registry URL: {REGISTRY_URL}")
    print(f"Server URL:  {BASE_URL}")
    
    # Check registry
    check_registry()
    list_services()
    
    # Demo 1: Architecture analysis
    print("\n" + "-"*70)
    print("DEMO 1: Architecture Analysis")
    print("-"*70)
    result = analyze_architecture(
        "Monolithic Python Flask application",
        "Add CI/CD pipeline with GitHub Actions"
    )
    
    # Demo 2: Submit tasks for different scenarios
    print("\n" + "-"*70)
    print("DEMO 2: Task Submission Workflow")
    print("-"*70)
    
    task_ids = []
    
    # Scenario 1: Requirements gathering
    task_id_1 = "demo-task-req-001"
    task_desc_1 = """
Analyze requirements for an e-commerce platform that needs:
- User authentication and authorization
- Product catalog management
- Shopping cart functionality  
- Payment processing integration
- Order tracking system

The platform should support 10K+ daily active users with potential for 1M+ monthly active users.
"""
    
    print(f"\n📝 Submit requirements analysis: {task_id_1}")
    result = submit_task(task_id_1, task_desc_1, assignee="requirement-engineer", priority="high")
    if result:
        task_ids.append(("Requirements Analysis", task_id_1))
    
    # Scenario 2: Implementation task
    task_id_2 = "demo-task-impl-001"
    task_desc_2 = """
Create a microservice for user authentication that:
- Uses JWT tokens for session management
- Implements rate limiting (100 req/min per IP)
- Integrates with PostgreSQL database
- Provides REST API endpoints

Requires Docker containerization and Kubernetes deployment manifests.
"""
    
    print(f"📝 Submitting implementation task: {task_id_2}")
    result = submit_task(task_id_2, task_desc_2, assignee="requirement-engineer", priority="high")
    if result:
        task_ids.append(("Implementation Task", task_id_2))
    
    # Scenario 3: Project planning
    task_id_3 = "demo-task-plan-001"
    task_desc_3 = """
Create a project plan for building a scalable API gateway that:
- Handles 10K+ RPM with sub-millisecond latency
- Implements rate limiting, authentication, and logging
- Supports gRPC and REST endpoints
- Deploys to Kubernetes cluster

Timeline: 8 weeks
Team: 5 engineers (2 backend, 2 DevOps, 1 QA)
"""
    
    print(f"📝 Submitting project planning task: {task_id_3}")
    result = submit_task(task_id_3, task_desc_3, assignee="requirement-engineer", priority="medium")
    if result:
        task_ids.append(("Project Planning", task_id_3))
    
    # Summary
    print("\n" + "="*70)
    print("WORKFLOW DEMONSTRATION COMPLETE")
    print("="*70)
    print(f"\n📋 Submitted {len(task_ids)} tasks:")
    for name, task_id in task_ids:
        print(f"   • {task_id}")
    
    print("\n🔍 Check registry at", REGISTRY_URL)
    print("📄 View logs: /tmp/mcp_registry.log")
    print()

if __name__ == "__main__":
    run_workflow_demo()
