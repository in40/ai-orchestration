#!/usr/bin/env python3
"""
Test server that attempts to register with the registry
"""

import asyncio
import json
from datetime import datetime
import sys
import os

# Add the project root to the path to access modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def create_test_server_and_register():
    """Create a test server and attempt to register with the registry."""
    print("Creating test server and attempting to register with registry...")
    
    try:
        # Import MCP server components
        from mcp.server import FastMCP
        import mcp
        
        print("✅ Imported MCP server components")
        
        # Create a simple MCP server
        test_server = FastMCP("test-mcp-server", streamable_http_path="/mcp")
        
        # Register a simple tool for testing
        @test_server.tool(
            name="test-tool",
            description="A simple test tool"
        )
        def test_tool(param: str = "default") -> dict:
            return {"result": f"Test tool executed with param: {param}"}
        
        print("✅ Created test server with basic tool")
        
        # Now try to connect to the registry and register
        # We need to use the MCP client to connect to the registry
        from mcp.client.streamable_http import streamable_http_client
        
        registry_url = "http://localhost:6000/mcp"
        
        print(f"Attempting to connect to registry at {registry_url}")
        
        # Connect to the registry using the proper client
        async with streamable_http_client(url=registry_url) as (receive_stream, send_stream, get_session_id_callback):
            print("✅ Connected to registry with streams")
            
            # Create a ClientSession with the streams
            client_session = mcp.ClientSession(
                read_stream=receive_stream,
                write_stream=send_stream
            )
            
            # Initialize the session
            init_result = await client_session.initialize()
            print(f"Session initialized: {init_result}")
            
            # Prepare registration data
            registration_data = {
                "name": "test-server-direct-connect",
                "description": "A test server connecting directly",
                "endpoint": "http://localhost:9000",  # This would be the server's actual endpoint
                "capabilities": {
                    "resources": False,
                    "tools": True,
                    "prompts": False,
                    "roots": False,
                    "sampling": False
                },
                "metadata": {
                    "version": "1.0.0",
                    "author": "Test Server"
                },
                "tags": ["test", "direct", "connection"]
            }
            
            print("Attempting to register with registry...")
            
            # Call the registration method
            result = await client_session.call_tool(
                "registry-register_server",
                registration_data
            )
            
            print(f"Registration result: {result}")
            
            if isinstance(result, dict) and result.get("success"):
                server_id = result.get("server_id")
                print(f"🎉 SUCCESS! Server registered with ID: {server_id}")
                return True, result
            else:
                print(f"❌ Registration failed: {result}")
                return False, result
                
    except Exception as e:
        print(f"❌ Error during server registration: {e}")
        import traceback
        traceback.print_exc()
        return False, {"error": str(e)}


async def main():
    """Main function to run the test server registration."""
    print("🚀 CREATING TEST SERVER AND ATTEMPTING REGISTRATION")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    success, result = await create_test_server_and_register()
    
    print("\n" + "=" * 60)
    print("📊 REGISTRATION ATTEMPT RESULTS:")
    print("=" * 60)
    
    if success:
        print("🎉 SUCCESS: Test server successfully registered with the registry!")
        if isinstance(result, dict):
            print(f"   Server ID: {result.get('server_id', 'N/A')}")
            print(f"   Message: {result.get('message', 'Registration completed')}")
    else:
        print("❌ REGISTRATION FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        print("\n💡 The registry requires proper session context for registration.")
        print("   This may require specific MCP client library usage patterns.")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)