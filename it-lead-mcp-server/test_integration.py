#!/usr/bin/env python3
"""
Test script to verify the integration between web UI and IT Lead server
"""
import asyncio
import httpx
import json

async def test_web_ui_integration():
    print("Testing web UI integration with IT Lead server...")
    
    # Test the web UI endpoint
    async with httpx.AsyncClient(timeout=10.0) as client:
        try:
            # Test the /api/tasks endpoint
            response = await client.get("http://localhost:8000/api/tasks")
            print(f"Status Code: {response.status_code}")
            
            if response.status_code == 200:
                tasks = response.json()
                print(f"Response: {json.dumps(tasks, indent=2)}")
                print(f"Number of tasks returned: {len(tasks)}")
                
                if len(tasks) == 0:
                    print("✓ Endpoint is working correctly - returning empty list instead of mock data")
                    print("  (Empty list is expected when no tasks exist in the system)")
                else:
                    print("✓ Endpoint is working correctly - returning actual tasks from the system")
            else:
                print(f"✗ Unexpected status code: {response.status_code}")
                print(f"Response: {response.text}")
                
        except Exception as e:
            print(f"✗ Error testing web UI endpoint: {e}")
            
        # Test direct connection to IT Lead server
        try:
            print("\nTesting direct connection to IT Lead server...")
            response = await client.post(
                "http://localhost:3061/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "test-tools-list",
                    "method": "tools/list",
                    "params": {}
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                tools = result.get("result", {}).get("tools", [])
                tool_names = [tool["name"] for tool in tools]
                
                print(f"Available tools: {tool_names}")
                
                if "get_all_tasks" in tool_names:
                    print("✓ New 'get_all_tasks' tool is available in IT Lead server")
                else:
                    print("✗ New 'get_all_tasks' tool is NOT available in IT Lead server")
                    
                if "track_task_progress" in tool_names:
                    print("✓ 'track_task_progress' tool is available in IT Lead server")
                else:
                    print("✗ 'track_task_progress' tool is NOT available in IT Lead server")
            else:
                print(f"✗ Failed to connect to IT Lead server: {response.status_code}")
                
        except Exception as e:
            print(f"✗ Error connecting to IT Lead server: {e}")

if __name__ == "__main__":
    asyncio.run(test_web_ui_integration())