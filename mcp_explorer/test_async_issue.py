#!/usr/bin/env python3
"""
Test to verify the async issue in TUI.
"""
import asyncio
from mcp_explorer.tui import MCPExplorerApp
import textual

async def test_async_issue():
    """Test the async issue in TUI."""
    print("Creating app...")
    app = MCPExplorerApp()
    
    print("Calling load_registries directly...")
    await app.load_registries()
    
    print(f"Servers found: {len(app.registry_manager.adapters)} adapters")
    
    # Get servers
    servers = await app.registry_manager.search_all_servers()
    print(f"Actual servers found: {len(servers)}")
    for server in servers:
        print(f"  - {server['name']}: {server['url']}")

if __name__ == "__main__":
    asyncio.run(test_async_issue())