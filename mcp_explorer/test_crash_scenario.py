#!/usr/bin/env python3
"""
Test script to simulate the exact scenario that causes the crash.
"""
import asyncio
import traceback
from mcp_explorer.tui import MCPExplorerApp, ToolFormScreen
from mcp_explorer.streamable_http import StreamableHTTPClient

async def test_crash_scenario():
    print("Testing the exact scenario that causes the crash...")
    
    try:
        # Get the tasks/list tool from the server
        client = StreamableHTTPClient("http://localhost:3060/mcp")
        await client.connect()
        
        # Initialize the connection
        init_response = await client.initialize()
        await client.initialized(init_response.get("result", {}))
        
        # Get the tools list
        tools_response = await client.list_tools()
        tools = tools_response.get('result', {}).get('tools', [])
        
        # Find the tasks/list tool
        tasks_list_tool = None
        for tool in tools:
            if tool.get('name') == 'tasks/list':
                tasks_list_tool = tool
                break
        
        if not tasks_list_tool:
            print("✗ tasks/list tool not found")
            return False
        
        print(f"✓ Found tasks/list tool: {tasks_list_tool['name']}")
        
        # Now simulate what happens in the show_tool_form method
        server_url = "http://localhost:3060/mcp"
        server_name = "localhost:3060"  # Extracted from URL in real app
        tool_name = f"{server_name}__{tasks_list_tool.get('name')}"
        
        print(f"Tool name before sanitization: {tool_name}")
        
        # Sanitize the tool name to make it a valid ID (replace invalid characters)
        sanitized_tool_name = tool_name.replace(':', '_').replace('.', '_').replace('/', '_')
        print(f"Sanitized tool name: {sanitized_tool_name}")
        
        # This is the exact code from show_tool_form that could cause issues
        # Create the tool form screen
        tool_form_screen = ToolFormScreen(tasks_list_tool, sanitized_tool_name, server_url)
        print("✓ ToolFormScreen created successfully")
        
        # Try to access the attributes we added
        if hasattr(tool_form_screen, 'sanitized_tool_name_for_ids'):
            print(f"✓ Sanitized name for IDs: {tool_form_screen.sanitized_tool_name_for_ids}")
        else:
            print("✗ Missing sanitized_tool_name_for_ids attribute")
            return False
        
        await client.close()
        print("✓ Test completed without crash!")
        return True
        
    except Exception as e:
        print(f"✗ Test failed with error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_crash_scenario())
    exit(0 if success else 1)