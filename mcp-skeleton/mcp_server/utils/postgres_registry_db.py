"""
PostgreSQL Integration for MCP Server Registry
Optional PostgreSQL support for the registry functionality
"""
import psycopg2
from psycopg2.extras import RealDictCursor
import json
from datetime import datetime
from typing import Dict, Any, List, Optional


class PostgresServiceRegistry:
    """
    Optional PostgreSQL integration for MCP server registry functionality.
    
    This class provides storage for service registration information when
    implementing a registry server that tracks multiple MCP services using PostgreSQL.
    
    HOW TO ENABLE:
    1. Install PostgreSQL dependencies: pip install psycopg2-binary
    2. Configure PostgreSQL connection parameters
    3. Initialize the registry in your server class
    4. Call register_service when services connect
    5. Use list_services to discover available services
    
    USAGE EXAMPLE:
    ```
    registry = PostgresServiceRegistry(
        host="localhost",
        port=5432,
        database="mcp_registry",
        user="postgres",
        password="your_password"
    )
    registry.register_service({
        "id": "db-service-1",
        "name": "Database Access Service",
        "description": "Provides database query capabilities",
        "endpoint": "http://localhost:8081",
        "capabilities": {"tools": ["query_db", "insert_record"]}
    })
    ```
    """
    
    def __init__(self, host: str = "localhost", port: int = 5432, database: str = "mcp_registry", 
                 user: str = "postgres", password: str = ""):
        print(f"DEBUG: PostgresServiceRegistry initializing with host={host}, port={port}, database={database}, user={user}")
        self.connection_params = {
            "host": host,
            "port": port,
            "database": database,
            "user": user,
            "password": password
        }
        self.connection = None
        print("DEBUG: About to initialize database...")
        self.init_db()
        print("DEBUG: Database initialization completed")
    
    def get_connection(self):
        """Get database connection, reconnecting if needed"""
        print(f"DEBUG: get_connection called, current connection: {self.connection is not None}, closed: {self.connection and getattr(self.connection, 'closed', True)}")
        print(f"DEBUG: Connection params: {self.connection_params}")
        if not self.connection or self.connection.closed:
            print("DEBUG: Creating new connection...")
            try:
                # Use the connection parameters as provided
                self.connection = psycopg2.connect(**self.connection_params)
                print("DEBUG: New connection created successfully")
            except psycopg2.Error as e:
                print(f"DEBUG: Connection error: {e}")
                raise Exception(f"Could not connect to PostgreSQL: {e}")
        else:
            print("DEBUG: Reusing existing connection")
        return self.connection
    
    def init_db(self):
        """
        Initialize the database with required tables.
        Creates a services table to store service registration information.
        """
        print("DEBUG: init_db called")
        conn = self.get_connection()
        cursor = conn.cursor()
        print("DEBUG: Connection and cursor created")
        
        # Create services table
        print("DEBUG: Creating services table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS services (
                id VARCHAR(255) PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                endpoint VARCHAR(500),
                capabilities JSONB,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        print("DEBUG: Services table created/verified")
        
        # Create indexes for better performance
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_services_id ON services(id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_services_last_seen ON services(last_seen);
        """)
        print("DEBUG: Indexes created")
        
        conn.commit()
        print("DEBUG: Transaction committed")
        cursor.close()
        print("DEBUG: Cursor closed")
    
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
        print(f"DEBUG: register_service called with service_info: {service_info.get('id')}")
        print(f"DEBUG: Service details - ID: {service_info.get('id')}, Name: {service_info.get('name')}, Endpoint: {service_info.get('endpoint')}")
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            print("DEBUG: Connection and cursor obtained for registration")
            
            # Convert capabilities to JSON
            capabilities_json = json.dumps(service_info.get("capabilities", {}))
            print(f"DEBUG: Converted capabilities to JSON: {capabilities_json[:100]}...")
            
            print(f"DEBUG: Preparing to execute query with values: id={service_info.get('id')}, name={service_info.get('name')}, endpoint={service_info.get('endpoint')}")
            print("DEBUG: Executing insert/update query...")
            cursor.execute("""
                INSERT INTO services 
                (id, name, description, endpoint, capabilities, last_seen)
                VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                ON CONFLICT (id) 
                DO UPDATE SET
                    name = EXCLUDED.name,
                    description = EXCLUDED.description,
                    endpoint = EXCLUDED.endpoint,
                    capabilities = EXCLUDED.capabilities,
                    last_seen = CURRENT_TIMESTAMP
            """, (
                service_info.get("id"),
                service_info.get("name", ""),
                service_info.get("description", ""),
                service_info.get("endpoint", ""),
                capabilities_json
            ))
            print("DEBUG: Query executed successfully")
            
            conn.commit()
            print("DEBUG: Transaction committed to database")
            cursor.close()
            print("DEBUG: Cursor closed, returning True")
            
            # Verify the insertion by querying the database
            verify_cursor = conn.cursor()
            verify_cursor.execute("SELECT id, name, endpoint FROM services WHERE id = %s", (service_info.get("id"),))
            result = verify_cursor.fetchone()
            verify_cursor.close()
            if result:
                print(f"DEBUG: Verification - Service found in database: {result[0]} - {result[1]}")
            else:
                print(f"DEBUG: Verification - Service NOT FOUND in database after registration: {service_info.get('id')}")
            
            return True
        except Exception as e:
            print(f"Error registering service: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def unregister_service(self, service_id: str) -> bool:
        """
        Remove a service from the registry.

        Args:
            service_id: ID of the service to remove

        Returns:
            True if removal was successful, False otherwise
        """
        print(f"DEBUG: unregister_service called for service_id: {service_id}")
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            print("DEBUG: Connection and cursor obtained for unregistering service")

            cursor.execute("DELETE FROM services WHERE id = %s", (service_id,))
            print(f"DEBUG: DELETE query executed for service: {service_id}")

            conn.commit()
            print("DEBUG: Transaction committed for unregister_service")
            cursor.close()

            result = cursor.rowcount > 0
            print(f"DEBUG: unregister_service result: {result} (deleted {cursor.rowcount} rows)")
            return result
        except Exception as e:
            print(f"Error unregistering service: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def list_services(self) -> List[Dict[str, Any]]:
        """
        Retrieve all registered services.

        Returns:
            List of dictionaries containing service information
        """
        print("DEBUG: list_services called")
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            print("DEBUG: Connection and cursor obtained for listing services")

            cursor.execute("""
                SELECT id, name, description, endpoint, capabilities, registered_at, last_seen
                FROM services
                ORDER BY last_seen DESC
            """)
            print("DEBUG: Query executed to list services")

            rows = cursor.fetchall()
            print(f"DEBUG: Retrieved {len(rows)} rows from database")

            services = []
            for row in rows:
                print(f"DEBUG: Processing row: {row['id']} - {row['name']}")
                service = {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "endpoint": row["endpoint"],
                    "capabilities": row["capabilities"] if row["capabilities"] else {},
                    "registered_at": row["registered_at"].isoformat() if row["registered_at"] else None,
                    "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None
                }
                services.append(service)

            print(f"DEBUG: Returning {len(services)} services from list_services")
            cursor.close()
            return services
        except Exception as e:
            print(f"Error listing services: {e}")
            import traceback
            traceback.print_exc()
            return []
    
    def get_service(self, service_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve a specific service by ID.

        Args:
            service_id: ID of the service to retrieve

        Returns:
            Service information dictionary or None if not found
        """
        print(f"DEBUG: get_service called for service_id: {service_id}")
        try:
            conn = self.get_connection()
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            print("DEBUG: Connection and cursor obtained for getting specific service")

            cursor.execute("""
                SELECT id, name, description, endpoint, capabilities, registered_at, last_seen
                FROM services
                WHERE id = %s
            """, (service_id,))
            print(f"DEBUG: Query executed to get service: {service_id}")

            row = cursor.fetchone()
            cursor.close()
            print(f"DEBUG: Row fetched: {'found' if row else 'not found'}")

            if row:
                print(f"DEBUG: Service found: {row['id']} - {row['name']}")
                return {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row["description"],
                    "endpoint": row["endpoint"],
                    "capabilities": row["capabilities"] if row["capabilities"] else {},
                    "registered_at": row["registered_at"].isoformat() if row["registered_at"] else None,
                    "last_seen": row["last_seen"].isoformat() if row["last_seen"] else None
                }
            print(f"DEBUG: Service not found: {service_id}")
            return None
        except Exception as e:
            print(f"Error getting service: {e}")
            import traceback
            traceback.print_exc()
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
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                UPDATE services
                SET last_seen = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (service_id,))

            conn.commit()
            cursor.close()

            result = cursor.rowcount > 0
            if result:
                print(f"⏱️  Updated last_seen for service {service_id}")
            else:
                print(f"⚠️  Service {service_id} not found for heartbeat update")
            return result
        except Exception as e:
            print(f"❌ Error updating last seen: {e}")
            import traceback
            traceback.print_exc()
            return False

    def cleanup_stale_services(self, max_age_minutes: int = 10) -> int:
        """
        Remove services that haven't been seen within the specified time window.

        Args:
            max_age_minutes: Maximum age in minutes before a service is considered stale

        Returns:
            Number of stale services removed
        """
        try:
            from datetime import timedelta
            cutoff_time = datetime.now() - timedelta(minutes=max_age_minutes)
            
            conn = self.get_connection()
            cursor = conn.cursor()

            cursor.execute("""
                DELETE FROM services
                WHERE last_seen < %s
            """, (cutoff_time,))

            deleted_count = cursor.rowcount
            conn.commit()
            cursor.close()

            if deleted_count > 0:
                print(f"🧹 Removed {deleted_count} stale services (not seen in last {max_age_minutes} minutes)")
            else:
                print(f"✅ No stale services to remove (all services seen in last {max_age_minutes} minutes)")
            return deleted_count
        except Exception as e:
            print(f"❌ Error cleaning up stale services: {e}")
            import traceback
            traceback.print_exc()
            return 0