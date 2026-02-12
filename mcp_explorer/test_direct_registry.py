#!/usr/bin/env python3
"""
Test direct method calls to registry endpoints.
"""
import asyncio
import json
import uuid
import httpx

async def test_direct_registry_calls():
    """Test direct method calls to registry endpoints."""
    print("Testing direct registry method calls...")

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

        print("3. Testing direct registry/list call...")
        # Direct registry/list call
        registry_list_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "registry/list",
            "params": {}
        }
        registry_list_response = await client.post("http://localhost:3031/mcp", json=registry_list_request)
        print(f"   Direct registry/list response: {registry_list_response.json()}")

        print("4. Testing direct registry/register call...")
        # Direct registry/register call
        registry_register_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "registry/register",
            "params": {
                "id": "direct-test-server",
                "name": "Direct Test Server",
                "description": "A server registered via direct call",
                "endpoint": "http://localhost:3033/mcp",
                "capabilities": {
                    "tools": ["test_tool"],
                    "resources": [],
                    "prompts": []
                }
            }
        }
        registry_register_response = await client.post("http://localhost:3031/mcp", json=registry_register_request)
        print(f"   Direct registry/register response: {registry_register_response.json()}")

        print("5. Testing direct registry/list again...")
        # Direct registry/list call again to see if registration worked
        registry_list_request2 = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "registry/list",
            "params": {}
        }
        registry_list_response2 = await client.post("http://localhost:3031/mcp", json=registry_list_request2)
        print(f"   Direct registry/list response: {registry_list_response2.json()}")

if __name__ == "__main__":
    asyncio.run(test_direct_registry_calls())