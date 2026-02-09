"""SQLAlchemy database models for the MCP Server Registry."""

from sqlalchemy import Column, String, DateTime, Text, JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
import uuid

Base = declarative_base()


class DBRegisteredServer(Base):
    """Database model for registered MCP servers."""
    __tablename__ = "registered_servers"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String, nullable=False)
    description = Column(Text)
    endpoint = Column(String, nullable=False)
    capabilities = Column(JSON, nullable=False)  # JSON representation of ServerCapabilities
    metadata_ = Column(JSON)  # Additional metadata as key-value pairs (using metadata_ to avoid conflict)
    registered_at = Column(DateTime, server_default=func.now())
    last_seen = Column(DateTime)
    health_status = Column(String, default="unknown")  # healthy, unhealthy, unknown
    tags = Column(JSON)  # List of tags