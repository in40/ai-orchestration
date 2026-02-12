from pydantic_settings import BaseSettings
from typing import Optional, List


class Settings(BaseSettings):
    server_name: str = "vibe-coding-agent"
    server_description: str = "AI coding agent that turns natural language into code using local LLM (vibe coding)"
    server_version: str = "1.0.0"
    capabilities: List[str] = ["tools", "resources"]   # we expose tools
    tags: List[str] = ["coding", "llm", "vibe", "local"]
    port: int = 3060                                   # changed to 3060 as requested
    registry_url: Optional[str] = "https://your-registry.com/register"  # Registry enabled
    host: str = "127.0.0.1"
    
    # LM Studio configuration
    llm_base_url: str = "http://asus-tus:1234/v1"
    llm_model: str = "qwen3-4b"


settings = Settings()