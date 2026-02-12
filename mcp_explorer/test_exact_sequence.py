#!/usr/bin/env python3
"""
Test to replicate the exact sequence that happens when clicking tasks/list.
"""
import asyncio
import urllib.parse
from mcp_explorer.tui import MCPExplorerApp
from mcp_explorer.streamable_http import StreamableHTTPClient

async def test_exact_sequence():
    """
    Replicate the exact sequence that happens when clicking on tasks/list:
    1. connect_to_server -> loads tools and stores them
    2. on_tree_node_selected -> calls update_details_for_single_item and show_tool_form
    """
    print("Testing the exact sequence that happens when clicking tasks/list...")
    
    try:
        # Create a mock app instance to test with
        app = MCPExplorerApp()
        
        # Step 1: Simulate connect_to_server (this populates current_tools)
        print("Step 1: Connecting to server and loading tools...")
        server_url = "http://localhost:3060/mcp"
        client = StreamableHTTPClient(server_url)
        await client.connect()
        
        # Initialize the connection
        init_response = await client.initialize()
        await client.initialized(init_response.get("result", {}))
        
        # Fetch tools
        tools_response = await client.list_tools()
        tools_list = tools_response.get("result", {}).get("tools", [])
        
        # Find the tasks/list tool
        tasks_list_tool = None
        for tool in tools_list:
            if tool.get("name") == "tasks/list":
                tasks_list_tool = tool
                break
        
        if not tasks_list_tool:
            print("✗ Could not find 'tasks/list' tool")
            return False
            
        print(f"✓ Found 'tasks/list' tool: {tasks_list_tool['name']}")
        
        # Store in app (simulating what connect_to_server does)
        app.current_server = "localhost:3060"  # This would be derived from URL
        app.current_server_url = server_url
        app.current_tools = tools_list
        
        await client.close()
        
        # Step 2: Simulate what happens in on_tree_node_selected when tasks/list is clicked
        print("\nStep 2: Simulating node selection (this is where the crash happens)...")
        
        # This is what happens in on_tree_node_selected for a capability_item:
        capability = "tools"
        item = tasks_list_tool
        server_url_from_node = server_url  # This comes from node data
        
        # First, update details for single item (this should work fine)
        print("  Calling update_details_for_single_item...")
        app.update_details_for_single_item(capability, item)
        print("  ✓ update_details_for_single_item completed")
        
        # Then, show tool form (this is where the crash was happening)
        print("  Calling show_tool_form (this was causing the crash)...")
        
        # This is the exact call from on_tree_node_selected:
        # self.show_tool_form(item, server_url)
        app.show_tool_form(item, server_url_from_node)
        print("  ✓ show_tool_form completed without crash!")
        
        print("\n✓ All steps completed successfully! The crash should be fixed.")
        return True
        
    except Exception as e:
        print(f"\n✗ Sequence test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_exact_sequence())
    exit(0 if success else 1)