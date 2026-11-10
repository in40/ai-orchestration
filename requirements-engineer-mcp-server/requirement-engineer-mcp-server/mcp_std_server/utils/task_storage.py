"""
Task Storage Module for MCP Server
Provides storage for tasks using PostgreSQL backend
"""
import json
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor


class TaskStorage:
    """Storage for tasks using PostgreSQL backend"""

    def __init__(self, use_postgres: bool = True, postgres_config: Optional[Dict[str, Any]] = None,
                 host: str = "localhost", port: int = 5432, database: str = "mcp_registry",
                 user: str = "postgres", password: str = "postgres"):
        # Handle postgres_config parameter (used by callers like requirement_engineer_handlers.py)
        if postgres_config:
            host = postgres_config.get("host", host)
            port = postgres_config.get("port", port)
            database = postgres_config.get("database", database)
            user = postgres_config.get("user", user)
            password = postgres_config.get("password", password)

        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.conn = None

        try:
            self._init_postgres()
        except Exception as e:
            print(f"Error initializing PostgreSQL task storage: {e}")
            raise

    def _init_postgres(self):
        """Initialize PostgreSQL database for task storage"""
        try:
            self.conn = psycopg2.connect(
                host=self.host,
                port=self.port,
                database=self.database,
                user=self.user,
                password=self.password
            )
            self.cursor = self.conn.cursor(cursor_factory=RealDictCursor)

            # Create tasks table
            create_tasks_table_query = '''
                CREATE TABLE IF NOT EXISTS tasks (
                    id VARCHAR(255) PRIMARY KEY,
                    name VARCHAR(255) NOT NULL,
                    arguments TEXT,
                    status VARCHAR(50) DEFAULT 'created',
                    result TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
            self.cursor.execute(create_tasks_table_query)

            # Create requirements specifications table
            create_specs_table_query = '''
                CREATE TABLE IF NOT EXISTS requirements_specifications (
                    id SERIAL PRIMARY KEY,
                    requirement_id VARCHAR(255) UNIQUE,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'draft',
                    priority VARCHAR(50) DEFAULT 'medium',
                    category VARCHAR(100),
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
            self.cursor.execute(create_specs_table_query)

            # Create traceability matrix table
            create_traceability_table_query = '''
                CREATE TABLE IF NOT EXISTS traceability_matrix (
                    id SERIAL PRIMARY KEY,
                    requirement_id VARCHAR(255),
                    artifact_type VARCHAR(50),
                    artifact_id VARCHAR(255),
                    relationship VARCHAR(50),
                    confidence REAL DEFAULT 0.5,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
            self.cursor.execute(create_traceability_table_query)

            # Create ambiguity log table
            create_ambiguity_table_query = '''
                CREATE TABLE IF NOT EXISTS ambiguity_log (
                    id SERIAL PRIMARY KEY,
                    ambiguity_id VARCHAR(255) UNIQUE,
                    requirement_id VARCHAR(255),
                    description TEXT,
                    severity VARCHAR(50) DEFAULT 'medium',
                    status VARCHAR(50) DEFAULT 'open',
                    resolution TEXT,
                    date_identified DATE,
                    date_resolved DATE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            '''
            self.cursor.execute(create_ambiguity_table_query)

            self.conn.commit()
        except psycopg2.Error as e:
            print(f"Error initializing PostgreSQL task storage: {e}")
            raise

    def create_task(self, task_id: str, name: str, arguments: dict, status: str = "created"):
        """Create a new task record"""
        try:
            query = """
                INSERT INTO tasks (id, name, arguments, status)
                VALUES (%s, %s, %s, %s)
                ON CONFLICT (id) DO UPDATE SET
                    name = EXCLUDED.name,
                    arguments = EXCLUDED.arguments,
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP
            """
            self.cursor.execute(query, (task_id, name, json.dumps(arguments), status))
            self.conn.commit()
        except Exception as e:
            print(f"Error creating task: {e}")

    def update_task_status(self, task_id: str, status: str, result: dict = None):
        """Update task status and optionally result"""
        try:
            if result:
                query = """
                    UPDATE tasks
                    SET status = %s, result = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                self.cursor.execute(query, (status, json.dumps(result), task_id))
            else:
                query = """
                    UPDATE tasks
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE id = %s
                """
                self.cursor.execute(query, (status, task_id))

            self.conn.commit()
        except Exception as e:
            print(f"Error updating task status: {e}")

    def get_task(self, task_id: str) -> dict:
        """Get a task by ID"""
        try:
            query = "SELECT * FROM tasks WHERE id = %s"
            self.cursor.execute(query, (task_id,))

            row = self.cursor.fetchone()
            if row:
                row_dict = dict(row)
                if row_dict['arguments']:
                    row_dict['arguments'] = json.loads(row_dict['arguments'])
                if row_dict['result']:
                    row_dict['result'] = json.loads(row_dict['result'])
                return row_dict
            return None
        except Exception as e:
            print(f"Error getting task: {e}")
            return None

    def list_tasks(self, limit: int = 100, offset: int = 0) -> list:
        """List tasks with pagination"""
        try:
            query = "SELECT * FROM tasks ORDER BY created_at DESC LIMIT %s OFFSET %s"
            self.cursor.execute(query, (limit, offset))

            rows = self.cursor.fetchall()
            tasks = []
            for row in rows:
                row_dict = dict(row)
                if row_dict['arguments']:
                    row_dict['arguments'] = json.loads(row_dict['arguments'])
                if row_dict['result']:
                    row_dict['result'] = json.loads(row_dict['result'])
                tasks.append(row_dict)
            return tasks
        except Exception as e:
            print(f"Error listing tasks: {e}")
            return []

    def store_requirement_specification(self, requirement_id: str, description: str, status: str = "draft",
                                       priority: str = "medium", category: str = ""):
        """Store a requirement specification"""
        try:
            query = """
                INSERT INTO requirements_specifications
                (requirement_id, description, status, priority, category)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (requirement_id) DO UPDATE SET
                    description = EXCLUDED.description,
                    status = EXCLUDED.status,
                    priority = EXCLUDED.priority,
                    category = EXCLUDED.category,
                    updated_at = CURRENT_TIMESTAMP
            """
            self.cursor.execute(query, (requirement_id, description, status, priority, category))
            self.conn.commit()
        except Exception as e:
            print(f"Error storing requirement specification: {e}")

    def get_requirement_specifications(self, limit: int = 100, offset: int = 0) -> list:
        """Get requirement specifications"""
        try:
            query = "SELECT * FROM requirements_specifications ORDER BY created_at DESC LIMIT %s OFFSET %s"
            self.cursor.execute(query, (limit, offset))

            rows = self.cursor.fetchall()
            specs = [dict(row) for row in rows]
            return specs
        except Exception as e:
            print(f"Error getting requirement specifications: {e}")
            return []

    def store_traceability_link(self, requirement_id: str, artifact_type: str, artifact_id: str,
                               relationship: str, confidence: float = 0.7):
        """Store a traceability link"""
        try:
            query = """
                INSERT INTO traceability_matrix
                (requirement_id, artifact_type, artifact_id, relationship, confidence)
                VALUES (%s, %s, %s, %s, %s)
            """
            self.cursor.execute(query, (requirement_id, artifact_type, artifact_id, relationship, confidence))
            self.conn.commit()
        except Exception as e:
            print(f"Error storing traceability link: {e}")

    def get_traceability_links(self, requirement_id: str = None, limit: int = 100, offset: int = 0) -> list:
        """Get traceability links"""
        try:
            if requirement_id:
                query = "SELECT * FROM traceability_matrix WHERE requirement_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s"
                self.cursor.execute(query, (requirement_id, limit, offset))
            else:
                query = "SELECT * FROM traceability_matrix ORDER BY created_at DESC LIMIT %s OFFSET %s"
                self.cursor.execute(query, (limit, offset))

            rows = self.cursor.fetchall()
            links = [dict(row) for row in rows]
            return links
        except Exception as e:
            print(f"Error getting traceability links: {e}")
            return []

    def store_ambiguity(self, ambiguity_id: str, requirement_id: str, description: str,
                       severity: str = "medium", status: str = "open", resolution: str = ""):
        """Store an ambiguity entry"""
        try:
            query = """
                INSERT INTO ambiguity_log
                (ambiguity_id, requirement_id, description, severity, status, resolution, date_identified)
                VALUES (%s, %s, %s, %s, %s, %s, CURRENT_DATE)
                ON CONFLICT (ambiguity_id) DO UPDATE SET
                    requirement_id = EXCLUDED.requirement_id,
                    description = EXCLUDED.description,
                    severity = EXCLUDED.severity,
                    status = EXCLUDED.status,
                    resolution = EXCLUDED.resolution,
                    date_resolved = CASE
                        WHEN EXCLUDED.status = 'resolved' THEN CURRENT_DATE
                        ELSE ambiguity_log.date_resolved
                    END,
                    updated_at = CURRENT_TIMESTAMP
            """
            self.cursor.execute(query, (ambiguity_id, requirement_id, description, severity, status, resolution))
            self.conn.commit()
        except Exception as e:
            print(f"Error storing ambiguity: {e}")

    def get_ambiguities(self, requirement_id: str = None, status: str = None, limit: int = 100, offset: int = 0) -> list:
        """Get ambiguities"""
        try:
            conditions = []
            params = []

            if requirement_id:
                conditions.append("requirement_id = %s")
                params.append(requirement_id)
            if status:
                conditions.append("status = %s")
                params.append(status)

            base_query = "SELECT * FROM ambiguity_log"
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)

            base_query += " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])

            self.cursor.execute(base_query, params)

            rows = self.cursor.fetchall()
            ambiguities = [dict(row) for row in rows]
            return ambiguities
        except Exception as e:
            print(f"Error getting ambiguities: {e}")
            return []

    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()
