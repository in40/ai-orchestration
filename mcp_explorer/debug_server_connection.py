#!/usr/bin/env python3
"""Debug script to test server connection."""

import asyncio
from mcp_explorer.streamable_http import StreamableHTTPClient

async def test_server_connection():
    print("Testing server connection...")
    
    server_url = "http://localhost:3031/mcp"
    print(f"Connecting to {server_url}")
    
    client = StreamableHTTPClient(server_url)
    
    try:
        await client.connect()
        print("✓ Connected successfully")
        
        # Try initialization
        print("Initializing...")
        init_response = await client.initialize()
        print(f"✓ Initialization response: {init_response}")
        
        # Complete initialization
        await client.initialized(init_response.get("result", {}))
        print("✓ Initialization completed")
        
        # List tools
        print("Listing tools...")
        tools_response = await client.list_tools()
        print(f"✓ Tools response: {tools_response}")
        
        tools_list = tools_response.get("result", {}).get("tools", [])
        print(f"Found {len(tools_list)} tools:")
        for tool in tools_list:
            print(f"  - {tool.get('name')}: {tool.get('description')}")
        
        await client.close()
        print("✓ Connection closed")
        
    except Exception as e:
        print(f"✗ Error: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_server_connection())