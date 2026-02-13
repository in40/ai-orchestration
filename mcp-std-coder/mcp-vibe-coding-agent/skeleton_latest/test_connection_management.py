"""
Test to reproduce the connection management issue
"""
import asyncio
import httpx
import json
from mcp_std_server.server import McpServer
import threading
import time


async def test_with_context_manager(port):
    """Test using async with context manager (working scenario)"""
    print("Testing with async with context manager...")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, application/json-rpc+mcp",
        "Mcp-Session-Id": "test-session-1"
    }
    
    async with httpx.AsyncClient(headers=headers) as client:
        # Initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": "init-test1",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "streams": False,
                    "experimental": {}
                }
            }
        }
        init_response = await client.post(f"http://localhost:{port}/mcp", json=init_request)
        print(f"Initialize response: {init_response.json()}")
        
        # Initialized request
        initialized_request = {
            "jsonrpc": "2.0",
            "id": "initialized-test1",
            "method": "initialized",
            "params": {
                "serverInfo": {"name": "mcp-standard-server", "version": "1.0.0"},
                "capabilities": {"experimental": {}}
            }
        }
        initialized_response = await client.post(f"http://localhost:{port}/mcp", json=initialized_request)
        print(f"Initialized response: {initialized_response.json()}")
        
        # Tools/list request
        tools_request = {
            "jsonrpc": "2.0",
            "id": "tools-test1",
            "method": "tools/list",
            "params": {}
        }
        tools_response = await client.post(f"http://localhost:{port}/mcp", json=tools_request)
        tools_data = tools_response.json()
        tools_count = len(tools_data['result']['tools']) if 'result' in tools_data and 'tools' in tools_data['result'] else 0
        print(f"Tools/list response: {tools_count} tools")
        return tools_count


async def test_with_manual_context(port):
    """Test using manual __aenter__() and aclose() (failing scenario)"""
    print("\\nTesting with manual context management...")
    
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, application/json-rpc+mcp",
        "Mcp-Session-Id": "test-session-2"
    }
    
    client = httpx.AsyncClient(
        headers=headers
    )
    await client.__aenter__()  # Manual context entry
    
    try:
        # Initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": "init-test2",
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "streams": False,
                    "experimental": {}
                }
            }
        }
        init_response = await client.post(f"http://localhost:{port}/mcp", json=init_request)
        print(f"Initialize response: {init_response.json()}")
        
        # Initialized request
        initialized_request = {
            "jsonrpc": "2.0",
            "id": "initialized-test2",
            "method": "initialized",
            "params": {
                "serverInfo": {"name": "mcp-standard-server", "version": "1.0.0"},
                "capabilities": {"experimental": {}}
            }
        }
        initialized_response = await client.post(f"http://localhost:{port}/mcp", json=initialized_request)
        print(f"Initialized response: {initialized_response.json()}")
        
        # Tools/list request
        tools_request = {
            "jsonrpc": "2.0",
            "id": "tools-test2",
            "method": "tools/list",
            "params": {}
        }
        tools_response = await client.post(f"http://localhost:{port}/mcp", json=tools_request)
        tools_data = tools_response.json()
        tools_count = len(tools_data['result']['tools']) if 'result' in tools_data and 'tools' in tools_data['result'] else 0
        print(f"Tools/list response: {tools_count} tools")
        return tools_count
    finally:
        await client.aclose()


async def run_connection_tests():
    """Run both connection management tests"""
    # Start server
    server = McpServer(transport_type='streamable-http', port=3047, enable_registry=True)
    
    def run_server():
        server.start()
    
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    time.sleep(2)  # Wait for server to start
    
    print("Running connection management tests...")
    
    # Test with context manager
    context_tools = await test_with_context_manager(3047)
    
    # Test with manual context
    manual_tools = await test_with_manual_context(3047)
    
    print(f"\\nResults:")
    print(f"Context manager tools: {context_tools}")
    print(f"Manual context tools: {manual_tools}")
    
    if context_tools > 0 and manual_tools == 0:
        print("❌ Issue reproduced: Manual context returns 0 tools while context manager works")
        return False
    elif context_tools == manual_tools and context_tools > 0:
        print("✅ Both return same number of tools")
        return True
    else:
        print("? Different behavior but not the exact reported issue")
        return True


if __name__ == "__main__":
    asyncio.run(run_connection_tests())