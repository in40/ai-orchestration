#!/usr/bin/env python3
"""
Submit test tasks to IT Lead Web UI API for testing code extraction fix.

This script submits 3 variations of "Create a Flappy Bird game in HTML" 
to test that the code is properly cleaned and stored.
"""

import httpx
import json
import sys
import uuid
from datetime import datetime

# Configuration
WEB_UI_BACKEND_URL = "http://127.0.0.1:8000"
IT_LEAD_URL = "http://127.0.0.1:3061/mcp"

# Test task variations
TEST_TASKS = [
    {
        "title": "Flappy Bird Clone - Classic HTML5 Game",
        "description": "Create a Flappy Bird game in HTML with canvas. The bird should jump when clicking/tapping, pipes should move from right to left, and there should be collision detection. Include score tracking and a game over screen.",
        "priority": "high",
        "context": {
            "tags": ["html", "javascript", "game", "canvas"],
            "programming_language": "HTML/JavaScript",
            "framework": "Vanilla JS"
        }
    },
    {
        "title": "Flappy Bird with Enhanced Graphics",
        "description": "Create a Flappy Bird game in HTML with colorful graphics. Add background images, animated bird sprite, rotating pipes, and particle effects when the bird jumps. Make it visually appealing with smooth animations.",
        "priority": "medium",
        "context": {
            "tags": ["html", "javascript", "game", "animation"],
            "programming_language": "HTML/JavaScript",
            "framework": "Canvas API"
        }
    },
    {
        "title": "Flappy Bird with Power-ups",
        "description": "Create an enhanced Flappy Bird game in HTML with power-up features. Add special items like: shield (protects from one collision), speed boost (slows down time), and magnet (attracts nearby points). Display power-up status in UI.",
        "priority": "high",
        "context": {
            "tags": ["html", "javascript", "game", "powerups"],
            "programming_language": "HTML/JavaScript",
            "framework": "Vanilla JS"
        }
    },
    {
        "title": "Flappy Bird with Multiple Levels",
        "description": "Create a Flappy Bird game in HTML with progressive difficulty. Implement 3 levels: Easy (wide gaps, slow speed), Medium (normal gaps, medium speed), Hard (narrow gaps, fast speed). Show level progression and unlock achievements.",
        "priority": "medium",
        "context": {
            "tags": ["html", "javascript", "game", "levels"],
            "programming_language": "HTML/JavaScript",
            "framework": "Canvas API"
        }
    }
]


def submit_task_to_it_lead(task_data):
    """Submit a task to IT Lead via Web UI backend with proper routing"""
    task_id = str(uuid.uuid4())[:8]
    
    # First, submit via the Web UI backend which handles routing
    url = f"{WEB_UI_BACKEND_URL}/api/planner/route"
    
    payload = {
        "task_id": task_id,
        "title": task_data["title"],
        "description": task_data["description"],
        "priority": task_data["priority"],
        "context": task_data.get("context", {})
    }
    
    print(f"\n{'='*60}")
    print(f"Submitting task: {task_data['title']}")
    print(f"   Task ID: {task_id}")
    print(f"{'='*60}")
    
    try:
        with httpx.Client(timeout=120.0) as client:
            # First route the task (this assigns it to the right agent)
            response = client.post(url, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ Task routed successfully!")
                
                if result.get("success"):
                    plan = result.get("plan", {})
                    primary_agent = plan.get("primary_agent", "unknown")
                    tools = plan.get("tools", {})
                    confidence = plan.get("confidence", 0)
                    
                    print(f"   Primary agent: {primary_agent}")
                    print(f"   Tools: {list(tools.keys())}")
                    print(f"   Confidence: {confidence:.2f}")
                    
                    # Now actually assign the task to the agent
                    assign_payload = {
                        "jsonrpc": "2.0",
                        "id": f"assign_{task_id}",
                        "method": "tools/call",
                        "params": {
                            "name": "assign_task",
                            "arguments": {
                                "task_id": task_id,
                                "title": task_data["title"],
                                "description": task_data["description"],
                                "priority": task_data["priority"],
                                "metadata": task_data.get("context", {}),
                                "llm_plan": plan
                            }
                        }
                    }
                    
                    assign_response = client.post(IT_LEAD_URL, json=assign_payload)
                    if assign_response.status_code == 200:
                        assign_result = assign_response.json()
                        if "result" in assign_result:
                            status = assign_result["result"].get("status", "unknown")
                            assigned_to = assign_result["result"].get("assigned_to", "unknown")
                            print(f"   Assignment status: {status}")
                            print(f"   Assigned to: {assigned_to}")
                    
                    return task_id
                else:
                    print(f"   Routing failed: {result}")
                    return None
            else:
                print(f"❌ Failed to route task: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return None
                
    except httpx.RequestError as e:
        print(f"❌ Request error: {e}")
        return None


def main():
    """Main function to submit all test tasks"""
    print("="*60)
    print("IT Lead Web UI API - Test Task Submission")
    print(f"IT Lead URL: {IT_LEAD_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print("="*60)
    
    # Check if IT Lead is available
    try:
        with httpx.Client(timeout=5.0) as client:
            # Try a simple call to check availability
            response = client.get(f"{IT_LEAD_URL.rsplit('/', 1)[0]}")
            # If we get here without exception, server is up
    except httpx.RequestError as e:
        print(f"❌ Cannot connect to IT Lead at {IT_LEAD_URL}")
        print(f"   Error: {e}")
        print("   Please ensure the IT Lead MCP server is running.")
        sys.exit(1)
    
    print("✅ IT Lead server is available")
    
    # Submit all test tasks
    submitted_tasks = []
    for task in TEST_TASKS:
        task_id = submit_task_to_it_lead(task)
        if task_id:
            submitted_tasks.append({
                "task_id": task_id,
                "title": task["title"],
                "language": "html",
                "description": task["description"]
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("SUBMISSION SUMMARY")
    print(f"{'='*60}")
    print(f"Total tasks submitted: {len(submitted_tasks)}/{len(TEST_TASKS)}")
    
    if submitted_tasks:
        print("\nSubmitted tasks:")
        for i, task in enumerate(submitted_tasks, 1):
            print(f"  {i}. [{task['task_id']}] {task['title']}")
        
        print(f"\n✅ Test tasks submitted successfully!")
        print("\nNext steps:")
        print("1. Wait for tasks to complete (check Web UI or use tasks/get)")
        print("2. Verify code extraction in git storage")
        print("3. Check that code is clean (no natural language)")
        print("\nTo check task status, use the Web UI at: http://192.168.51.1:5173")
    else:
        print("\n❌ No tasks were submitted successfully")
        sys.exit(1)


if __name__ == "__main__":
    main()
