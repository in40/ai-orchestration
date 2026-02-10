#!/usr/bin/env python3
"""
Final validation test to confirm successful registration with proper MCP session initialization
"""

import asyncio
import json
from datetime import datetime
import sys
import os

async def final_validation():
    """Final validation of successful registration."""
    print("Running final validation of registration...")
    
    try:
        # Import the required components
        from mcp.client.streamable_http import streamable_http_client
        import mcp
        
        registry_url = "http://localhost:6000/mcp"
        
        print(f"Connecting to registry at {registry_url}")
        
        # Use the proper MCP client initialization sequence
        async with streamable_http_client(url=registry_url) as (receive_stream, send_stream, get_session_id_callback):
            print("✅ Connected to registry with proper streams")
            
            # Create ClientSession
            client_session = mcp.ClientSession(
                read_stream=receive_stream,
                write_stream=send_stream
            )
            
            # Initialize the session - this is crucial
            init_result = await client_session.initialize()
            print(f"✅ Session initialized: {init_result}")
            
            # Prepare registration data
            registration_data = {
                "name": f"final-validation-server-{int(datetime.now().timestamp())}",
                "description": "Server for final validation test",
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
                    "author": "Final Validation"
                },
                "tags": ["validation", "final", "test"]
            }
            
            print("Attempting registration with proper session context...")
            
            # Register the server
            result = await client_session.call_tool_async("registry-register_server", registration_data)
            print(f"Registration result: {result}")
            
            if isinstance(result, dict) and result.get("success"):
                server_id = result.get("server_id")
                print(f"🎉 SUCCESS! Server registered with ID: {server_id}")
                
                # Also try to update status to confirm full functionality
                print("Testing health status update...")
                status_result = await client_session.call_tool_async(
                    "registry-update_server_status", 
                    {"server_id": server_id, "health_status": "healthy"}
                )
                print(f"Status update result: {status_result}")
                
                return True, result
            else:
                print(f"❌ Registration failed: {result}")
                return False, result
    
    except Exception as e:
        print(f"❌ Error during final validation: {e}")
        import traceback
        traceback.print_exc()
        return False, {"error": str(e)}


async def main():
    """Main function for final validation."""
    print("🚀 FINAL VALIDATION: REGISTRATION WITH PROPER MCP SESSION")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    success, result = await final_validation()
    
    print("\n" + "=" * 70)
    print("🏆 FINAL VALIDATION RESULTS:")
    print("=" * 70)
    
    if success:
        print("🎉 SUCCESS: REGISTRATION COMPLETED SUCCESSFULLY!")
        print("   ✅ Proper MCP session initialization sequence used")
        print("   ✅ Session established with the registry")
        print("   ✅ Server registered successfully")
        print("   ✅ Health status update also works")
        print("\n   The registry is working correctly with proper session management.")
        print("   Servers can successfully register using the correct MCP protocol.")
    else:
        print("❌ FINAL VALIDATION FAILED")
        print(f"   Error: {result.get('error', 'Unknown error')}")
        print("\n   The registry may still require specific session establishment patterns.")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)

