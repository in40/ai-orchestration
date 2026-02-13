"""
PostgreSQL Integration for MCP Server Registry
Optional PostgreSQL support for the registry functionality
"""
import json
import time
from typing import Dict, List, Any, Optional
import logging


class PostgresServiceRegistry:
    """Optional PostgreSQL integration for MCP server registry functionality.

    This class provides PostgreSQL storage for the registry functionality,
    enabling a registry server that tracks multiple MCP services using PostgreSQL.
    """

    def __init__(self, host: str = "localhost", port: int = 5432, database: str = "mcp_registry",
                 user: str = "postgres", password: str = ""):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

        print(f"DEBUG: PostgresServiceRegistry initializing with host={host}, port={port}, database={database}, user={user}")

        try:
            import psycopg2
            import psycopg2.extras
            self.psycopg2 = psycopg2
            self.extras = psycopg2.extras
            self._connect()
            self._init_db()
        except ImportError:
            raise ImportError("psycopg2 is required for PostgreSQL registry support. Install it with: pip install psycopg2-binary")

    def _connect(self):
        """Establish connection to PostgreSQL database"""
        try:
            self.connection = self.psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            print("✅ Successfully connected to PostgreSQL registry database")
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {e}")
            raise

    def _init_db(self):
        """Initialize the database and create tables if they don't exist"""
        try:
            cursor = self.connection.cursor()

            # Create services table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS services (
                    id VARCHAR(255) PRIMARY KEY,
                    name TEXT NOT NULL,
                    description TEXT,
                    endpoint TEXT NOT NULL,
                    capabilities JSONB,
                    registered_at DOUBLE PRECISION NOT NULL,
                    last_seen DOUBLE PRECISION NOT NULL
                )
            """)

            self.connection.commit()
            cursor.close()
            print("✅ Registry database initialized")
        except Exception as e:
            print(f"❌ Error initializing database: {e}")
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
            # Set timestamps
            now = time.time()
            service_info.setdefault('registered_at', now)
            service_info['last_seen'] = now

            cursor = self.connection.cursor()

            # Insert or update the service
            cursor.execute("""
                INSERT INTO services (id, name, description, endpoint, capabilities, registered_at, last_seen)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (id)
                DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    endpoint = EXCLUDED.endpoint,
                    capabilities = EXCLUDED.capabilities,
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
            self.connection.rollback()
            return False

    def list_services(self) -> List[Dict[str, Any]]:
        """List all registered services in the registry.

        Returns:
            List of dictionaries containing service information
        """
        try:
            cursor = self.connection.cursor(cursor_factory=self.extras.RealDictCursor)

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
                    "id": row['id'],
                    "name": row['name'],
                    "description": row['description'],
                    "endpoint": row['endpoint'],
                    "capabilities": row['capabilities'] if row['capabilities'] else {},
                    "registered_at": row['registered_at'],
                    "last_seen": row['last_seen']
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
            cursor = self.connection.cursor(cursor_factory=self.extras.RealDictCursor)

            cursor.execute("""
                SELECT id, name, description, endpoint, capabilities, registered_at, last_seen
                FROM services
                WHERE id = %s
            """, (service_id,))

            row = cursor.fetchone()
            cursor.close()

            if row:
                return {
                    "id": row['id'],
                    "name": row['name'],
                    "description": row['description'],
                    "endpoint": row['endpoint'],
                    "capabilities": row['capabilities'] if row['capabilities'] else {},
                    "registered_at": row['registered_at'],
                    "last_seen": row['last_seen']
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
            self.connection.rollback()
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
            self.connection.rollback()
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
            self.connection.rollback()
            return 0