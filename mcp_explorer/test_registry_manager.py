#!/usr/bin/env python3
"""
Test script to verify the registry manager works with the corrected server.
"""
import asyncio
from mcp_explorer.registry_adapters import RegistryManager

async def test_registry_manager():
    print("Testing registry manager...")
    try:
        manager = RegistryManager()
        servers = await manager.search_all_servers()
        print(f"Registry manager found {len(servers)} servers:")
        for server in servers:
            print(f"  - {server}")
        return len(servers) > 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_registry_manager())
    print(f"Test {'passed' if success else 'failed'}")