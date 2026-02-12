#!/usr/bin/env python3
"""
Test the exact async behavior in the UI.
"""
import asyncio
from mcp_explorer.tui import MCPExplorerApp

async def test_ui_async_behavior():
    """Test the exact async behavior in the UI."""
    print("Testing UI async behavior...")
    
    app = MCPExplorerApp()
    
    print("\n1. Testing load_registries method directly...")
    await app.load_registries()
    print("   load_registries completed")
    
    # Check if the registry tree has been populated
    try:
        registry_tree = app.query_one("#registry-tree")
        print(f"   Registry tree root label: {registry_tree.root.label}")
        print(f"   Registry tree root children count: {len(registry_tree.root.children)}")
        
        for i, child in enumerate(registry_tree.root.children):
            print(f"   Child {i}: {child.label}, data: {child.data}")
    except Exception as e:
        print(f"   Error accessing registry tree: {e}")

if __name__ == "__main__":
    asyncio.run(test_ui_async_behavior())