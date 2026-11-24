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
    llm_base_url: str = os.environ.get("LLM_BASE_URL") or os.environ.get("OPENCODE_BASE_URL") or ""
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


def results_repo_url():
    """ssh-url of the results repository (settings override, then env).
    Required: a silent default would push customer artifacts elsewhere."""
    url = (settings.mcp_git_repo_url or os.environ.get("MCP_GIT_REPO_URL") or "").strip()
    if not url:
        raise RuntimeError(
            "MCP_GIT_REPO_URL is not set - add the ssh url of the results "
            "repository to .env (e.g. ssh://user@host/home/user/mcp-results.git)")
    return url