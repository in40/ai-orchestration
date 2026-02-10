#!/usr/bin/env python3
"""
Registry Query Client for MCP Server
Act as an HTTP/SSE client to query the registry and show registered servers
"""

import json
import time
import uuid
import requests
from threading import Thread, Event
from queue import Queue
import argparse
import sys


class RegistryQueryClient:
    def __init__(self, registry_url="http://localhost:3031", timeout=10):
        self.registry_url = registry_url.rstrip('/')
        self.timeout = timeout
        self.response_queue = Queue()
        self.stop_event = Event()
        self.session = requests.Session()
        self.sse_thread = None
        
    def start_sse_listener(self):
        """Start listening to SSE stream in a separate thread"""
        self.session_id = None  # Store the session ID from the endpoint event
        self.session_id_received = False  # Flag to indicate if session ID has been received
        
        def listen():
            try:
                # Open SSE connection
                sse_url = f"{self.registry_url}/sse"
                response = self.session.get(sse_url, stream=True, timeout=self.timeout)

                for line in response.iter_lines(decode_unicode=True):
                    if self.stop_event.is_set():
                        break

                    line = line.strip()
                    if line.startswith("event: endpoint"):
                        # This is the endpoint event that contains the session ID
                        # Next line should contain the data
                        continue
                    elif line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        try:
                            json_data = json.loads(data)
                            
                            # Check if this is an endpoint event with session ID
                            if isinstance(json_data, dict) and 'sessionId' in json_data:
                                self.session_id = json_data['sessionId']
                                self.session_id_received = True
                                print(f"📝 Got session ID from server: {self.session_id}")
                            else:
                                # This is a regular message, put it in the queue
                                self.response_queue.put(json_data)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"Error in SSE listener: {e}")

        self.sse_thread = Thread(target=listen, daemon=True)
        self.sse_thread.start()
        
        # Wait briefly to allow session ID to be received
        import time
        time.sleep(0.5)
        
        return self.sse_thread

    def send_request(self, method, params=None, request_id=None):
        """Send a request to the registry server"""
        if request_id is None:
            request_id = str(uuid.uuid4())

        # Wait for session ID if not yet received
        if hasattr(self, 'session_id_received') and not self.session_id_received:
            print("⏳ Waiting for session ID from server...")
            import time
            wait_start = time.time()
            while (not getattr(self, 'session_id_received', False) and 
                   time.time() - wait_start < 5):  # Wait up to 5 seconds
                time.sleep(0.1)

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

        send_url = f"{self.registry_url}/send"
        headers = {}
        
        # Add session ID to headers if available
        if hasattr(self, 'session_id') and self.session_id:
            headers['X-MCP-Session-ID'] = self.session_id
            print(f"📤 Using session ID for request: {self.session_id}")
        
        try:
            response = self.session.post(send_url, json=payload, headers=headers, timeout=5)
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "received":
                    print(f"✓ Request '{method}' sent successfully (ID: {request_id})")
                    return request_id
                else:
                    print(f"Response received: {result}")
                    return result
            else:
                print(f"Error sending request: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"Error sending request: {e}")
            return None

    def wait_for_response(self, expected_id, timeout=10):
        """Wait for a specific response by ID"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                response = self.response_queue.get(timeout=0.1)
                if response.get("id") == expected_id:
                    return response
            except:
                continue
        return None

    def query_registry(self):
        """Query the registry for all registered services"""
        print(f"📡 Connecting to registry at {self.registry_url}")
        
        # Start SSE listener
        listener_thread = self.start_sse_listener()
        
        # Send registry/list request
        request_id = str(uuid.uuid4())
        print(f"🔍 Querying registry for services (Request ID: {request_id})...")
        
        req_id = self.send_request("registry/list", {}, request_id)
        if not req_id:
            print("❌ Failed to send registry query")
            return None
        
        # Wait for response
        print("⏳ Waiting for registry response...")
        response = self.wait_for_response(request_id, self.timeout)
        
        # Stop the SSE listener
        self.stop_event.set()
        
        if response:
            return response
        else:
            print("❌ No response received from registry within timeout period")
            return None

    def query_single_service(self, service_id):
        """Query for a specific service"""
        print(f"📡 Connecting to registry at {self.registry_url}")
        
        # Start SSE listener
        listener_thread = self.start_sse_listener()
        
        # Send registry/get request
        request_id = str(uuid.uuid4())
        print(f"🔍 Querying registry for service '{service_id}' (Request ID: {request_id})...")
        
        params = {"id": service_id}
        req_id = self.send_request("registry/get", params, request_id)
        if not req_id:
            print("❌ Failed to send service query")
            return None
        
        # Wait for response
        print("⏳ Waiting for service details...")
        response = self.wait_for_response(request_id, self.timeout)
        
        # Stop the SSE listener
        self.stop_event.set()
        
        if response:
            return response
        else:
            print("❌ No response received from registry within timeout period")
            return None

    def close(self):
        """Close the client connection"""
        self.stop_event.set()
        if self.session:
            self.session.close()


def format_service_info(service):
    """Format service information for display"""
    print(f"  🆔 ID: {service.get('id', 'N/A')}")
    print(f"  🏷️  Name: {service.get('name', 'N/A')}")
    print(f"  📝 Description: {service.get('description', 'N/A')}")
    print(f"  🌐 Endpoint: {service.get('endpoint', 'N/A')}")
    
    capabilities = service.get('capabilities', {})
    if capabilities:
        print(f"  ⚙️  Capabilities:")
        for cap_type, items in capabilities.items():
            if isinstance(items, list) and items:
                print(f"    • {cap_type}: {', '.join(str(item) for item in items)}")
            elif isinstance(items, dict) and items:
                print(f"    • {cap_type}: {json.dumps(items, indent=4)}")
            elif items:  # For scalar values
                print(f"    • {cap_type}: {items}")
    print()


def main():
    parser = argparse.ArgumentParser(description='Query MCP Registry for registered services')
    parser.add_argument('--registry-url', default='http://localhost:3031',
                        help='Registry server URL (default: http://localhost:3031)')
    parser.add_argument('--service-id', 
                        help='Query specific service by ID (optional)')
    parser.add_argument('--timeout', type=int, default=10,
                        help='Timeout in seconds (default: 10)')
    
    args = parser.parse_args()
    
    client = RegistryQueryClient(args.registry_url, args.timeout)
    
    try:
        if args.service_id:
            # Query specific service
            print(f"🔍 Querying specific service: {args.service_id}")
            response = client.query_single_service(args.service_id)
        else:
            # Query all services
            print("🔍 Querying all registered services")
            response = client.query_registry()
        
        if response:
            print("\n" + "="*60)
            print("📋 REGISTRY RESPONSE")
            print("="*60)
            print(f"Response ID: {response.get('id', 'N/A')}")
            
            if 'result' in response:
                result = response['result']
                if 'services' in result:
                    # List of services
                    services = result['services']
                    total_count = result.get('total_count', len(services))
                    
                    print(f"Total Services Found: {total_count}")
                    print("-" * 60)
                    
                    if services:
                        for i, service in enumerate(services, 1):
                            print(f"{i}. Service Details:")
                            format_service_info(service)
                    else:
                        print("No services registered in the registry.")
                        
                elif 'service' in result:
                    # Single service
                    service = result['service']
                    print("Service Details:")
                    format_service_info(service)
                    
                else:
                    print(f"Other result data: {json.dumps(result, indent=2)}")
            else:
                print(f"Unexpected response format: {json.dumps(response, indent=2)}")
        else:
            print("❌ No response received from registry")
            
    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        client.close()


if __name__ == "__main__":
    main()