"""
Test to reproduce the sequential request issue
"""
from mcp_std_server.server import McpServer
from mcp_std_server.utils.json_rpc import JsonRpcMessage, MessageType


def test_sequential_requests():
    """Test the exact sequence that's failing"""
    print("Testing sequential request sequence...")
    
    # Create a server
    server = McpServer(transport_type='streamable-http', port=3043)
    
    # Step 1: Send initialize
    print("Step 1: Sending initialize...")
    init_msg = JsonRpcMessage(
        message_type=MessageType.REQUEST,
        id='init',
        method='initialize',
        params={'clientInfo': {'name': 'test-client', 'version': '1.0.0'}}
    )
    
    init_response = server.rpc_handler.handle_message_sync(init_msg)
    print(f"Initialize response: {init_response.result if init_response and hasattr(init_response, 'result') else 'ERROR'}")
    
    # Step 2: Send initialized
    print("Step 2: Sending initialized...")
    initialized_msg = JsonRpcMessage(
        message_type=MessageType.REQUEST,
        id='initialized',
        method='initialized',
        params={}
    )
    
    initialized_response = server.rpc_handler.handle_message_sync(initialized_msg)
    print(f"Initialized response: {initialized_response.result if initialized_response and hasattr(initialized_response, 'result') else 'ERROR'}")
    
    # Step 3: Send tools/list
    print("Step 3: Sending tools/list...")
    tools_msg = JsonRpcMessage(
        message_type=MessageType.REQUEST,
        id='tools_list',
        method='tools/list',
        params={}
    )
    
    tools_response = server.rpc_handler.handle_message_sync(tools_msg)
    
    if tools_response and hasattr(tools_response, 'result'):
        tools_count = len(tools_response.result.get('tools', []))
        print(f"Tools/list response: Found {tools_count} tools")
        print(f"Tools: {tools_response.result.get('tools', [])}")
        
        if tools_count == 0:
            print("❌ ISSUE REPRODUCED: tools/list returns 0 tools after handshake sequence")
            return False
        else:
            print("✅ tools/list returns tools correctly after handshake sequence")
            return True
    else:
        print(f"Tools/list error: {tools_response.error if tools_response and hasattr(tools_response, 'error') else 'UNKNOWN ERROR'}")
        return False


def test_individual_requests():
    """Test individual requests to compare"""
    print("\nTesting individual requests...")
    
    # Create a fresh server
    server = McpServer(transport_type='streamable-http', port=3044)
    
    # Test tools/list directly without handshake
    print("Sending tools/list without handshake...")
    tools_msg = JsonRpcMessage(
        message_type=MessageType.REQUEST,
        id='tools_list_direct',
        method='tools/list',
        params={}
    )
    
    tools_response = server.rpc_handler.handle_message_sync(tools_msg)
    
    if tools_response and hasattr(tools_response, 'result'):
        tools_count = len(tools_response.result.get('tools', []))
        print(f"Direct tools/list response: Found {tools_count} tools")
        return tools_count > 0
    else:
        print(f"Direct tools/list error: {tools_response.error if tools_response and hasattr(tools_response, 'error') else 'UNKNOWN ERROR'}")
        return False


if __name__ == "__main__":
    print("Testing sequential vs individual request behavior...\n")
    
    individual_ok = test_individual_requests()
    sequential_ok = test_sequential_requests()
    
    print(f"\nResults:")
    print(f"Individual requests work: {individual_ok}")
    print(f"Sequential requests work: {sequential_ok}")
    
    if individual_ok and not sequential_ok:
        print("\n❌ CONFIRMED: Issue exists - sequential requests fail while individual requests work")
    elif individual_ok and sequential_ok:
        print("\n✅ Both work correctly - issue may be elsewhere")
    else:
        print("\n❓ Both fail - different issue exists")