#!/usr/bin/env python3
"""
Script to submit a task to the IT Lead server to create a Python Hello World app
"""
import json
import requests
import time
from urllib.parse import urlparse

def submit_task_via_http():
    """Submit the task using HTTP POST to the IT Lead server"""
    url = "http://127.0.0.1:3061/mcp"
    
    # Create the task assignment request
    task_request = {
        "jsonrpc": "2.0",
        "id": "hello-world-task-1",
        "method": "tools/call",
        "params": {
            "name": "assign_task",
            "arguments": {
                "task_id": "HELLO-WORLD-APP-001",
                "task_description": "Create a Python Hello World application that prints 'Hello, World!' to the console. The application should be in a file named hello.py and include proper Python conventions like a main function.",
                "assignee": "implementation-engineer",
                "priority": "medium",
                "deadline": "2026-02-20T10:00:00Z"
            }
        }
    }
    
    print("Sending task assignment request to IT Lead server...")
    print(f"Request: {json.dumps(task_request, indent=2)}")
    
    try:
        response = requests.post(url, json=task_request, timeout=30)
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            response_json = response.json()
            if "result" in response_json:
                print("\nTask assigned successfully!")
                print(f"Result: {json.dumps(response_json['result'], indent=2)}")
                return response_json['result']
            else:
                print(f"Unexpected response format: {response_json}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    
    return None

def submit_detailed_implementation_task():
    """Submit a more detailed implementation task to create the Hello World app"""
    url = "http://127.0.0.1:3061/mcp"
    
    # Create a more specific request for implementation
    task_request = {
        "jsonrpc": "2.0",
        "id": "detailed-hello-task-1",
        "method": "tools/call",
        "params": {
            "name": "implement_feature_with_guidelines",
            "arguments": {
                "feature_requirements": "Create a Python application that prints 'Hello, World!' to the console",
                "architectural_guidelines": "Simple single-file Python application with main function",
                "dependencies": [],
                "performance_requirements": ["minimal startup time", "no external dependencies"]
            }
        }
    }
    
    print("\nSending detailed implementation request to IT Lead server...")
    print(f"Request: {json.dumps(task_request, indent=2)}")
    
    try:
        response = requests.post(url, json=task_request, timeout=30)
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            response_json = response.json()
            if "result" in response_json:
                print("\nImplementation task assigned successfully!")
                print(f"Result: {json.dumps(response_json['result'], indent=2)}")
                return response_json['result']
            else:
                print(f"Unexpected response format: {response_json}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    
    return None

def list_available_tools():
    """List available tools from the IT Lead server"""
    url = "http://127.0.0.1:3061/mcp"
    
    list_request = {
        "jsonrpc": "2.0",
        "id": "list-tools-1",
        "method": "tools/list",
        "params": {}
    }
    
    print("\nListing available tools from IT Lead server...")
    print(f"Request: {json.dumps(list_request, indent=2)}")
    
    try:
        response = requests.post(url, json=list_request, timeout=30)
        print(f"Response status: {response.status_code}")
        
        if response.status_code == 200:
            response_json = response.json()
            if "result" in response_json and "tools" in response_json["result"]:
                print(f"\nFound {len(response_json['result']['tools'])} tools:")
                for tool in response_json['result']['tools']:
                    print(f"- {tool['name']}: {tool['description']}")
                return response_json['result']['tools']
            else:
                print(f"Unexpected response format: {response_json}")
        else:
            print(f"Error: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    
    return None

if __name__ == "__main__":
    print("IT Lead Task Submission Tool")
    print("=" * 40)
    
    # First, list available tools
    available_tools = list_available_tools()
    
    # Submit the basic task
    result1 = submit_task_via_http()
    
    # Submit a more detailed implementation task
    result2 = submit_detailed_implementation_task()
    
    print("\nTask submission process completed.")