"""Database service for the MCP Server Registry."""

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker
from sqlalchemy.exc import SQLAlchemyError
from contextlib import contextmanager
import os
from typing import Generator

from src.models.database import Base, DBRegisteredServer
from src.models.server import RegisteredServer, RegisterServerRequest, UpdateServerStatusRequest
from config.settings import settings


class DatabaseService:
    def __init__(self):
        # Use settings for database URL
        self.engine = create_engine(settings.database_url)
        self.SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=self.engine)
        
        # Create tables
        Base.metadata.create_all(bind=self.engine)

    @contextmanager
    def get_db_session(self):
        """Context manager for database sessions."""
        db = self.SessionLocal()
        try:
            yield db
        except SQLAlchemyError:
            db.rollback()
            raise
        finally:
            db.close()

    def register_server(self, server_request: RegisterServerRequest) -> RegisteredServer:
        """Register a new server in the database."""
        db_server = DBRegisteredServer(
            name=server_request.name,
            description=server_request.description,
            endpoint=server_request.endpoint,
            capabilities=server_request.capabilities.model_dump(),
            metadata_=server_request.metadata,
            tags=server_request.tags
        )
        
        with self.get_db_session() as db:
            db.add(db_server)
            db.commit()
            db.refresh(db_server)
            
            # Convert to Pydantic model
            return RegisteredServer(
                id=db_server.id,
                name=db_server.name,
                description=db_server.description,
                endpoint=db_server.endpoint,
                capabilities=server_request.capabilities,
                metadata=db_server.metadata_,
                registered_at=db_server.registered_at,
                last_seen=db_server.last_seen,
                health_status=db_server.health_status,
                tags=db_server.tags
            )

    def get_server_by_id(self, server_id: str) -> RegisteredServer:
        """Retrieve a server by its ID."""
        with self.get_db_session() as db:
            db_server = db.query(DBRegisteredServer).filter(DBRegisteredServer.id == server_id).first()
            if not db_server:
                return None
                
            # Convert to Pydantic model
            capabilities = db_server.capabilities
            return RegisteredServer(
                id=db_server.id,
                name=db_server.name,
                description=db_server.description,
                endpoint=db_server.endpoint,
                capabilities=capabilities,
                metadata=db_server.metadata_,
                registered_at=db_server.registered_at,
                last_seen=db_server.last_seen,
                health_status=db_server.health_status,
                tags=db_server.tags
            )

    def get_all_servers(self) -> list[RegisteredServer]:
        """Retrieve all registered servers."""
        with self.get_db_session() as db:
            db_servers = db.query(DBRegisteredServer).all()
            
            servers = []
            for db_server in db_servers:
                capabilities = db_server.capabilities
                server = RegisteredServer(
                    id=db_server.id,
                    name=db_server.name,
                    description=db_server.description,
                    endpoint=db_server.endpoint,
                    capabilities=capabilities,
                    metadata=db_server.metadata_,
                    registered_at=db_server.registered_at,
                    last_seen=db_server.last_seen,
                    health_status=db_server.health_status,
                    tags=db_server.tags
                )
                servers.append(server)
                
            return servers

    def update_server_status(self, server_id: str, status_request: UpdateServerStatusRequest) -> bool:
        """Update the status of a registered server."""
        with self.get_db_session() as db:
            db_server = db.query(DBRegisteredServer).filter(DBRegisteredServer.id == server_id).first()
            if not db_server:
                return False
                
            db_server.health_status = status_request.health_status
            db_server.last_seen = func.now()
            db.commit()
            return True

    def search_servers(self, query: str = None, tags: list[str] = None) -> list[RegisteredServer]:
        """Search for servers based on query and tags."""
        with self.get_db_session() as db:
            query_obj = db.query(DBRegisteredServer)
            
            if query:
                # Search in name and description
                query_obj = query_obj.filter(
                    (DBRegisteredServer.name.contains(query)) | 
                    (DBRegisteredServer.description.contains(query))
                )
            
            if tags:
                # Filter by tags - using a simple approach that works with JSON columns
                # This checks if the tag exists in the JSON array by converting to string
                for tag in tags:
                    # Simple approach: check if tag exists in the JSON string representation
                    query_obj = query_obj.filter(
                        DBRegisteredServer.tags.cast(String).contains(tag)
                    )
            
            db_servers = query_obj.all()
            
            servers = []
            for db_server in db_servers:
                capabilities = db_server.capabilities
                server = RegisteredServer(
                    id=db_server.id,
                    name=db_server.name,
                    description=db_server.description,
                    endpoint=db_server.endpoint,
                    capabilities=capabilities,
                    metadata=db_server.metadata_,
                    registered_at=db_server.registered_at,
                    last_seen=db_server.last_seen,
                    health_status=db_server.health_status,
                    tags=db_server.tags
                )
                servers.append(server)
                
            return servers