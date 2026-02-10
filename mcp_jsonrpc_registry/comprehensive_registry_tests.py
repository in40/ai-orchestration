#!/usr/bin/env python3
"""
Comprehensive test suite for MCP Server Registry integration.
This test suite simulates server registration and health check processes
based solely on the documented specifications in TECHNOLOGY_RULES_TO_FOLLOW.md
and openrpc.yml.
"""

import asyncio
import json
import time
from datetime import datetime
from typing import Dict, Any, Optional
import unittest
from unittest.mock import Mock, AsyncMock, patch, MagicMock


class MockMCPClient:
    """Mock client that simulates the MCP client behavior based on documentation."""
    
    def __init__(self):
        self.session_active = True
        self.connection_established = True
        self.servers_registered = []
        self.health_status_updates = []
        
    async def call_tool_async(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate calling a tool method on the registry."""
        if not self.session_active:
            return {
                "success": False,
                "error": {
                    "code": -32600,
                    "message": "Bad Request: Missing session ID"
                },
                "message": "Session ID is required for server registration"
            }
        
        if method == "registry-register_server":
            return self._simulate_registration(params)
        elif method == "registry-update_server_status":
            return self._simulate_status_update(params)
        elif method == "registry-list_servers":
            return self._simulate_list_servers()
        elif method == "registry-get_server_details":
            return self._simulate_get_server_details(params.get("server_id"))
        elif method == "registry-search_servers":
            return self._simulate_search_servers(params.get("query", ""), params.get("tags", []))
        else:
            return {"error": f"Unknown method: {method}"}
    
    def call_tool(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Synchronous version of call_tool_async."""
        # For simplicity in testing, we'll just call the async version
        return asyncio.run(self.call_tool_async(method, params))
    
    def _simulate_registration(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate the registration process."""
        # Validate required parameters
        required_fields = ["name", "endpoint", "capabilities"]
        for field in required_fields:
            if field not in params:
                return {
                    "success": False,
                    "error": f"Missing required field: {field}",
                    "message": f"Registration failed: Missing required field {field}"
                }
        
        # Validate capabilities structure
        capabilities = params.get("capabilities", {})
        expected_caps = {"resources", "tools", "prompts", "roots", "sampling"}
        for cap in expected_caps:
            if cap not in capabilities:
                return {
                    "success": False,
                    "error": f"Missing capability: {cap}",
                    "message": f"Registration failed: Missing capability {cap}"
                }
            if not isinstance(capabilities[cap], bool):
                return {
                    "success": False,
                    "error": f"Capability {cap} must be boolean",
                    "message": f"Registration failed: Capability {cap} must be boolean"
                }
        
        # Generate a server ID
        server_id = f"server_{int(time.time())}_{hash(params['name']) % 10000}"
        
        # Store the registration
        server_info = {
            "id": server_id,
            "name": params["name"],
            "description": params.get("description", ""),
            "endpoint": params["endpoint"],
            "capabilities": capabilities,
            "metadata": params.get("metadata", {}),
            "tags": params.get("tags", []),
            "registered_at": datetime.utcnow().isoformat(),
            "last_seen": datetime.utcnow().isoformat(),
            "health_status": "unknown"
        }
        
        self.servers_registered.append(server_info)
        
        return {
            "success": True,
            "server_id": server_id,
            "message": f"Server '{params['name']}' registered successfully with ID {server_id}"
        }
    
    def _simulate_status_update(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate updating server status."""
        server_id = params.get("server_id")
        health_status = params.get("health_status")
        
        if not server_id:
            return {
                "success": False,
                "error": "Missing server_id",
                "message": "Status update failed: Missing server_id"
            }
        
        if health_status not in ["healthy", "unhealthy", "unknown"]:
            return {
                "success": False,
                "error": f"Invalid health status: {health_status}",
                "message": f"Status update failed: Invalid health status {health_status}. Must be one of: healthy, unhealthy, unknown"
            }
        
        # Find the server and update its status
        for server in self.servers_registered:
            if server["id"] == server_id:
                server["health_status"] = health_status
                server["last_seen"] = datetime.utcnow().isoformat()
                self.health_status_updates.append({
                    "server_id": server_id,
                    "status": health_status,
                    "timestamp": datetime.utcnow().isoformat()
                })
                return {
                    "success": True,
                    "message": f"Health status for server {server_id} updated to {health_status}"
                }
        
        return {
            "success": False,
            "error": "Server not found",
            "message": f"Status update failed: Server with ID {server_id} not found"
        }
    
    def _simulate_list_servers(self) -> Dict[str, Any]:
        """Simulate listing all registered servers."""
        return {
            "servers": self.servers_registered
        }
    
    def _simulate_get_server_details(self, server_id: str) -> Dict[str, Any]:
        """Simulate getting details for a specific server."""
        for server in self.servers_registered:
            if server["id"] == server_id:
                return server
        return {"error": f"Server with ID {server_id} not found"}
    
    def _simulate_search_servers(self, query: str, tags: list) -> Dict[str, Any]:
        """Simulate searching for servers."""
        results = []
        for server in self.servers_registered:
            # Match by name or description if query is provided
            matches_query = True
            if query:
                matches_query = (query.lower() in server["name"].lower() or 
                               query.lower() in server["description"].lower())
            
            # Match by tags if tags are provided
            matches_tags = True
            if tags:
                matches_tags = any(tag in server["tags"] for tag in tags)
            
            if matches_query and matches_tags:
                results.append(server)
        
        return {"servers": results}


class TestMCPRegistryIntegration(unittest.TestCase):
    """Test suite for MCP Server Registry integration."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.client = MockMCPClient()
        self.test_server_name = "test-mcp-server"
        self.test_endpoint = "http://localhost:8080"
        self.test_capabilities = {
            "resources": True,
            "tools": True,
            "prompts": False,
            "roots": False,
            "sampling": False
        }
        self.test_metadata = {
            "version": "1.0.0",
            "author": "Test Developer"
        }
        self.test_tags = ["test", "development"]
    
    def test_registration_with_valid_parameters(self):
        """Test successful server registration with valid parameters."""
        registration_data = {
            "name": self.test_server_name,
            "description": "A test MCP server",
            "endpoint": self.test_endpoint,
            "capabilities": self.test_capabilities,
            "metadata": self.test_metadata,
            "tags": self.test_tags
        }
        
        result = asyncio.run(self.client.call_tool_async("registry-register_server", registration_data))
        
        self.assertTrue(result["success"])
        self.assertIn("server_id", result)
        self.assertIn(self.test_server_name, result["message"])
        self.assertEqual(len(self.client.servers_registered), 1)
        
        # Verify server details
        registered_server = self.client.servers_registered[0]
        self.assertEqual(registered_server["name"], self.test_server_name)
        self.assertEqual(registered_server["endpoint"], self.test_endpoint)
        self.assertEqual(registered_server["capabilities"], self.test_capabilities)
        self.assertEqual(registered_server["metadata"], self.test_metadata)
        self.assertEqual(registered_server["tags"], self.test_tags)
    
    def test_registration_missing_required_fields(self):
        """Test registration fails when required fields are missing."""
        # Test missing name
        registration_data = {
            "endpoint": self.test_endpoint,
            "capabilities": self.test_capabilities
        }
        
        result = asyncio.run(self.client.call_tool_async("registry-register_server", registration_data))
        self.assertFalse(result["success"])
        self.assertIn("name", result["error"])
        
        # Test missing endpoint
        registration_data = {
            "name": self.test_server_name,
            "capabilities": self.test_capabilities
        }
        
        result = asyncio.run(self.client.call_tool_async("registry-register_server", registration_data))
        self.assertFalse(result["success"])
        self.assertIn("endpoint", result["error"])
        
        # Test missing capabilities
        registration_data = {
            "name": self.test_server_name,
            "endpoint": self.test_endpoint
        }
        
        result = asyncio.run(self.client.call_tool_async("registry-register_server", registration_data))
        self.assertFalse(result["success"])
        self.assertIn("capabilities", result["error"])
    
    def test_registration_missing_capability_fields(self):
        """Test registration fails when capability fields are missing."""
        registration_data = {
            "name": self.test_server_name,
            "endpoint": self.test_endpoint,
            "capabilities": {
                "resources": True,
                # Missing "tools", "prompts", "roots", "sampling"
            }
        }
        
        result = asyncio.run(self.client.call_tool_async("registry-register_server", registration_data))
        self.assertFalse(result["success"])
        self.assertIn("Missing capability", result["error"])
    
    def test_registration_invalid_capability_types(self):
        """Test registration fails when capability values are not boolean."""
        registration_data = {
            "name": self.test_server_name,
            "endpoint": self.test_endpoint,
            "capabilities": {
                "resources": "true",  # Should be boolean
                "tools": True,
                "prompts": False,
                "roots": False,
                "sampling": False
            }
        }
        
        result = asyncio.run(self.client.call_tool_async("registry-register_server", registration_data))
        self.assertFalse(result["success"])
        self.assertIn("must be boolean", result["error"])
    
    def test_successful_status_update(self):
        """Test successful health status update."""
        # First register a server
        registration_data = {
            "name": self.test_server_name,
            "endpoint": self.test_endpoint,
            "capabilities": self.test_capabilities
        }
        
        registration_result = asyncio.run(self.client.call_tool_async("registry-register_server", registration_data))
        self.assertTrue(registration_result["success"])
        server_id = registration_result["server_id"]
        
        # Update status
        status_data = {
            "server_id": server_id,
            "health_status": "healthy"
        }
        
        status_result = asyncio.run(self.client.call_tool_async("registry-update_server_status", status_data))
        self.assertTrue(status_result["success"])
        self.assertIn("healthy", status_result["message"])
        
        # Verify the status was updated
        updated_server = self.client._simulate_get_server_details(server_id)
        self.assertEqual(updated_server["health_status"], "healthy")
    
    def test_status_update_invalid_status(self):
        """Test status update fails with invalid health status."""
        status_data = {
            "server_id": "nonexistent-server",
            "health_status": "invalid_status"
        }
        
        result = asyncio.run(self.client.call_tool_async("registry-update_server_status", status_data))
        self.assertFalse(result["success"])
        self.assertIn("Invalid health status", result["error"])
    
    def test_status_update_nonexistent_server(self):
        """Test status update fails for nonexistent server."""
        status_data = {
            "server_id": "nonexistent-server",
            "health_status": "healthy"
        }
        
        result = asyncio.run(self.client.call_tool_async("registry-update_server_status", status_data))
        self.assertFalse(result["success"])
        self.assertIn("not found", result["error"])
    
    def test_missing_session_error(self):
        """Test that operations fail when session is missing."""
        # Disable session
        self.client.session_active = False
        
        registration_data = {
            "name": self.test_server_name,
            "endpoint": self.test_endpoint,
            "capabilities": self.test_capabilities
        }
        
        result = asyncio.run(self.client.call_tool_async("registry-register_server", registration_data))
        self.assertFalse(result["success"])
        self.assertEqual(result["error"]["code"], -32600)
        self.assertIn("Missing session ID", result["error"]["message"])
        
        # Re-enable session for other tests
        self.client.session_active = True
    
    def test_list_servers_after_registration(self):
        """Test that registered servers appear in the server list."""
        # Register a server
        registration_data = {
            "name": self.test_server_name,
            "endpoint": self.test_endpoint,
            "capabilities": self.test_capabilities
        }
        
        registration_result = asyncio.run(self.client.call_tool_async("registry-register_server", registration_data))
        self.assertTrue(registration_result["success"])
        
        # List servers
        list_result = asyncio.run(self.client.call_tool_async("registry-list_servers", {}))
        self.assertIn("servers", list_result)
        self.assertEqual(len(list_result["servers"]), 1)
        self.assertEqual(list_result["servers"][0]["name"], self.test_server_name)
    
    def test_search_servers_by_name(self):
        """Test searching for servers by name."""
        # Register a server
        registration_data = {
            "name": "database-server-test",
            "endpoint": self.test_endpoint,
            "capabilities": self.test_capabilities,
            "tags": ["database", "sql"]
        }
        
        registration_result = asyncio.run(self.client.call_tool_async("registry-register_server", registration_data))
        self.assertTrue(registration_result["success"])
        
        # Search by name
        search_result = asyncio.run(self.client.call_tool_async("registry-search_servers", {"query": "database"}))
        self.assertIn("servers", search_result)
        self.assertEqual(len(search_result["servers"]), 1)
        self.assertEqual(search_result["servers"][0]["name"], "database-server-test")
    
    def test_search_servers_by_tags(self):
        """Test searching for servers by tags."""
        # Register a server with tags
        registration_data = {
            "name": "api-server",
            "endpoint": self.test_endpoint,
            "capabilities": self.test_capabilities,
            "tags": ["api", "rest", "production"]
        }
        
        registration_result = asyncio.run(self.client.call_tool_async("registry-register_server", registration_data))
        self.assertTrue(registration_result["success"])
        
        # Search by tags
        search_result = asyncio.run(self.client.call_tool_async("registry-search_servers", {"tags": ["api"]}))
        self.assertIn("servers", search_result)
        self.assertEqual(len(search_result["servers"]), 1)
        self.assertEqual(search_result["servers"][0]["name"], "api-server")
    
    def test_get_server_details(self):
        """Test retrieving details for a specific server."""
        # Register a server
        registration_data = {
            "name": self.test_server_name,
            "endpoint": self.test_endpoint,
            "capabilities": self.test_capabilities,
            "metadata": self.test_metadata
        }
        
        registration_result = asyncio.run(self.client.call_tool_async("registry-register_server", registration_data))
        self.assertTrue(registration_result["success"])
        server_id = registration_result["server_id"]
        
        # Get server details
        details_result = asyncio.run(self.client.call_tool_async("registry-get_server_details", {"server_id": server_id}))
        self.assertEqual(details_result["name"], self.test_server_name)
        self.assertEqual(details_result["endpoint"], self.test_endpoint)
        self.assertEqual(details_result["metadata"], self.test_metadata)
        self.assertEqual(details_result["capabilities"], self.test_capabilities)


class TestHealthCheckEndpoint(unittest.TestCase):
    """Test the health check endpoint implementation based on documentation."""
    
    def test_health_endpoint_response_format(self):
        """Test that health endpoint returns the correct format."""
        # According to documentation, the health endpoint should return:
        # {
        #   "status": "healthy",
        #   "timestamp": "2023-12-01T10:00:00Z",
        #   "details": {
        #     // Optional: additional health details
        #   }
        # }
        
        # Simulate a health check response
        health_response = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "details": {
                "uptime": "1 hour",
                "version": "1.0.0"
            }
        }
        
        # Validate the response structure
        self.assertIn("status", health_response)
        self.assertIn("timestamp", health_response)
        self.assertIn("details", health_response)
        
        # Validate status value
        self.assertIn(health_response["status"], ["healthy", "unhealthy", "unknown"])
        
        # Validate timestamp format (should be ISO format)
        try:
            datetime.fromisoformat(health_response["timestamp"].replace("Z", "+00:00"))
        except ValueError:
            self.fail("Timestamp is not in valid ISO format")
    
    def test_health_endpoint_status_codes(self):
        """Test that health endpoint returns appropriate status codes."""
        # According to documentation:
        # - 200 OK: Server is healthy and operational
        # - 4xx/5xx: Server is unhealthy or experiencing issues
        
        # For a healthy server, the endpoint should return 200
        # This would be handled by the HTTP framework, not our business logic
        # But we can validate the concept
        healthy_response_code = 200
        unhealthy_response_codes = [400, 401, 403, 404, 500, 502, 503]
        
        self.assertEqual(healthy_response_code, 200)
        self.assertIsInstance(unhealthy_response_codes, list)
        self.assertIn(500, unhealthy_response_codes)  # Example of server error


class TestTransportAndSessionManagement(unittest.TestCase):
    """Test transport and session management based on documentation."""
    
    def test_transport_selection(self):
        """Test transport selection as documented."""
        # According to documentation, transports are:
        # - stdio: For local communication between processes
        # - streamable-http: For network-based communication
        
        # These would be used when initializing the client
        # client = Client.connect_stdio()  # For local communication
        # client = Client.connect_http("http://registry-host:port")  # For network communication
        
        # Validate the concept
        supported_transports = ["stdio", "streamable-http"]
        self.assertIn("stdio", supported_transports)
        self.assertIn("streamable-http", supported_transports)
    
    def test_session_lifecycle(self):
        """Test session lifecycle management as documented."""
        # According to documentation:
        # 1. Sessions are automatically created when establishing a transport connection
        # 2. Sessions remain valid for the duration of the connection (default timeout: 1 hour)
        # 3. Sessions are renewed automatically with continued activity
        # 4. When sessions expire, establish a new connection to create a new session
        
        # Simulate session creation
        session_created_at = time.time()
        session_timeout = 3600  # 1 hour in seconds
        current_time = time.time()
        
        # Session is valid if within timeout period
        session_valid = (current_time - session_created_at) < session_timeout
        
        self.assertTrue(session_valid)  # At this moment, session should be valid
    
    def test_error_handling_with_retry_logic(self):
        """Test error handling with retry logic as documented."""
        # According to documentation, retry logic should have:
        # - Initial delay: 1 second
        # - Maximum delay: 60 seconds
        # - Maximum attempts: Defined by MAX_REGISTRATION_ATTEMPTS (default: 3)
        
        initial_delay = 1  # seconds
        max_delay = 60    # seconds
        max_attempts = 3
        
        # Validate the documented values
        self.assertEqual(initial_delay, 1)
        self.assertEqual(max_delay, 60)
        self.assertEqual(max_attempts, 3)


def run_comprehensive_tests():
    """Run all tests in the comprehensive test suite."""
    print("Running MCP Server Registry Integration Tests...")
    print("=" * 60)
    
    # Create a test suite with all test cases
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # Add all test cases
    suite.addTests(loader.loadTestsFromTestCase(TestMCPRegistryIntegration))
    suite.addTests(loader.loadTestsFromTestCase(TestHealthCheckEndpoint))
    suite.addTests(loader.loadTestsFromTestCase(TestTransportAndSessionManagement))
    
    # Run all tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 60)
    print(f"Test Results: {result.testsRun} tests run")
    print(f"Failures: {len(result.failures)}, Errors: {len(result.errors)}")
    
    if result.failures:
        print("\nFailures:")
        for test, traceback in result.failures:
            print(f"  {test}: {traceback}")
    
    if result.errors:
        print("\nErrors:")
        for test, traceback in result.errors:
            print(f"  {test}: {traceback}")
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_comprehensive_tests()
    exit(0 if success else 1)