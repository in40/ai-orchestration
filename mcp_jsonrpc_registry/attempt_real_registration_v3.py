#!/usr/bin/env python3
"""
Third attempt: Use ClientSession with the streams from streamable_http_client
"""

import asyncio
import json
from datetime import datetime
import sys
import os
from uuid import uuid4

# Add the project root to the path to access modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def attempt_registry_registration_with_clientsession():
    """Attempt to register with the registry using ClientSession."""
    print("Attempting to register with the registry using ClientSession...")
    
    try:
        # Import the required components
        from mcp.client.streamable_http import streamable_http_client
        import mcp
        import anyio
        
        print("✅ Successfully imported required components")
        
        # Connect to the registry using the proper streamable HTTP client
        registry_url = "http://localhost:6000/mcp"
        
        print(f"Connecting to registry at {registry_url}")
        
        # Use the streamable_http_client context manager
        # It returns (receive_stream, send_stream, get_session_id_callback)
        async with streamable_http_client(url=registry_url) as (receive_stream, send_stream, get_session_id_callback):
            print("✅ Successfully connected to registry with streams")
            
            # Create a ClientSession using the streams
            client_session = mcp.ClientSession(
                read_stream=receive_stream,
                write_stream=send_stream
            )
            
            # Initialize the session (this is typically required for MCP protocol)
            print("Initializing MCP session...")
            initialize_result = await client_session.initialize()
            print(f"Initialization result: {initialize_result}")
            
            # Prepare registration data based on documentation
            registration_params = {
                "name": "test-server-with-clientsession",
                "description": "A test server registered via ClientSession",
                "endpoint": "http://localhost:9000",  # Placeholder endpoint
                "capabilities": {
                    "resources": False,
                    "tools": True,
                    "prompts": False,
                    "roots": False,
                    "sampling": False
                },
                "metadata": {
                    "version": "1.0.0",
                    "author": "ClientSession Test"
                },
                "tags": ["test", "clientsession", "registration"]
            }
            
            print("Calling registry-register_server via ClientSession...")
            
            # Call the registry-register_server method using the client session
            result = await client_session.call_tool(
                "registry-register_server",
                registration_params
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
        print(f"❌ Error during registration attempt: {e}")
        import traceback
        traceback.print_exc()
        return False, {"error": str(e)}


async def main():
    """Main function to attempt registry registration."""
    print("🚀 ATTEMPTING REGISTRY REGISTRATION WITH CLIENTSESSION")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Try the ClientSession approach
    success, result = await attempt_registry_registration_with_clientsession()
    
    print("\n" + "=" * 60)
    print("📊 REGISTRATION ATTEMPT RESULTS:")
    print("=" * 60)
    
    if success:
        print("🎉 SUCCESS: Server successfully registered with the registry!")
        if isinstance(result, dict):
            print(f"   Server ID: {result.get('server_id', 'N/A')}")
            print(f"   Message: {result.get('message', 'Registration completed')}")
    else:
        print("❌ REGISTRATION FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        print("\n💡 The registry requires proper session context for registration.")
        print("   The 'Bad Request: Missing session ID' error indicates that")
        print("   individual RPC calls need proper session context, which may")
        print("   require a specific client implementation pattern.")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)