"""
Concurrent Request Tests for MCP Server
Tests to validate concurrent request handling functionality
"""
import asyncio
import json
import time
import threading
from typing import Dict, Any
import aiohttp
import pytest
from mcp_server.server import McpServer


class TestConcurrentRequests:
    """Test class for concurrent request handling"""
    
    def setup_method(self):
        """Set up test server instance"""
        self.server = McpServer(
            transport_type="http",
            host="127.0.0.1",
            port=3032,  # Use a different port for testing
            max_concurrent_requests=5  # Limit for testing
        )
        
        # Start server in a separate thread
        self.server_thread = threading.Thread(target=self.server.start, daemon=True)
        self.server_thread.start()
        
        # Give the server time to start
        time.sleep(2)
        
        self.base_url = "http://127.0.0.1:3032"
    
    def teardown_method(self):
        """Clean up test server"""
        self.server.stop()
    
    async def make_request(self, session: aiohttp.ClientSession, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Helper to make a JSON-RPC request"""
        payload = {
            "jsonrpc": "2.0",
            "id": f"test-{int(time.time())}",
            "method": method
        }
        
        if params:
            payload["params"] = params
            
        async with session.post(f"{self.base_url}/send", json=payload) as response:
            return await response.json()
    
    async def test_concurrent_initialize_requests(self):
        """Test multiple concurrent initialize requests"""
        async with aiohttp.ClientSession() as session:
            # Create multiple concurrent initialize requests
            tasks = [
                self.make_request(session, "initialize", {
                    "clientInfo": {
                        "name": f"test-client-{i}",
                        "version": "1.0.0"
                    }
                }) for i in range(5)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all requests were processed successfully
            for result in results:
                assert "result" in result
                assert result["result"]["serverInfo"]["name"] == "mcp-standard-server"
    
    async def test_concurrent_tools_list_requests(self):
        """Test multiple concurrent tools/list requests"""
        async with aiohttp.ClientSession() as session:
            # Create multiple concurrent tools/list requests
            tasks = [
                self.make_request(session, "tools/list") for _ in range(3)
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all requests were processed successfully
            for result in results:
                assert "result" in result
                assert "tools" in result["result"]
    
    async def test_concurrent_mixed_requests(self):
        """Test multiple concurrent mixed requests"""
        async with aiohttp.ClientSession() as session:
            # Create various concurrent requests
            tasks = [
                self.make_request(session, "initialize", {
                    "clientInfo": {"name": "test-client-1", "version": "1.0.0"}
                }),
                self.make_request(session, "tools/list"),
                self.make_request(session, "resources/list"),
                self.make_request(session, "prompts/list"),
                self.make_request(session, "initialize", {
                    "clientInfo": {"name": "test-client-2", "version": "1.0.0"}
                })
            ]
            
            results = await asyncio.gather(*tasks)
            
            # Verify all requests were processed successfully
            assert len(results) == 5
            for result in results:
                assert "result" in result
    
    async def test_concurrent_requests_with_delay(self):
        """Test concurrent requests with simulated delays in handlers"""
        # Note: This test would require modifying handlers to include artificial delays
        # For now, we'll just verify that concurrent requests don't interfere with each other
        async with aiohttp.ClientSession() as session:
            # Create multiple requests that would take time if processed sequentially
            start_time = time.time()
            
            tasks = [
                self.make_request(session, "tools/list") for _ in range(10)
            ]
            
            results = await asyncio.gather(*tasks)
            end_time = time.time()
            
            total_time = end_time - start_time
            
            # Verify all requests were processed
            assert len(results) == 10
            for result in results:
                assert "result" in result
                assert "tools" in result["result"]
            
            # The total time should be much less than if processed sequentially
            # (though this depends on the actual implementation and system)
            print(f"Processed 10 concurrent requests in {total_time:.2f} seconds")
    
    async def test_metrics_endpoint(self):
        """Test the metrics endpoint for monitoring concurrent requests"""
        async with aiohttp.ClientSession() as session:
            # First, make a few requests to populate metrics
            await self.make_request(session, "initialize", {
                "clientInfo": {"name": "test-client-metrics", "version": "1.0.0"}
            })
            
            # Then check the metrics endpoint
            async with session.get(f"{self.base_url}/metrics") as response:
                metrics = await response.json()
                
            # Verify metrics structure
            assert "current_concurrent_requests" in metrics
            assert "max_concurrent_requests" in metrics
            assert "total_requests" in metrics
            assert "completed_requests" in metrics
            assert "uptime_seconds" in metrics
            assert "requests_per_second" in metrics
            assert "average_duration_ms" in metrics


# Additional standalone test functions
async def run_concurrent_test():
    """Run a simple concurrent test to validate functionality"""
    print("Running concurrent request test...")
    
    # Create a test server
    server = McpServer(
        transport_type="http",
        host="127.0.0.1", 
        port=3033,
        max_concurrent_requests=3
    )
    
    # Start server in background
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    time.sleep(2)  # Wait for server to start
    
    try:
        async with aiohttp.ClientSession() as session:
            # Make several concurrent requests
            start_time = time.time()
            
            tasks = []
            for i in range(5):
                payload = {
                    "jsonrpc": "2.0",
                    "id": f"test-{i}",
                    "method": "initialize",
                    "params": {
                        "clientInfo": {
                            "name": f"test-client-{i}",
                            "version": "1.0.0"
                        }
                    }
                }
                
                task = session.post("http://127.0.0.1:3033/send", json=payload)
                tasks.append(task)
            
            responses = await asyncio.gather(*[await t for t in tasks])
            results = [await r.json() for r in responses]
            
            end_time = time.time()
            
            print(f"Completed 5 concurrent requests in {end_time - start_time:.2f} seconds")
            print(f"All succeeded: {all('result' in r for r in results)}")
            
            # Check metrics
            async with session.get("http://127.0.0.1:3033/metrics") as metrics_resp:
                metrics = await metrics_resp.json()
                print(f"Current concurrent: {metrics['current_concurrent_requests']}")
                print(f"Max concurrent: {metrics['max_concurrent_requests']}")
                print(f"Total requests: {metrics['total_requests']}")
    
    finally:
        server.stop()


if __name__ == "__main__":
    # Run the standalone test
    asyncio.run(run_concurrent_test())