#!/usr/bin/env python3
"""
Script to trace the task through the IT Lead server and check its status
"""
import json
import requests
import time
import sqlite3
import os

def check_task_status():
    """Check if our task was processed by querying the task tracking system"""
    print("Checking task status...")
    
    # Try to list all tasks using the track_task_progress tool
    url = "http://127.0.0.1:3061/mcp"
    
    track_request = {
        "jsonrpc": "2.0",
        "id": "track-task-1",
        "method": "tools/call",
        "params": {
            "name": "track_task_progress",
            "arguments": {
                "task_ids": ["HELLO-WORLD-APP-001"],
                "include_details": True
            }
        }
    }
    
    print("Sending task tracking request...")
    print(f"Request: {json.dumps(track_request, indent=2)}")
    
    try:
        response = requests.post(url, json=track_request, timeout=30)
        print(f"Response status: {response.status_code}")
        print(f"Response: {response.text}")
        
        if response.status_code == 200:
            response_json = response.json()
            if "result" in response_json:
                print("\nTask tracking result:")
                print(json.dumps(response_json['result'], indent=2))
                return response_json['result']
            else:
                print(f"No result in response: {response_json}")
        else:
            print(f"Error tracking task: {response.status_code} - {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
    
    return None

def check_resources():
    """Check resources that might contain task information"""
    print("\nChecking resources...")
    
    url = "http://127.0.0.1:3061/mcp"
    
    # Read the team status resource
    resource_request = {
        "jsonrpc": "2.0",
        "id": "read-resource-1",
        "method": "resources/read",
        "params": {
            "uri": "it-lead://resource/team-status"
        }
    }
    
    print("Reading team status resource...")
    try:
        response = requests.post(url, json=resource_request, timeout=30)
        print(f"Response status: {response.status_code}")
        if response.status_code == 200:
            response_json = response.json()
            if "result" in response_json:
                print("Team status:")
                print(json.dumps(response_json['result'], indent=2))
        else:
            print(f"Error reading resource: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")

def verify_hello_world_app():
    """Verify that the Hello World application was created and works"""
    print("\nVerifying Hello World application...")
    
    hello_py_path = "/root/qwen/base/it-lead-mcp-server/hello.py"
    
    if os.path.exists(hello_py_path):
        print(f"✅ Hello World file exists: {hello_py_path}")
        
        # Read the file content
        with open(hello_py_path, 'r') as f:
            content = f.read()
            print(f"File content:\n{content}")
        
        # Run the application
        import subprocess
        try:
            result = subprocess.run(['python', hello_py_path], 
                                  capture_output=True, text=True, 
                                  cwd='/root/qwen/base/it-lead-mcp-server')
            print(f"Application output: {result.stdout.strip()}")
            if result.returncode == 0 and "Hello, World!" in result.stdout:
                print("✅ Hello World application runs correctly!")
                return True
            else:
                print(f"❌ Application didn't run as expected. Return code: {result.returncode}, Error: {result.stderr}")
                return False
        except Exception as e:
            print(f"❌ Error running application: {e}")
            return False
    else:
        print(f"❌ Hello World file does not exist: {hello_py_path}")
        return False

def check_server_health():
    """Check the health of the IT Lead server"""
    print("\nChecking server health...")
    
    url = "http://127.0.0.1:3061/mcp"
    
    health_request = {
        "jsonrpc": "2.0",
        "id": "health-check-1",
        "method": "ping",
        "params": {}
    }
    
    try:
        response = requests.post(url, json=health_request, timeout=30)
        print(f"Health check response status: {response.status_code}")
        if response.status_code == 200:
            response_json = response.json()
            print("Server health:")
            print(json.dumps(response_json, indent=2))
        else:
            print(f"Error checking health: {response.status_code} - {response.text}")
    except requests.exceptions.RequestException as e:
        print(f"Health check failed: {e}")

if __name__ == "__main__":
    print("IT Lead Task Tracing Tool")
    print("=" * 40)
    
    # Check server health
    check_server_health()
    
    # Check if the Hello World app was created
    app_verified = verify_hello_world_app()
    
    # Check task status
    check_task_status()
    
    # Check resources
    check_resources()
    
    print(f"\nTask tracing completed.")
    print(f"Hello World app verification: {'✅ SUCCESS' if app_verified else '❌ FAILED'}")