"""Main entry point for the MCP Server Registry."""

import argparse
import asyncio
import sys
import os

# Add the project root to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.server.registry_server import RegistryServer


def main():
    parser = argparse.ArgumentParser(description="MCP Server Registry")
    parser.add_argument(
        "--transport",
        choices=["stdio", "streamable-http"],
        default="stdio",
        help="Transport method for the MCP server (default: stdio)"
    )
    parser.add_argument(
        "--host",
        default="0.0.0.0",
        help="Host for HTTP transport (default: 0.0.0.0)"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8080,
        help="Port for HTTP transport (default: 8080)"
    )
    
    args = parser.parse_args()
    
    print(f"Starting MCP Server Registry with {args.transport} transport...")
    
    registry_server = RegistryServer()
    
    if args.transport == "streamable-http":
        registry_server.run(
            transport="streamable-http",
            host=args.host,
            port=args.port
        )
    else:
        # Default to stdio for local connections
        registry_server.run(transport="stdio")


if __name__ == "__main__":
    main()