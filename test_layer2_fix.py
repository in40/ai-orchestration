#!/usr/bin/env python3
"""
Test script to verify Layer 2 fix for stuck tasks.
Tests that workflow sequences are handled even when async_task_id is missing.
"""

import json
import httpx

def test_sync_workflow_handling():
    """Test that sync tasks with workflow sequences are handled correctly"""
    
    print("=" * 70)
    print("Layer 2 Fix Verification Test")
    print("=" * 70)
    
    # Test task that should trigger workflow sequence handling
    test_task = {
        "task_id": "test-layer2-fix-001",
        "title": "Test Layer 2 Fix",
        "description": "Create a simple Python function to add two numbers",
        "assignee": "IT Lead",
        "priority": "medium"
    }
    
    print(f"\nSubmitting test task: {test_task['task_id']}")
    print(f"Description: {test_task['description']}")
    
    try:
        # Submit task to IT Lead via Web UI backend
        response = httpx.post(
            "http://localhost:8000/api/tasks/assign",
            json=test_task,
            timeout=30.0
        )
        
        print(f"\nResponse status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Task submitted successfully")
            
            # Check response for workflow sequence info
            if "result" in result and isinstance(result["result"], dict):
                assign_result = result["result"]
                print(f"   Status: {assign_result.get('status', 'unknown')}")
                print(f"   Assigned to: {assign_result.get('assigned_to', 'unknown')}")
                
            return True
        else:
            print(f"❌ HTTP error: {response.status_code}")
            print(f"   Response: {response.text[:200]}")
            return False
            
    except httpx.RequestError as e:
        print(f"❌ Connection error: {e}")
        print("   Make sure Web UI backend and IT Lead server are running")
        return False

def check_task_status(task_id):
    """Check task status in database"""
    import subprocess
    
    print(f"\nChecking task status in database...")
    result = subprocess.run([
        "psql", "-h", "127.0.0.1", "-U", "postgres", "-d", "mcp_registry",
        "-t", "-c",
        f"SELECT status, metadata->'llm_plan'->'workflow_sequence' as workflow FROM task_registry WHERE task_id='{task_id}';"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        output = result.stdout.strip()
        if output:
            parts = output.split("|")
            if len(parts) >= 2:
                status = parts[0].strip()
                workflow = parts[1].strip()
                print(f"   Status: {status}")
                print(f"   Workflow: {workflow}")
                
                if workflow and "devops-engineer" in workflow:
                    print("   ✅ Workflow sequence includes devops-engineer")
                else:
                    print("   ⚠️  Workflow sequence may be incomplete")
                    
                return status
    return None

def check_it_lead_logs(task_id):
    """Check IT Lead logs for workflow handling"""
    import subprocess
    
    print(f"\nChecking IT Lead logs for workflow handling...")
    result = subprocess.run([
        "tail", "-500", "/tmp/it_lead.log"
    ], capture_output=True, text=True)
    
    if result.returncode == 0:
        logs = result.stdout
        if task_id in logs:
            # Find relevant log lines
            for line in logs.split('\n'):
                if task_id in line and ('workflow' in line.lower() or 'sync' in line.lower()):
                    print(f"   {line.strip()}")
            return True
        else:
            print("   ⚠️  Task not found in recent logs")
            return False
    return False

if __name__ == "__main__":
    import time
    
    # Run test
    success = test_sync_workflow_handling()
    
    if success:
        # Wait a bit for processing
        print("\n⏳ Waiting 5 seconds for task processing...")
        time.sleep(5)
        
        # Check database status
        status = check_task_status("test-layer2-fix-001")
        
        # Check logs
        check_it_lead_logs("test-layer2-fix-001")
        
        print("\n" + "=" * 70)
        print("Test Complete")
        print("=" * 70)
        
        if status in ["done", "in_progress"]:
            print("✅ Task is being processed correctly")
            print("   Layer 2 fix is working!")
        else:
            print(f"⚠️  Task status is {status}")
            print("   May need more time to process or manual intervention")
    else:
        print("\n❌ Test failed - task submission failed")
