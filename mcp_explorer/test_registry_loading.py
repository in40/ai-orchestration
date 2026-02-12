#!/usr/bin/env python3
"""
Direct test of the registry loading functionality with error handling.
"""
import asyncio
from mcp_explorer.registry_adapters import RegistryManager

async def test_registry_loading():
    """Test registry loading with detailed error handling."""
    print("Testing registry loading with detailed error handling...")
    
    manager = RegistryManager()
    
    try:
        print("Calling search_all_servers()...")
        servers = await manager.search_all_servers()
        print(f"Success! Found {len(servers)} servers:")
        for i, server in enumerate(servers):
            print(f"  {i+1}. Name: {server.get('name', 'N/A')}")
            print(f"     URL: {server.get('url', 'N/A')}")
            print(f"     Description: {server.get('description', 'N/A')}")
            print(f"     Adapter Type: {server.get('adapter_type', 'N/A')}")
            print()
        
        return servers
    except Exception as e:
        print(f"Error in registry loading: {e}")
        import traceback
        traceback.print_exc()
        return []

if __name__ == "__main__":
    servers = asyncio.run(test_registry_loading())
    print(f"\nTotal servers found: {len(servers)}")