"""
Configuration Module

This module handles configuration for the MCP server using environment variables,
command-line arguments, and configuration files.
"""
import os
from typing import Optional
from dataclasses import dataclass
from dotenv import load_dotenv


# Load environment variables from .env file if it exists
load_dotenv()


@dataclass
class ServerConfig:
    """
    Configuration class holding all server settings.
    """
    # Transport settings
    transport: str = "stdio"
    host: str = "0.0.0.0"
    port: int = 8080
    
    # Server identification
    name: str = "dns-resolver-mcp-server"
    description: str = "DNS Resolver MCP server that provides DNS resolution services"
    
    # Registry settings
    registry_endpoint: str = "stdio://"
    
    # Health monitoring
    health_check_interval: int = 60
    enable_health_monitoring: bool = True
    
    # Logging
    log_level: str = "INFO"
    
    # Database settings (if needed)
    database_url: str = "sqlite:///./mcp_server.db"
    
    # Cache settings (if needed)
    redis_url: str = "redis://localhost:6379"
    
    # Security settings
    jwt_secret: str = "dev-secret-change-in-production"
    cors_origins: str = "*"
    
    # Registration settings
    max_registration_attempts: int = 3
    registration_timeout: int = 30


def load_config_from_env() -> ServerConfig:
    """
    Load configuration from environment variables.
    
    Returns:
        ServerConfig: Configuration object with values from environment variables
    """
    config = ServerConfig()
    
    # Transport settings
    config.transport = os.getenv("MCP_TRANSPORT", config.transport)
    config.host = os.getenv("MCP_HOST", config.host)
    config.port = int(os.getenv("MCP_PORT", config.port))
    
    # Server identification
    config.name = os.getenv("MCP_NAME", config.name)
    config.description = os.getenv("MCP_DESCRIPTION", config.description)
    
    # Registry settings
    config.registry_endpoint = os.getenv("MCP_REGISTRY_ENDPOINT", config.registry_endpoint)
    
    # Health monitoring
    config.health_check_interval = int(os.getenv("MCP_HEALTH_CHECK_INTERVAL", config.health_check_interval))
    config.enable_health_monitoring = os.getenv("MCP_ENABLE_HEALTH_MONITORING", str(config.enable_health_monitoring)).lower() == "true"
    
    # Logging
    config.log_level = os.getenv("MCP_LOG_LEVEL", config.log_level)
    
    # Database settings
    config.database_url = os.getenv("MCP_DATABASE_URL", config.database_url)
    
    # Cache settings
    config.redis_url = os.getenv("MCP_REDIS_URL", config.redis_url)
    
    # Security settings
    config.jwt_secret = os.getenv("MCP_JWT_SECRET", config.jwt_secret)
    config.cors_origins = os.getenv("MCP_CORS_ORIGINS", config.cors_origins)
    
    # Registration settings
    config.max_registration_attempts = int(os.getenv("MCP_MAX_REGISTRATION_ATTEMPTS", config.max_registration_attempts))
    config.registration_timeout = int(os.getenv("MCP_REGISTRATION_TIMEOUT", config.registration_timeout))
    
    return config


def merge_config_with_args(config: ServerConfig, args) -> ServerConfig:
    """
    Merge configuration from environment variables with command-line arguments.
    
    Args:
        config: Configuration object loaded from environment
        args: Parsed command-line arguments
        
    Returns:
        ServerConfig: Merged configuration object
    """
    # Override with command-line arguments if provided
    if hasattr(args, 'transport') and args.transport:
        config.transport = args.transport
    
    if hasattr(args, 'host') and args.host:
        config.host = args.host
    
    if hasattr(args, 'port') and args.port:
        config.port = args.port
    
    if hasattr(args, 'log_level') and args.log_level:
        config.log_level = args.log_level
    
    return config