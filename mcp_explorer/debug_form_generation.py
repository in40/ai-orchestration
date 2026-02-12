#!/usr/bin/env python3
"""
Debug script to test the explorer's handling of tasks/list tool.
"""
import asyncio
from mcp_explorer.tui import ToolFormScreen
from textual.app import App

def test_form_generation_for_tasks_list():
    print("Testing form generation for tasks/list tool...")
    
    # Create a mock tool schema similar to the tasks/list tool
    tool_schema = {
        'name': 'tasks/list',
        'description': 'List all async tasks with optional status filtering',
        'inputSchema': {
            'type': 'object',
            'properties': {
                'status': {
                    'type': 'string',
                    'description': 'Filter tasks by status (submitted, working, completed, failed, cancelled)'
                },
                'limit': {
                    'type': 'integer',
                    'description': 'Maximum number of tasks to return',
                    'default': 100
                }
            }
        }
    }
    
    server_url = "http://localhost:3060/mcp"
    
    try:
        # This simulates what happens in the show_tool_form method
        server_name = "localhost:3060"
        tool_name = f"{server_name}__{tool_schema.get('name', 'unnamed')}"
        
        print(f"Tool name: {tool_name}")
        
        # Sanitize the tool name to make it a valid ID (this is what the calling code does)
        sanitized_tool_name = tool_name.replace(':', '_').replace('.', '_').replace('/', '_')
        print(f"Sanitized tool name: {sanitized_tool_name}")
        
        # Try to create the tool form screen - this should now work with our fix
        tool_form_screen = ToolFormScreen(tool_schema, sanitized_tool_name, server_url)
        print("✓ ToolFormScreen created successfully")
        
        # Try to access the form widgets that would be generated in the compose method
        # Since we can't call compose directly without a full app context, 
        # we'll just verify that the sanitized_tool_name_for_ids attribute exists
        if hasattr(tool_form_screen, 'sanitized_tool_name_for_ids'):
            print(f"✓ Sanitized tool name for IDs: {tool_form_screen.sanitized_tool_name_for_ids}")
            print("✓ The fix appears to be in place")
        else:
            print("✗ Sanitized tool name for IDs attribute not found")
            return False
        
        print("✓ Form generation preparation successful")
        return True
        
    except Exception as e:
        print(f"✗ Error in form generation: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_form_generation_for_tasks_list()
    exit(0 if success else 1)