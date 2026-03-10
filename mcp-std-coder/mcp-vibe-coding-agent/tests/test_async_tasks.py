#!/usr/bin/env python3
"""
Test script for async task functionality in vibe coding server
"""
import asyncio
import json
import aiohttp
import time


async def test_async_task_functionality():
    """Test the new async task functionality."""
    print("Testing async task functionality...")
    
    # Test 1: List all tools to see if new async tools are available
    print("\n1. Testing tools listing...")
    request_data = {
        "jsonrpc": "2.0",
        "id": "test-list-tools",
        "method": "tools/list",
        "params": {}
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "MCP-Session-Id": "test-session-1"
            }
            
            async with session.post("http://127.0.0.1:3060/mcp", 
                                  json=request_data, 
                                  headers=headers) as resp:
                response_data = await resp.json()
                
                if "result" in response_data and "tools" in response_data["result"]:
                    tools = response_data["result"]["tools"]
                    print(f"Found {len(tools)} tools:")
                    for tool in tools:
                        print(f"  - {tool['name']}: {tool['description'][:60]}...")
                        
                        # Check if async tools are present
                        if tool['name'] in ['vibe_code_async', 'tasks/list', 'tasks/get', 'tasks/result', 'tasks/cancel']:
                            print(f"    ✓ {tool['name']} - ASYNC TOOL DETECTED")
                            
    except Exception as e:
        print(f"Error during tools listing test: {e}")
    
    # Test 2: Submit an async task
    print("\n2. Testing async task submission...")
    async_task_request = {
        "jsonrpc": "2.0",
        "id": "test-async-task",
        "method": "tools/call",
        "params": {
            "name": "vibe_code_async",
            "arguments": {
                "task_description": "Write a Python function that returns the nth Fibonacci number using iteration",
                "language": "python",
                "vibe_level": 6,
                "style_guide": "include type hints and docstrings"
            }
        }
    }
    
    try:
        async with aiohttp.ClientSession() as session:
            headers = {
                "Content-Type": "application/json",
                "MCP-Session-Id": "test-session-1"
            }
            
            async with session.post("http://127.0.0.1:3060/mcp", 
                                  json=async_task_request, 
                                  headers=headers) as resp:
                response_data = await resp.json()
                print(f"Async task submission response: {json.dumps(response_data, indent=2)}")
                
                # Extract task ID if available
                task_id = None
                if "result" in response_data and "taskId" in response_data["result"]:
                    task_id = response_data["result"]["taskId"]
                    print(f"✓ Async task submitted successfully with ID: {task_id}")
                
                # Test 3: Check task status
                if task_id:
                    print(f"\n3. Testing task status check for task {task_id}...")
                    status_request = {
                        "jsonrpc": "2.0",
                        "id": "test-get-status",
                        "method": "tools/call",
                        "params": {
                            "name": "tasks/get",
                            "arguments": {
                                "taskId": task_id
                            }
                        }
                    }
                    
                    async with session.post("http://127.0.0.1:3060/mcp", 
                                          json=status_request, 
                                          headers=headers) as status_resp:
                        status_data = await status_resp.json()
                        print(f"Task status response: {json.dumps(status_data, indent=2)}")
                        
                        # Test 4: List all tasks
                        print(f"\n4. Testing tasks list...")
                        list_request = {
                            "jsonrpc": "2.0",
                            "id": "test-list-tasks",
                            "method": "tools/call",
                            "params": {
                                "name": "tasks/list",
                                "arguments": {}
                            }
                        }
                        
                        async with session.post("http://127.0.0.1:3060/mcp", 
                                              json=list_request, 
                                              headers=headers) as list_resp:
                            list_data = await list_resp.json()
                            print(f"Tasks list response: {json.dumps(list_data, indent=2)}")
                        
                        # Wait a bit for the task to process, then check result
                        print(f"\n5. Waiting for task to complete...")
                        time.sleep(5)  # Wait for processing
                        
                        print(f"6. Testing task result retrieval...")
                        result_request = {
                            "jsonrpc": "2.0",
                            "id": "test-get-result",
                            "method": "tools/call",
                            "params": {
                                "name": "tasks/result",
                                "arguments": {
                                    "taskId": task_id
                                }
                            }
                        }
                        
                        async with session.post("http://127.0.0.1:3060/mcp", 
                                              json=result_request, 
                                              headers=headers) as result_resp:
                            result_data = await result_resp.json()
                            print(f"Task result response: {json.dumps(result_data, indent=2)}")
                            
                            if "result" in result_data and "result" in result_data["result"]:
                                print("\n=== GENERATED CODE ===")
                                print(result_data["result"])
                                print("=====================")
    
    except Exception as e:
        print(f"Error during async task test: {e}")
        import traceback
        traceback.print_exc()


async def main():
    print("Starting async task functionality tests...\n")
    
    await test_async_task_functionality()
    
    print("\nAsync task functionality tests completed!")


if __name__ == "__main__":
    asyncio.run(main())