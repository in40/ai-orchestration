#!/usr/bin/env python3
"""Debug script to test registry loading."""

import asyncio
from mcp_explorer.registry_adapters import RegistryManager

async def test_registry():
    print("Testing registry loading...")
    
    registry_manager = RegistryManager()
    
    print(f"Registry adapters: {len(registry_manager.adapters)}")
    for i, adapter in enumerate(registry_manager.adapters):
        print(f"  Adapter {i}: {type(adapter).__name__}")
    
    print("\nSearching for servers...")
    servers = await registry_manager.search_all_servers()
    
    print(f"Found {len(servers)} servers:")
    for server in servers:
        print(f"  - Name: {server.get('name')}")
        print(f"    URL: {server.get('url')}")
        print(f"    Description: {server.get('description')}")
        print(f"    Type: {server.get('adapter_type')}")
        print()

if __name__ == "__main__":
    asyncio.run(test_registry())