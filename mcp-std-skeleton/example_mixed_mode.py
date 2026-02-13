"""
Example demonstrating mixed-mode MCP server functionality
"""
from mcp_std_server.server import McpServer


def main():
    print("Starting Mixed-Mode MCP Server Example")
    print("=====================================")
    print("This server operates in mixed mode, functioning as both:")
    print("- An MCP server (receiving tasks from clients)")
    print("- An MCP client (submitting tasks to other servers)")
    print("")
    
    # Create a mixed-mode server
    server = McpServer(
        transport_type="streamable-http",
        host="127.0.0.1", 
        port=3030,
        enable_client_mode=True,           # Enable client functionality
        client_transport_type="streamable-http",
        client_host="127.0.0.1",
        client_port=3031,                # Connect to another server at port 3031
        enable_registry=True,             # Enable service discovery
        register_with_registry=True,      # Register with a registry server
        registry_host="127.0.0.1",
        registry_port=3032               # Registry server at port 3032
    )
    
    print("Server configuration:")
    print(f"  - Server transport: {server.transport_type} on {server.host}:{server.port}")
    print(f"  - Client enabled: {server.enable_client_mode}")
    print(f"  - Client transport: {server.client_transport_type} to {server.client_host}:{server.client_port}")
    print(f"  - Registry enabled: {server.enable_registry}")
    print("")
    
    print("In mixed mode, this server can:")
    print("1. Accept incoming connections and handle requests")
    print("2. Connect to other MCP servers as a client")
    print("3. Delegate tasks to other registered servers via the registry")
    print("4. Perform cross-server operations like remote tool calls")
    print("")
    
    print("To run this server, use:")
    print("python -m mcp_std_server.server --transport streamable-http --port 3030 --enable-client-mode --client-host 127.0.0.1 --client-port 3031 --enable-registry")
    print("")
    
    print("The server would normally start listening, but for this example we'll just show the configuration.")


if __name__ == "__main__":
    main()