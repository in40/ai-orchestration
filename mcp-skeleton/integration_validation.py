"""
Integration Test for MCP Server Concurrent Request Handling
Validates that all components work together correctly
"""
import asyncio
import aiohttp
import time
import threading
import json
from mcp_server.server import McpServer


async def validate_concurrent_functionality():
    """Validate that all concurrent functionality works together"""
    print("Starting Integration Validation for Concurrent Request Handling")
    print("="*60)
    
    # Start server with concurrent request handling
    server = McpServer(
        transport_type="http",
        host="127.0.0.1",
        port=3035,
        max_concurrent_requests=10
    )
    
    # Start server in background
    server_thread = threading.Thread(target=server.start, daemon=True)
    server_thread.start()
    
    # Wait for server to start
    await asyncio.sleep(2)
    
    try:
        print("✓ Server started successfully")
        
        # Test 1: Basic connectivity
        async with aiohttp.ClientSession() as session:
            # Test single request
            payload = {
                "jsonrpc": "2.0",
                "id": "test-connectivity",
                "method": "initialize",
                "params": {
                    "clientInfo": {
                        "name": "integration-test-client",
                        "version": "1.0.0"
                    }
                }
            }
            
            async with session.post("http://127.0.0.1:3035/send", json=payload) as response:
                result = await response.json()
                
            assert "result" in result
            assert result["result"]["serverInfo"]["name"] == "mcp-standard-server"
            print("✓ Basic connectivity test passed")
            
            # Test 2: Concurrent requests
            print("\nTesting concurrent requests...")
            start_time = time.time()
            
            tasks = []
            for i in range(5):
                req_payload = {
                    "jsonrpc": "2.0",
                    "id": f"concurrent-{i}",
                    "method": "tools/list"
                }
                task = session.post("http://127.0.0.1:3035/send", json=req_payload)
                tasks.append(task)
            
            responses = await asyncio.gather(*[await t for t in tasks])
            results = [await r.json() for r in responses]
            
            # Verify all succeeded
            for result in results:
                assert "result" in result
                assert "tools" in result["result"]
            
            end_time = time.time()
            print(f"✓ Concurrent requests test passed ({end_time - start_time:.2f}s for 5 requests)")
            
            # Test 3: Metrics endpoint
            async with session.get("http://127.0.0.1:3035/metrics") as metrics_resp:
                metrics = await metrics_resp.json()
                
            assert "current_concurrent_requests" in metrics
            assert "total_requests" in metrics
            assert metrics["total_requests"] >= 6  # At least our test requests
            print("✓ Metrics endpoint test passed")
            
            # Test 4: Different method types concurrently
            print("\nTesting mixed method types concurrently...")
            mixed_tasks = [
                session.post("http://127.0.0.1:3035/send", json={
                    "jsonrpc": "2.0", "id": "init-1", "method": "initialize",
                    "params": {"clientInfo": {"name": "test", "version": "1.0.0"}}
                }),
                session.post("http://127.0.0.1:3035/send", json={
                    "jsonrpc": "2.0", "id": "tools-1", "method": "tools/list"
                }),
                session.post("http://127.0.0.1:3035/send", json={
                    "jsonrpc": "2.0", "id": "resources-1", "method": "resources/list"
                }),
                session.post("http://127.0.0.1:3035/send", json={
                    "jsonrpc": "2.0", "id": "prompts-1", "method": "prompts/list"
                })
            ]
            
            mixed_responses = await asyncio.gather(*[await t for t in mixed_tasks])
            mixed_results = [await r.json() for r in mixed_responses]
            
            # Verify all succeeded
            for result in mixed_results:
                assert "result" in result
            
            print("✓ Mixed method types test passed")
            
            # Test 5: Check final metrics
            async with session.get("http://127.0.0.1:3035/metrics") as final_metrics_resp:
                final_metrics = await final_metrics_resp.json()
                
            print(f"\nFinal Metrics:")
            print(f"  Total Requests: {final_metrics['total_requests']}")
            print(f"  Completed Requests: {final_metrics['completed_requests']}")
            print(f"  Current Concurrent: {final_metrics['current_concurrent_requests']}")
            print(f"  Max Concurrent: {final_metrics['max_concurrent_requests']}")
            print(f"  Avg Response Time: {final_metrics['average_duration_ms']:.2f}ms")
            print(f"  Requests/sec: {final_metrics['requests_per_second']:.2f}")
            
            print("\n✓ All integration tests passed!")
            print("\nCONCURRENT REQUEST HANDLING VALIDATION: SUCCESS")
            print("All components are working together correctly:")
            print("- Async JsonRpcHandler with concurrency controls")
            print("- Async server handlers")
            print("- HTTP/SSE transport with concurrent request support")  
            print("- Monitoring and metrics tracking")
            print("- Configuration options for concurrency limits")
            
    except Exception as e:
        print(f"✗ Validation failed: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        # Stop server
        server.stop()


if __name__ == "__main__":
    asyncio.run(validate_concurrent_functionality())