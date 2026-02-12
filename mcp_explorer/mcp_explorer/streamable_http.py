"""Streamable HTTP client for MCP protocol."""
import json
import uuid
from typing import Dict, Any, Optional, List
import httpx
from pydantic import BaseModel, ValidationError


class MCPRequest(BaseModel):
    """Base class for MCP requests."""
    jsonrpc: str = "2.0"
    id: str
    method: str
    params: Optional[Dict[str, Any]] = None


class MCPResponse(BaseModel):
    """Base class for MCP responses."""
    jsonrpc: str = "2.0"
    id: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


class StreamableHTTPClient:
    """Client for MCP Streamable HTTP transport."""
    
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
        
    async def send_request(self, method: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
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
    
    async def initialize(self, protocol_version: str = "2025-03-26") -> Dict[str, Any]:
        """Perform MCP initialization handshake."""
        params = {
            "protocolVersion": protocol_version,
            "capabilities": {
                "streams": False,  # Using Streamable HTTP, not streams
                "experimental": {}
            }
        }
        return await self.send_request("initialize", params)
    
    async def initialized(self, server_info: Dict[str, Any]) -> Dict[str, Any]:
        """Complete initialization handshake."""
        params = {
            "serverInfo": server_info,
            "capabilities": {
                "experimental": {}
            }
        }
        return await self.send_request("initialized", params)
    
    async def list_tools(self) -> Dict[str, Any]:
        """List available tools from the server."""
        return await self.send_request("tools/list")
    
    async def call_tool(self, tool_id: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Call a specific tool with arguments."""
        params = {
            "tool": tool_id,
            "arguments": arguments
        }
        return await self.send_request("tools/call", params)
    
    async def list_resources(self) -> Dict[str, Any]:
        """List available resources from the server."""
        return await self.send_request("resources/list")
    
    async def read_resource(self, resource: str) -> Dict[str, Any]:
        """Read a specific resource."""
        params = {"resource": resource}
        return await self.send_request("resources/read", params)
    
    async def ping(self) -> Dict[str, Any]:
        """Send a ping to the server."""
        return await self.send_request("ping")