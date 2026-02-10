"""
Database Integration for MCP Server Registry
Optional feature to store service information in a database
"""
import sqlite3
import json
from datetime import datetime
from typing import Dict, Any, List, Optional


class ServiceRegistryDB:
    """
    Optional database integration for MCP server registry functionality.
    
    This class provides storage for service registration information when
    implementing a registry server that tracks multiple MCP services.
    
    HOW TO ENABLE:
    1. Uncomment the ServiceRegistryDB import in server.py
    2. Initialize the registry in your server class
    3. Call register_service when services connect
    4. Use list_services to discover available services
    
    USAGE EXAMPLE:
    ```
    registry = ServiceRegistryDB(db_path="mcp_registry.db")
    registry.register_service({
        "id": "db-service-1",
        "name": "Database Access Service",
        "description": "Provides database query capabilities",
        "endpoint": "http://localhost:8081",
        "capabilities": {"tools": ["query_db", "insert_record"]}
    })
    ```
    """
    
    def __init__(self, db_path: str = "mcp_registry.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """
        Initialize the database with required tables.
        Creates a services table to store service registration information.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                description TEXT,
                endpoint TEXT,
                capabilities TEXT,  -- JSON string of capabilities
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        conn.commit()
        conn.close()
    
    def register_service(self, service_info: Dict[str, Any]) -> bool:
        """
        Register a service in the database.
        
        Args:
            service_info: Dictionary containing service information with keys:
                         - id: Unique identifier for the service
                         - name: Human-readable name
                         - description: Brief description of the service
                         - endpoint: Connection endpoint (URL, etc.)
                         - capabilities: Dictionary of service capabilities
        
        Returns:
            True if registration was successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Convert capabilities to JSON string
            capabilities_json = json.dumps(service_info.get("capabilities", {}))
            
            cursor.execute("""
                INSERT OR REPLACE INTO services 
                (id, name, description, endpoint, capabilities, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                service_info.get("id"),
                service_info.get("name", ""),
                service_info.get("description", ""),
                service_info.get("endpoint", ""),
                capabilities_json,
                datetime.now().isoformat()
            ))
            
            conn.commit()
            conn.close()
            return True
        except Exception as e:
            print(f"Error registering service: {e}")
            return False
    
    def unregister_service(self, service_id: str) -> bool:
        """
        Remove a service from the registry.
        
        Args:
            service_id: ID of the service to remove
        
        Returns:
            True if removal was successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM services WHERE id = ?", (service_id,))
            conn.commit()
            conn.close()
            
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error unregistering service: {e}")
            return False
    
    def list_services(self) -> List[Dict[str, Any]]:
        """
        Retrieve all registered services.
        
        Returns:
            List of dictionaries containing service information
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT id, name, description, endpoint, capabilities, registered_at, last_seen
                FROM services
                ORDER BY last_seen DESC
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
        """
        Retrieve a specific service by ID.
        
        Args:
            service_id: ID of the service to retrieve
        
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
    
    def update_last_seen(self, service_id: str) -> bool:
        """
        Update the last seen timestamp for a service.
        
        Args:
            service_id: ID of the service to update
        
        Returns:
            True if update was successful, False otherwise
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("""
                UPDATE services 
                SET last_seen = ? 
                WHERE id = ?
            """, (datetime.now().isoformat(), service_id))
            
            conn.commit()
            conn.close()
            
            return cursor.rowcount > 0
        except Exception as e:
            print(f"Error updating last seen: {e}")
            return False