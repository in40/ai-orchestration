"""
Test to verify client functionality in mixed-mode server
"""
from mcp_std_server.client import McpClient


def test_client_creation():
    """Test creating an MCP client"""
    print("Testing MCP Client Creation...")
    
    # Create a client instance
    client = McpClient(
        transport_type="stdio",
        host="127.0.0.1",
        port=3030,
        endpoint="http://127.0.0.1:3030"
    )
    
    print("✓ MCP Client created successfully")
    print(f"  - Transport type: {client.transport_type}")
    print(f"  - Host: {client.host}")
    print(f"  - Port: {client.port}")
    print(f"  - Endpoint: {client.endpoint}")
    
    # Verify client has required methods
    required_methods = [
        'connect', 'disconnect', 'is_connected',
        'call_tool', 'list_tools', 'read_resource', 
        'list_resources', 'get_prompt', 'list_prompts'
    ]
    
    for method in required_methods:
        if hasattr(client, method):
            print(f"  ✓ Method '{method}' available")
        else:
            print(f"  ✗ Method '{method}' missing")
    
    print("\nClient functionality test completed!")


if __name__ == "__main__":
    test_client_creation()