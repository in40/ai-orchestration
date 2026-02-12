#!/usr/bin/env python3
"""
Test to see if the Tree widget is being populated.
"""
import asyncio
from mcp_explorer.tui import MCPExplorerApp

async def test_widget_population():
    """Test if the Tree widget is being populated."""
    print("Creating app...")
    app = MCPExplorerApp()
    
    print("Calling load_registries...")
    await app.load_registries()
    
    print(f"Registry manager has adapters: {len(app.registry_manager.adapters)}")
    
    # Get servers
    servers = await app.registry_manager.search_all_servers()
    print(f"Found {len(servers)} servers:")
    for server in servers:
        print(f"  - {server['name']}: {server['url']}")

if __name__ == "__main__":
    asyncio.run(test_widget_population())