#!/usr/bin/env python3
"""
Script to check the status of agents from the web UI backend perspective
"""
import requests
import json

def check_web_ui_agents():
    """Check what agents the web UI sees"""
    print("Checking agents from Web UI backend...")
    
    # Query the web UI backend
    url = "http://localhost:8000/api/agents"
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            agents = response.json()
            print(f"\nAgents seen by Web UI:")
            for agent in agents:
                print(f"- {agent['name']}: {agent['status']}")
                print(f"  Last seen: {agent['last_seen']}")
                print(f"  Capabilities: {agent['capabilities'][:3]}...")  # Show first 3 capabilities
                print()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

def check_web_ui_tasks():
    """Check what tasks the web UI sees"""
    print("Checking tasks from Web UI backend...")
    
    # Query the web UI backend for tasks
    url = "http://localhost:8000/api/tasks"
    
    try:
        response = requests.get(url, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            tasks = response.json()
            print(f"\nTasks seen by Web UI:")
            for task in tasks:
                print(f"- {task['id']}: {task['title']}")
                print(f"  Assignee: {task['assignee']}")
                print(f"  Status: {task['status']}")
                print(f"  Priority: {task['priority']}")
                print()
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

def check_direct_it_lead_tasks():
    """Try to check tasks directly from IT Lead server"""
    print("Checking if we can track our specific task via IT Lead server...")
    
    # Try to use the track_task_progress tool to see if our task exists
    url = "http://127.0.0.1:3061/mcp"
    
    track_request = {
        "jsonrpc": "2.0",
        "id": "check-specific-task",
        "method": "tools/call",
        "params": {
            "name": "track_task_progress",
            "arguments": {
                "task_ids": ["HELLO-WORLD-APP-001"],
                "include_details": True
            }
        }
    }
    
    print("Sending task tracking request for our specific task...")
    print(f"Request: {json.dumps(track_request, indent=2)}")
    
    try:
        response = requests.post(url, json=track_request, timeout=30)
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

def submit_task_through_web_ui_api():
    """Submit a task through the web UI API to see if it gets tracked"""
    print("\nSubmitting a new task through Web UI API to see if it gets tracked...")
    
    url = "http://localhost:8000/api/tasks/assign"
    
    task_data = {
        "task_id": "WEB-UI-TEST-TASK-001",
        "title": "Web UI Test Task - Create Python Hello World App",
        "description": "Create a Python Hello World application that prints 'Hello, World!' to the console",
        "assignee": "Implementation Engineer",
        "priority": "medium",
        "due_date": "2026-02-20T10:00:00Z"
    }
    
    try:
        response = requests.post(url, json=task_data, timeout=30)
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            print("Task submitted through Web UI API successfully!")
        else:
            print(f"Error submitting task: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    print("Web UI Agent and Task Status Check")
    print("=" * 50)
    
    # Check agents from web UI perspective
    check_web_ui_agents()
    
    # Check tasks from web UI perspective
    check_web_ui_tasks()
    
    # Check our specific task directly
    check_direct_it_lead_tasks()
    
    # Submit a new task through the web UI API
    submit_task_through_web_ui_api()