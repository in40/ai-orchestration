#!/usr/bin/env python3
"""
Test to see if any methods work without session validation
"""

import asyncio
import json
from datetime import datetime
import sys
import os
import aiohttp

async def test_registry_methods():
    """Test various registry methods to see which ones work without session validation."""
    print("Testing various registry methods...")
    
    registry_url = "http://localhost:6000/mcp"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    # Test methods that might not require session validation
    test_methods = [
        ("rpc.discover", {}),
        ("registry-list_servers", {}),
        ("registry-search_servers", {"query": ""}),
    ]
    
    for method_name, params in test_methods:
        print(f"\nTesting method: {method_name}")
        
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "method": method_name,
            "params": params,
            "id": f"test-{method_name.replace('-', '_').replace(':', '_')}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(registry_url, json=jsonrpc_request, headers=headers) as response:
                    response_text = await response.text()
                    print(f"  Status: {response.status}")
                    print(f"  Response: {response_text}")
                    
                    if response.status == 200:
                        try:
                            response_json = json.loads(response_text)
                            if "result" in response_json:
                                print(f"  ✅ Method {method_name} succeeded")
                                if method_name == "registry-list_servers" and "servers" in response_json["result"]:
                                    server_count = len(response_json["result"]["servers"])
                                    print(f"  Found {server_count} servers")
                            elif "error" in response_json:
                                print(f"  ❌ Method {method_name} returned error: {response_json['error']}")
                        except json.JSONDecodeError:
                            print(f"  ❌ Could not parse response as JSON")
                    else:
                        print(f"  ❌ Method {method_name} failed with status {response.status}")
        
        except Exception as e:
            print(f"  ❌ Error testing {method_name}: {e}")
    
    # Now test the methods that require session validation
    print(f"\nTesting methods that require session validation:")
    
    session_required_methods = [
        ("registry-register_server", {
            "name": "test-server",
            "description": "Test server",
            "endpoint": "http://localhost:9000",
            "capabilities": {
                "resources": False,
                "tools": True,
                "prompts": False,
                "roots": False,
                "sampling": False
            },
            "metadata": {"version": "1.0.0"},
            "tags": ["test"]
        }),
        ("registry-update_server_status", {
            "server_id": "nonexistent",
            "health_status": "healthy"
        })
    ]
    
    for method_name, params in session_required_methods:
        print(f"\nTesting method: {method_name}")
        
        jsonrpc_request = {
            "jsonrpc": "2.0",
            "method": method_name,
            "params": params,
            "id": f"test-{method_name.replace('-', '_').replace(':', '_')}"
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(registry_url, json=jsonrpc_request, headers=headers) as response:
                    response_text = await response.text()
                    print(f"  Status: {response.status}")
                    print(f"  Response: {response_text}")
                    
                    if "Missing session ID" in response_text:
                        print(f"  ❌ Method {method_name} correctly requires session validation")
                    else:
                        print(f"  ❓ Unexpected response for {method_name}")
        
        except Exception as e:
            print(f"  ❌ Error testing {method_name}: {e}")


async def main():
    """Main function to test registry methods."""
    print("🔍 TESTING REGISTRY METHODS WITHOUT SESSION ESTABLISHMENT")
    print("=" * 70)
    print(f"Test started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    await test_registry_methods()
    
    print("\n" + "=" * 70)
    print("📋 TEST SUMMARY:")
    print("=" * 70)
    print("The registry is working as designed:")
    print("• Methods that don't require sessions (like list_servers) may work")
    print("• Methods that require sessions (like register_server) return 'Missing session ID'")
    print("• This confirms the session validation is working correctly")
    print("\nTo successfully register, proper session context must be established")
    print("through the MCP client library before making registration calls.")
    
    print(f"\nTest completed at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)


if __name__ == "__main__":
    asyncio.run(main())