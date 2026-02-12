#!/usr/bin/env python3
"""
Registry-Based Concurrent Request Load Test for MCP Server
Queries the registry for available services and tests their capabilities
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


class RegistryBasedConcurrentTester:
    """Concurrent tester that queries registry for services and tests their capabilities"""
    
    def __init__(self, registry_url: str):
        self.registry_url = registry_url
        self.session = None
    
    async def get_available_services(self):
        """Query the registry to get available services and their capabilities"""
        print("🔍 Querying registry for available services...")
        
        async with aiohttp.ClientSession() as session:
            # First, establish an SSE connection to receive the response
            session_id = str(uuid.uuid4())
            
            async def listen_for_response():
                sse_url = f"{self.registry_url}/sse"
                responses = {}
                
                async with session.get(sse_url) as response:
                    print("✅ Registry SSE connection established")
                    async for line in response.content:
                        line_str = line.decode('utf-8').strip()
                        
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                                
                                # Check if this is a response to our registry/list request
                                req_id = data.get('id')
                                if req_id and req_id.startswith('registry-query-'):
                                    responses[req_id] = data
                                    break  # We got our response
                            except json.JSONDecodeError:
                                continue
                        elif line_str.startswith(': ping'):
                            continue
                        elif line_str == '':
                            continue
                
                return responses
            
            # Start SSE listener in background
            sse_task = asyncio.create_task(listen_for_response())
            
            # Send registry/list request
            request_id = f"registry-query-{uuid.uuid4()}"
            payload = {
                "jsonrpc": "2.0",
                "id": request_id,
                "method": "registry/list",
                "params": {}
            }
            
            headers = {"X-MCP-Session-ID": session_id, "Content-Type": "application/json"}
            async with session.post(f"{self.registry_url}/send", json=payload, headers=headers) as response:
                result = await response.json()
                print(f"Registry list request sent: {result}")
            
            # Wait for the response
            responses = await sse_task
            if request_id in responses:
                registry_response = responses[request_id]
                if 'result' in registry_response:
                    services = registry_response['result'].get('services', [])
                    print(f"✅ Found {len(services)} services in registry")
                    for service in services:
                        print(f"   - {service.get('name', 'Unknown')}: {service.get('endpoint', 'N/A')}")
                        caps = service.get('capabilities', {})
                        if caps:
                            print(f"     Capabilities: {caps}")
                    return services
                else:
                    print(f"❌ Registry response error: {registry_response}")
                    return []
            else:
                print(f"❌ No response received for registry query")
                return []
    
    async def test_service_capabilities(self, service_endpoint: str, capabilities: Dict[str, Any], num_requests: int) -> List[Dict[str, Any]]:
        """Test the capabilities of a specific service"""
        print(f"Testing {num_requests} concurrent requests to service at {service_endpoint}...")
        
        # Determine what methods to test based on capabilities
        methods_to_test = []
        
        # Add tool methods if available
        if 'tools' in capabilities:
            tools = capabilities['tools']
            if isinstance(tools, list):
                for tool in tools:
                    if isinstance(tool, str):
                        methods_to_test.append(('tools/call', {'name': tool, 'arguments': {}}))
                    elif isinstance(tool, dict) and 'name' in tool:
                        methods_to_test.append(('tools/call', {'name': tool['name'], 'arguments': {}}))
        
        # Add resource methods if available
        if 'resources' in capabilities:
            resources = capabilities['resources']
            if isinstance(resources, list):
                for resource in resources:
                    if isinstance(resource, str):
                        methods_to_test.append(('resources/read', {'uri': resource}))
                    elif isinstance(resource, dict) and 'uri' in resource:
                        methods_to_test.append(('resources/read', {'uri': resource['uri']}))
        
        # Add prompt methods if available
        if 'prompts' in capabilities:
            prompts = capabilities['prompts']
            if isinstance(prompts, list):
                for prompt in prompts:
                    if isinstance(prompt, str):
                        methods_to_test.append(('prompts/get', {'name': prompt, 'arguments': {}}))
                    elif isinstance(prompt, dict) and 'name' in prompt:
                        methods_to_test.append(('prompts/get', {'name': prompt['name'], 'arguments': {}}))
        
        # Add generic methods if no specific ones found
        if not methods_to_test:
            # Fallback to generic methods
            methods_to_test = [
                ('initialize', {'clientInfo': {'name': 'test-client', 'version': '1.0.0'}}),
                ('tools/list', {}),
                ('resources/list', {}),
                ('prompts/list', {})
            ]
        
        # Use a single SSE connection for all requests to this service
        async with SingleServerConcurrentTester(service_endpoint, "service") as tester:
            tasks = []
            for i in range(num_requests):
                # Pick a random method to test
                method, params = random.choice(methods_to_test)
                
                # Add unique identifier to params if needed
                if 'clientInfo' in params:
                    params['clientInfo']['name'] = f'test-client-{i}'
                
                task = tester.make_request_with_sse_response(method, params)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            return results
    
    async def run_registry_based_concurrent_test(self, num_requests_per_service: int) -> List[Dict[str, Any]]:
        """Run concurrent tests based on services discovered in registry"""
        print("🚀 Starting registry-based concurrent request test...")
        
        # Get available services from registry
        services = await self.get_available_services()
        
        if not services:
            print("❌ No services found in registry")
            return []
        
        all_results = []
        
        # Test each service found in the registry
        for service in services:
            service_endpoint = service.get('endpoint')
            capabilities = service.get('capabilities', {})
            
            if not service_endpoint:
                continue
                
            print(f"\nTesting service: {service.get('name', 'Unknown')}")
            print(f"Endpoint: {service_endpoint}")
            print(f"Capabilities: {capabilities}")
            
            # Test this service's capabilities
            service_results = await self.test_service_capabilities(
                service_endpoint, 
                capabilities, 
                num_requests_per_service
            )
            
            all_results.extend(service_results)
        
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


async def run_registry_based_tests(registry_url: str, num_requests_per_service: int):
    """Run registry-based concurrent tests"""
    print("="*70)
    print("MCP SERVER REGISTRY-BASED CONCURRENT REQUEST LOAD TEST")
    print("="*70)
    print(f"Registry URL: {registry_url}")
    print(f"Number of concurrent requests per service: {num_requests_per_service}")
    print("-"*70)
    
    tester = RegistryBasedConcurrentTester(registry_url)
    
    # Run registry-based concurrent test
    start_time = time.time()
    all_results = await tester.run_registry_based_concurrent_test(num_requests_per_service)
    total_time = time.time() - start_time
    
    # Analyze results
    tester.analyze_results(all_results, "REGISTRY-BASED CONCURRENT TEST")
    print(f"  Time taken: {total_time:.2f}s")
    
    # Overall summary
    print("\n" + "="*70)
    print("OVERALL SUMMARY")
    print("="*70)
    total_requests = len(all_results)
    successful = sum(1 for r in all_results if r["success"])
    success_rate = (successful / total_requests * 100) if total_requests > 0 else 0
    
    print(f"Total Requests Across All Services: {total_requests}")
    print(f"Successful Requests: {successful}")
    print(f"Success Rate: {success_rate:.2f}%")
    if successful > 0:
        successful_results = [r for r in all_results if r["success"]]
        avg_response_time = sum(r['duration'] for r in successful_results)/len(successful_results)
        print(f"Average Response Time: {avg_response_time*1000:.2f}ms")
    
    if successful == total_requests:
        print("\n🎉 ALL TESTS PASSED! Registry-based concurrent request handling is working correctly.")
        print("✓ Discovered services from registry")
        print("✓ Tested capabilities of each service")
        print("✓ All requests processed successfully via SSE transport")
    else:
        print(f"\n⚠ SOME REQUESTS FAILED. Success rate: {success_rate:.2f}%")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Registry-Based Concurrent Request Load Test for MCP Server")
    parser.add_argument("--registry-url", default="http://127.0.0.1:3031", help="Registry server URL (default: http://127.0.0.1:3031)")
    parser.add_argument("--requests-per-service", type=int, default=3, help="Number of concurrent requests per service (default: 3)")
    
    args = parser.parse_args()
    
    asyncio.run(run_registry_based_tests(args.registry_url, args.requests_per_service))