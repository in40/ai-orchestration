#!/usr/bin/env python3
"""
Test without updating session ID from response.
"""
import asyncio
import json
import uuid
import httpx

class TestClientNoSessionUpdate:
    """Test client without updating session ID from response."""
    
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

        # DON'T update session ID from response (this might be the issue!)
        # new_session_id = response.headers.get("Mcp-Session-Id")
        # if new_session_id:
        #     self.session_id = new_session_id
        #     self.client.headers["Mcp-Session-Id"] = self.session_id

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

async def test_no_session_update():
    """Test without updating session ID."""
    print("Testing without updating session ID from response...")
    
    client = TestClientNoSessionUpdate("http://localhost:3031/mcp")
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

if __name__ == "__main__":
    tool_count = asyncio.run(test_no_session_update())
    print(f"\nTotal tools found: {tool_count}")