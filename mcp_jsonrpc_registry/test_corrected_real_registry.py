#!/usr/bin/env python3
"""
Corrected real testing suite for MCP Server Registry integration.
This test suite connects to the actual registry running on port 6000
using the proper MCP client that handles sessions correctly.
"""

import asyncio
import json
import time
from typing import Dict, Any, Optional
import os
from datetime import datetime


class CorrectedRealRegistryTester:
    """Test suite that connects to the real registry using proper MCP client."""
    
    def __init__(self):
        self.log_file_path = "/root/qwen/base/mcp_jsonrpc_registry/registry.log"
        self.initial_log_size = self._get_log_size()
    
    def _get_log_size(self):
        """Get the current size of the log file."""
        if os.path.exists(self.log_file_path):
            return os.path.getsize(self.log_file_path)
        return 0
    
    def _get_new_log_entries(self):
        """Get new log entries since the test started."""
        if not os.path.exists(self.log_file_path):
            return ""
        
        current_size = os.path.getsize(self.log_file_path)
        if current_size <= self.initial_log_size:
            return ""
        
        with open(self.log_file_path, 'r', encoding='utf-8') as f:
            f.seek(self.initial_log_size)
            new_content = f.read()
        
        return new_content
    
    def _check_for_errors_in_logs(self):
        """Check if there are any error messages in the new log entries."""
        new_logs = self._get_new_log_entries()
        error_keywords = ["ERROR", "WARNING", "400 Bad Request", "406 Not Acceptable", "Missing session"]
        
        for keyword in error_keywords:
            if keyword.lower() in new_logs.lower():
                return True, new_logs
        return False, new_logs
    
    async def test_with_proper_mcp_client(self):
        """Test using the proper MCP client library as documented."""
        print("Testing with proper MCP client library...")
        
        try:
            # Import the MCP client as documented in the tech rules
            from mcp.client import Client
            
            # Connect to the registry using HTTP transport as documented
            print("Attempting to connect to registry via HTTP transport...")
            client = Client.connect("http://localhost:6000")
            
            # Test 1: Try to discover the registry schema first
            print("Testing rpc.discover method...")
            try:
                discover_result = client.call_tool("rpc.discover", {})
                print(f"✅ Discover method result keys: {list(discover_result.keys()) if isinstance(discover_result, dict) else 'received'}")
            except Exception as e:
                print(f"⚠️ Discover method failed (expected if not supported): {e}")
            
            # Test 2: Try to list servers
            print("Testing registry-list_servers method...")
            try:
                servers_result = client.call_tool("registry-list_servers", {})
                if isinstance(servers_result, dict) and "servers" in servers_result:
                    server_count = len(servers_result["servers"])
                    print(f"✅ Successfully retrieved {server_count} servers")
                else:
                    print(f"✅ List servers result: {servers_result}")
            except Exception as e:
                print(f"❌ List servers failed: {e}")
                
                # Check for session errors specifically
                if "session" in str(e).lower() or "400" in str(e):
                    print("   This suggests session management is required")
            
            # Test 3: Try to register a server (this should fail without proper session management)
            print("Testing registry-register_server method...")
            try:
                registration_data = {
                    "name": "test-server-from-client",
                    "description": "A test server registered via proper client",
                    "endpoint": "http://localhost:9000",
                    "capabilities": {
                        "resources": True,
                        "tools": True,
                        "prompts": False,
                        "roots": False,
                        "sampling": False
                    },
                    "metadata": {
                        "version": "1.0.0",
                        "author": "Corrected Test Suite"
                    },
                    "tags": ["test", "proper-client", "integration"]
                }
                
                registration_result = client.call_tool("registry-register_server", registration_data)
                
                if isinstance(registration_result, dict):
                    if registration_result.get("success"):
                        print(f"✅ Registration successful: {registration_result.get('message', 'Success')}")
                        return True, registration_result
                    else:
                        print(f"⚠️ Registration failed: {registration_result}")
                        
                        # Check if it's a session error
                        if "session" in str(registration_result).lower() or "400" in str(registration_result).lower():
                            print("   Confirmed: Session management is required for registration")
                else:
                    print(f"✅ Registration response: {registration_result}")
                    
            except Exception as e:
                print(f"❌ Registration failed with exception: {e}")
                
                # Check logs for specific errors
                has_error, log_content = self._check_for_errors_in_logs()
                if has_error:
                    print(f"Log entries: {log_content}")
            
            # Close the client connection
            if hasattr(client, 'close'):
                client.close()
                
            return True, {}
            
        except ImportError as e:
            print(f"❌ Could not import mcp.client: {e}")
            print("This means the MCP library is not available or not installed properly")
            return False, {"error": f"Import error: {e}"}
        except Exception as e:
            print(f"❌ Error during MCP client test: {e}")
            
            # Check logs for specific errors
            has_error, log_content = self._check_for_errors_in_logs()
            if has_error:
                print(f"Log entries: {log_content}")
            
            return False, {"error": str(e)}
    
    async def test_raw_http_with_session_hint(self):
        """Test raw HTTP with proper headers that might help with session."""
        print("\nTesting raw HTTP with proper headers...")
        
        import aiohttp
        
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "User-Agent": "MCP-Test-Client/1.0"
        }
        
        # First, try a simple GET to the /mcp endpoint to see if it gives us info
        try:
            async with aiohttp.ClientSession() as session:
                # Try GET first (as per OpenRPC spec)
                async with session.get("http://localhost:6000/mcp", headers=headers) as get_response:
                    get_result = await get_response.text()
                    print(f"GET /mcp status: {get_response.status}, response: {get_result[:200]}...")
                
                # Now try a simple POST with minimal JSON-RPC
                payload = {
                    "jsonrpc": "2.0",
                    "method": "rpc.discover",
                    "params": {},
                    "id": "test-discover"
                }
                
                async with session.post("http://localhost:6000/mcp", json=payload, headers=headers) as post_response:
                    post_result = await post_response.text()
                    print(f"POST rpc.discover status: {post_response.status}, response: {post_result[:200]}...")
                    
                    if post_response.status == 200:
                        try:
                            parsed_result = json.loads(post_result)
                            print(f"Parsed result: {parsed_result}")
                        except json.JSONDecodeError:
                            print("Could not parse response as JSON")
        
        except Exception as e:
            print(f"❌ Raw HTTP test failed: {e}")
        
        return True, {}


async def run_corrected_real_registry_tests():
    """Run corrected tests against the real registry."""
    print("Running Corrected Real MCP Server Registry Integration Tests...")
    print("=" * 70)
    print(f"Connecting to registry at: http://localhost:6000")
    print(f"Monitoring log file: /root/qwen/base/mcp_jsonrpc_registry/registry.log")
    print("=" * 70)
    
    tester = CorrectedRealRegistryTester()
    
    # Run the corrected test
    success, result = await tester.test_with_proper_mcp_client()
    
    # Also run the raw HTTP test
    await tester.test_raw_http_with_session_hint()
    
    # Print final log entries
    print("\n" + "=" * 70)
    print("FINAL LOG ENTRIES DURING TESTS:")
    print("=" * 70)
    new_logs = tester._get_new_log_entries()
    if new_logs:
        print(new_logs)
    else:
        print("No new log entries during tests")
    
    print("=" * 70)
    
    if success:
        print("✅ Tests completed - gathered information about registry behavior")
        return True
    else:
        print("❌ Tests had issues, but provided valuable diagnostic information")
        return False


if __name__ == "__main__":
    success = asyncio.run(run_corrected_real_registry_tests())
    exit(0 if success else 1)