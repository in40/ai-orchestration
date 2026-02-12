#!/usr/bin/env python3
"""
Debug the difference between client and manual requests.
"""
import asyncio
import json
import uuid
import httpx
from mcp_explorer.streamable_http import StreamableHTTPClient

async def debug_client_vs_manual():
    """Compare client vs manual requests."""
    print("=== Comparing Client vs Manual Requests ===")
    
    # Test with the actual client
    print("\n1. Testing with StreamableHTTPClient:")
    client = StreamableHTTPClient("http://localhost:3031/mcp")
    await client.connect()
    
    # Capture the exact request being sent
    print("   About to send initialize...")
    init_response = await client.initialize()
    print(f"   Initialize response: {init_response}")
    
    print("   About to send initialized handshake...")
    try:
        initialized_response = await client.initialized(init_response.get("result", {}))
        print(f"   Initialized response: {initialized_response}")
    except Exception as e:
        print(f"   Initialized error: {e}")
    
    print("   About to list tools...")
    tools_response = await client.list_tools()
    tools = tools_response.get("result", {}).get("tools", [])
    print(f"   Tools response: Found {len(tools)} tools")
    for tool in tools:
        print(f"     - {tool.get('name', 'unnamed')}")
    
    await client.close()
    
    print("\n2. Testing with manual HTTP request (matching client format):")
    # Manually send the same request format as the client
    session_id = str(uuid.uuid4())
    request_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient(
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, application/json-rpc+mcp",
            "Mcp-Session-Id": session_id
        }
    ) as http_client:
        # Send initialize like the client does
        request_data = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "streams": False,
                    "experimental": {}
                }
            }
        }
        
        response = await http_client.post("http://localhost:3031/mcp", content=json.dumps(request_data))
        manual_init_response = response.json()
        print(f"   Manual initialize response: {manual_init_response}")
        
        # Send tools/list like the client does
        request_id2 = str(uuid.uuid4())
        tools_request = {
            "jsonrpc": "2.0",
            "id": request_id2,
            "method": "tools/list"
        }
        
        response = await http_client.post("http://localhost:3031/mcp", content=json.dumps(tools_request))
        manual_tools_response = response.json()
        manual_tools = manual_tools_response.get("result", {}).get("tools", [])
        print(f"   Manual tools response: Found {len(manual_tools)} tools")
        for tool in manual_tools:
            print(f"     - {tool.get('name', 'unnamed')}")

if __name__ == "__main__":
    asyncio.run(debug_client_vs_manual())