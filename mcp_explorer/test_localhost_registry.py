#!/usr/bin/env python3
"""
Test script to verify the localhost registry adapter works with the corrected server.
"""
import asyncio
from mcp_explorer.registry_adapters import LocalhostRegistryAdapter

async def test_localhost_registry():
    print("Testing localhost registry adapter...")
    try:
        adapter = LocalhostRegistryAdapter()
        servers = await adapter.search_servers()
        print(f"Found {len(servers)} servers:")
        for server in servers:
            print(f"  - {server}")
        return len(servers) > 0
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_localhost_registry())
    print(f"Test {'passed' if success else 'failed'}")