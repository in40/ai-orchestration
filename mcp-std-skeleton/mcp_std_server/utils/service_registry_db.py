"""
Database Integration for MCP Server Registry
Database integration for the registry functionality using PostgreSQL
enabling a registry server that tracks multiple MCP services.

HOW TO USE REGISTRY FUNCTIONALITY:
1. Initialize the ServiceRegistryDB in your server class
2. Call register_service, list_services, and unregister_service methods as needed

EXAMPLE USAGE:
    registry = ServiceRegistryDB(host="localhost", database="mcp_registry", user="postgres", password="postgres")
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
import json
import time
from typing import Dict, List, Any, Optional
import psycopg2


class ServiceRegistryDB:
    """Database integration for MCP server registry functionality using PostgreSQL.

    This class provides database storage for the registry functionality,
    enabling a registry server that tracks multiple MCP services.
    """

    def __init__(self, host: str = "localhost", port: int = 5432, database: str = "mcp_registry",
                 user: str = "postgres", password: str = "postgres"):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        self.init_db()

    def _connect(self):
        """Establish connection to PostgreSQL database"""
        try:
            self.connection = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
        except Exception as e:
            print(f"Failed to connect to PostgreSQL: {e}")
            raise

    def init_db(self):
        """Initialize the database and create tables if they don't exist"""
        try:
            self._connect()
            cursor = self.connection.cursor()

            # Create services table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id TEXT PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    endpoint TEXT NOT NULL,
                    capabilities JSONB,
                    registered_at DOUBLE PRECISION NOT NULL,
                    last_seen DOUBLE PRECISION NOT NULL
                )
            """)

            # Create index for capability searches
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_services_name ON services(name)
            """)

            self.connection.commit()
            cursor.close()
        except Exception as e:
            print(f"Error initializing database: {e}")
            raise

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
            cursor = self.connection.cursor()

            # Set timestamps
            now = time.time()
            service_info.setdefault('registered_at', now)
            service_info['last_seen'] = now

            # Insert or replace the service
            cursor.execute("""
                INSERT INTO services
                (id, name, description, endpoint, capabilities, registered_at, last_seen)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    endpoint = EXCLUDED.endpoint,
                    capabilities = EXCLUDED.capabilities,
                    registered_at = EXCLUDED.registered_at,
                    last_seen = EXCLUDED.last_seen
            """, (
                service_info['id'],
                service_info['name'],
                service_info['description'],
                service_info['endpoint'],
                json.dumps(service_info.get('capabilities', {})),
                service_info['registered_at'],
                service_info['last_seen']
            ))

            self.connection.commit()
            cursor.close()

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
            cursor = self.connection.cursor()

            cursor.execute("""
                SELECT id, name, description, endpoint, capabilities, registered_at, last_seen
                FROM services
                ORDER BY name
            """)

            rows = cursor.fetchall()
            cursor.close()

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
            cursor = self.connection.cursor()

            cursor.execute("""
                SELECT id, name, description, endpoint, capabilities, registered_at, last_seen
                FROM services
                WHERE id = %s
            """, (service_id,))

            row = cursor.fetchone()
            cursor.close()

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
            cursor = self.connection.cursor()

            cursor.execute("DELETE FROM services WHERE id = %s", (service_id,))
            affected_rows = cursor.rowcount

            self.connection.commit()
            cursor.close()

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
            cursor = self.connection.cursor()

            now = time.time()
            cursor.execute("""
                UPDATE services
                SET last_seen = %s
                WHERE id = %s
            """, (now, service_id))

            affected_rows = cursor.rowcount
            self.connection.commit()
            cursor.close()

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
            cursor = self.connection.cursor()

            max_age_seconds = max_age_minutes * 60
            cutoff_time = time.time() - max_age_seconds

            cursor.execute("""
                DELETE FROM services
                WHERE last_seen < %s
            """, (cutoff_time,))

            removed_count = cursor.rowcount
            self.connection.commit()
            cursor.close()

            return removed_count
        except Exception as e:
            print(f"Error cleaning up stale services: {e}")
            return 0

    def find_services_by_capability(self, capability_type: str, capability_name: str) -> List[Dict[str, Any]]:
        """Find services that support a specific capability.

        Args:
            capability_type: Type of capability ('tools', 'resources', 'prompts')
            capability_name: Name of the specific capability

        Returns:
            List of services that support the specified capability
        """
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                SELECT id, name, description, endpoint, capabilities, registered_at, last_seen
                FROM services
            """)

            rows = cursor.fetchall()
            cursor.close()

            matching_services = []
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

                # Check if the service has the requested capability
                capabilities = service.get("capabilities", {})
                if capability_type in capabilities:
                    cap_list = capabilities[capability_type]
                    if isinstance(cap_list, list) and capability_name in cap_list:
                        matching_services.append(service)
                    elif isinstance(cap_list, dict) and capability_name in cap_list:
                        matching_services.append(service)

            return matching_services
        except Exception as e:
            print(f"Error finding services by capability: {e}")
            return []

    def find_services_by_capability_types(self, capability_types: List[str]) -> List[Dict[str, Any]]:
        """Find services that support any of the specified capability types.

        Args:
            capability_types: List of capability types to search for

        Returns:
            List of services that support any of the specified capability types
        """
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                SELECT id, name, description, endpoint, capabilities, registered_at, last_seen
                FROM services
            """)

            rows = cursor.fetchall()
            cursor.close()

            matching_services = []
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

                # Check if the service has any of the requested capability types
                capabilities = service.get("capabilities", {})
                if any(cap_type in capabilities for cap_type in capability_types):
                    matching_services.append(service)

            return matching_services
        except Exception as e:
            print(f"Error finding services by capability types: {e}")
            return []

    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
