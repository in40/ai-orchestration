#!/usr/bin/env python3
"""Comprehensive test to simulate user interaction with the explorer."""

import asyncio
from mcp_explorer.tui import MCPExplorerApp


async def test_full_interaction():
    app = MCPExplorerApp()
    try:
        async with app.run_test(size=(120, 40)) as pilot:
            print("Initial state:")
            tree = app.query_one('#registry-tree')
            tools_table = app.query_one('#tools-table')
            print(f"- Registry tree nodes: {len(tree.root.children)}")
            print(f"- Tools table rows: {tools_table.row_count}")
            print(f"- Current server: {app.current_server}")
            print()
            
            # Wait a bit for the registry to load
            await pilot.pause(0.5)
            print("After initial load:")
            print(f"- Registry tree nodes: {len(tree.root.children)}")
            print(f"- Tools table rows: {tools_table.row_count}")
            print(f"- Current server: {app.current_server}")
            print()
            
            # Find and select the localhost registry node
            localhost_node = None
            for child in tree.root.children:
                if 'localhost-registry' in str(child.label):
                    localhost_node = child
                    break
            
            if localhost_node:
                print("Selecting localhost registry node...")
                # Simulate clicking on the node
                tree.select_node(localhost_node)
                
                # Wait for tools to load
                await pilot.pause(1.0)
                
                print("After selecting server:")
                print(f"- Tools table rows: {tools_table.row_count}")
                print(f"- Current server: {app.current_server}")
                print(f"- Current server URL: {app.current_server_url}")
                
                # Print the tools if any
                if tools_table.row_count > 0:
                    print("Tools found:")
                    for i in range(min(tools_table.row_count, 5)):  # Show first 5 tools
                        row = tools_table.get_row_at(i)
                        print(f"  - {row[0]}: {row[1]}")
                else:
                    print("No tools found.")
            else:
                print("Could not find localhost registry node!")
                
    except Exception as e:
        print(f"Error in test: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_full_interaction())