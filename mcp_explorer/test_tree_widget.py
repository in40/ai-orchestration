#!/usr/bin/env python3
"""
Test the Tree widget update mechanism.
"""
import asyncio
from textual.app import App
from textual.widgets import Tree, Header, Footer
from textual.containers import Vertical
from textual import on
from mcp_explorer.registry_adapters import RegistryManager

class TestTreeApp(App):
    """Test app to see if Tree widget updates properly."""

    def __init__(self):
        super().__init__()
        self.registry_manager = RegistryManager()

    def compose(self):
        yield Header()
        with Vertical():
            yield Tree("Test Root", id="test-tree")
        yield Footer()

    def on_mount(self):
        """Called when app mounts."""
        # Schedule the async operation
        self.call_later(self.populate_tree)

    async def populate_tree(self):
        """Populate the tree with registry data."""
        print("populate_tree called")
        try:
            servers = await self.registry_manager.search_all_servers()
            print(f"Found {len(servers)} servers")
            
            tree = self.query_one("#test-tree", Tree)
            print(f"Tree object: {tree}")
            print(f"Tree root: {tree.root}")
            
            # Clear existing nodes
            tree.clear()
            print("Cleared tree")
            
            # Add servers to tree
            for server in servers:
                print(f"Adding server: {server}")
                node = tree.root.add(server["name"], data=server)
                node.expand()
            
            print(f"Tree now has {len(tree.root.children)} children")
            
            # Force refresh
            tree.refresh()
            
        except Exception as e:
            print(f"Error in populate_tree: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    app = TestTreeApp()
    print("Running test tree app...")
    app.run()