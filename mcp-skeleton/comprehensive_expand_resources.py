#!/usr/bin/env python3
"""
Comprehensive Resource Expansion Tool for MCP Services
This script allows expanding all resources from a service in a single SSE connection
"""

import json
import time
import uuid
import requests
from threading import Thread, Event
from queue import Queue
import argparse
import sys


class ComprehensiveResourceExpander:
    def __init__(self, service_endpoint="http://localhost:3030", timeout=15):
        self.service_endpoint = service_endpoint.rstrip('/')
        self.timeout = timeout
        self.response_queue = Queue()
        self.stop_event = Event()
        self.session = requests.Session()
        self.sse_thread = None
        self.request_responses = {}  # Store responses by request ID
        self.pending_requests = {}   # Track pending requests

    def start_sse_listener(self):
        """Start listening to SSE stream in a separate thread"""
        def listen():
            try:
                # Open SSE connection
                sse_url = f"{self.service_endpoint}/sse"
                print(f"🔌 Opening SSE connection to {sse_url}")

                response = self.session.get(sse_url, stream=True, timeout=self.timeout)

                print("✅ SSE connection established")
                for line in response.iter_lines(decode_unicode=True):
                    if self.stop_event.is_set():
                        break

                    line = line.strip()
                    if line.startswith("data: "):
                        data = line[6:]  # Remove "data: " prefix
                        try:
                            json_data = json.loads(data)

                            # Check if this is a response to one of our requests
                            req_id = json_data.get('id')
                            if req_id and req_id in self.pending_requests:
                                print(f"📥 Received response for request {req_id}")
                                self.request_responses[req_id] = json_data
                                # Remove from pending requests
                                del self.pending_requests[req_id]

                            # Also put in queue for general processing
                            self.response_queue.put(json_data)
                        except json.JSONDecodeError:
                            continue
            except Exception as e:
                if not self.stop_event.is_set():
                    print(f"❌ Error in SSE listener: {e}")

        self.sse_thread = Thread(target=listen, daemon=True)
        self.sse_thread.start()
        return self.sse_thread

    def send_request(self, method, params=None, request_id=None):
        """Send a request to the service"""
        if request_id is None:
            request_id = str(uuid.uuid4())

        payload = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method,
            "params": params or {}
        }

        send_url = f"{self.service_endpoint}/send"
        try:
            print(f"📤 Sending request '{method}' with ID: {request_id}")
            response = self.session.post(send_url, json=payload, timeout=5)
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "received":
                    print(f"✅ Request '{method}' sent successfully (ID: {request_id})")
                    # Mark this request as pending
                    self.pending_requests[request_id] = {
                        'method': method,
                        'timestamp': time.time()
                    }
                    return request_id
                else:
                    print(f"Response received immediately: {result}")
                    return result
            else:
                print(f"❌ Error sending request: {response.status_code} - {response.text}")
                return None
        except Exception as e:
            print(f"❌ Error sending request: {e}")
            return None

    def wait_for_response(self, request_id, timeout=10):
        """Wait for a specific response by ID"""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if request_id in self.request_responses:
                return self.request_responses[request_id]
            time.sleep(0.1)
        return None

    def expand_multiple_resources(self, resources_list):
        """Expand and read the content of multiple resources using a single SSE connection"""
        # Start SSE listener FIRST if not already started
        if self.sse_thread is None:
            print(f"📡 Connecting to service at {self.service_endpoint}")
            listener_thread = self.start_sse_listener()

            # Wait a moment for SSE connection to establish
            time.sleep(0.2)

        results = {}
        request_ids = {}

        # Send all resource read requests
        for resource_uri in resources_list:
            print(f"\n🔍 Queuing resource read for: {resource_uri}")
            
            # Send resources/read request
            request_id = str(uuid.uuid4())
            params = {"uri": resource_uri}
            req_id = self.send_request("resources/read", params, request_id)
            if not req_id:
                print(f"❌ Failed to send resource read request for {resource_uri}")
                results[resource_uri] = None
            else:
                request_ids[request_id] = resource_uri

        # Wait for all responses
        print(f"\n⏳ Waiting for responses for {len(request_ids)} resources...")
        start_time = time.time()
        timeout_time = start_time + self.timeout
        
        while len(results) < len(request_ids) and time.time() < timeout_time:
            # Check for completed requests
            completed_uris = []
            for req_id, resource_uri in request_ids.items():
                if req_id in self.request_responses and resource_uri not in results:
                    response = self.request_responses[req_id]
                    
                    if 'result' in response:
                        content = response['result'].get('content', response['result'])
                        print(f"📄 Resource '{resource_uri}' content retrieved")
                        results[resource_uri] = content
                        completed_uris.append(req_id)
                    elif 'error' in response:
                        print(f"❌ Error reading resource '{resource_uri}': {response['error']}")
                        results[resource_uri] = {"error": response['error']}
                        completed_uris.append(req_id)
                    else:
                        print(f"❓ Unexpected response format for '{resource_uri}': {response}")
                        results[resource_uri] = response
                        completed_uris.append(req_id)
            
            # Remove completed requests from tracking
            for req_id in completed_uris:
                if req_id in request_ids:
                    del request_ids[req_id]
            
            time.sleep(0.1)  # Brief pause before checking again

        # Check for any remaining uncompleted requests
        for req_id, resource_uri in request_ids.items():
            print(f"❌ Timeout waiting for resource '{resource_uri}'")
            results[resource_uri] = None

        return results

    def list_all_resources(self):
        """Get a list of all available resources from the service"""
        print(f"📡 Connecting to service at {self.service_endpoint}")

        # Start SSE listener FIRST if not already started
        if self.sse_thread is None:
            listener_thread = self.start_sse_listener()
            # Wait a moment for SSE connection to establish
            time.sleep(0.2)

        # Send resources/list request
        request_id = str(uuid.uuid4())
        print(f"🔍 Listing all resources (Request ID: {request_id})...")

        req_id = self.send_request("resources/list", {}, request_id)
        if not req_id:
            print("❌ Failed to send resources list request")
            return None

        # Wait for response
        print("⏳ Waiting for resource list...")
        response = self.wait_for_response(request_id, self.timeout)

        if response:
            return response
        else:
            print("❌ No response received from service within timeout period")
            return None

    def close(self):
        """Close the client connection"""
        self.stop_event.set()
        if self.session:
            self.session.close()


def main():
    parser = argparse.ArgumentParser(description='Comprehensive MCP service resource expansion')
    parser.add_argument('--service-endpoint', default='http://localhost:3030',
                        help='Service endpoint URL (default: http://localhost:3030)')
    parser.add_argument('--resource', action='append', dest='resources',
                        help='Specific resource URI to expand (can be used multiple times)')
    parser.add_argument('--list-resources', action='store_true',
                        help='List all available resources from the service')
    parser.add_argument('--expand-all-from-service', action='store_true',
                        help='Expand all resources available from the service')
    parser.add_argument('--timeout', type=int, default=15,
                        help='Timeout in seconds (default: 15)')

    args = parser.parse_args()

    expander = ComprehensiveResourceExpander(args.service_endpoint, args.timeout)

    try:
        if args.list_resources:
            # List all resources from the service
            print("🔍 Getting list of all available resources...")
            response = expander.list_all_resources()
            
            if response and 'result' in response and 'resources' in response['result']:
                resources = response['result']['resources']
                print(f"\n📋 Available resources ({len(resources)}):")
                for i, resource in enumerate(resources, 1):
                    uri = resource.get('uri', 'N/A')
                    name = resource.get('name', 'N/A')
                    desc = resource.get('description', 'No description')
                    print(f"  {i}. {uri}")
                    print(f"     Name: {name}")
                    print(f"     Description: {desc}")
            else:
                print("❌ Could not retrieve resource list")
                
        elif args.expand_all_from_service:
            # First get all resources, then expand them
            print("🔍 Getting list of all available resources...")
            response = expander.list_all_resources()
            
            if response and 'result' in response and 'resources' in response['result']:
                resources = response['result']['resources']
                resource_uris = [r.get('uri', '') for r in resources if r.get('uri')]
                
                print(f"🔍 Expanding {len(resource_uris)} resources...")
                results = expander.expand_multiple_resources(resource_uris)
                
                print("\n" + "="*60)
                print("📋 RESOURCE EXPANSION RESULTS")
                print("="*60)
                
                for resource_uri, content in results.items():
                    print(f"\nResource: {resource_uri}")
                    print("-" * 40)
                    if content:
                        if isinstance(content, dict) and 'error' in content:
                            print(f"❌ Error: {content['error']}")
                        else:
                            print(json.dumps(content, indent=2))
                    else:
                        print("❌ No content retrieved")
            else:
                print("❌ Could not retrieve resource list to expand")
                
        elif args.resources:
            # Expand specific resources
            print(f"🔍 Expanding {len(args.resources)} resources...")
            results = expander.expand_multiple_resources(args.resources)
            
            print("\n" + "="*60)
            print("📋 RESOURCE EXPANSION RESULTS")
            print("="*60)
            
            for resource_uri, content in results.items():
                print(f"\nResource: {resource_uri}")
                print("-" * 40)
                if content:
                    if isinstance(content, dict) and 'error' in content:
                        print(f"❌ Error: {content['error']}")
                    else:
                        print(json.dumps(content, indent=2))
                else:
                    print("❌ No content retrieved")
        else:
            print("❌ No resources specified. Use --resource to specify resource URIs to expand.")
            print("   Or use --list-resources to list all available resources from the service.")
            parser.print_help()

    except KeyboardInterrupt:
        print("\n⚠️  Operation cancelled by user")
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        expander.close()


if __name__ == "__main__":
    main()