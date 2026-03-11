from pydantic_settings import BaseSettings
from typing import Optional, List
import os


class Settings(BaseSettings):
    server_name: str = "Implementation Engineer"
    server_description: str = "AI coding agent that turns natural language into code using local LLM (vibe coding)"
    server_version: str = "1.0.0"
    capabilities: List[str] = ["tools", "resources"]   # we expose tools
    tags: List[str] = ["coding", "llm", "vibe", "local"]
    port: int = 3060                                   # changed to 3060 as requested
    registry_url: Optional[str] = "https://your-registry.com/register"  # Registry enabled
    host: str = "127.0.0.1"

    # LM Studio configuration
    llm_base_url: str = "http://192.168.51.237:1234/v1"
    llm_model: Optional[str] = None  # REQUIRED from config

    # PostgreSQL configuration for persistent task storage
    postgres_host: str = "127.0.0.1"
    postgres_port: int = 5432
    postgres_db: str = "mcp_registry"
    postgres_user: str = "postgres"
    postgres_password: str = os.getenv("POSTGRES_PASSWORD", "")  # Use environment variable

    # Git repository configuration for code storage
    mcp_git_repo_url: Optional[str] = None  # Git repository for MCP agent results (falls back to MCP_GIT_REPO_URL env var)


settings = Settings()