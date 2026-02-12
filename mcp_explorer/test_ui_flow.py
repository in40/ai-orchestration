#!/usr/bin/env python3
"""
Test the exact UI flow to see if it updates properly.
"""
import asyncio
from mcp_explorer.tui import MCPExplorerApp
import textual

async def test_ui_flow():
    """Test the UI flow to see if it updates properly."""
    print("Creating MCP Explorer app...")
    
    app = MCPExplorerApp()
    
    # Simulate the same flow as the UI
    print("\n1. Getting servers from registry...")
    servers = await app.registry_manager.search_all_servers()
    print(f"Found {len(servers)} servers:")
    for server in servers:
        print(f"  - {server['name']}: {server['url']}")
    
    if servers:
        server_info = servers[0]  # Take the first server
        print(f"\n2. Connecting to server: {server_info['name']}")
        
        # Connect to the server and get tools
        try:
            client = app.current_client
            if client:
                await client.close()  # Close any existing connection
            
            # Create new client
            from mcp_explorer.streamable_http import StreamableHTTPClient
            client = StreamableHTTPClient(server_info["url"])
            app.current_client = client
            
            print("   Connecting to server...")
            await client.connect()
            
            print("   Initializing...")
            init_response = await client.initialize()
            print(f"   Initialize response: {init_response.get('result', {}).get('serverInfo', {})}")
            
            print("   Sending initialized handshake...")
            await client.initialized(init_response.get("result", {}))
            
            print("   Listing tools...")
            tools_response = await client.list_tools()
            tools = tools_response.get("result", {}).get("tools", [])
            print(f"   Found {len(tools)} tools:")
            for tool in tools:
                print(f"     - {tool.get('name', 'unnamed')}: {tool.get('description', 'No description')}")
                
            print("\n3. Testing tool calling...")
            if tools:
                # Try calling the first tool as a test
                first_tool = tools[0]
                tool_name = first_tool.get('name')
                print(f"   Attempting to call tool: {tool_name}")
                
                # For example_tool, we need to provide input parameter
                if tool_name == "example_tool":
                    result = await client.call_tool(tool_name, {"input": "test input"})
                    print(f"   Tool call result: {result}")
                    
        except Exception as e:
            print(f"   Error during server connection: {e}")
            import traceback
            traceback.print_exc()
        finally:
            if app.current_client:
                await app.current_client.close()
                app.current_client = None

if __name__ == "__main__":
    asyncio.run(test_ui_flow())