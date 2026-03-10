"""
Database Integration for MCP Server Registry
Optional database integration for the registry functionality
enabling a registry server that tracks multiple MCP services.

HOW TO USE REGISTRY FUNCTIONALITY:
1. Initialize the ServiceRegistryDB in your server class
2. Call register_service, list_services, and unregister_service methods as needed

EXAMPLE USAGE:
    registry = ServiceRegistryDB(db_path="/root/qwen/base/mcp-std-skeleton/mcp_registry.db")
    registry.register_service({
        "id": "service-123",
        "name": "Example Service",
        "description": "An example service",
        "endpoint": "http://localhost:3030",
        "capabilities": {
            "tools": ["tool1", "tool2"],
            "resources": ["resource1", "resource2"],
            "prompts": ["prompt1", "prompt2"]
        }
    })
    services = registry.list_services()
    registry.unregister_service("service-123")
"""
import sqlite3
import json
import time
from typing import Dict, List, Any, Optional


class ServiceRegistryDB:
    """Optional database integration for MCP server registry functionality.
    
    This class provides database storage for the registry functionality,
    enabling a registry server that tracks multiple MCP services.
    """

    def __init__(self, db_path: str = "/root/qwen/base/mcp-std-skeleton/mcp_registry.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Initialize the database and create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create services table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                endpoint TEXT NOT NULL,
                capabilities TEXT,  -- JSON string
                registered_at REAL NOT NULL,
                last_seen REAL NOT NULL
            )
        """)
        
        conn.commit()
        conn.close()

    def register_service(self, service_info: Dict[str, Any]) -> bool:
        """Register a service with the registry.
        
        Args:
            service_info: Dictionary containing service information
                         Must include: id, name, description, endpoint
                         Can include: capabilities (dict), registered_at (timestamp)
        
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Set timestamps
            now = time.time()
            service_info.setdefault('registered_at', now)
            service_info['last_seen'] = now
            
            # Insert or replace the service
            cursor.execute("""
                INSERT OR REPLACE INTO services 
                (id, name, description, endpoint, capabilities, registered_at, last_seen)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                service_info['id'],
                service_info['name'], 
                service_info['description'],
                service_info['endpoint'],
                json.dumps(service_info.get('capabilities', {})),
                service_info['registered_at'],
                service_info['last_seen']
            ))
            
            conn.commit()
            conn.close()
            
            return True
        except Exception as e:
            print(f"Error registering service: {e}")
            return False

    def list_services(self) -> List[Dict[str, Any]]:
        """List all registered services in the registry.
        
        Returns:
            List of dictionaries containing service information
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, description, endpoint, capabilities, registered_at, last_seen
                FROM services
                ORDER BY name
            """)
            
            rows = cursor.fetchall()
            conn.close()
            
            services = []
            for row in rows:
                service = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "endpoint": row[3],
                    "capabilities": json.loads(row[4]) if row[4] else {},
                    "registered_at": row[5],
                    "last_seen": row[6]
                }
                services.append(service)
            
            return services
        except Exception as e:
            print(f"Error listing services: {e}")
            return []

    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific service by ID.
        
        Args:
            service_id: The ID of the service to retrieve
        
        Returns:
            Service information dictionary or None if not found
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, description, endpoint, capabilities, registered_at, last_seen
                FROM services
                WHERE id = ?
            """, (service_id,))
            
            row = cursor.fetchone()
            conn.close()
            
            if row:
                return {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "endpoint": row[3],
                    "capabilities": json.loads(row[4]) if row[4] else {},
                    "registered_at": row[5],
                    "last_seen": row[6]
                }
            
            return None
        except Exception as e:
            print(f"Error getting service: {e}")
            return None

    def unregister_service(self, service_id: str) -> bool:
        """Remove a service from the registry.
        
        Args:
            service_id: The ID of the service to remove
        
        Returns:
            True if removal was successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
            affected_rows = cursor.rowcount
            
            conn.commit()
            conn.close()
            
            return affected_rows > 0
        except Exception as e:
            print(f"Error unregistering service: {e}")
            return False

    def update_last_seen(self, service_id: str) -> bool:
        """Update the last_seen timestamp for a service.
        
        Args:
            service_id: The ID of the service to update
        
        Returns:
            True if update was successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            now = time.time()
            cursor.execute("""
                UPDATE services 
                SET last_seen = ?
                WHERE id = ?
            """, (now, service_id))
            
            affected_rows = cursor.rowcount
            conn.commit()
            conn.close()
            
            return affected_rows > 0
        except Exception as e:
            print(f"Error updating last seen: {e}")
            return False

    def cleanup_stale_services(self, max_age_minutes: int = 10) -> int:
        """Remove services that haven't been seen within the specified time.
        
        Args:
            max_age_minutes: Maximum age in minutes for services to be considered active
        
        Returns:
            Number of services removed
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            max_age_seconds = max_age_minutes * 60
            cutoff_time = time.time() - max_age_seconds
            
            cursor.execute("""
                DELETE FROM services 
                WHERE last_seen < ?
            """, (cutoff_time,))
            
            removed_count = cursor.rowcount
            conn.commit()
            conn.close()
            
            return removed_count
        except Exception as e:
            print(f"Error cleaning up stale services: {e}")
            return 0