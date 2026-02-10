"""Configuration settings for the MCP Server Registry."""

import os
from typing import Optional


class Settings:
    """Application settings loaded from environment variables."""
    
    def __init__(self):
        self.database_url: str = os.getenv(
            "DATABASE_URL", 
            "postgresql://mcp_user:mcp_password@localhost/mcp_registry"
        )
        self.redis_url: str = os.getenv(
            "REDIS_URL", 
            "redis://localhost:6379"
        )
        self.http_host: str = os.getenv("HTTP_HOST", "0.0.0.0")
        self.http_port: int = int(os.getenv("HTTP_PORT", "8080"))
        self.log_level: str = os.getenv("LOG_LEVEL", "INFO")
        self.health_check_interval: int = int(os.getenv("HEALTH_CHECK_INTERVAL", "60"))  # seconds
        
        # JWT secret for authentication (should be set in production)
        self.jwt_secret: str = os.getenv("JWT_SECRET", "dev-secret-change-in-production")
        self.jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
        
        # CORS settings
        self.cors_origins: str = os.getenv("CORS_ORIGINS", "*")
        
        # Registry-specific settings
        self.max_registration_attempts: int = int(os.getenv("MAX_REGISTRATION_ATTEMPTS", "3"))
        self.registration_timeout: int = int(os.getenv("REGISTRATION_TIMEOUT", "30"))  # seconds
        
        # Session management settings
        self.session_timeout: int = int(os.getenv("SESSION_TIMEOUT", "3600"))  # seconds
        # Initially disable session requirement for registration to allow first-time registration
        self.require_session_for_registration: bool = os.getenv("REQUIRE_SESSION_FOR_REGISTRATION", "false").lower() == "true"
        self.require_session_for_updates: bool = os.getenv("REQUIRE_SESSION_FOR_UPDATES", "true").lower() == "true"


# Global settings instance
settings = Settings()