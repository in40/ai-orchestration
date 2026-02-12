#!/usr/bin/env python3
"""
Test script to verify MCP Explorer can connect to a server.
"""
import asyncio
from mcp_explorer.streamable_http import StreamableHTTPClient

async def test_connection():
    print("Testing connection to test server...")
    try:
        client = StreamableHTTPClient("http://localhost:8080/mcp")
        await client.connect()
        
        # Test initialize
        init_response = await client.initialize()
        print(f"✓ Initialize successful: {init_response.get('result', {}).get('serverInfo', {}).get('name', 'Unknown')}")
        
        # Test list tools
        tools_response = await client.list_tools()
        tools = tools_response.get('result', {}).get('tools', [])
        print(f"✓ Found {len(tools)} tools")
        
        for tool in tools:
            print(f"  - {tool.get('name')}: {tool.get('description', 'No description')}")
        
        await client.close()
        print("✓ Connection test completed successfully")
        return True
    except Exception as e:
        print(f"✗ Connection test failed: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(test_connection())
    exit(0 if success else 1)