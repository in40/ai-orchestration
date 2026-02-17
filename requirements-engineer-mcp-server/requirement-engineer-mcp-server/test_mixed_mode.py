"""
Test script to verify mixed-mode MCP server functionality
"""
import asyncio
import threading
import time
from mcp_std_server.server import McpServer


def test_mixed_mode_server():
    """Test the mixed-mode server functionality"""
    print("Testing mixed-mode server functionality...")
    
    # Create a server instance in mixed mode
    server = McpServer(
        transport_type="stdio",  # Using stdio for simplicity in test
        host="127.0.0.1",
        port=3030,
        enable_client_mode=True,
        client_transport_type="stdio",
        client_host="127.0.0.1",
        client_port=3031,
        enable_registry=True
    )
    
    print("✓ Mixed-mode server created successfully")
    print(f"  - Server transport: {server.transport_type}")
    print(f"  - Client enabled: {server.enable_client_mode}")
    print(f"  - Client transport: {server.client_transport_type}")
    print(f"  - Registry enabled: {server.enable_registry}")
    
    # Verify that the client was created
    if server.client:
        print("✓ Client component created successfully")
    else:
        print("✗ Client component not created")
    
    # Test that the server has delegation methods
    try:
        # This should work if the server handlers were extended properly
        if hasattr(server.server_handlers, 'delegate_tool_call'):
            print("✓ Delegation methods available")
        else:
            print("✗ Delegation methods not available")
    except Exception as e:
        print(f"✗ Error checking delegation methods: {e}")
    
    print("\nMixed-mode functionality test completed!")


if __name__ == "__main__":
    test_mixed_mode_server()