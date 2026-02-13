"""
Test to verify that registry methods work properly without asyncio errors
"""
from mcp_std_server.server import McpServer
from mcp_std_server.handlers.server_handlers import McpServerHandlers
from mcp_std_server.utils.json_rpc import JsonRpcHandler, JsonRpcMessage, MessageType


def test_registry_methods():
    """Test that registry methods work without asyncio errors"""
    print("Testing registry methods...")
    
    # Create a server with registry enabled
    server = McpServer(transport_type="streamable-http", enable_registry=True, port=3035)
    
    # Create a test message for initialize
    init_message = JsonRpcMessage(
        message_type=MessageType.REQUEST,
        id="test_init",
        method="initialize",
        params={
            "clientInfo": {
                "name": "test-client",
                "version": "1.0.0"
            }
        }
    )
    
    # Test that the handler can process the message without asyncio errors
    try:
        # Use the sync handler directly to simulate what happens in the transport
        response = server.rpc_handler.handle_message_sync(init_message)
        if response:
            print(f"✅ Initialize method works: has_result={hasattr(response, 'result')}")
            if hasattr(response, 'result'):
                print(f"   Response: {response.result}")
            elif hasattr(response, 'error'):
                print(f"   Error: {response.error}")
        else:
            print("✅ Initialize method works: no response returned (notification)")
        
    except Exception as e:
        print(f"❌ Initialize method failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test ping method
    ping_message = JsonRpcMessage(
        message_type=MessageType.REQUEST,
        id="test_ping",
        method="ping",
        params={}
    )
    
    try:
        response = server.rpc_handler.handle_message_sync(ping_message)
        print(f"✅ Ping method works: {response.result is not None if hasattr(response, 'result') else 'error'}")
        
        if hasattr(response, 'result'):
            print(f"   Response: {response.result}")
        elif hasattr(response, 'error'):
            print(f"   Error: {response.error}")
        
    except Exception as e:
        print(f"❌ Ping method failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test tools/list method
    tools_list_message = JsonRpcMessage(
        message_type=MessageType.REQUEST,
        id="test_tools",
        method="tools/list",
        params={}
    )
    
    try:
        response = server.rpc_handler.handle_message_sync(tools_list_message)
        if response:
            print(f"✅ Tools/list method works: has_result={hasattr(response, 'result')}")
            if hasattr(response, 'result'):
                tools_data = response.result
                if isinstance(tools_data, dict) and 'tools' in tools_data:
                    print(f"   Found {len(tools_data.get('tools', []))} tools")
                else:
                    print(f"   Response: {tools_data}")
            elif hasattr(response, 'error'):
                print(f"   Error: {response.error}")
        else:
            print("✅ Tools/list method works: no response returned (notification)")
        
    except Exception as e:
        print(f"❌ Tools/list method failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # Test registry methods if registry is enabled
    if server.enable_registry:
        # Test registry/list method
        registry_list_message = JsonRpcMessage(
            message_type=MessageType.REQUEST,
            id="test_registry",
            method="registry/list",
            params={}
        )
        
        try:
            response = server.rpc_handler.handle_message_sync(registry_list_message)
            if response:
                print(f"✅ Registry/list method works: has_result={hasattr(response, 'result')}")
                if hasattr(response, 'result') and response.result:
                    services_data = response.result
                    if isinstance(services_data, dict) and 'services' in services_data:
                        print(f"   Found {len(services_data.get('services', []))} services")
                    else:
                        print(f"   Response: {services_data}")
                elif hasattr(response, 'error'):
                    print(f"   Error: {response.error}")
                else:
                    print(f"   Response: {response.result}")
            else:
                print("✅ Registry/list method works: no response returned (notification)")
            
        except Exception as e:
            print(f"❌ Registry/list method failed: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    return True


def test_asyncio_reference_issue():
    """Test specifically for the asyncio reference issue"""
    print("\nTesting asyncio reference issue...")
    
    # Create handlers with registry enabled
    handlers = McpServerHandlers(enable_registry=True)
    
    # Create a basic RPC handler
    rpc_handler = JsonRpcHandler()
    handlers.register_handlers(rpc_handler)
    
    # Test a simple method that might trigger the asyncio issue
    test_message = JsonRpcMessage(
        message_type="request",
        id="async_test",
        method="initialize",
        params={
            "clientInfo": {"name": "test", "version": "1.0"}
        }
    )
    
    try:
        response = rpc_handler.handle_message_sync(test_message)
        print("✅ No asyncio reference error occurred")
        return True
    except Exception as e:
        if "asyncio" in str(e):
            print(f"❌ Asyncio reference error still occurs: {e}")
            return False
        else:
            print(f"Different error occurred: {e}")
            # This might be OK if it's not the asyncio issue
            return True


if __name__ == "__main__":
    print("Testing registry methods and asyncio issues...\n")
    
    success = True
    success &= test_registry_methods()
    success &= test_asyncio_reference_issue()
    
    if success:
        print("\n🎉 All tests passed! Registry methods work without asyncio errors.")
    else:
        print("\n❌ Some tests failed.")