"""Data models for registered MCP servers."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel


class ServerCapabilities(BaseModel):
    """Capabilities of an MCP server."""
    resources: Optional[bool] = False
    tools: Optional[bool] = False
    prompts: Optional[bool] = False
    roots: Optional[bool] = False
    sampling: Optional[bool] = False


class RegisteredServer(BaseModel):
    """Model representing a registered MCP server."""
    id: str
    name: str
    description: Optional[str] = None
    endpoint: str  # URL or stdio for the server
    capabilities: ServerCapabilities
    metadata: Optional[Dict[str, str]] = None
    registered_at: datetime
    last_seen: Optional[datetime] = None
    health_status: str = "unknown"  # healthy, unhealthy, unknown
    tags: Optional[List[str]] = None


class RegisterServerRequest(BaseModel):
    """Request model for registering a new server."""
    name: str
    description: Optional[str] = None
    endpoint: str
    capabilities: ServerCapabilities
    metadata: Optional[Dict[str, str]] = None
    tags: Optional[List[str]] = None


class UpdateServerStatusRequest(BaseModel):
    """Request model for updating server status."""
    health_status: str  # healthy, unhealthy, unknown