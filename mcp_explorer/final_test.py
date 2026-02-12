#!/usr/bin/env python3
"""
Final test to simulate the exact workflow that was crashing.
"""
import asyncio
from mcp_explorer.tui import MCPExplorerApp, ToolFormScreen
from mcp_explorer.streamable_http import StreamableHTTPClient

async def simulate_user_workflow():
    """
    Simulate the user workflow that was causing the crash:
    1. Connect to server on port 3060
    2. Find the tasks/list tool
    3. Try to show the tool form (this was causing the crash)
    """
    print("Simulating the user workflow that was causing the crash...")
    
    try:
        # Step 1: Connect to the server and get tools (simulating what happens in connect_to_server)
        client = StreamableHTTPClient("http://localhost:3060/mcp")
        await client.connect()
        
        # Initialize the connection
        init_response = await client.initialize()
        await client.initialized(init_response.get("result", {}))
        
        # Get tools list
        tools_response = await client.list_tools()
        tools_list = tools_response.get("result", {}).get("tools", [])
        
        # Find the tasks/list tool (this is what was causing the crash)
        tasks_list_tool = None
        for tool in tools_list:
            if tool.get("name") == "tasks/list":
                tasks_list_tool = tool
                print(f"✓ Found 'tasks/list' tool: {tool}")
                break
        
        if not tasks_list_tool:
            print("✗ Could not find 'tasks/list' tool")
            return False
        
        await client.close()
        
        # Step 2: Simulate what happens in show_tool_form method when user selects tasks/list
        print("\nSimulating show_tool_form for tasks/list tool...")
        
        # This is the exact code from show_tool_form method:
        server_url = "http://localhost:3060/mcp"
        server_name = "localhost:3060"  # This would be derived from the URL
        tool_name = f"{server_name}__{tasks_list_tool.get('name', 'unnamed')}"
        
        print(f"  Tool name before sanitization: {tool_name}")
        
        # Sanitize the tool name to make it a valid ID (replace invalid characters)
        sanitized_tool_name = tool_name.replace(':', '_').replace('.', '_').replace('/', '_')
        print(f"  Sanitized tool name: {sanitized_tool_name}")
        
        # Validate that the tool has a proper input schema
        input_schema = tasks_list_tool.get("inputSchema", {})
        if not isinstance(input_schema, dict):
            print(f"✗ Invalid input schema for tool {tasks_list_tool.get('name', 'unnamed')}")
            return False
        
        # This is where the crash was happening - creating the ToolFormScreen
        print("  Creating ToolFormScreen (this was causing the crash)...")
        tool_form_screen = ToolFormScreen(tasks_list_tool, sanitized_tool_name, server_url)
        print("  ✓ ToolFormScreen created successfully")
        
        # Check that our fix is in place
        if hasattr(tool_form_screen, 'sanitized_tool_name_for_ids'):
            print(f"  ✓ Sanitized name for IDs: {tool_form_screen.sanitized_tool_name_for_ids}")
        else:
            print("  ✗ Missing sanitized_tool_name_for_ids attribute")
            return False
        
        # Try to access the form widgets that would be generated in the compose method
        # This would trigger the form generation that was failing before
        print("  Attempting form generation (this was failing before the fix)...")
        
        # Import here to avoid circular imports
        from mcp_explorer.form_generator import SchemaFormGenerator
        
        # This is the exact call that was failing in the compose method
        form_widgets = SchemaFormGenerator.generate_form_fields(
            input_schema,
            f"field-{tool_form_screen.sanitized_tool_name_for_ids}"  # Using sanitized name
        )
        
        print(f"  ✓ Generated {len(form_widgets)} form widgets successfully")
        
        print("\n✓ All steps completed successfully! The crash should be fixed.")
        return True
        
    except Exception as e:
        print(f"\n✗ Workflow simulation failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(simulate_user_workflow())
    exit(0 if success else 1)