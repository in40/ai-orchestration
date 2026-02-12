#!/usr/bin/env python3
"""
Simple test to see if Tree widget updates properly.
"""
import asyncio
from textual.app import App
from textual.widgets import Tree, Header, Footer
from textual.containers import Vertical

class SimpleTreeTest(App):
    """Simple app to test Tree widget."""

    def compose(self):
        yield Header()
        with Vertical():
            yield Tree("Root", id="simple-tree")
        yield Footer()

    def on_mount(self):
        """Add nodes after mount."""
        # Use call_later to schedule the update after the UI is ready
        self.call_after_refresh(self.add_nodes)

    def add_nodes(self):
        """Add nodes to the tree."""
        print("Adding nodes to tree...")
        tree = self.query_one("#simple-tree", Tree)
        
        # Add some test nodes
        tree.root.add("Test Server 1", data={"name": "server1", "url": "http://test1"})
        tree.root.add("Test Server 2", data={"name": "server2", "url": "http://test2"})
        
        print(f"Added {len(tree.root.children)} nodes to tree")
        tree.root.expand_all()

if __name__ == "__main__":
    app = SimpleTreeTest()
    app.run()