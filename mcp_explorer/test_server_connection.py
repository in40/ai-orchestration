#!/usr/bin/env python3
"""
Test the connect to server functionality.
"""
import asyncio
from mcp_explorer.streamable_http import StreamableHTTPClient

async def test_server_connection():
    """Test connecting to the server and listing tools."""
    print("Testing server connection and tools listing...")
    
    # Use the same server URL as found by the registry
    server_url = "http://localhost:3031/mcp"
    server_name = "localhost-registry"
    
    try:
        client = StreamableHTTPClient(server_url)
        await client.connect()

        # Initialize the connection
        init_response = await client.initialize()
        print(f"Initialize response: {init_response.get('result', {}).get('serverInfo', {})}")
        
        await client.initialized(init_response.get("result", {}))

        # List tools
        tools_response = await client.list_tools()
        tools_list = tools_response.get("result", {}).get("tools", [])
        print(f"Found {len(tools_list)} tools:")
        for tool in tools_list:
            print(f"  - {tool.get('name', 'unnamed')}: {tool.get('description', 'No description')}")

        await client.close()
        print("Connection test completed successfully")
        return True

    except Exception as e:
        print(f"Failed to connect to server: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = asyncio.run(test_server_connection())
    print(f"Server connection test: {'SUCCESS' if success else 'FAILED'}")