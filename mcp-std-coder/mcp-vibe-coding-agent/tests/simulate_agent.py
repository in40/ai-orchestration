#!/usr/bin/env python3
"""
Simulation test for the vibe coding MCP server.
This script simulates an AI agent calling the vibe_code tool.
"""
import asyncio
import json
import aiohttp
import time


async def test_vibe_coding_tool():
    """Test the vibe_code tool by sending a request directly to the MCP server."""
    print("Testing vibe coding tool...")
    
    # Create a test request to the MCP server
    request_data = {
        "jsonrpc": "2.0",
        "id": "test-request-1",
        "method": "tools/call",
        "params": {
            "name": "vibe_code",
            "arguments": {
                "task_description": "Write a Python function that returns the nth Fibonacci number",
                "language": "python",
                "vibe_level": 8,
                "style_guide": "use type hints"
            }
        }
    }
    
    # Send the request to the server
    try:
        async with aiohttp.ClientSession() as session:
            # First, let's check if the server is running by hitting the health endpoint
            async with session.get("http://127.0.0.1:3060/health") as health_resp:
                health_data = await health_resp.json()
                print(f"Health check: {health_data}")
            
            # Now send the tool call request
            headers = {
                "Content-Type": "application/json",
                "MCP-Session-Id": "test-session-1"
            }
            
            async with session.post("http://127.0.0.1:3060/mcp", 
                                  json=request_data, 
                                  headers=headers) as resp:
                response_data = await resp.json()
                print(f"Tool call response: {json.dumps(response_data, indent=2)}")
                
                if "result" in response_data:
                    print("\n=== Generated Code ===")
                    print(response_data["result"])
                    print("=====================")
                elif "error" in response_data:
                    print(f"Error: {response_data['error']}")
                    
    except Exception as e:
        print(f"Error during test: {e}")
        print("Note: The server may not be running. Start it with: python -m mcp_std_server.server --port 3060")


async def test_tool_listing():
    """Test listing available tools."""
    print("\nTesting tools listing...")
    
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
                print(f"Tools list response: {json.dumps(response_data, indent=2)}")
                
                if "result" in response_data and "tools" in response_data["result"]:
                    tools = response_data["result"]["tools"]
                    print(f"\nFound {len(tools)} tools:")
                    for tool in tools:
                        print(f"  - {tool['name']}: {tool['description']}")
                        
    except Exception as e:
        print(f"Error during tools listing test: {e}")


async def main():
    print("Starting vibe coding agent simulation tests...\n")
    
    # Test 1: List tools
    await test_tool_listing()
    
    # Test 2: Call the vibe_code tool
    await test_vibe_coding_tool()
    
    print("\nSimulation tests completed!")


if __name__ == "__main__":
    asyncio.run(main())