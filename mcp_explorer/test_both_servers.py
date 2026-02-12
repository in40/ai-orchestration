#!/usr/bin/env python3
"""
Test both connection patterns against a regular server (not registry).
"""
import asyncio
import json
import uuid
import httpx

async def test_context_manager_approach():
    """Test using the context manager approach."""
    print("Testing with context manager approach...")

    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, application/json-rpc+mcp",
        "Mcp-Session-Id": str(uuid.uuid4())  # Generate a new session ID
    }

    async with httpx.AsyncClient(headers=headers) as client:
        print("1. Initializing...")
        
        # Initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "streams": False,
                    "experimental": {}
                }
            }
        }
        init_response = await client.post("http://localhost:3045/mcp", json=init_request)
        print(f"   Initialize response: {init_response.json()['result'].get('serverInfo', {})}")

        print("2. Sending initialized handshake...")
        # Initialized request
        initialized_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialized",
            "params": {
                "serverInfo": init_response.json()["result"]["serverInfo"],
                "capabilities": {"experimental": {}}
            }
        }
        initialized_response = await client.post("http://localhost:3045/mcp", json=initialized_request)
        print(f"   Initialized response: {initialized_response.json()}")

        print("3. Listing tools...")
        # Tools/list request
        tools_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {}
        }
        tools_response = await client.post("http://localhost:3045/mcp", json=tools_request)
        tools_data = tools_response.json()
        tools = tools_data.get("result", {}).get("tools", [])
        print(f"   Tools response: Found {len(tools)} tools")
        for tool in tools:
            print(f"     - {tool.get('name', 'unnamed')}: {tool.get('description', 'No description')}")

    return len(tools)


class ManualClient:
    """Test client using manual context management."""

    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())
        self.client = httpx.AsyncClient(
            headers={
                "Content-Type": "application/json",
                "Accept": "application/json, application/json-rpc+mcp",
                "Mcp-Session-Id": self.session_id
            }
        )

    async def connect(self):
        """Initialize the HTTP client."""
        await self.client.__aenter__()

    async def close(self):
        """Close the HTTP client."""
        await self.client.aclose()

    async def send_request(self, method: str, params=None):
        """Send an MCP request via HTTP POST."""
        request_id = str(uuid.uuid4())
        request_data = {
            "jsonrpc": "2.0",
            "id": request_id,
            "method": method
        }

        if params:
            request_data["params"] = params

        response = await self.client.post(
            f"{self.base_url}",
            content=json.dumps(request_data)
        )

        # Update session ID if server responded with a new one
        new_session_id = response.headers.get("Mcp-Session-Id")
        if new_session_id:
            self.session_id = new_session_id
            self.client.headers["Mcp-Session-Id"] = self.session_id

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        try:
            return response.json()
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {e}")

    async def initialize(self, protocol_version="2025-03-26"):
        """Perform MCP initialization handshake."""
        params = {
            "protocolVersion": protocol_version,
            "capabilities": {
                "streams": False,  # Using Streamable HTTP, not streams
                "experimental": {}
            }
        }
        return await self.send_request("initialize", params)

    async def initialized(self, server_info):
        """Complete initialization handshake."""
        params = {
            "serverInfo": server_info,
            "capabilities": {
                "experimental": {}
            }
        }
        return await self.send_request("initialized", params)

    async def list_tools(self):
        """List available tools from the server."""
        return await self.send_request("tools/list")


async def test_manual_approach():
    """Test using the manual approach."""
    print("\nTesting with manual approach...")

    client = ManualClient("http://localhost:3045/mcp")
    await client.connect()

    print("1. Initializing...")
    init_response = await client.initialize()
    print(f"   Initialize response: {init_response.get('result', {}).get('serverInfo', {})}")

    print("2. Sending initialized handshake...")
    server_info = init_response.get("result", {}).get("serverInfo", {})
    initialized_response = await client.initialized(server_info)
    print(f"   Initialized response: {initialized_response}")

    print("3. Listing tools...")
    tools_response = await client.list_tools()
    tools = tools_response.get("result", {}).get("tools", [])
    print(f"   Tools response: Found {len(tools)} tools")
    for tool in tools:
        print(f"     - {tool.get('name', 'unnamed')}: {tool.get('description', 'No description')}")

    await client.close()

    return len(tools)


async def run_comparison():
    """Run both tests and compare results."""
    print("Comparing connection patterns on regular server (port 3045)...\n")
    
    context_tools = await test_context_manager_approach()
    manual_tools = await test_manual_approach()
    
    print(f"\nResults on regular server (port 3045):")
    print(f"Context manager tools: {context_tools}")
    print(f"Manual approach tools: {manual_tools}")
    
    if context_tools == manual_tools:
        print("✅ Both approaches return same number of tools on regular server")
    else:
        print("❌ Approaches return different numbers of tools on regular server")
    
    print("\nNow testing on registry server (port 3031)...")
    
    # Also test on registry server
    context_tools_reg = await test_context_manager_approach_registry()
    manual_tools_reg = await test_manual_approach_registry()
    
    print(f"\nResults on registry server (port 3031):")
    print(f"Context manager tools: {context_tools_reg}")
    print(f"Manual approach tools: {manual_tools_reg}")
    
    if context_tools_reg > 0 and manual_tools_reg == 0:
        print("❌ Issue confirmed: Manual approach returns 0 tools on registry server")
    elif context_tools_reg == manual_tools_reg and context_tools_reg > 0:
        print("✅ Both approaches work correctly on registry server")
    else:
        print("? Unexpected results on registry server")


async def test_context_manager_approach_registry():
    """Test using the context manager approach on registry server."""
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, application/json-rpc+mcp",
        "Mcp-Session-Id": str(uuid.uuid4())  # Generate a new session ID
    }

    async with httpx.AsyncClient(headers=headers) as client:
        # Initialize request
        init_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialize",
            "params": {
                "protocolVersion": "2025-03-26",
                "capabilities": {
                    "streams": False,
                    "experimental": {}
                }
            }
        }
        init_response = await client.post("http://localhost:3031/mcp", json=init_request)

        # Initialized request
        initialized_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "initialized",
            "params": {
                "serverInfo": init_response.json()["result"]["serverInfo"],
                "capabilities": {"experimental": {}}
            }
        }
        await client.post("http://localhost:3031/mcp", json=initialized_request)

        # Tools/list request
        tools_request = {
            "jsonrpc": "2.0",
            "id": str(uuid.uuid4()),
            "method": "tools/list",
            "params": {}
        }
        tools_response = await client.post("http://localhost:3031/mcp", json=tools_request)
        tools_data = tools_response.json()
        tools = tools_data.get("result", {}).get("tools", [])
        
    return len(tools)


async def test_manual_approach_registry():
    """Test using the manual approach on registry server."""
    client = ManualClient("http://localhost:3031/mcp")
    await client.connect()

    # Initialize
    init_response = await client.initialize()
    
    # Initialized
    server_info = init_response.get("result", {}).get("serverInfo", {})
    await client.initialized(server_info)
    
    # List tools
    tools_response = await client.list_tools()
    tools = tools_response.get("result", {}).get("tools", [])

    await client.close()
    
    return len(tools)


if __name__ == "__main__":
    asyncio.run(run_comparison())