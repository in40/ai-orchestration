#!/usr/bin/env python3
"""
Test to see if we can call registry methods using the proper MCP client approach
"""

import asyncio
import json
from datetime import datetime
import sys
import os

async def test_with_proper_mcp_client():
    """Test using the proper MCP client approach."""
    print("Testing with proper MCP client approach...")
    
    try:
        # Import the proper MCP client components
        from mcp.client import Client
        from mcp.client.streamable_http import streamable_http_client
        import mcp
        import aiohttp
        
        registry_url = "http://localhost:6000/mcp"
        
        print(f"Connecting to registry at {registry_url}")
        
        # Use the proper streamable HTTP client approach
        async with streamable_http_client(url=registry_url) as (receive_stream, send_stream, get_session_id_callback):
            print("✅ Successfully connected to registry with proper streams")
            
            # Get the session ID to confirm it's working
            session_id = get_session_id_callback()
            print(f"Session ID: {session_id}")
            
            # Create a ClientSession with the streams
            client_session = mcp.ClientSession(
                read_stream=receive_stream,
                write_stream=send_stream
            )
            
            # Initialize the session (this is required for MCP protocol)
            init_result = await client_session.initialize()
            print(f"Session initialized: {init_result}")
            
            # Try to list servers first (should not require session validation based on code)
            print("\nTrying to list servers...")
            try:
                list_result = await client_session.call_tool_async("registry-list_servers", {})
                print(f"List servers result: {list_result}")
                
                if isinstance(list_result, dict) and "servers" in list_result:
                    print(f"✅ Successfully listed {len(list_result['servers'])} servers")
                else:
                    print(f"❌ Unexpected result format: {list_result}")
            except Exception as e:
                print(f"❌ Error listing servers: {e}")
            
            # Now try to register a server
            print("\nTrying to register a server...")
            registration_data = {
                "name": "test-server-proper-client",
                "description": "A test server registered via proper client",
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
                    "author": "Proper Client Test"
                },
                "tags": ["test", "proper", "client"]
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
    
    except ImportError as e:
        print(f"❌ Could not import required MCP components: {e}")
        return False, {"error": f"Import error: {e}"}
    except Exception as e:
        print(f"❌ Error in proper client approach: {e}")
        import traceback
        traceback.print_exc()
        return False, {"error": str(e)}


async def main():
    """Main function to run the test."""
    print("🚀 TESTING REGISTRY CONNECTION WITH PROPER MCP CLIENT")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    success, result = await test_with_proper_mcp_client()
    
    print("\n" + "=" * 60)
    print("📊 TEST RESULTS:")
    print("=" * 60)
    
    if success:
        print("🎉 SUCCESS: Proper MCP client approach worked!")
        print("   - Session context was properly established")
        print("   - Registration completed successfully")
        print("   - Registry is working as expected")
    else:
        print("❌ TEST FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        print("\n💡 The registry may require specific session establishment patterns")
        print("   that need to be followed using the MCP client library.")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)