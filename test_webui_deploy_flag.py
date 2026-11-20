#!/usr/bin/env python3
"""
Test Web UI deploy_after_implementation flag passthrough to rule-based routing.
This simulates what the Web UI backend sends to the IT Lead server.
"""

import json
import httpx

# Simulate Web UI task submission with deploy checkbox checked
task_data = {
    "id": "test-webui-deploy-flag-001",
    "title": "Test Game Deployment",
    "description": "Create a flappy bird game in Python",  # Will match rule-1.1 (Python implementation)
    "assignee": "IT Lead",
    "priority": "medium",
    "context": {
        "tags": ["game", "python", "web"],
        "programming_language": "Python",
        "deploy_after_implementation": True  # ← CHECKBOX CHECKED!
    }
}

# Build metadata exactly like Web UI does
base_arguments = {
    "task_id": task_data.get("id"),
    "task_description": task_data.get("description"),
    "assignee": task_data.get("assignee"),
    "priority": task_data.get("priority", "medium")
}

context = task_data.get("context", {})
if context:
    base_arguments["metadata"] = {
        "tags": context.get("tags", []),
        "programming_language": context.get("programming_language"),
        "deploy_after_implementation": context.get("deploy_after_implementation", False)
    }

print("=" * 70)
print("Web UI Task Submission Simulation")
print("=" * 70)
print(f"\nTask: {task_data['id']}")
print(f"Description: {task_data['description']}")
print(f"deploy_after_implementation: {base_arguments['metadata'].get('deploy_after_implementation')}")
print(f"\nMetadata sent to IT Lead:")
print(json.dumps(base_arguments['metadata'], indent=2))

# Submit to IT Lead
print("\n" + "=" * 70)
print("Submitting to IT Lead server...")
print("=" * 70)

try:
    response = httpx.post(
        "http://127.0.0.1:3061/mcp",
        json={
            "jsonrpc": "2.0",
            "id": task_data["id"],
            "method": "tools/call",
            "params": {
                "name": "assign_task",
                "arguments": base_arguments
            }
        },
        timeout=30.0
    )
    
    print(f"\nResponse status: {response.status_code}")
    
    if response.status_code == 200:
        result = response.json()
        print("\n✅ Task submitted successfully!")
        
        if "result" in result and isinstance(result["result"], dict):
            assign_result = result["result"]
            print(f"\nAssignment status: {assign_result.get('status', 'unknown')}")
            print(f"Assigned to: {assign_result.get('assigned_to', 'unassigned')}")
            
            # Check metadata for workflow_sequence
            if "metadata" in assign_result:
                metadata = assign_result["metadata"]
                llm_plan = metadata.get("llm_plan")
                
                if llm_plan:
                    workflow = llm_plan.get("workflow_sequence", [])
                    print(f"\n📋 Workflow sequence: {workflow}")
                    print(f"   Tools: {llm_plan.get('tools', {})}")
                    
                    if "devops-engineer" in workflow:
                        print("\n✅ SUCCESS: devops-engineer is in workflow!")
                    else:
                        print("\n❌ FAIL: devops-engineer NOT in workflow!")
                        print(f"   Expected: ['implementation-engineer', 'devops-engineer']")
                        print(f"   Got: {workflow}")
                else:
                    print("\n⚠️  No llm_plan found in metadata")
                    print(f"   metadata keys: {list(metadata.keys())}")
            else:
                print("\n⚠️  No metadata in result")
        else:
            print(f"\nUnexpected result structure: {result}")
    else:
        print(f"\n❌ HTTP error: {response.status_code}")
        print(f"Response: {response.text[:500]}")
        
except httpx.RequestError as e:
    print(f"\n❌ Connection error: {e}")
    print("Make sure IT Lead server is running on port 3061")

print("\n" + "=" * 70)
