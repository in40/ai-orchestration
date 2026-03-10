#!/usr/bin/env python3
"""
Submit test tasks directly to Implementation Engineer's vibe_code_async tool.

This bypasses the IT Lead routing and directly submits coding tasks to the
Implementation Engineer, which will generate code and store it in git.
"""

import httpx
import json
import sys
import uuid
from datetime import datetime

# Configuration
IMPLEMENTATION_ENGINEER_URL = "http://0.0.0.0:3060/mcp"

# Test task variations
TEST_TASKS = [
    {
        "title": "Flappy Bird Clone - Classic HTML5 Game",
        "description": "Create a Flappy Bird game in HTML with canvas. The bird should jump when clicking/tapping, pipes should move from right to left, and there should be collision detection. Include score tracking and a game over screen.",
        "language": "html",
        "vibe_level": 7
    },
    {
        "title": "Flappy Bird with Enhanced Graphics",
        "description": "Create a Flappy Bird game in HTML with colorful graphics. Add background images, animated bird sprite, rotating pipes, and particle effects when the bird jumps. Make it visually appealing with smooth animations.",
        "language": "html",
        "vibe_level": 8
    },
    {
        "title": "Flappy Bird with Power-ups",
        "description": "Create an enhanced Flappy Bird game in HTML with power-up features. Add special items like: shield (protects from one collision), speed boost (slows down time), and magnet (attracts nearby points). Display power-up status in UI.",
        "language": "html",
        "vibe_level": 9
    },
    {
        "title": "Flappy Bird with Multiple Levels",
        "description": "Create a Flappy Bird game in HTML with progressive difficulty. Implement 3 levels: Easy (wide gaps, slow speed), Medium (normal gaps, medium speed), Hard (narrow gaps, fast speed). Show level progression and unlock achievements.",
        "language": "html",
        "vibe_level": 8
    }
]


def submit_vibe_code_task(task_data):
    """Submit a task to Implementation Engineer's vibe_code_async tool"""
    task_id = str(uuid.uuid4())
    
    payload = {
        "jsonrpc": "2.0",
        "id": task_id,
        "method": "tools/call",
        "params": {
            "name": "vibe_code_async",
            "arguments": {
                "task_description": f"{task_data['title']}: {task_data['description']}",
                "language": task_data["language"],
                "vibe_level": task_data["vibe_level"]
            }
        }
    }
    
    short_id = task_id[:8]
    print(f"\n{'='*60}")
    print(f"Submitting task: {task_data['title']}")
    print(f"   Task ID: {short_id}")
    print(f"   Language: {task_data['language']}")
    print(f"   Vibe level: {task_data['vibe_level']}")
    print(f"{'='*60}")
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(IMPLEMENTATION_ENGINEER_URL, json=payload)
            
            if response.status_code == 200:
                result = response.json()
                task_result = result.get("result", {})
                
                if "taskId" in task_result:
                    actual_task_id = task_result["taskId"]
                    status = task_result.get("status", "unknown")
                    print(f"✅ Task submitted successfully!")
                    print(f"   Actual Task ID: {actual_task_id}")
                    print(f"   Status: {status}")
                    return actual_task_id
                elif "error" in task_result:
                    print(f"❌ Error: {task_result['error']}")
                    return None
                else:
                    print(f"   Response: {json.dumps(result, indent=2)}")
                    return None
            else:
                print(f"❌ Failed to submit task: {response.status_code}")
                print(f"   Response: {response.text[:500]}")
                return None
                
    except httpx.RequestError as e:
        print(f"❌ Request error: {e}")
        return None


def check_task_status(task_id):
    """Check the status of a vibe_code_async task"""
    payload = {
        "jsonrpc": "2.0",
        "id": f"status_{task_id}",
        "method": "tools/call",
        "params": {
            "name": "tasks/get",
            "arguments": {"taskId": task_id}
        }
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(IMPLEMENTATION_ENGINEER_URL, json=payload)
            if response.status_code == 200:
                result = response.json()
                return result.get("result", {})
    except Exception as e:
        print(f"Error checking task {task_id}: {e}")
    
    return None


def get_task_result(task_id):
    """Get the result of a completed task"""
    payload = {
        "jsonrpc": "2.0",
        "id": f"result_{task_id}",
        "method": "tools/call",
        "params": {
            "name": "tasks/result",
            "arguments": {"taskId": task_id}
        }
    }
    
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(IMPLEMENTATION_ENGINEER_URL, json=payload)
            if response.status_code == 200:
                result = response.json()
                return result.get("result", {})
    except Exception as e:
        print(f"Error getting result for task {task_id}: {e}")
    
    return None


def main():
    """Main function to submit all test tasks"""
    print("="*60)
    print("Implementation Engineer - Test Task Submission")
    print(f"Target: {IMPLEMENTATION_ENGINEER_URL}")
    print(f"Time: {datetime.now().isoformat()}")
    print("="*60)
    
    # Check if Implementation Engineer is available
    try:
        with httpx.Client(timeout=5.0) as client:
            # Simple ping
            response = client.get(IMPLEMENTATION_ENGINEER_URL.rsplit('/', 1)[0])
    except httpx.RequestError as e:
        print(f"❌ Cannot connect to Implementation Engineer at {IMPLEMENTATION_ENGINEER_URL}")
        print(f"   Error: {e}")
        sys.exit(1)
    
    print("✅ Implementation Engineer is available")
    
    # Submit all test tasks
    submitted_tasks = []
    for task in TEST_TASKS:
        task_id = submit_vibe_code_task(task)
        if task_id:
            submitted_tasks.append({
                "task_id": task_id,
                "title": task["title"],
                "language": task["language"]
            })
    
    # Summary
    print(f"\n{'='*60}")
    print("SUBMISSION SUMMARY")
    print(f"{'='*60}")
    print(f"Total tasks submitted: {len(submitted_tasks)}/{len(TEST_TASKS)}")
    
    if submitted_tasks:
        print("\nSubmitted tasks:")
        for i, task in enumerate(submitted_tasks, 1):
            print(f"  {i}. [{task['task_id'][:8]}] {task['title']}")
        
        print(f"\n✅ Test tasks submitted successfully!")
        print("\nNext steps:")
        print("1. Wait for tasks to complete (LLM generation takes time)")
        print("2. Run: python3 check_task_results.py")
        print("3. Verify code is clean and stored in git")
        print("\nNote: Tasks will be processed asynchronously.")
        print("      Check status using the Web UI or tasks/get tool.")
    else:
        print("\n❌ No tasks were submitted successfully")
        sys.exit(1)


if __name__ == "__main__":
    main()
