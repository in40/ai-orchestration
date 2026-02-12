#!/usr/bin/env python3
"""
Debug script to test the tasks/list functionality specifically.
"""
import asyncio
from mcp_explorer.streamable_http import StreamableHTTPClient

async def test_tasks_list():
    print("Testing tasks/list functionality...")
    try:
        client = StreamableHTTPClient("http://localhost:3060/mcp")
        await client.connect()

        # Test initialize
        init_response = await client.initialize()
        print(f"✓ Initialize successful: {init_response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")

        # Test list tools
        tools_response = await client.list_tools()
        tools = tools_response.get('result', {}).get('tools', [])
        print(f"✓ Found {len(tools)} tools")

        # Look for the tasks/list tool specifically
        tasks_list_tool = None
        for tool in tools:
            tool_name = tool.get('name')
            print(f"  - {tool_name}: {tool.get('description', 'No description')}")
            
            if tool_name == 'tasks/list':
                tasks_list_tool = tool
                print(f"  ^ Found tasks/list tool: {tool}")
                
        if tasks_list_tool:
            # Try calling the tasks/list tool
            print("\nTrying to call tasks/list tool...")
            result = await client.call_tool('tasks/list', {})
            print(f"✓ tasks/list result: {result}")
        else:
            print("No tasks/list tool found")

        await client.close()
        print("✓ Connection test completed successfully")
        return True
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_tasks_list())
    exit(0 if success else 1)