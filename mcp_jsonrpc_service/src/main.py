#!/usr/bin/env python3
"""
Main entry point for the base MCP server.

This script initializes and runs an MCP server that can be extended with specific functionality.
"""

import argparse
import asyncio
import logging
import sys
from typing import Optional

from .server import BaseMCPServer
from .config import load_config_from_env, merge_config_with_args


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description="Base MCP Server")
    parser.add_argument(
        "--transport",
        choices=["stdio", "http"],
        help="Transport method for the server"
    )
    parser.add_argument(
        "--host",
        help="Host for HTTP transport"
    )
    parser.add_argument(
        "--port",
        type=int,
        help="Port for HTTP transport"
    )
    parser.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        help="Logging level"
    )
    parser.add_argument(
        "--registry-endpoint",
        help="Registry endpoint to register with"
    )
    parser.add_argument(
        "--disable-health-monitoring",
        action="store_true",
        help="Disable automatic health monitoring"
    )
    parser.add_argument(
        "--health-interval",
        type=int,
        help="Health check interval in seconds"
    )
    
    return parser.parse_args()


def setup_logging(log_level: str):
    """Set up logging configuration."""
    logging.basicConfig(
        level=getattr(logging, log_level),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )


async def main():
    """Main entry point for the base MCP server."""
    args = parse_args()
    
    # Load configuration from environment variables
    config = load_config_from_env()
    
    # Merge with command-line arguments
    config = merge_config_with_args(config, args)
    
    setup_logging(config.log_level)
    
    logger = logging.getLogger(__name__)
    logger.info(f"Starting base MCP server with transport: {config.transport}")
    
    # Initialize the base server
    server = BaseMCPServer(
        transport=config.transport,
        host=config.host,
        port=config.port
    )
    
    # Set server properties from config
    server.name = config.name
    server.description = config.description
    
    try:
        # Start the server
        await server.start()
        
        # Enable health monitoring if configured
        if config.enable_health_monitoring and not args.disable_health_monitoring:
            registry_endpoint = config.registry_endpoint
            if args.registry_endpoint:  # Override with command-line arg if provided
                registry_endpoint = args.registry_endpoint
            server.enable_health_monitoring(
                interval=args.health_interval or config.health_check_interval,
                registry_endpoint=registry_endpoint
            )
        
        # Register with the registry
        registry_endpoint = config.registry_endpoint
        if args.registry_endpoint:
            registry_endpoint = args.registry_endpoint
        await server.register_with_registry(registry_endpoint)
        
        # Keep the server running
        await server.wait_for_shutdown()
        
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        await server.shutdown()


if __name__ == "__main__":
    asyncio.run(main())