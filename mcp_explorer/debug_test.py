#!/usr/bin/env python3
"""
Debug test to see what's happening with the different approaches.
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

    print(f"   Session ID: {headers['Mcp-Session-Id']}")

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
        print(f"   Init request: {init_request}")
        init_response = await client.post("http://localhost:3045/mcp", json=init_request)
        print(f"   Init response: {init_response.json()}")

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
        print(f"   Initialized request: {initialized_request}")
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
        print(f"   Tools request: {tools_request}")
        tools_response = await client.post("http://localhost:3045/mcp", json=tools_request)
        print(f"   Tools raw response: {tools_response.text}")
        tools_data = tools_response.json()
        tools = tools_data.get("result", {}).get("tools", [])
        print(f"   Tools response: Found {len(tools)} tools")
        for tool in tools:
            print(f"     - {tool.get('name', 'unnamed')}: {tool.get('description', 'No description')}")

    return len(tools)

class ManualClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.session_id = str(uuid.uuid4())
        print(f"   Manual client session ID: {self.session_id}")
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

        print(f"   Manual request ({method}): {request_data}")
        response = await self.client.post(
            f"{self.base_url}",
            content=json.dumps(request_data)
        )

        # Update session ID if server responded with a new one
        new_session_id = response.headers.get("Mcp-Session-Id")
        if new_session_id:
            print(f"   Server sent new session ID: {new_session_id}")
            self.session_id = new_session_id
            self.client.headers["Mcp-Session-Id"] = self.session_id

        if response.status_code != 200:
            raise Exception(f"HTTP {response.status_code}: {response.text}")

        try:
            response_json = response.json()
            print(f"   Manual response ({method}): {response_json}")
            return response_json
        except json.JSONDecodeError as e:
            raise Exception(f"Invalid JSON response: {e}")

    async def initialize(self, protocol_version="2025-03-26"):
        """Perform MCP initialization handshake."""
        params = {
            "protocolVersion": protocol_version,
            "capabilities": {
                "streams": False,
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

async def run_debug_test():
    """Run both tests and compare results."""
    print("Running debug test on regular server (port 3045)...\n")

    context_tools = await test_context_manager_approach()
    manual_tools = await test_manual_approach()

    print(f"\nResults:")
    print(f"Context manager tools: {context_tools}")
    print(f"Manual approach tools: {manual_tools}")

if __name__ == "__main__":
    asyncio.run(run_debug_test())