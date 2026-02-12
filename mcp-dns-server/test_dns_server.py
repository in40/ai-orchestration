#!/usr/bin/env python3
"""
Test script for DNS Resolving MCP Server
"""
import asyncio
import json
import aiohttp
from typing import Dict, Any


async def test_dns_server():
    base_url = "http://localhost:3040"
    
    async with aiohttp.ClientSession() as session:
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
            print(f"Initialize response: {result}")
        
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
            print(f"Tools list response: {result}")
        
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
            print(f"DNS resolve response: {result}")
        
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
            print(f"Ping response: {result}")


if __name__ == "__main__":
    asyncio.run(test_dns_server())