#!/usr/bin/env python3
"""
Test the registry tools fix.
"""
import asyncio
import json
import uuid
import httpx

async def test_registry_tools():
    """Test the registry tools to see if they work now."""
    print("Testing registry tools fix...")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, application/json-rpc+mcp",
        "Mcp-Session-Id": str(uuid.uuid4())
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

        print("\n4. Testing registry/list via tools/call...")
        # Test registry/list via tools/call (this was failing before)
        tools_call_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "tool": "registry/list",  # Using "tool" parameter as shown in bug report
                "arguments": {}
            }
        }
        try:
            tools_call_response = await client.post("http://localhost:3031/mcp", json=tools_call_request)
            print(f"   Tools/call response: {tools_call_response.text}")
            response_data = tools_call_response.json()
            if 'error' in response_data:
                print(f"   ❌ Error in tools/call: {response_data['error']}")
            else:
                print(f"   ✅ Success: {response_data.get('result', {})}")
        except Exception as e:
            print(f"   ❌ Exception in tools/call: {e}")

        print("\n5. Testing registry/register via tools/call...")
        # Test registry/register via tools/call (this was failing before)
        register_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "tool": "registry/register",  # Using "tool" parameter as shown in bug report
                "arguments": {
                    "id": "dummy-server",
                    "name": "Dummy Test Server",
                    "description": "A dummy server for testing",
                    "endpoint": "http://localhost:3032/mcp",
                    "capabilities": {
                        "tools": ["test_tool"],
                        "resources": [],
                        "prompts": []
                    }
                }
            }
        }
        try:
            register_response = await client.post("http://localhost:3031/mcp", json=register_request)
            print(f"   Register response: {register_response.text}")
            response_data = register_response.json()
            if 'error' in response_data:
                print(f"   ❌ Error in register: {response_data['error']}")
            else:
                print(f"   ✅ Success: {response_data.get('result', {})}")
        except Exception as e:
            print(f"   ❌ Exception in register: {e}")

        print("\n6. Testing registry/list again to see if registration worked...")
        # Test registry/list again to see if the registration worked
        tools_call_request2 = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/call",
            "params": {
                "tool": "registry/list",
                "arguments": {}
            }
        }
        try:
            tools_call_response2 = await client.post("http://localhost:3031/mcp", json=tools_call_request2)
            print(f"   Tools/call response: {tools_call_response2.text}")
            response_data2 = tools_call_response2.json()
            if 'error' in response_data2:
                print(f"   ❌ Error in tools/call: {response_data2['error']}")
            else:
                print(f"   ✅ Success: {response_data2.get('result', {})}")
        except Exception as e:
            print(f"   ❌ Exception in tools/call: {e}")

if __name__ == "__main__":
    asyncio.run(test_registry_tools())