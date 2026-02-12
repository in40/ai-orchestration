"""
Example usage of the MCP Server
Demonstrates how to extend the server with custom functionality
"""

from mcp_server.server import McpServer
from mcp_server.handlers.server_handlers import McpServerHandlers
from mcp_server.utils.notifications import NotificationManager


class CustomMcpServer(McpServer):
    """Example of extending the MCP server with custom functionality"""
    
    def __init__(self, transport_type="stdio", host="127.0.0.1", port=3030, enable_registry=False):
        super().__init__(transport_type, host, port, enable_registry)
        
        # Add custom tools, resources, or prompts
        self._add_custom_endpoints()
    
    def _add_custom_endpoints(self):
        """Add custom endpoints to demonstrate extensibility"""
        # Add a custom tool
        custom_tool = {
            "name": "custom_weather_tool",
            "description": "A custom tool to get weather information",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "The city and country to get weather for"
                    }
                },
                "required": ["location"]
            }
        }
        self.server_handlers.tools.append(custom_tool)
        
        # Add a custom resource
        custom_resource = {
            "uri": "custom://config/settings",
            "name": "System Settings",
            "description": "Current system configuration settings"
        }
        self.server_handlers.resources.append(custom_resource)
        
        # Add a custom prompt
        custom_prompt = {
            "name": "custom_report_prompt",
            "description": "A template for generating custom reports",
            "arguments": [
                {
                    "name": "report_type",
                    "type": "string",
                    "description": "The type of report to generate"
                }
            ]
        }
        self.server_handlers.prompts.append(custom_prompt)


class RegistryMcpServer(CustomMcpServer):
    """
    Example of an MCP server configured as a registry.
    
    This server can track multiple MCP services and allow AI agents to discover
    available services and their capabilities.
    
    HOW TO USE REGISTRY FUNCTIONALITY:
    1. Run the registry server with --enable-registry flag:
       python example.py --transport http --port 3030 --enable-registry
       
    2. Other MCP servers can register with this registry by calling:
       POST /send with JSON-RPC message:
       {
         "jsonrpc": "2.0",
         "id": "1",
         "method": "registry/register",
         "params": {
           "id": "db-service-1",
           "name": "Database Access Service",
           "description": "Provides database query capabilities",
           "endpoint": "http://localhost:3031",  # Different port for the service
           "capabilities": {
             "tools": ["query_db", "insert_record"],
             "resources": ["db://users", "db://products"]
           }
         }
       }
       
    3. AI agents can discover services by calling:
       POST /send with JSON-RPC message:
       {
         "jsonrpc": "2.0",
         "id": "2",
         "method": "registry/list",
         "params": {}
       }
    """
    
    def __init__(self, transport_type="http", host="127.0.0.1", port=3030):
        # Enable registry functionality
        super().__init__(transport_type, host, port, enable_registry=True)
        
        print(f"Registry server initialized at http://{host}:{port}")
        print("Other MCP services can register with this server")
        print("AI agents can discover available services through this server")


def run_example_stdio():
    """Example of running the server with stdio transport"""
    print("Starting MCP Server with stdio transport...")
    print("Try sending a message like:")
    print('{"jsonrpc": "2.0", "id": "1", "method": "initialize", "params": {"clientInfo": {"name": "example-client", "version": "1.0"}}}')
    print("")
    
    server = CustomMcpServer(transport_type="stdio")
    server.start()


def run_example_http():
    """Example of running the server with HTTP transport"""
    print("Starting MCP Server with HTTP/SSE transport...")
    print(f"Server will be available at http://127.0.0.1:3030")
    print("SSE endpoint: /sse")
    print("Message endpoint: /send")
    print("")
    
    server = CustomMcpServer(transport_type="http", host="127.0.0.1", port=3030)
    server.start()


def run_example_registry():
    """Example of running the server as a registry"""
    print("Starting MCP Registry Server...")
    print("This server can track multiple MCP services")
    print("Other services can register with this server")
    print("AI agents can discover available services through this server")
    print("")
    
    server = RegistryMcpServer(transport_type="http", host="127.0.0.1", port=3030)
    server.start()


if __name__ == "__main__":
    import sys
    import argparse
    
    parser = argparse.ArgumentParser(description='MCP Server Examples')
    parser.add_argument('--transport', 
                       choices=['stdio', 'http'], 
                       default='stdio',
                       help='Transport mechanism to use (default: stdio)')
    parser.add_argument('--enable-registry', 
                       action='store_true',
                       help='Run as a registry server')
    
    args = parser.parse_args()
    
    if args.enable_registry:
        run_example_registry()
    elif args.transport == "http":
        run_example_http()
    else:
        run_example_stdio()