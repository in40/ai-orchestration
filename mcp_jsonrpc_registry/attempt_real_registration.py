#!/usr/bin/env python3
"""
Actual implementation to register with the registry.
This script attempts to properly connect to the registry and register a server.
"""

import asyncio
import json
from datetime import datetime
import sys
import os

# Add the project root to the path to access modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def attempt_registry_registration():
    """Attempt to register with the registry using the proper MCP client."""
    print("Attempting to register with the registry...")
    
    try:
        # Import the MCP client components
        from mcp.client.streamable_http import streamable_http_client
        import aiohttp
        
        print("✅ Successfully imported MCP client components")
        
        # Create a proper client connection to the registry
        # The registry is running at http://localhost:6000/mcp
        registry_url = "http://localhost:6000/mcp"
        
        print(f"Connecting to registry at {registry_url}")
        
        # Try to create a client using the streamable HTTP transport
        # This is the proper way to establish a session with the registry
        async with streamable_http_client(url=registry_url) as client:
            print("✅ Successfully connected to registry with session context")
            
            # Prepare registration data based on documentation
            registration_data = {
                "name": "test-server-successful-registration",
                "description": "A test server registered via proper MCP client",
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
                    "author": "Real Registration Test"
                },
                "tags": ["test", "registration", "success"]
            }
            
            print("Attempting to register server...")
            
            # Call the registry-register_server method using the client
            # This should work because the session context is properly established
            result = await client.call_tool_async("registry-register_server", registration_data)
            
            print(f"Registration result: {result}")
            
            if isinstance(result, dict) and result.get("success"):
                server_id = result.get("server_id")
                print(f"🎉 SUCCESS! Server registered with ID: {server_id}")
                return True, result
            else:
                print(f"❌ Registration failed: {result}")
                return False, result
                
    except ImportError as e:
        print(f"❌ Could not import required MCP client components: {e}")
        print("This suggests the exact API for streamable_http_client may be different")
        
        # Let's try to find the correct way to connect
        try:
            # Try importing the client session approach
            from mcp.client.session import ClientSession
            print("✅ Found ClientSession, trying alternative approach...")
            
            # This is a different approach - let's see if we can create a session
            async with ClientSession() as session:
                # Connect to the registry
                await session.initialize(url="http://localhost:6000/mcp")
                print("✅ Connected via ClientSession")
                
                # Try registration
                registration_data = {
                    "name": "test-server-via-session",
                    "description": "A test server via ClientSession",
                    "endpoint": "http://localhost:9001",
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
                    "tags": ["test", "session", "attempt"]
                }
                
                result = await session.call_tool_async("registry-register_server", registration_data)
                print(f"ClientSession registration result: {result}")
                
                if isinstance(result, dict) and result.get("success"):
                    server_id = result.get("server_id")
                    print(f"🎉 SUCCESS! Server registered with ID: {server_id}")
                    return True, result
                else:
                    print(f"❌ ClientSession registration failed: {result}")
                    return False, result
                    
        except Exception as session_e:
            print(f"❌ ClientSession approach also failed: {session_e}")
            return False, {"error": f"Both approaches failed - import: {e}, session: {session_e}"}
    
    except Exception as e:
        print(f"❌ Error during registration attempt: {e}")
        import traceback
        traceback.print_exc()
        return False, {"error": str(e)}


async def try_basic_client_approach():
    """Try a more basic client approach if the advanced ones don't work."""
    print("\nTrying basic client approach...")
    
    try:
        # Let's try to see what's available in the mcp.client module
        import mcp.client as mcpc
        
        # Check what's available
        print(f"Available in mcp.client: {[item for item in dir(mcpc) if not item.startswith('_')]}")
        
        # Try to see if there's a direct way to connect
        # Let's look at the streamable_http module more closely
        import mcp.client.streamable_http as sh
        
        print(f"Available in streamable_http: {[item for item in dir(sh) if 'client' in item.lower() or 'connect' in item.lower()]}")
        
        # Try to use create_mcp_http_client if it exists
        if hasattr(sh, 'create_mcp_http_client'):
            print("Found create_mcp_http_client, attempting connection...")
            client = await sh.create_mcp_http_client(url="http://localhost:6000/mcp")
            
            registration_data = {
                "name": "test-server-create-client",
                "description": "A test server via create_mcp_http_client",
                "endpoint": "http://localhost:9002",
                "capabilities": {
                    "resources": False,
                    "tools": True,
                    "prompts": False,
                    "roots": False,
                    "sampling": False
                },
                "metadata": {
                    "version": "1.0.0",
                    "author": "CreateClient Test"
                },
                "tags": ["test", "create", "attempt"]
            }
            
            result = await client.call_tool_async("registry-register_server", registration_data)
            print(f"create_mcp_http_client result: {result}")
            
            if isinstance(result, dict) and result.get("success"):
                server_id = result.get("server_id")
                print(f"🎉 SUCCESS! Server registered with ID: {server_id}")
                return True, result
            else:
                print(f"❌ create_mcp_http_client registration failed: {result}")
                return False, result
        else:
            print("create_mcp_http_client not available")
            return False, {"error": "No suitable client creation method found"}
    
    except Exception as e:
        print(f"❌ Basic client approach failed: {e}")
        import traceback
        traceback.print_exc()
        return False, {"error": str(e)}


async def main():
    """Main function to attempt registry registration."""
    print("🚀 ATTEMPTING ACTUAL REGISTRY REGISTRATION")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Try the advanced client approach
    success, result = await attempt_registry_registration()
    
    if not success:
        # If that fails, try the basic approach
        print("\n⚠️  Advanced approach failed, trying basic approach...")
        success, result = await try_basic_client_approach()
    
    print("\n" + "=" * 60)
    print("📊 REGISTRATION ATTEMPT RESULTS:")
    print("=" * 60)
    
    if success:
        print("🎉 SUCCESS: Server successfully registered with the registry!")
        print(f"   Server ID: {result.get('server_id', 'N/A')}")
        print(f"   Message: {result.get('message', 'Registration completed')}")
    else:
        print("❌ REGISTRATION FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        print("\n💡 The registry requires proper session context for registration.")
        print("   This may require specific MCP client library usage patterns")
        print("   that are not immediately apparent from the available modules.")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)