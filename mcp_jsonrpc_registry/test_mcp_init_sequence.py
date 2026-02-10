#!/usr/bin/env python3
"""
Test to understand the proper MCP session initialization sequence
"""

import asyncio
import json
from datetime import datetime
import sys
import os

async def test_mcp_session_initialization():
    """Test the proper MCP session initialization sequence."""
    print("Testing proper MCP session initialization sequence...")
    
    try:
        # Import the required components
        from mcp.client.streamable_http import streamable_http_client
        import mcp
        import aiohttp
        
        print("✅ Successfully imported MCP components")
        
        registry_url = "http://localhost:6000/mcp"
        
        print(f"Connecting to registry at {registry_url}")
        
        # Use the streamable HTTP client to establish connection
        async with streamable_http_client(url=registry_url) as (receive_stream, send_stream, get_session_id_callback):
            print("✅ Successfully connected to registry with streams")
            
            # Get session ID to confirm it's working
            session_id = get_session_id_callback()
            print(f"Session ID: {session_id}")
            
            # Create a ClientSession with the streams
            client_session = mcp.ClientSession(
                read_stream=receive_stream,
                write_stream=send_stream
            )
            
            # Initialize the session - this is the key step
            print("Initializing MCP session...")
            init_result = await client_session.initialize()
            print(f"Initialization result: {init_result}")
            
            # Now try to call a method
            print("Trying to call registry-list_servers...")
            try:
                list_result = await client_session.call_tool_async("registry-list_servers", {})
                print(f"List servers result: {list_result}")
                
                if isinstance(list_result, dict) and "servers" in list_result:
                    print(f"✅ Successfully listed {len(list_result['servers'])} servers")
                else:
                    print(f"❌ Unexpected result format: {list_result}")
            except Exception as e:
                print(f"❌ Error listing servers: {e}")
                import traceback
                traceback.print_exc()
            
            # Now try to register
            print("Trying to register server...")
            registration_data = {
                "name": f"mcp-init-test-server-{int(datetime.now().timestamp())}",
                "description": "A server registered via proper MCP initialization",
                "endpoint": "http://localhost:9000",
                "capabilities": {
                    "resources": False,
                    "tools": True,
                    "prompts": False,
                    "roots": False,
                    "sampling": False
                },
                "metadata": {
                    "version": "1.0.0",
                    "author": "MCP Init Test"
                },
                "tags": ["test", "mcp", "init"]
            }
            
            try:
                registration_result = await client_session.call_tool_async("registry-register_server", registration_data)
                print(f"Registration result: {registration_result}")
                
                if isinstance(registration_result, dict) and registration_result.get("success"):
                    server_id = registration_result.get("server_id")
                    print(f"🎉 SUCCESS! Server registered with ID: {server_id}")
                    return True, registration_result
                else:
                    print(f"❌ Registration failed: {registration_result}")
                    return False, registration_result
            except Exception as e:
                print(f"❌ Error during registration: {e}")
                import traceback
                traceback.print_exc()
                return False, {"error": str(e)}
    
    except Exception as e:
        print(f"❌ Error in MCP session initialization: {e}")
        import traceback
        traceback.print_exc()
        return False, {"error": str(e)}


async def main():
    """Main function to test MCP session initialization."""
    print("🚀 TESTING MCP SESSION INITIALIZATION SEQUENCE")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    success, result = await test_mcp_session_initialization()
    
    print("\n" + "=" * 60)
    print("📊 MCP INITIALIZATION TEST RESULTS:")
    print("=" * 60)
    
    if success:
        print("🎉 SUCCESS: MCP session initialization worked!")
        print("   - Session was properly established")
        print("   - Registration completed successfully")
        print("   - Registry is working as expected")
    else:
        print("❌ MCP INITIALIZATION TEST FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        print("\n💡 The registry requires proper MCP session initialization.")
        print("   This involves establishing streams and initializing the session")
        print("   using the ClientSession.initialize() method.")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)