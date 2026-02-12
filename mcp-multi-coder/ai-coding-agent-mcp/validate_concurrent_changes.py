#!/usr/bin/env python3
"""
Quick validation that concurrent request handling changes work
"""
import asyncio
import aiohttp
import threading
import time
from mcp_server.server import McpServer


def run_server_in_thread(server):
    """Run server in a thread"""
    server.start()


async def test_concurrent_changes():
    """Test that our concurrent changes work"""
    print("Testing concurrent request handling changes...")
    
    # Start server
    server = McpServer(
        transport_type="http",
        host="127.0.0.1",
        port=3037,
        max_concurrent_requests=5
    )
    
    # Start server in background thread
    server_thread = threading.Thread(target=run_server_in_thread, args=(server,), daemon=True)
    server_thread.start()
    
    # Give server time to start
    await asyncio.sleep(3)
    
    try:
        print("✓ Server started with concurrent request handling")
        
        # Test basic functionality
        async with aiohttp.ClientSession() as session:
            # Test 1: Regular request
            payload = {
                "jsonrpc": "2.0",
                "id": "test-basic",
                "method": "initialize",
                "params": {
                    "clientInfo": {"name": "test-client", "version": "1.0.0"}
                }
            }
            
            async with session.post("http://127.0.0.1:3037/send", json=payload) as response:
                result = await response.json()
                
            if "result" in result:
                print("✓ Basic request handling works")
            else:
                print(f"✗ Basic request failed: {result}")
                return False
            
            # Test 2: Metrics endpoint
            async with session.get("http://127.0.0.1:3037/metrics") as metrics_resp:
                if metrics_resp.status == 200:
                    metrics = await metrics_resp.json()
                    print("✓ Metrics endpoint available")
                    print(f"  Total requests: {metrics.get('total_requests', 0)}")
                    print(f"  Current concurrent: {metrics.get('current_concurrent_requests', 0)}")
                    print(f"  Max concurrent: {metrics.get('max_concurrent_requests', 0)}")
                else:
                    print(f"✗ Metrics endpoint failed: {metrics_resp.status}")
                    return False
            
            # Test 3: Multiple concurrent requests
            print("\nTesting concurrent requests...")
            start_time = time.time()
            
            tasks = []
            for i in range(3):
                req_payload = {
                    "jsonrpc": "2.0",
                    "id": f"concurrent-{i}",
                    "method": "tools/list"
                }
                task = session.post("http://127.0.0.1:3037/send", json=req_payload)
                tasks.append(task)
            
            responses = await asyncio.gather(*tasks)
            results = [await r.json() for r in responses]
            
            all_successful = all("result" in r for r in results)
            if all_successful:
                end_time = time.time()
                print(f"✓ Concurrent requests successful ({end_time - start_time:.2f}s)")
            else:
                print(f"✗ Some concurrent requests failed: {results}")
                return False
        
        print("\n✓ All tests passed! Concurrent request handling is working correctly.")
        return True
        
    except Exception as e:
        print(f"✗ Test failed with exception: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Stop the server
        server.stop()


if __name__ == "__main__":
    success = asyncio.run(test_concurrent_changes())
    if success:
        print("\n" + "="*50)
        print("SUCCESS: All concurrent request handling changes validated!")
        print("="*50)
    else:
        print("\n" + "="*50)
        print("FAILURE: Some tests failed")
        print("="*50)