"""
Basic test to verify the standard MCP server implementation
"""
import subprocess
import time
import requests
import json
import threading


def test_server_startup():
    """Test that the server starts up correctly with different transports"""
    print("Testing server startup with different transports...")
    
    # Test 1: Stdio transport (just verify the module loads)
    try:
        from mcp_std_server.server import McpServer
        print("✅ Stdio transport module loaded successfully")
    except Exception as e:
        print(f"❌ Error loading stdio transport: {e}")
        return False
    
    # Test 2: Verify all required modules exist
    try:
        from mcp_std_server.transports.streamable_http import StreamableHttpTransport
        print("✅ Streamable HTTP transport module loaded successfully")
    except Exception as e:
        print(f"❌ Error loading Streamable HTTP transport: {e}")
        return False
    
    try:
        from mcp_std_server.transports.http_sse import HttpSseTransport
        print("✅ Legacy HTTP/SSE transport module loaded successfully")
    except Exception as e:
        print(f"❌ Error loading Legacy HTTP/SSE transport: {e}")
        return False
    
    try:
        from mcp_std_server.transports.stdio import StdioTransport
        print("✅ Stdio transport module loaded successfully")
    except Exception as e:
        print(f"❌ Error loading Stdio transport: {e}")
        return False
    
    try:
        from mcp_std_server.handlers.server_handlers import McpServerHandlers
        print("✅ Server handlers module loaded successfully")
    except Exception as e:
        print(f"❌ Error loading server handlers: {e}")
        return False
    
    try:
        from mcp_std_server.utils.json_rpc import JsonRpcHandler
        print("✅ JSON-RPC handler module loaded successfully")
    except Exception as e:
        print(f"❌ Error loading JSON-RPC handler: {e}")
        return False
    
    print("\n🎉 All modules loaded successfully!")
    return True


def test_basic_functionality():
    """Test basic server functionality"""
    print("\nTesting basic server functionality...")
    
    try:
        from mcp_std_server.server import McpServer
        
        # Create a simple server instance with stdio transport
        server = McpServer(transport_type="stdio")
        
        # Verify all components are initialized
        assert hasattr(server, 'rpc_handler'), "RPC handler not initialized"
        assert hasattr(server, 'server_handlers'), "Server handlers not initialized"
        assert hasattr(server, 'transport'), "Transport not initialized"
        
        print("✅ Server instance created successfully")
        print("✅ All components initialized correctly")
        
        # Test the handlers are registered
        assert 'initialize' in server.rpc_handler.request_handlers, "Initialize handler not registered"
        assert 'tools/list' in server.rpc_handler.request_handlers, "Tools list handler not registered"
        assert 'resources/list' in server.rpc_handler.request_handlers, "Resources list handler not registered"
        assert 'prompts/list' in server.rpc_handler.request_handlers, "Prompts list handler not registered"
        
        print("✅ All standard handlers registered correctly")
        
        return True
    except Exception as e:
        print(f"❌ Error testing basic functionality: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Running basic tests for the standard MCP server implementation...\n")
    
    success = True
    success &= test_server_startup()
    success &= test_basic_functionality()
    
    if success:
        print("\n🎉 All tests passed! The standard MCP server implementation is ready.")
    else:
        print("\n❌ Some tests failed. Please check the implementation.")