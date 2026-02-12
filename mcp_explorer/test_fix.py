#!/usr/bin/env python3
"""
Comprehensive test to verify the fix for the tasks/list functionality.
"""
import asyncio
from mcp_explorer.tui import ToolFormScreen
from mcp_explorer.streamable_http import StreamableHTTPClient

async def test_full_integration():
    print("Testing full integration with tasks/list tool...")
    
    # First, get the tasks/list tool from the server
    client = StreamableHTTPClient("http://localhost:3060/mcp")
    try:
        await client.connect()
        
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
        
        # Now test creating a ToolFormScreen with this tool
        server_url = "http://localhost:3060/mcp"
        server_name = "localhost:3060"  # This would be extracted from the URL in the actual app
        tool_name = f"{server_name}__{tasks_list_tool.get('name')}"
        
        # Sanitize the tool name (this is what show_tool_form does)
        sanitized_tool_name = tool_name.replace(':', '_').replace('.', '_').replace('/', '_')
        
        print(f"Tool name: {tool_name}")
        print(f"Sanitized tool name: {sanitized_tool_name}")
        
        # Create the tool form screen - this should now work without crashing
        tool_form_screen = ToolFormScreen(tasks_list_tool, sanitized_tool_name, server_url)
        print("✓ ToolFormScreen created successfully without errors")
        
        # Verify the sanitized name for IDs is correct
        expected_sanitized = "localhost_3060__tasks_list"
        if tool_form_screen.sanitized_tool_name_for_ids == expected_sanitized:
            print(f"✓ Sanitized name for IDs is correct: {tool_form_screen.sanitized_tool_name_for_ids}")
        else:
            print(f"✗ Sanitized name for IDs is incorrect: {tool_form_screen.sanitized_tool_name_for_ids}, expected: {expected_sanitized}")
            return False
        
        await client.close()
        print("✓ Full integration test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_full_integration())
    exit(0 if success else 1)