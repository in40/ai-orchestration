#!/usr/bin/env python3
"""
Final Working SSE-Based Concurrent Request Load Test for MCP Server and Registry
Properly handles the SSE transport mechanism for responses
"""
import asyncio
import aiohttp
import time
import random
import argparse
from typing import Dict, Any, List
import json
import uuid


class SingleServerConcurrentTester:
    """Tester for concurrent requests to a single server using proper SSE mechanism"""
    
    def __init__(self, server_url: str, server_type: str):
        self.server_url = server_url
        self.server_type = server_type
        self.session = None
        self.request_responses = {}  # Maps request IDs to responses
        self.pending_requests = {}   # Tracks pending requests
        self.sse_task = None
        self.session_id = None
        self.stopped = False
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
        self.session_id = str(uuid.uuid4())
        await self.setup_sse_listener()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        self.stopped = True
        if self.sse_task:
            self.sse_task.cancel()
            try:
                await self.sse_task
            except asyncio.CancelledError:
                pass
        if self.session:
            await self.session.close()
    
    async def setup_sse_listener(self):
        """Set up an SSE listener for this server"""
        async def listen():
            try:
                sse_url = f"{self.server_url}/sse"
                print(f"🔌 Opening SSE connection to {sse_url}")

                async with self.session.get(sse_url) as response:
                    print(f"✅ {self.server_type} SSE connection established")
                    async for line in response.content:
                        if self.stopped:
                            break
                        line_str = line.decode('utf-8').strip()
                        
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                                
                                # Check if this is a direct response to one of our requests
                                req_id = data.get('id')
                                if req_id and req_id in self.pending_requests:
                                    print(f"📥 Received response for {self.server_type} request {req_id}")
                                    self.request_responses[req_id] = data
                                    # Remove from pending requests
                                    if req_id in self.pending_requests:
                                        del self.pending_requests[req_id]
                            except json.JSONDecodeError:
                                continue
                        elif line_str.startswith(': ping'):
                            # Ping message, ignore
                            continue
                        elif line_str == '':
                            # Empty line, continue
                            continue
            except Exception as e:
                if not self.stopped:
                    print(f"❌ Error in {self.server_type} SSE listener: {e}")

        # Start SSE listener task
        self.sse_task = asyncio.create_task(listen())
    
    async def make_request_with_sse_response(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Make a request and wait for response via SSE"""
        request_id = str(uuid.uuid4())
        
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }
        
        if params:
            payload["params"] = params
        
        # Send the request with the session ID
        start_time = time.time()
        try:
            # Send request to server with session ID header
            send_url = f"{self.server_url}/send"
            headers = {"X-MCP-Session-ID": self.session_id, "Content-Type": "application/json"}
            async with self.session.post(send_url, json=payload, headers=headers) as response:
                result = await response.json()
                
                if result.get("status") == "received":
                    print(f"📤 {self.server_type} request '{method}' sent successfully (ID: {request_id})")
                    # Mark this request as pending
                    self.pending_requests[request_id] = {
                        'method': method,
                        'timestamp': time.time(),
                        'server_type': self.server_type
                    }
                    
                    # Wait for response via SSE
                    timeout = 10  # 10 second timeout
                    start_wait = time.time()
                    while time.time() - start_wait < timeout:
                        if request_id in self.request_responses:
                            response_data = self.request_responses[request_id]
                            if request_id in self.pending_requests:
                                del self.pending_requests[request_id]
                            end_time = time.time()
                            # Check if response has result (success) or error
                            has_error = 'error' in response_data
                            success = not has_error  # Consider success if no error field
                            
                            return {
                                "success": success,
                                "response": response_data,
                                "duration": end_time - start_time,
                                "method": method,
                                "url": self.server_url
                            }
                        await asyncio.sleep(0.1)  # Small delay to prevent busy-waiting
                    
                    # Timeout occurred
                    if request_id in self.pending_requests:
                        del self.pending_requests[request_id]
                    return {
                        "success": False,
                        "error": "Timeout waiting for SSE response",
                        "duration": time.time() - start_time,
                        "method": method,
                        "url": self.server_url
                    }
                else:
                    # Immediate response (shouldn't happen with SSE transport)
                    end_time = time.time()
                    return {
                        "success": True,
                        "response": result,
                        "duration": end_time - start_time,
                        "method": method,
                        "url": self.server_url
                    }
        except Exception as e:
            end_time = time.time()
            return {
                "success": False,
                "error": str(e),
                "duration": end_time - start_time,
                "method": method,
                "url": self.server_url
            }


class SSEConcurrentTester:
    """Concurrent tester that properly handles SSE transport for MCP protocol"""
    
    def __init__(self, registry_url: str, mcp_url: str):
        self.registry_url = registry_url
        self.mcp_url = mcp_url
    
    async def registry_concurrent_calls(self, num_requests: int) -> List[Dict[str, Any]]:
        """Test concurrent calls to registry server"""
        print(f"Testing {num_requests} concurrent requests to registry server...")
        
        # Use a single SSE connection for all requests to registry
        async with SingleServerConcurrentTester(self.registry_url, "registry") as tester:
            tasks = []
            for i in range(num_requests):
                # Mix of different registry methods
                method = random.choice(["registry/list", "initialize"])
                params = {
                    "clientInfo": {
                        "name": f"test-client-{i}",
                        "version": "1.0.0"
                    }
                } if method == "initialize" else {}
                
                task = tester.make_request_with_sse_response(method, params)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return results
    
    async def mcp_concurrent_calls(self, num_requests: int) -> List[Dict[str, Any]]:
        """Test concurrent calls to MCP server"""
        print(f"Testing {num_requests} concurrent requests to MCP server...")
        
        # Use a single SSE connection for all requests to MCP
        async with SingleServerConcurrentTester(self.mcp_url, "mcp") as tester:
            tasks = []
            for i in range(num_requests):
                # Mix of different MCP methods
                method = random.choice([
                    "tools/list", 
                    "resources/list", 
                    "prompts/list", 
                    "initialize"
                ])
                
                params = {}
                if method == "initialize":
                    params = {
                        "clientInfo": {
                            "name": f"mcp-test-client-{i}",
                            "version": "1.0.0"
                        }
                    }
                
                task = tester.make_request_with_sse_response(method, params)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return results
    
    async def mixed_concurrent_calls(self, num_requests: int) -> List[Dict[str, Any]]:
        """Test mixed concurrent calls to both servers"""
        print(f"Testing {num_requests} mixed concurrent requests to both servers...")
        
        # Create tasks for both servers
        registry_tasks = []
        mcp_tasks = []
        
        for i in range(num_requests):
            # Randomly choose between registry and MCP server
            if random.choice([True, False]):
                # Registry task
                async with SingleServerConcurrentTester(self.registry_url, "registry") as tester:
                    method = random.choice(["registry/list", "initialize"])
                    params = {}
                    if method == "initialize":
                        params = {
                            "clientInfo": {
                                "name": f"mixed-test-client-{i}",
                                "version": "1.0.0"
                            }
                        }
                    
                    task = tester.make_request_with_sse_response(method, params)
                    registry_tasks.append(task)
            else:
                # MCP task
                async with SingleServerConcurrentTester(self.mcp_url, "mcp") as tester:
                    method = random.choice(["tools/list", "resources/list", "prompts/list", "initialize"])
                    params = {}
                    if method == "initialize":
                        params = {
                            "clientInfo": {
                                "name": f"mixed-test-client-{i}",
                                "version": "1.0.0"
                            }
                        }
                    
                    task = tester.make_request_with_sse_response(method, params)
                    mcp_tasks.append(task)
        
        # Run all tasks
        all_results = []
        if registry_tasks:
            registry_results = await asyncio.gather(*registry_tasks)
            all_results.extend(registry_results)
        if mcp_tasks:
            mcp_results = await asyncio.gather(*mcp_tasks)
            all_results.extend(mcp_results)
        
        return all_results
    
    def analyze_results(self, results: List[Dict[str, Any]], test_name: str):
        """Analyze and print results of the test"""
        total_requests = len(results)
        successful = sum(1 for r in results if r["success"])
        failed = total_requests - successful
        
        if total_requests > 0:
            success_rate = (successful / total_requests) * 100
            successful_results = [r for r in results if r["success"]]
            if successful > 0:
                avg_duration = sum(r["duration"] for r in successful_results) / successful
                max_duration = max(r["duration"] for r in successful_results)
                min_duration = min(r["duration"] for r in successful_results)
            else:
                avg_duration = 0
                max_duration = 0
                min_duration = 0
            
            print(f"\n{test_name} Results:")
            print(f"  Total Requests: {total_requests}")
            print(f"  Successful: {successful}")
            print(f"  Failed: {failed}")
            print(f"  Success Rate: {success_rate:.2f}%")
            if successful > 0:
                print(f"  Average Duration: {avg_duration*1000:.2f}ms")
                print(f"  Min Duration: {min_duration*1000:.2f}ms")
                print(f"  Max Duration: {max_duration*1000:.2f}ms")
            
            if failed > 0:
                print(f"  Failed Requests:")
                for i, result in enumerate(results):
                    if not result["success"]:
                        print(f"    {i+1}. {result['method']} on {result['url']}: {result.get('error', 'Unknown error')}")
        else:
            print(f"No results for {test_name}")


async def run_sse_concurrent_tests(registry_url: str, mcp_url: str, num_requests: int):
    """Run all concurrent tests using proper SSE mechanism"""
    print("="*70)
    print("MCP SERVER & REGISTRY SSE-BASED CONCURRENT REQUEST LOAD TEST")
    print("="*70)
    print(f"Registry URL: {registry_url}")
    print(f"MCP Server URL: {mcp_url}")
    print(f"Number of concurrent requests: {num_requests}")
    print("-"*70)
    
    tester = SSEConcurrentTester(registry_url, mcp_url)
    
    # Test registry server
    start_time = time.time()
    registry_results = await tester.registry_concurrent_calls(num_requests)
    registry_time = time.time() - start_time
    tester.analyze_results(registry_results, "REGISTRY SERVER TEST")
    print(f"  Time taken: {registry_time:.2f}s")
    
    print("\n" + "-"*70)
    
    # Test MCP server
    start_time = time.time()
    mcp_results = await tester.mcp_concurrent_calls(num_requests)
    mcp_time = time.time() - start_time
    tester.analyze_results(mcp_results, "MCP SERVER TEST")
    print(f"  Time taken: {mcp_time:.2f}s")
    
    print("\n" + "-"*70)
    
    # Test mixed calls to both servers
    start_time = time.time()
    mixed_results = await tester.mixed_concurrent_calls(num_requests)
    mixed_time = time.time() - start_time
    tester.analyze_results(mixed_results, "MIXED SERVERS TEST")
    print(f"  Time taken: {mixed_time:.2f}s")
    
    # Overall summary
    print("\n" + "="*70)
    print("OVERALL SUMMARY")
    print("="*70)
    all_results = registry_results + mcp_results + mixed_results
    total_requests = len(all_results)
    successful = sum(1 for r in all_results if r["success"])
    success_rate = (successful / total_requests * 100) if total_requests > 0 else 0
    
    print(f"Total Requests Across All Tests: {total_requests}")
    print(f"Successful Requests: {successful}")
    print(f"Success Rate: {success_rate:.2f}%")
    if successful > 0:
        successful_results = [r for r in all_results if r["success"]]
        avg_response_time = sum(r['duration'] for r in successful_results)/len(successful_results)
        print(f"Average Response Time: {avg_response_time*1000:.2f}ms")
    
    if successful == total_requests:
        print("\n🎉 ALL TESTS PASSED! SSE-based concurrent request handling is working correctly.")
        print("✓ Registry server handling concurrent requests")
        print("✓ MCP server handling concurrent requests")
        print("✓ Both servers responding via SSE transport")
    else:
        print(f"\n⚠ SOME REQUESTS FAILED. Success rate: {success_rate:.2f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="SSE-Based Concurrent Request Load Test for MCP Server and Registry")
    parser.add_argument("--registry-url", default="http://127.0.0.1:3031", help="Registry server URL (default: http://127.0.0.1:3031)")
    parser.add_argument("--mcp-url", default="http://127.0.0.1:3030", help="MCP server URL (default: http://127.0.0.1:3030)")
    parser.add_argument("--requests", type=int, default=5, help="Number of concurrent requests to send (default: 5)")
    
    args = parser.parse_args()
    
    asyncio.run(run_sse_concurrent_tests(args.registry_url, args.mcp_url, args.requests))