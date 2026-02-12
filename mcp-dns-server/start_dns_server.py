#!/bin/bash
"""
Start the DNS Resolving MCP Server
"""
import sys
import argparse
from dns_server import DnsResolvingMcpServer


def main():
    parser = argparse.ArgumentParser(description='DNS Resolving MCP Server')
    parser.add_argument('--transport',
                       choices=['stdio', 'http'],
                       default='stdio',
                       help='Transport mechanism to use (default: stdio)')
    parser.add_argument('--host',
                       default='127.0.0.1',
                       help='Host for HTTP transport (default: 127.0.0.1)')
    parser.add_argument('--port',
                       type=int,
                       default=3040,  # Changed from default 3030 to 3040
                       help='Port for HTTP transport (default: 3040)')
    parser.add_argument('--enable-registry',
                       action='store_true',
                       help='Enable registry functionality to track multiple MCP services (optional)')
    parser.add_argument('--register-with-registry',
                       action='store_true',
                       help='Register this server with a registry server (requires --registry-host and --registry-port)')
    parser.add_argument('--registry-host',
                       default='127.0.0.1',
                       help='Registry server host to register with (default: 127.0.0.1)')
    parser.add_argument('--registry-port',
                       type=int,
                       default=3031,
                       help='Registry server port to register with (default: 3031)')
    parser.add_argument('--use-postgres',
                       action='store_true',
                       help='Use PostgreSQL for registry storage instead of SQLite (optional)')
    parser.add_argument('--postgres-host',
                       default='127.0.0.1',
                       help='PostgreSQL host (default: 127.0.0.1)')
    parser.add_argument('--postgres-port',
                       type=int,
                       default=5432,
                       help='PostgreSQL port (default: 5432)')
    parser.add_argument('--postgres-db',
                       default='mcp_registry',
                       help='PostgreSQL database name (default: mcp_registry)')
    parser.add_argument('--postgres-user',
                       default='postgres',
                       help='PostgreSQL username (default: postgres)')
    parser.add_argument('--postgres-password',
                       default='',
                       help='PostgreSQL password (default: empty)')

    args = parser.parse_args()

    # Convert localhost to 127.0.0.1 to avoid IPv6 resolution issues
    postgres_host = args.postgres_host
    if postgres_host == "localhost":
        postgres_host = "127.0.0.1"
    elif postgres_host == "::1":
        postgres_host = "127.0.0.1"

    print(f"Starting DNS Resolving MCP Server on {args.host}:{args.port}")
    
    server = DnsResolvingMcpServer(
        transport_type=args.transport,
        host=args.host,
        port=args.port,
        enable_registry=args.enable_registry,
        register_with_registry=args.register_with_registry,
        registry_host=args.registry_host,
        registry_port=args.registry_port,
        use_postgres=args.use_postgres,
        postgres_host=postgres_host,
        postgres_port=args.postgres_port,
        postgres_db=args.postgres_db,
        postgres_user=args.postgres_user,
        postgres_password=args.postgres_password
    )
    server.start()


if __name__ == "__main__":
    main()