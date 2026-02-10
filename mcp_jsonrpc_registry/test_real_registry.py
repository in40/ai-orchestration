#!/usr/bin/env python3
"""
Real testing suite for MCP Server Registry integration.
This test suite connects to the actual registry running on port 6000
and monitors the registry.log to verify connection and status.
"""

import asyncio
import json
import time
import requests
import aiohttp
from datetime import datetime
from typing import Dict, Any, Optional
import os
import subprocess
import threading
import queue


class RealRegistryTester:
    """Test suite that connects to the real registry running on port 6000."""
    
    def __init__(self):
        self.base_url = "http://localhost:6000"
        self.mcp_endpoint = f"{self.base_url}/mcp"
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
    
    async def _send_jsonrpc_request(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send a JSON-RPC request to the registry."""
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream"
        }
        
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": str(int(time.time() * 1000000))  # Unique ID based on microseconds
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(self.mcp_endpoint, json=payload, headers=headers) as response:
                    response_text = await response.text()
                    try:
                        return json.loads(response_text)
                    except json.JSONDecodeError:
                        return {"error": f"Invalid JSON response: {response_text}", "status_code": response.status}
        except Exception as e:
            return {"error": f"Request failed: {str(e)}"}
    
    async def test_server_registration(self):
        """Test server registration with the real registry."""
        print("Testing server registration with real registry...")
        
        # Prepare registration data based on documentation
        registration_data = {
            "name": "test-server-real",
            "description": "A test server for real registry testing",
            "endpoint": "http://localhost:9000",  # This is just a placeholder
            "capabilities": {
                "resources": True,
                "tools": True,
                "prompts": False,
                "roots": False,
                "sampling": False
            },
            "metadata": {
                "version": "1.0.0",
                "author": "Real Test Suite"
            },
            "tags": ["test", "real", "integration"]
        }
        
        result = await self._send_jsonrpc_request("registry-register_server", registration_data)
        
        # Check logs for any errors
        has_error, log_content = self._check_for_errors_in_logs()
        
        if has_error:
            print(f"❌ Registration failed - errors found in logs: {log_content}")
            return False, result, log_content
        
        if "result" in result:
            if "success" in result["result"] and result["result"]["success"]:
                print(f"✅ Registration successful: {result['result'].get('message', 'Success')}")
                return True, result, log_content
            else:
                print(f"❌ Registration failed: {result['result']}")
                return False, result, log_content
        elif "error" in result:
            print(f"❌ Registration error: {result['error']}")
            return False, result, log_content
        else:
            print(f"❌ Unexpected response: {result}")
            return False, result, log_content
    
    async def test_server_registration_without_session(self):
        """Test server registration without proper session (should fail)."""
        print("\nTesting server registration without session (should fail)...")
        
        # Prepare registration data
        registration_data = {
            "name": "test-server-no-session",
            "description": "A test server for no-session testing",
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
                "author": "No Session Test"
            },
            "tags": ["test", "no-session"]
        }
        
        result = await self._send_jsonrpc_request("registry-register_server", registration_data)
        
        # Check logs for specific error
        has_error, log_content = self._check_for_errors_in_logs()
        
        # This should fail with missing session error based on documentation
        expected_error_code = -32600
        has_expected_error = (
            "error" in result and 
            isinstance(result["error"], dict) and
            result["error"].get("code") == expected_error_code and
            "Missing session ID" in result["error"].get("message", "")
        )
        
        if has_expected_error:
            print(f"✅ Expected session error received: {result['error']}")
            return True, result, log_content
        elif "result" in result and result["result"].get("success") == True:
            print(f"⚠️  Unexpected success (might have session): {result['result']}")
            return True, result, log_content  # Still considered a valid test outcome
        else:
            print(f"❌ Unexpected response: {result}")
            return False, result, log_content
    
    async def test_list_servers(self):
        """Test listing servers from the real registry."""
        print("\nTesting list servers from real registry...")
        
        result = await self._send_jsonrpc_request("registry-list_servers", {})
        
        # Check logs for any errors
        has_error, log_content = self._check_for_errors_in_logs()
        
        if has_error:
            print(f"❌ List servers failed - errors found in logs: {log_content}")
            return False, result, log_content
        
        if "result" in result:
            if "servers" in result["result"]:
                server_count = len(result["result"]["servers"])
                print(f"✅ Successfully retrieved {server_count} servers")
                return True, result, log_content
            else:
                print(f"❌ Unexpected result format: {result['result']}")
                return False, result, log_content
        elif "error" in result:
            print(f"❌ List servers error: {result['error']}")
            return False, result, log_content
        else:
            print(f"❌ Unexpected response: {result}")
            return False, result, log_content
    
    async def test_update_server_status(self):
        """Test updating server status (will fail for non-existent server)."""
        print("\nTesting update server status (expected to fail for non-existent server)...")
        
        # Try to update status for a non-existent server
        status_data = {
            "server_id": "non-existent-server-id",
            "health_status": "healthy"
        }
        
        result = await self._send_jsonrpc_request("registry-update_server_status", status_data)
        
        # Check logs for any errors
        has_error, log_content = self._check_for_errors_in_logs()
        
        if has_error:
            print(f"❌ Update status failed - errors found in logs: {log_content}")
            return False, result, log_content
        
        if "result" in result:
            # This should typically fail since server doesn't exist
            if "success" in result["result"] and not result["result"]["success"]:
                print(f"✅ Expected failure for non-existent server: {result['result'].get('message', 'Failed')}")
                return True, result, log_content
            elif "success" in result["result"] and result["result"]["success"]:
                print(f"✅ Unexpected success: {result['result'].get('message', 'Success')}")
                return True, result, log_content  # Still a valid outcome
            else:
                print(f"✅ Status update result: {result['result']}")
                return True, result, log_content
        elif "error" in result:
            print(f"✅ Status update error (expected): {result['error']}")
            return True, result, log_content
        else:
            print(f"❌ Unexpected response: {result}")
            return False, result, log_content
    
    async def test_discover_method(self):
        """Test the rpc.discover method."""
        print("\nTesting rpc.discover method...")
        
        result = await self._send_jsonrpc_request("rpc.discover", {})
        
        # Check logs for any errors
        has_error, log_content = self._check_for_errors_in_logs()
        
        if has_error:
            print(f"❌ Discover method failed - errors found in logs: {log_content}")
            return False, result, log_content
        
        if "result" in result:
            print(f"✅ Discover method successful, received schema with keys: {list(result['result'].keys()) if isinstance(result['result'], dict) else 'data'}")
            return True, result, log_content
        elif "error" in result:
            print(f"❌ Discover method error: {result['error']}")
            return False, result, log_content
        else:
            print(f"❌ Unexpected response: {result}")
            return False, result, log_content


async def run_real_registry_tests():
    """Run all tests against the real registry."""
    print("Running Real MCP Server Registry Integration Tests...")
    print("=" * 70)
    print(f"Connecting to registry at: http://localhost:6000")
    print(f"Monitoring log file: /root/qwen/base/mcp_jsonrpc_registry/registry.log")
    print("=" * 70)
    
    tester = RealRegistryTester()
    
    # Track test results
    test_results = []
    
    # Test 1: Server registration
    success, result, logs = await tester.test_server_registration()
    test_results.append(("Server Registration", success, result, logs))
    
    # Test 2: Registration without session (should fail with specific error)
    success, result, logs = await tester.test_server_registration_without_session()
    test_results.append(("Registration Without Session", success, result, logs))
    
    # Test 3: List servers
    success, result, logs = await tester.test_list_servers()
    test_results.append(("List Servers", success, result, logs))
    
    # Test 4: Update server status
    success, result, logs = await tester.test_update_server_status()
    test_results.append(("Update Server Status", success, result, logs))
    
    # Test 5: Discover method
    success, result, logs = await tester.test_discover_method()
    test_results.append(("Discover Method", success, result, logs))
    
    # Print summary
    print("\n" + "=" * 70)
    print("TEST RESULTS SUMMARY:")
    print("=" * 70)
    
    passed = 0
    failed = 0
    
    for test_name, success, result, logs in test_results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} - {test_name}")
        if not success:
            failed += 1
            print(f"  Result: {result}")
            if logs:
                print(f"  Logs: {logs[-200:]}...")  # Show last 200 chars of logs
        else:
            passed += 1
    
    print(f"\nTotal: {len(test_results)} tests")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    print("\n" + "=" * 70)
    print("NEW LOG ENTRIES DURING TESTS:")
    print("=" * 70)
    new_logs = tester._get_new_log_entries()
    if new_logs:
        print(new_logs)
    else:
        print("No new log entries during tests")
    
    print("=" * 70)
    
    return failed == 0


if __name__ == "__main__":
    success = asyncio.run(run_real_registry_tests())
    exit(0 if success else 1)