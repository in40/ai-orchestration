#!/usr/bin/env python3
"""
Test the exact same async call that happens in the TUI.
"""
import asyncio
from mcp_explorer.tui import MCPExplorerApp

async def test_ui_async_call():
    """Test the same async call that happens in the UI."""
    print("Testing the same async call as in the UI...")
    
    app = MCPExplorerApp()
    
    # Replicate the exact call from on_mount
    try:
        servers = await app.registry_manager.search_all_servers()
        print(f"Found {len(servers)} servers in the same way as the UI:")
        for server in servers:
            print(f"  - {server}")
        
        if not servers:
            print("This explains why the UI shows empty - no servers found!")
            print("Checking individual adapter...")
            
            from mcp_explorer.registry_adapters import LocalhostRegistryAdapter
            adapter = LocalhostRegistryAdapter()
            adapter_servers = await adapter.search_servers()
            print(f"Localhost adapter found: {len(adapter_servers)} servers")
            for server in adapter_servers:
                print(f"  - {server}")
                
    except Exception as e:
        print(f"Error in async call: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_ui_async_call())