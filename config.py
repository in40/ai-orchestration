"""
MCP Orchestration System - Central Configuration

This module provides centralized configuration management for all MCP servers.
Settings are loaded from .env file and can be overridden by environment variables.

Usage:
    from config import get_settings
    settings = get_settings()
    
    # Access settings
    print(settings.IT_LEAD_PORT)
    print(settings.POSTGRES_HOST)
"""

from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from functools import lru_cache
from typing import Optional
from pathlib import Path

# Get the directory where config.py is located
BASE_DIR = Path(__file__).parent

# Full path to .env file
ENV_FILE = BASE_DIR / ".env"


class Settings(BaseSettings):
    """
    Central configuration for MCP Orchestration System.
    
    All settings can be set via:
    1. .env file (primary method)
    2. Environment variables (overrides .env)
    3. Default values (fallback)
    """
    
    # =========================================================================
    # NETWORK CONFIGURATION
    # =========================================================================
    
    NETWORK_DOMAIN: str = Field(
        default="192.168.51.0/24",
        description="Local network domain for multi-computer access"
    )
    
    # =========================================================================
    # SERVER PORTS
    # =========================================================================
    
    REGISTRY_PORT: int = Field(
        default=3031,
        description="MCP Registry Server port"
    )
    
    IMPLEMENTATION_PORT: int = Field(
        default=3060,
        description="Implementation Engineer Server port"
    )
    
    REQUIREMENTS_PORT: int = Field(
        default=3062,
        description="Requirements Engineer Server port"
    )
    
    IT_LEAD_PORT: int = Field(
        default=3061,
        description="IT Lead Server port"
    )
    
    TEAM_PORT: int = Field(
        default=3063,
        description="Team Management Server port"
    )
    
    DEVOPS_PORT: int = Field(
        default=3071,
        description="DevOps Release Engineer Server port"
    )
    
    DOCUMENT_STORE_PORT: int = Field(
        default=3070,
        description="Document Store Server port"
    )
    
    WEB_UI_BACKEND_PORT: int = Field(
        default=8000,
        description="Web UI Backend API port"
    )
    
    WEB_UI_FRONTEND_PORT: int = Field(
        default=5173,
        description="Web UI Frontend dev server port"
    )
    
    # =========================================================================
    # SERVER HOSTS
    # =========================================================================
    
    REGISTRY_HOST: str = Field(
        default="127.0.0.1",
        description="Registry Server host (use 0.0.0.0 for network access)"
    )
    
    IT_LEAD_HOST: str = Field(
        default="127.0.0.1",
        description="IT Lead Server host"
    )
    
    WEB_UI_HOST: str = Field(
        default="0.0.0.0",
        description="Web UI Backend host (0.0.0.0 for network access)"
    )
    
    # =========================================================================
    # POSTGRESQL DATABASE
    # =========================================================================
    
    POSTGRES_HOST: str = Field(
        default="127.0.0.1",
        description="PostgreSQL database host"
    )
    
    POSTGRES_PORT: int = Field(
        default=5432,
        description="PostgreSQL database port"
    )
    
    POSTGRES_DB: str = Field(
        default="mcp_registry",
        description="PostgreSQL database name"
    )
    
    POSTGRES_USER: str = Field(
        default="postgres",
        description="PostgreSQL username"
    )
    
    POSTGRES_PASSWORD: str = Field(
        default="postgres",
        description="PostgreSQL password (change in production!)"
    )
    
    # =========================================================================
    # LLM CONFIGURATION
    # =========================================================================

    LLM_PROVIDER_URL: str = Field(
        default="http://192.168.51.237:1234/v1/chat/completions",
        description="LLM API endpoint URL"
    )

    LLM_MODEL: str = Field(
        default=None,  # MUST be set in .env file, no hardcoded default
        description="LLM model name - MUST be configured in .env file"
    )
    
    LLM_TEMPERATURE: float = Field(
        default=0.3,
        description="Default LLM temperature for planning"
    )
    
    # =========================================================================
    # GIT REPOSITORY
    # =========================================================================
    
    GIT_SERVER_HOST: str = Field(
        default="192.168.51.187",
        description="Git repository server hostname"
    )
    
    GIT_SERVER_PORT: int = Field(
        default=22,
        description="Git server SSH port"
    )
    
    GIT_REPO_PATH: str = Field(
        default="/home/sorokin/mcp-results",
        description="Path to Git repository on server"
    )
    
    GIT_REPO_URL: str = Field(
        default="ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git",
        description="Full Git repository URL for cloning"
    )
    
    GIT_LOCAL_CLONE_PATH: str = Field(
        default="/tmp/mcp-vibe-coding-git/repo",
        description="Local path to Git repository clone"
    )
    
    # =========================================================================
    # WEB UI CONFIGURATION
    # =========================================================================
    
    WEB_UI_PUBLIC_URL: str = Field(
        default="http://192.168.51.1:8000",
        description="Public URL for Web UI (used for generating links)"
    )
    
    WEB_UI_FRONTEND_URL: str = Field(
        default="http://192.168.51.1:5173",
        description="Public URL for Web UI frontend"
    )
    
    # =========================================================================
    # PERFORMANCE & LIMITS
    # =========================================================================
    
    MAX_CONCURRENT_REQUESTS: int = Field(
        default=10,
        description="Maximum concurrent requests per server"
    )
    
    REQUEST_TIMEOUT: int = Field(
        default=120,
        description="HTTP request timeout in seconds"
    )
    
    MAX_FILE_SIZE_MB: int = Field(
        default=50,
        description="Maximum file size for uploads (MB)"
    )
    
    # =========================================================================
    # LOGGING
    # =========================================================================
    
    LOG_LEVEL: str = Field(
        default="INFO",
        description="Logging level (DEBUG, INFO, WARNING, ERROR)"
    )
    
    LOG_DIR: str = Field(
        default="/tmp",
        description="Directory for log files"
    )
    
    # =========================================================================
    # FEATURE FLAGS
    # =========================================================================
    
    ENABLE_REGISTRY: bool = Field(
        default=True,
        description="Enable service registry"
    )
    
    REGISTER_WITH_REGISTRY: bool = Field(
        default=True,
        description="Auto-register servers with registry"
    )
    
    USE_POSTGRES: bool = Field(
        default=True,
        description="Use PostgreSQL instead of SQLite"
    )
    
    # =========================================================================
    # PATHS
    # =========================================================================
    
    BASE_DIR: str = Field(
        default="/root/qwen/base",
        description="Base directory for MCP system"
    )
    
    DATA_DIR: str = Field(
        default="/root/qwen/base/data",
        description="Data directory for storage"
    )

    model_config = SettingsConfigDict(
        env_file=str(ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )


# Global settings cache
_settings: Optional[Settings] = None


def get_settings() -> Settings:
    """
    Get settings instance (cached for performance).
    
    Returns:
        Settings: Configuration settings
    """
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reload_settings() -> Settings:
    """
    Force reload settings from .env file.
    Use this when .env file changes at runtime.
    
    Returns:
        Settings: Fresh configuration settings
    """
    global _settings
    # Clear the cache
    _settings = None
    # Create new instance
    _settings = Settings()
    return _settings


def clear_settings_cache():
    """
    Clear the settings cache without reloading.
    Next call to get_settings() will reload from .env.
    """
    global _settings
    _settings = None


# Convenience function for quick access
settings = get_settings()


if __name__ == "__main__":
    # Print current configuration when run as script
    s = get_settings()
    print("MCP System Configuration")
    print("=" * 60)
    print(f"Network Domain:        {s.NETWORK_DOMAIN}")
    print(f"\nServer Ports:")
    print(f"  Registry:            {s.REGISTRY_PORT}")
    print(f"  IT Lead:             {s.IT_LEAD_PORT}")
    print(f"  Implementation:      {s.IMPLEMENTATION_PORT}")
    print(f"  Requirements:        {s.REQUIREMENTS_PORT}")
    print(f"  Web UI Backend:      {s.WEB_UI_BACKEND_PORT}")
    print(f"  Web UI Frontend:     {s.WEB_UI_FRONTEND_PORT}")
    print(f"\nDatabase:")
    print(f"  Host:                {s.POSTGRES_HOST}:{s.POSTGRES_PORT}")
    print(f"  Database:            {s.POSTGRES_DB}")
    print(f"  User:                {s.POSTGRES_USER}")
    print(f"\nLLM:")
    print(f"  URL:                 {s.LLM_PROVIDER_URL}")
    print(f"  Model:               {s.LLM_MODEL}")
    print(f"\nGit Repository:")
    print(f"  Server:              {s.GIT_SERVER_HOST}")
    print(f"  URL:                 {s.GIT_REPO_URL}")
    print(f"\nWeb UI:")
    print(f"  Public URL:          {s.WEB_UI_PUBLIC_URL}")
