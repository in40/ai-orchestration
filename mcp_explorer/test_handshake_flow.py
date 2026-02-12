#!/usr/bin/env python3
"""
Test the full handshake flow that the client performs.
"""
import asyncio
import uuid
import httpx

async def test_full_handshake():
    """Test the full handshake flow."""
    print("Testing full handshake flow...")
    
    base_url = "http://localhost:3031/mcp"
    session_id = str(uuid.uuid4())
    
    async with httpx.AsyncClient(
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json, application/json-rpc+mcp",
            "Mcp-Session-Id": session_id
        }
    ) as client:
        try:
            # Step 1: Initialize
            print("\n1. Sending initialize...")
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
            
            response = await client.post(base_url, content=str(init_request).replace("'", '"'))
            init_result = response.json()
            print(f"Initialize result: {init_result.get('result', {}).get('serverInfo', {})}")
            
            # Step 2: Initialized handshake
            print("\n2. Sending initialized handshake...")
            initialized_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "initialized",
                "params": {
                    "serverInfo": init_result.get('result', {}).get('serverInfo', {}),
                    "capabilities": {
                        "experimental": {}
                    }
                }
            }
            
            response = await client.post(base_url, content=str(initialized_request).replace("'", '"'))
            initialized_result = response.json()
            print(f"Initialized result: {initialized_result}")
            
            # Step 3: List tools
            print("\n3. Listing tools...")
            tools_request = {
                "jsonrpc": "2.0",
                "id": str(uuid.uuid4()),
                "method": "tools/list",
                "params": {}
            }
            
            response = await client.post(base_url, content=str(tools_request).replace("'", '"'))
            tools_result = response.json()
            tools = tools_result.get('result', {}).get('tools', [])
            print(f"Tools result: Found {len(tools)} tools")
            for tool in tools:
                print(f"  - {tool.get('name', 'unnamed')}: {tool.get('description', 'No description')}")
            
            return True
            
        except Exception as e:
            print(f"Error in handshake flow: {e}")
            import traceback
            traceback.print_exc()
            return False

if __name__ == "__main__":
    success = asyncio.run(test_full_handshake())
    print(f"\nHandshake flow test: {'SUCCESS' if success else 'FAILED'}")