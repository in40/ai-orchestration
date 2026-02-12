#!/usr/bin/env python3
"""
Test script to check what methods are registered in the server
"""

from mcp_std_server.handlers.server_handlers import McpServerHandlers
from mcp_std_server.utils.json_rpc import JsonRpcHandler
from mcp_std_server.utils.notifications import NotificationManager


def test_registered_methods():
    """Test what methods are registered in the server"""
    
    # Create a mock notification manager
    rpc_handler = JsonRpcHandler()
    notification_manager = NotificationManager(rpc_handler)
    
    # Initialize server handlers with the notification manager
    handlers = McpServerHandlers(notification_manager=notification_manager)
    
    # Register all handlers
    handlers.register_handlers(rpc_handler)
    
    # Print all registered request handlers
    print("Registered request handlers:")
    for method_name in sorted(rpc_handler.request_handlers.keys()):
        print(f"  - {method_name}")
    
    # Check specifically for prompt-related methods
    print("\nPrompt-related methods:")
    prompt_methods = [method for method in rpc_handler.request_handlers.keys() if 'prompt' in method.lower()]
    for method in sorted(prompt_methods):
        print(f"  - {method}")
    
    # Check specifically for the new methods
    print("\nNew prompt methods:")
    new_methods = [
        'prompts/submit',
        'prompts/update', 
        'prompts/delete',
        'prompts/search',
        'prompts/export'
    ]
    for method in new_methods:
        if method in rpc_handler.request_handlers:
            print(f"  ✓ {method}")
        else:
            print(f"  ✗ {method}")


if __name__ == "__main__":
    test_registered_methods()