"""
MCP Client Implementation
Enables the server to connect to other MCP servers and delegate tasks
"""
import asyncio
import json
import time
from typing import Dict, Any, Optional
from .utils.json_rpc import JsonRpcHandler, JsonRpcMessage, MessageType


class McpClient:
    """MCP Client implementation for connecting to other MCP servers"""

    def __init__(self, transport_type: str = "streamable-http", host: str = "127.0.0.1", 
                 port: int = 3030, endpoint: Optional[str] = None, max_concurrent_requests: int = 10):
        self.transport_type = transport_type
        self.host = host
        self.port = port
        self.endpoint = endpoint or f"http://{host}:{port}/mcp"
        self.max_concurrent_requests = max_concurrent_requests
        self.connected = False
        
        # Initialize RPC handler for client
        self.rpc_handler = JsonRpcHandler(max_concurrent_requests=max_concurrent_requests)
        
        # Transport-specific attributes
        self.transport = None

    def connect(self):
        """Connect to the remote MCP server"""
        print(f"Connecting to MCP server at {self.endpoint} using {self.transport_type} transport...")
        
        if self.transport_type == "streamable-http":
            # For client, we'll use HTTP requests to communicate with the server
            self.connected = True
            print(f"Connected to MCP server at {self.endpoint}")
        elif self.transport_type == "http":
            # Legacy HTTP/SSE transport
            self.connected = True
            print(f"Connected to MCP server at {self.endpoint} using legacy HTTP transport")
        elif self.transport_type == "stdio":
            # STDIO transport - would require subprocess management
            print("STDIO transport not supported for client mode in this implementation")
            return False
        else:
            print(f"Unsupported transport type: {self.transport_type}")
            return False

        return self.connected

    def disconnect(self):
        """Disconnect from the remote MCP server"""
        print(f"Disconnecting from MCP server at {self.endpoint}")
        self.connected = False

    def call_tool(self, tool_name: str, arguments: Dict[str, Any], timeout: float = 1200.0) -> Dict[str, Any]:
        """Call a tool on the remote server"""
        if not self.connected:
            return {
                "error": {
                    "type": "not_connected",
                    "message": "Client not connected to remote server"
                }
            }

        try:
            # Create the tool call request
            request = {
                "jsonrpc": "2.0",
                "id": f"tool-call-{int(time.time() * 1000)}",
                "method": "tools/call",
                "params": {
                    "name": tool_name,
                    "arguments": arguments
                }
            }

            # Send the request to the remote server
            import requests
            response = requests.post(self.endpoint, json=request, timeout=timeout)

            if response.status_code == 200:
                result = response.json()
                return result.get("result", result)
            else:
                return {
                    "error": {
                        "type": "http_error",
                        "message": f"HTTP {response.status_code}: {response.text}"
                    }
                }
        except Exception as e:
            return {
                "error": {
                    "type": "call_failed",
                    "message": f"Failed to call tool: {str(e)}"
                }
            }

    def read_resource(self, uri: str, timeout: float = 1200.0) -> Dict[str, Any]:
        """Read a resource from the remote server"""
        if not self.connected:
            return {
                "error": {
                    "type": "not_connected",
                    "message": "Client not connected to remote server"
                }
            }

        try:
            # Create the resource read request
            request = {
                "jsonrpc": "2.0",
                "id": f"resource-read-{int(time.time() * 1000)}",
                "method": "resources/read",
                "params": {
                    "uri": uri
                }
            }

            # Send the request to the remote server
            import requests
            response = requests.post(self.endpoint, json=request, timeout=timeout)

            if response.status_code == 200:
                result = response.json()
                return result.get("result", result)
            else:
                return {
                    "error": {
                        "type": "http_error",
                        "message": f"HTTP {response.status_code}: {response.text}"
                    }
                }
        except Exception as e:
            return {
                "error": {
                    "type": "read_failed",
                    "message": f"Failed to read resource: {str(e)}"
                }
            }

    def get_prompt(self, prompt_name: str, arguments: Dict[str, Any], timeout: float = 1200.0) -> Dict[str, Any]:
        """Get a prompt from the remote server"""
        if not self.connected:
            return {
                "error": {
                    "type": "not_connected",
                    "message": "Client not connected to remote server"
                }
            }

        try:
            # Create the prompt get request
            request = {
                "jsonrpc": "2.0",
                "id": f"prompt-get-{int(time.time() * 1000)}",
                "method": "prompts/get",
                "params": {
                    "name": prompt_name,
                    "arguments": arguments
                }
            }

            # Send the request to the remote server
            import requests
            response = requests.post(self.endpoint, json=request, timeout=timeout)

            if response.status_code == 200:
                result = response.json()
                return result.get("result", result)
            else:
                return {
                    "error": {
                        "type": "http_error",
                        "message": f"HTTP {response.status_code}: {response.text}"
                    }
                }
        except Exception as e:
            return {
                "error": {
                    "type": "get_failed",
                    "message": f"Failed to get prompt: {str(e)}"
                }
            }

    def send_notification(self, method: str, params: Dict[str, Any]) -> Dict[str, Any]:
        """Send an MCP notification (fire-and-forget, no response expected)
        
        Args:
            method: Notification method name (e.g., 'notifications/tasks/new')
            params: Notification parameters
            
        Returns:
            Status dict with success indicator
        """
        if not self.connected:
            return {
                "success": False,
                "error": "Client not connected to remote server"
            }

        try:
            # Create notification (no id field - that's what makes it a notification)
            notification = {
                "jsonrpc": "2.0",
                "method": method,
                "params": params
            }

            # Send the notification to the remote server
            import requests
            response = requests.post(self.endpoint, json=notification, timeout=10.0)

            # Notifications don't return results, but we check for HTTP errors
            if response.status_code in [200, 202, 204]:
                return {
                    "success": True,
                    "method": method,
                    "http_status": response.status_code
                }
            else:
                return {
                    "success": False,
                    "error": f"HTTP {response.status_code}: {response.text}"
                }
        except Exception as e:
            return {
                "success": False,
                "error": f"Failed to send notification: {str(e)}"
            }

    def send_task_notification(self, task_id: str, tool: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Send task assignment notification to agent
        
        Args:
            task_id: Unique task identifier
            tool: Tool name to invoke on agent
            arguments: Tool arguments
            
        Returns:
            Status dict with success indicator
        """
        return self.send_notification(
            "notifications/tasks/new",
            {
                "task_id": task_id,
                "tool": tool,
                "arguments": arguments
            }
        )

    def send_task_status_notification(self, task_id: str, status: str, 
                                       progress: int = 0, 
                                       result: Optional[Dict[str, Any]] = None,
                                       error: Optional[str] = None) -> Dict[str, Any]:
        """Send task status update notification
        
        Args:
            task_id: Unique task identifier
            status: Task status (queued, in_progress, completed, failed)
            progress: Progress percentage (0-100)
            result: Task result (if completed)
            error: Error message (if failed)
            
        Returns:
            Status dict with success indicator
        """
        params = {
            "task_id": task_id,
            "status": status,
            "progress": progress,
            "timestamp": time.time()
        }
        
        if result is not None:
            params["result"] = result
        if error is not None:
            params["error"] = error
            
        return self.send_notification("notifications/tasks/status", params)