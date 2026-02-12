#!/usr/bin/env python3
"""
Test script for DNS Resolving MCP Server that also reads SSE responses
"""
import asyncio
import json
import aiohttp
from typing import Dict, Any


async def test_dns_server():
    base_url = "http://localhost:3040"
    
    async with aiohttp.ClientSession() as session:
        # First, establish SSE connection to receive responses
        sse_task = asyncio.create_task(read_sse_responses(base_url))
        
        # Wait a moment for SSE to connect
        await asyncio.sleep(1)
        
        # Test initialization
        print("Testing initialization...")
        init_payload = {
            "jsonrpc": "2.0",
            "id": "1",
            "method": "initialize",
            "params": {
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0"
                }
            }
        }
        
        async with session.post(f"{base_url}/send", json=init_payload) as response:
            result = await response.json()
            print(f"Initialize request sent: {result}")
        
        # Test tools list
        print("\nTesting tools list...")
        tools_list_payload = {
            "jsonrpc": "2.0",
            "id": "2",
            "method": "tools/list",
            "params": {}
        }
        
        async with session.post(f"{base_url}/send", json=tools_list_payload) as response:
            result = await response.json()
            print(f"Tools list request sent: {result}")
        
        # Test DNS resolution
        print("\nTesting DNS resolution...")
        dns_resolve_payload = {
            "jsonrpc": "2.0",
            "id": "3",
            "method": "tools/call",
            "params": {
                "name": "dns_resolve",
                "arguments": {
                    "domain": "google.com",
                    "record_type": "A"
                }
            }
        }
        
        async with session.post(f"{base_url}/send", json=dns_resolve_payload) as response:
            result = await response.json()
            print(f"DNS resolve request sent: {result}")
        
        # Test health check
        print("\nTesting health check...")
        ping_payload = {
            "jsonrpc": "2.0",
            "id": "4",
            "method": "ping",
            "params": {}
        }
        
        async with session.post(f"{base_url}/send", json=ping_payload) as response:
            result = await response.json()
            print(f"Ping request sent: {result}")
        
        # Wait a bit more to receive responses via SSE
        await asyncio.sleep(3)
        
        # Cancel the SSE task
        sse_task.cancel()
        try:
            await sse_task
        except asyncio.CancelledError:
            pass


async def read_sse_responses(base_url):
    """Read responses from the SSE stream"""
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(f"{base_url}/sse") as response:
                async for line in response.content:
                    line_str = line.decode('utf-8').strip()
                    if line_str.startswith('data: ') and line_str != 'data: ':
                        data_part = line_str[6:]  # Remove 'data: ' prefix
                        if data_part.startswith('{'):  # It's a JSON object
                            try:
                                json_data = json.loads(data_part)
                                print(f"SSE Response: {json_data}")
                            except json.JSONDecodeError:
                                print(f"SSE Data (non-JSON): {data_part}")
                        else:
                            print(f"SSE Data: {data_part}")
    except Exception as e:
        print(f"Error reading SSE: {e}")


if __name__ == "__main__":
    asyncio.run(test_dns_server())