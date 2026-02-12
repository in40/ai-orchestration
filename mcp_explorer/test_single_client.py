#!/usr/bin/env python3
"""
Test with a single httpx client instance to mimic the client behavior exactly.
"""
import asyncio
import httpx
import uuid

async def test_single_client_instance():
    """Test using a single httpx client instance like the real client."""
    print("Testing with single httpx client instance...")
    
    session_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient(
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, application/json-rpc+mcp",
            "Mcp-Session-Id": session_id
        }
    ) as client:
        # Send initialize
        print("1. Sending initialize...")
        init_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "streams": False,
                    "experimental": {}
                }
            }
        }
        
        response = await client.post("http://localhost:3031/mcp", json=init_request)
        init_result = response.json()
        print(f"   Initialize response: {init_result.get('result', {}).get('serverInfo', {})}")
        
        # Send initialized
        print("2. Sending initialized...")
        initialized_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialized",
            "params": {}
        }
        
        response = await client.post("http://localhost:3031/mcp", json=initialized_request)
        initialized_result = response.json()
        print(f"   Initialized response: {initialized_result}")
        
        # Send tools/list
        print("3. Sending tools/list...")
        tools_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {}
        }
        
        response = await client.post("http://localhost:3031/mcp", json=tools_request)
        tools_result = response.json()
        tools = tools_result.get("result", {}).get("tools", [])
        print(f"   Tools response: Found {len(tools)} tools")
        for tool in tools:
            print(f"     - {tool.get('name', 'unnamed')}: {tool.get('description', 'No description')}")
        
        return len(tools)

if __name__ == "__main__":
    tool_count = asyncio.run(test_single_client_instance())
    print(f"\nTotal tools found: {tool_count}")