#!/usr/bin/env python3
"""
Simple Registry Query Test Based on Working Script
"""
import asyncio
import aiohttp
import json
import time
import uuid
from typing import Dict, Any, List


class SimpleRegistryTester:
    """Simple registry tester based on the working query script approach"""
    
    def __init__(self, registry_url: str):
        self.registry_url = registry_url
        self.session = None
        self.request_responses = {}
        self.pending_requests = {}
        self.sse_task = None
        self.stopped = False
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
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
        """Set up SSE listener"""
        async def listen():
            try:
                sse_url = f"{self.registry_url}/sse"
                print(f"🔌 Opening SSE connection to {sse_url}")
                
                async with self.session.get(sse_url) as response:
                    print("✅ Registry SSE connection established")
                    async for line in response.content:
                        if self.stopped:
                            break
                        line_str = line.decode('utf-8').strip()
                        
                        if line_str.startswith('data: '):
                            try:
                                data = json.loads(line_str[6:])  # Remove 'data: ' prefix
                                
                                # Check if this is a response to one of our requests
                                req_id = data.get('id')
                                if req_id and req_id in self.pending_requests:
                                    print(f"📥 Received response for request {req_id}")
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
                    print(f"❌ Error in registry SSE listener: {e}")

        # Start SSE listener task
        self.sse_task = asyncio.create_task(listen())
    
    async def send_registry_request(self, method: str, params: Dict[str, Any] = None) -> str:
        """Send a request to the registry"""
        request_id = str(uuid.uuid4())
        
        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }
        
        send_url = f"{self.registry_url}/send"
        print(f"📤 Sending request '{method}' with ID: {request_id}")
        
        try:
            async with self.session.post(send_url, json=payload) as response:
                result = await response.json()
                if result.get("status") == "received":
                    print(f"✅ Request '{method}' sent successfully (ID: {request_id})")
                    # Mark as pending
                    self.pending_requests[request_id] = {
                        'method': method,
                        'timestamp': time.time()
                    }
                    return request_id
                else:
                    print(f"Response received immediately: {result}")
                    return None
        except Exception as e:
            print(f"❌ Error sending request: {e}")
            return None
    
    async def wait_for_response(self, request_id: str, timeout: int = 10) -> Dict[str, Any]:
        """Wait for a specific response"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if request_id in self.request_responses:
                return self.request_responses[request_id]
            await asyncio.sleep(0.1)
        return None
    
    async def query_registry_services(self) -> List[Dict[str, Any]]:
        """Query the registry for available services"""
        print(f"📡 Connecting to registry at {self.registry_url}")
        
        # Start SSE listener FIRST - this is the MCP way
        await self.setup_sse_listener()
        
        # Wait a moment for SSE connection to establish (important!)
        await asyncio.sleep(1)
        
        # Send registry/list request
        request_id = await self.send_registry_request("registry/list", {})
        if not request_id:
            print("❌ Failed to send registry query")
            return []
        
        # Wait for response
        print("⏳ Waiting for registry response...")
        response = await self.wait_for_response(request_id, 10)
        
        if response:
            print("✅ Registry response received")
            services = response.get('result', {}).get('services', [])
            print(f"Found {len(services)} services in registry")
            return services
        else:
            print("❌ No response received from registry within timeout period")
            if self.pending_requests:
                print(f"Still waiting for responses to: {list(self.pending_requests.keys())}")
            return []


class SimpleConcurrentTester:
    """Simple concurrent tester that works with the registry-discovered services"""
    
    def __init__(self, server_url: str, server_type: str):
        self.server_url = server_url
        self.server_type = server_type
        self.session = None
        self.request_responses = {}
        self.pending_requests = {}
        self.sse_task = None
        self.stopped = False
    
    async def __aenter__(self):
        self.session = aiohttp.ClientSession()
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
        """Set up SSE listener for this server"""
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
                                
                                # Check if this is a response to one of our requests
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
        
        start_time = time.time()
        try:
            # Send request to server
            send_url = f"{self.server_url}/send"
            async with self.session.post(send_url, json=payload) as response:
                result = await response.json()
                
                if result.get("status") == "received":
                    print(f"📤 {self.server_type} request '{method}' sent successfully (ID: {request_id})")
                    # Mark as pending
                    self.pending_requests[request_id] = {
                        'method': method,
                        'timestamp': time.time(),
                        'server_type': self.server_type
                    }
                    
                    # Wait for response via SSE
                    timeout = 10
                    start_wait = time.time()
                    while time.time() - start_wait < timeout:
                        if request_id in self.request_responses:
                            response_data = self.request_responses[request_id]
                            if request_id in self.pending_requests:
                                del self.pending_requests[request_id]
                            end_time = time.time()
                            
                            # Check if response has result (success) or error
                            has_result = 'result' in response_data
                            has_error = 'error' in response_data
                            success = has_result and not has_error
                            
                            return {
                                "success": success,
                                "response": response_data,
                                "duration": end_time - start_time,
                                "method": method,
                                "url": self.server_url
                            }
                        await asyncio.sleep(0.1)
                    
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
                    # Immediate response
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


async def run_simple_registry_test():
    """Run a simple registry-based concurrent test"""
    print("🚀 SIMPLE REGISTRY-BASED CONCURRENT REQUEST TEST")
    print("="*50)
    
    # First, query the registry for available services
    async with SimpleRegistryTester("http://127.0.0.1:3031") as registry_tester:
        services = await registry_tester.query_registry_services()
        
        if not services:
            print("❌ No services found in registry")
            return
    
    print(f"\nFound {len(services)} services in registry:")
    for i, service in enumerate(services, 1):
        print(f"  {i}. {service.get('name', 'Unknown')} at {service.get('endpoint', 'N/A')}")
        caps = service.get('capabilities', {})
        if caps:
            print(f"     Capabilities: {list(caps.keys())}")
    
    # Now test concurrent requests to each service
    print(f"\n🧪 Testing concurrent requests to discovered services...")
    
    all_results = []
    
    for service in services:
        endpoint = service.get('endpoint')
        if not endpoint or 'registry' in service.get('name', '').lower():
            # Skip the registry service itself for this test
            continue
            
        print(f"\nTesting service: {service.get('name', 'Unknown')} at {endpoint}")
        
        # Determine what methods to test based on capabilities
        capabilities = service.get('capabilities', {})
        methods_to_test = []
        
        if 'tools' in capabilities:
            tools = capabilities['tools']
            if isinstance(tools, list):
                for tool in tools[:2]:  # Test first 2 tools to avoid too many requests
                    if isinstance(tool, str):
                        methods_to_test.append(('tools/call', {'name': tool, 'arguments': {}}))
        
        if 'resources' in capabilities:
            resources = capabilities['resources']
            if isinstance(resources, list):
                for resource in resources[:2]:  # Test first 2 resources
                    if isinstance(resource, str):
                        methods_to_test.append(('resources/read', {'uri': resource}))
        
        # Add generic methods if no specific ones found
        if not methods_to_test:
            methods_to_test = [
                ('initialize', {'clientInfo': {'name': 'test-client', 'version': '1.0.0'}}),
                ('tools/list', {}),
            ]
        
        # Test concurrent requests to this service
        async with SimpleConcurrentTester(endpoint, "service") as tester:
            tasks = []
            for i in range(2):  # Test 2 concurrent requests
                method, params = methods_to_test[i % len(methods_to_test)]  # Cycle through methods
                if 'clientInfo' in params:
                    params['clientInfo']['name'] = f'test-client-{i}'
                
                task = tester.make_request_with_sse_response(method, params)
                tasks.append(task)
            
            results = await asyncio.gather(*tasks)
            all_results.extend(results)
            
            successful = sum(1 for r in results if r["success"])
            print(f"  Results: {successful}/{len(results)} successful")
    
    # Analyze overall results
    print(f"\n🎯 OVERALL RESULTS:")
    total_requests = len(all_results)
    successful = sum(1 for r in all_results if r["success"])
    
    if total_requests > 0:
        success_rate = (successful / total_requests) * 100
        print(f"  Total Requests: {total_requests}")
        print(f"  Successful: {successful}")
        print(f"  Success Rate: {success_rate:.2f}%")
        
        if successful > 0:
            successful_results = [r for r in all_results if r["success"]]
            avg_duration = sum(r['duration'] for r in successful_results) / len(successful_results)
            print(f"  Average Response Time: {avg_duration*1000:.2f}ms")
        
        if successful == total_requests:
            print(f"\n🎉 ALL TESTS PASSED! Registry-based concurrent request handling is working!")
        else:
            print(f"\n⚠ SOME REQUESTS FAILED. Success rate: {success_rate:.2f}%")
    else:
        print("  No requests were made to services")


if __name__ == "__main__":
    asyncio.run(run_simple_registry_test())