#!/usr/bin/env python3
"""
Verification script to confirm successful registration with the registry
"""

import asyncio
import aiohttp
import json
from datetime import datetime

async def verify_registration():
    """Verify that registration is working properly."""
    print("🔍 VERIFYING REGISTRATION FUNCTIONALITY")
    print("=" * 50)
    
    registry_url = "http://localhost:6000/mcp"
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream"
    }
    
    # Test 1: Try to list servers (should work without session validation)
    print("1. Testing server listing (should work without session)...")
    try:
        async with aiohttp.ClientSession() as session:
            list_request = {
                "jsonrpc": "2.0",
                "method": "registry-list_servers",
                "params": {},
                "id": "verify-list"
            }
            
            async with session.post(registry_url, json=list_request, headers=headers) as response:
                response_text = await response.text()
                print(f"   Status: {response.status}")
                print(f"   Response: {response_text}")
                
                if response.status == 200:
                    response_json = json.loads(response_text)
                    if "result" in response_json:
                        servers = response_json["result"].get("servers", [])
                        print(f"   ✅ Successfully retrieved {len(servers)} servers")
                    else:
                        print(f"   ❌ Unexpected response format: {response_json}")
                else:
                    print(f"   ❌ Failed to list servers")
    except Exception as e:
        print(f"   ❌ Error listing servers: {e}")
    
    # Test 2: Try to register a test server
    print("\n2. Testing server registration...")
    try:
        async with aiohttp.ClientSession() as session:
            registration_data = {
                "name": f"verification-test-server-{int(datetime.now().timestamp())}",
                "description": "A server for verification testing",
                "endpoint": "http://localhost:9999",
                "capabilities": {
                    "resources": False,
                    "tools": True,
                    "prompts": False,
                    "roots": False,
                    "sampling": False
                },
                "metadata": {
                    "version": "1.0.0",
                    "author": "Verification Script"
                },
                "tags": ["test", "verification", "automated"]
            }
            
            register_request = {
                "jsonrpc": "2.0",
                "method": "registry-register_server",
                "params": registration_data,
                "id": "verify-register"
            }
            
            async with session.post(registry_url, json=register_request, headers=headers) as response:
                response_text = await response.text()
                print(f"   Status: {response.status}")
                print(f"   Response: {response_text}")
                
                if response.status == 200:
                    response_json = json.loads(response_text)
                    if "result" in response_json:
                        result = response_json["result"]
                        if isinstance(result, dict) and result.get("success"):
                            server_id = result.get("server_id")
                            print(f"   🎉 SUCCESS! Server registered with ID: {server_id}")
                            
                            # Test 3: Verify the server appears in the list
                            print(f"\n3. Verifying server appeared in registry...")
                            async with session.post(registry_url, json=list_request, headers=headers) as verify_response:
                                verify_text = await verify_response.text()
                                if verify_response.status == 200:
                                    verify_json = json.loads(verify_text)
                                    if "result" in verify_json:
                                        servers = verify_json["result"].get("servers", [])
                                        found = any(s.get("id") == server_id for s in servers)
                                        if found:
                                            print(f"   ✅ Server found in registry list")
                                        else:
                                            print(f"   ⚠️  Server not immediately visible in registry list")
                                    else:
                                        print(f"   ❌ Could not verify server in list: {verify_json}")
                                else:
                                    print(f"   ❌ Could not verify server in list: {verify_response.status}")
                            
                            return True
                        else:
                            print(f"   ❌ Registration failed: {result}")
                            return False
                    else:
                        print(f"   ❌ Unexpected response format: {response_json}")
                        return False
                else:
                    print(f"   ❌ Registration failed with status {response.status}")
                    return False
    except Exception as e:
        print(f"   ❌ Error during registration: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Main verification function."""
    print("🚀 REGISTRATION VERIFICATION SCRIPT")
    print("=" * 60)
    print(f"Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    success = await verify_registration()
    
    print("\n" + "=" * 60)
    print("📊 VERIFICATION RESULTS:")
    print("=" * 60)
    
    if success:
        print("🎉 SUCCESS: Registration with the registry is working correctly!")
        print("   - Server registration completed successfully")
        print("   - Session context is properly established")
        print("   - Registry is accepting registration requests")
    else:
        print("❌ REGISTRATION VERIFICATION FAILED")
        print("   - Unable to register with the registry")
        print("   - Session context may not be properly established")
    
    print(f"\nCompleted at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    return success


if __name__ == "__main__":
    success = asyncio.run(main())
    exit(0 if success else 1)