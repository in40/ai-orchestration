#!/usr/bin/env python3
"""
Test script to simulate server startup and check methods
"""

from mcp_std_server.server import McpServer
import json


def test_server_startup():
    """Test server startup and method registration"""
    
    print("Creating server instance...")
    server = McpServer(transport_type='stdio', max_concurrent_requests=1)
    
    print("Checking registered handlers...")
    handlers = server.server_handlers
    rpc_handler = server.rpc_handler
    
    print(f"Total registered handlers: {len(rpc_handler.request_handlers)}")
    print("\nAll registered handlers:")
    for method_name in sorted(rpc_handler.request_handlers.keys()):
        print(f"  - {method_name}")
    
    print("\nPrompt-related handlers:")
    prompt_handlers = [method for method in rpc_handler.request_handlers.keys() if 'prompt' in method.lower()]
    for method in sorted(prompt_handlers):
        print(f"  - {method}")
    
    print("\nChecking server handlers attributes:")
    print(f"- Number of prompts: {len(handlers.prompts)}")
    print(f"- Number of tools: {len(handlers.tools)}")
    print(f"- Number of resources: {len(handlers.resources)}")
    
    print("\nPrompts:")
    for prompt in handlers.prompts:
        print(f"  - {prompt['name']}: {prompt.get('description', 'No description')}")
    
    print("\nTools:")
    for tool in handlers.tools:
        print(f"  - {tool['name']}: {tool.get('description', 'No description')}")
    
    print("\nResources:")
    for resource in handlers.resources:
        print(f"  - {resource['uri']}: {resource.get('name', 'No name')}")


if __name__ == "__main__":
    test_server_startup()