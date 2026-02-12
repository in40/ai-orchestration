#!/usr/bin/env python3
"""
Test script to check server capabilities during initialization
"""

from mcp_std_server.handlers.server_handlers import McpServerHandlers
from mcp_std_server.utils.json_rpc import JsonRpcHandler
from mcp_std_server.utils.notifications import NotificationManager


def test_server_capabilities():
    """Test what capabilities are reported by the server"""
    
    # Create a mock notification manager
    rpc_handler = JsonRpcHandler()
    notification_manager = NotificationManager(rpc_handler)
    
    # Initialize server handlers with the notification manager
    handlers = McpServerHandlers(notification_manager=notification_manager)
    
    # Register all handlers
    handlers.register_handlers(rpc_handler)
    
    # Simulate initialize request
    init_params = {
        "clientInfo": {
            "name": "test-client",
            "version": "1.0.0"
        }
    }
    
    init_response = handlers.handle_initialize(init_params, "test_init")
    
    print("Server Info:")
    print(f"  Name: {init_response['serverInfo']['name']}")
    print(f"  Version: {init_response['serverInfo']['version']}")
    
    print("\nCapabilities:")
    for cap_category, cap_details in init_response['capabilities'].items():
        print(f"  {cap_category}: {cap_details}")
    
    print("\nAvailable tools:")
    for tool in handlers.tools:
        print(f"  - {tool['name']}")
    
    print(f"\nTotal tools: {len(handlers.tools)}")
    
    print("\nAvailable resources:")
    for resource in handlers.resources:
        print(f"  - {resource['uri']}")
    
    print(f"\nTotal resources: {len(handlers.resources)}")
    
    print("\nAvailable prompts:")
    for prompt in handlers.prompts:
        print(f"  - {prompt['name']}")
    
    print(f"\nTotal prompts: {len(handlers.prompts)}")


if __name__ == "__main__":
    test_server_capabilities()