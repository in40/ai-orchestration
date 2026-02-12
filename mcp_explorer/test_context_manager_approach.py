#!/usr/bin/env python3
"""
Test using the context manager approach to compare with manual approach.
"""
import asyncio
import json
import uuid
import httpx

async def test_context_manager_approach():
    """Test using the context manager approach."""
    print("Testing with context manager approach...")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, application/json-rpc+mcp",
        "Mcp-Session-Id": str(uuid.uuid4())  # Generate a new session ID
    }

    async with httpx.AsyncClient(headers=headers) as client:
        print("1. Initializing...")
        
        # Initialize request
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
        init_response = await client.post("http://localhost:3031/mcp", json=init_request)
        print(f"   Initialize response: {init_response.json()['result'].get('serverInfo', {})}")

        print("2. Sending initialized handshake...")
        # Initialized request
        initialized_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialized",
            "params": {
                "serverInfo": init_response.json()["result"]["serverInfo"],
                "capabilities": {"experimental": {}}
            }
        }
        initialized_response = await client.post("http://localhost:3031/mcp", json=initialized_request)
        print(f"   Initialized response: {initialized_response.json()}")

        print("3. Listing tools...")
        # Tools/list request
        tools_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {}
        }
        tools_response = await client.post("http://localhost:3031/mcp", json=tools_request)
        tools_data = tools_response.json()
        tools = tools_data.get("result", {}).get("tools", [])
        print(f"   Tools response: Found {len(tools)} tools")
        for tool in tools:
            print(f"     - {tool.get('name', 'unnamed')}: {tool.get('description', 'No description')}")

    return len(tools)

if __name__ == "__main__":
    tool_count = asyncio.run(test_context_manager_approach())
    print(f"\nTotal tools found with context manager: {tool_count}")