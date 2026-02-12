#!/usr/bin/env python3
"""
Test the exact TUI behavior with debugging.
"""
import asyncio
from mcp_explorer.tui import MCPExplorerApp
import textual

async def test_tui_debug():
    """Test the exact TUI behavior with debugging."""
    print("Testing TUI behavior with debugging...")
    
    # Create the app
    app = MCPExplorerApp()
    
    # Manually call the load_registries method and see what happens
    print("\nCalling load_registries method...")
    await app.load_registries()
    print("load_registries completed")
    
    # Check if any servers were found by looking at the internal state
    print(f"Current server: {app.current_server}")
    print(f"Current server URL: {app.current_server_url}")
    print(f"Current tools count: {len(app.current_tools) if hasattr(app, 'current_tools') else 'N/A'}")
    
    # Try to access the tree widget if possible (though it might not be available without running the app)
    try:
        # This will likely fail since widgets aren't mounted yet
        registry_tree = app.query_one("#registry-tree", expect_type=textual.widgets.Tree)
        print(f"Registry tree found: {registry_tree}")
        print(f"Root children count: {len(registry_tree.root.children)}")
    except Exception as e:
        print(f"Could not access tree widget directly: {e}")
        print("(This is expected since widgets aren't mounted until app runs)")

if __name__ == "__main__":
    asyncio.run(test_tui_debug())