#!/usr/bin/env python3
"""
Proper implementation to register with the registry using the MCP protocol correctly.
"""

import asyncio
import json
from datetime import datetime
import sys
import os
from uuid import uuid4

# Add the project root to the path to access modules
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def send_jsonrpc_request(send_stream, receive_stream, method, params, request_id=None):
    """Send a JSON-RPC request and wait for response."""
    if request_id is None:
        request_id = str(uuid4())
    
    # Create JSON-RPC request
    request = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": request_id
    }
    
    # Send the request
    await send_stream.send(request)
    
    # Wait for response
    while True:
        response = await receive_stream.receive()
        # Check if this is the response to our request
        if hasattr(response, 'id') and response.id == request_id:
            return response
        # If it's a notification or other message, continue waiting


async def attempt_registry_registration_properly():
    """Attempt to register with the registry using the proper MCP protocol over streams."""
    print("Attempting to register with the registry using proper MCP protocol...")
    
    try:
        # Import the streamable HTTP client
        from mcp.client.streamable_http import streamable_http_client
        import anyio
        
        print("✅ Successfully imported streamable HTTP client")
        
        # Connect to the registry using the proper streamable HTTP client
        registry_url = "http://localhost:6000/mcp"
        
        print(f"Connecting to registry at {registry_url}")
        
        # Use the streamable_http_client context manager
        # It returns (receive_stream, send_stream, get_session_id_callback)
        async with streamable_http_client(url=registry_url, headers={"Accept": "application/json, text/event-stream"}) as (receive_stream, send_stream, get_session_id_callback):
            print("✅ Successfully connected to registry with streams")
            
            # Get session ID if available
            session_id = get_session_id_callback()
            print(f"Session ID: {session_id}")
            
            # Prepare registration data based on documentation
            registration_params = {
                "name": "test-server-proper-streams",
                "description": "A test server registered via proper MCP streams",
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
                    "author": "Proper Streams Test"
                },
                "tags": ["test", "streams", "registration"]
            }
            
            print("Sending registration request via MCP protocol...")
            
            # Create a unique request ID
            req_id = str(uuid4())
            
            # Create JSON-RPC request
            request = {
                "jsonrpc": "2.0",
                "method": "registry-register_server",
                "params": registration_params,
                "id": req_id
            }
            
            # Send the request via the send stream
            from mcp.shared.message import SessionMessage
            session_msg = SessionMessage(method=request["method"], params=request["params"], id=request["id"])
            await send_stream.send(session_msg)
            
            # Wait for response via the receive stream
            response_received = False
            timeout = 10  # 10 seconds timeout
            start_time = asyncio.get_event_loop().time()
            
            while not response_received and (asyncio.get_event_loop().time() - start_time) < timeout:
                try:
                    response_msg = await asyncio.wait_for(receive_stream.receive(), timeout=1.0)
                    
                    # Check if this is a response to our request
                    if hasattr(response_msg, 'id') and response_msg.id == req_id:
                        print(f"Received response: {response_msg}")
                        
                        # Extract result or error
                        if hasattr(response_msg, 'result'):
                            result = response_msg.result
                            print(f"Registration result: {result}")
                            
                            if isinstance(result, dict) and result.get("success"):
                                server_id = result.get("server_id")
                                print(f"🎉 SUCCESS! Server registered with ID: {server_id}")
                                return True, result
                            else:
                                print(f"❌ Registration failed: {result}")
                                return False, result
                        elif hasattr(response_msg, 'error'):
                            error = response_msg.error
                            print(f"❌ Registration error: {error}")
                            return False, {"error": error}
                        else:
                            print(f"❓ Unexpected response format: {response_msg}")
                            return False, {"error": f"Unexpected response format: {response_msg}"}
                            
                        response_received = True
                        
                except asyncio.TimeoutError:
                    print("Waiting for response...")
                    continue
                except Exception as e:
                    print(f"Error receiving response: {e}")
                    break
            
            if not response_received:
                print("❌ Timeout waiting for registration response")
                return False, {"error": "Timeout waiting for response"}
                
    except Exception as e:
        print(f"❌ Error during registration attempt: {e}")
        import traceback
        traceback.print_exc()
        return False, {"error": str(e)}


async def try_alternative_approach():
    """Try an alternative approach using the MCP client patterns."""
    print("\nTrying alternative approach...")
    
    try:
        # Let's try to see if there's a higher-level client
        # Maybe we need to use the ClientSession differently
        from mcp.client.session import ClientSession
        from mcp.client.streamable_http import streamable_http_client
        import httpx
        
        print("Creating HTTP client and attempting connection...")
        
        # Create an HTTP client to communicate with the registry
        async with httpx.AsyncClient() as http_client:
            # Prepare registration data
            registration_data = {
                "name": "test-server-alt-approach",
                "description": "A test server via alternative approach",
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
                    "author": "Alternative Approach Test"
                },
                "tags": ["test", "alt", "approach"]
            }
            
            # Create JSON-RPC request
            jsonrpc_request = {
                "jsonrpc": "2.0",
                "method": "registry-register_server",
                "params": registration_data,
                "id": str(int(datetime.now().timestamp() * 1000))
            }
            
            # Headers as specified in documentation
            headers = {
                "Content-Type": "application/json",
                "Accept": "application/json, text/event-stream"
            }
            
            print(f"Sending registration request to http://localhost:6000/mcp")
            
            # Send request directly to the registry
            response = await http_client.post(
                "http://localhost:6000/mcp",
                json=jsonrpc_request,
                headers=headers
            )
            
            print(f"Response status: {response.status_code}")
            print(f"Response text: {response.text}")
            
            try:
                response_json = response.json()
                if "result" in response_json:
                    result = response_json["result"]
                    if isinstance(result, dict) and result.get("success"):
                        server_id = result.get("server_id")
                        print(f"🎉 SUCCESS! Server registered with ID: {server_id}")
                        return True, result
                    else:
                        print(f"❌ Registration returned but not successful: {result}")
                        return False, result
                elif "error" in response_json:
                    error = response_json["error"]
                    print(f"❌ Registration failed with error: {error}")
                    return False, {"error": error}
                else:
                    print(f"❓ Unexpected response: {response_json}")
                    return False, {"error": f"Unexpected response: {response_json}"}
            except Exception as json_error:
                print(f"❌ Could not parse JSON response: {json_error}")
                return False, {"error": f"Could not parse response: {response.text}"}
    
    except Exception as e:
        print(f"❌ Alternative approach failed: {e}")
        import traceback
        traceback.print_exc()
        return False, {"error": str(e)}


async def main():
    """Main function to attempt registry registration."""
    print("🚀 ATTEMPTING ACTUAL REGISTRY REGISTRATION - PROPER IMPLEMENTATION")
    print("=" * 70)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 70)
    
    # Try the proper streams approach
    success, result = await attempt_registry_registration_properly()
    
    if not success:
        print("\n⚠️  Proper streams approach failed, trying alternative approach...")
        success, result = await try_alternative_approach()
    
    print("\n" + "=" * 70)
    print("📊 REGISTRATION ATTEMPT RESULTS:")
    print("=" * 70)
    
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
    print("=" * 70)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)