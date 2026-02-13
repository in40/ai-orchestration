"""
Task Storage for IT Lead MCP Server
Handles storage of received and submitted tasks in PostgreSQL
"""
import json
import time
from typing import Dict, List, Any, Optional
import logging


class TaskStorage:
    """Handles storage of tasks in PostgreSQL database"""

    def __init__(self, host: str = "localhost", port: int = 5432, database: str = "mcp_registry",
                 user: str = "postgres", password: str = ""):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None

        print(f"DEBUG: TaskStorage initializing with host={host}, port={port}, database={database}, user={user}")

        try:
            import psycopg2
            import psycopg2.extras
            self.psycopg2 = psycopg2
            self.extras = psycopg2.extras
            self._connect()
            self._init_db()
        except ImportError:
            raise ImportError("psycopg2 is required for task storage. Install it with: pip install psycopg2-binary")

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
            print("✅ Successfully connected to PostgreSQL task storage database")
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {e}")
            raise

    def _init_db(self):
        """Initialize the database and create tasks table if it doesn't exist"""
        try:
            cursor = self.connection.cursor()

            # Create tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    task_id VARCHAR(255) UNIQUE NOT NULL,
                    title TEXT,
                    description TEXT,
                    status VARCHAR(50) DEFAULT 'received',
                    assigned_to VARCHAR(255),
                    priority VARCHAR(20) DEFAULT 'medium',
                    deadline TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    source_server VARCHAR(255),
                    target_server VARCHAR(255),
                    result TEXT,
                    metadata JSONB
                )
            """)

            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_id ON tasks(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assigned_to ON tasks(assigned_to)")

            self.connection.commit()
            cursor.close()
            print("✅ Task storage database initialized")
        except Exception as e:
            print(f"❌ Error initializing task storage database: {e}")
            raise

    def store_received_task(self, task_id: str, title: str, description: str, 
                          assigned_to: Optional[str] = None, priority: str = "medium",
                          deadline: Optional[str] = None, source_server: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store a received task in the database"""
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                INSERT INTO tasks (task_id, title, description, status, assigned_to, priority, deadline, source_server, metadata)
                VALUES (%s, %s, %s, 'received', %s, %s, %s, %s, %s)
                ON CONFLICT (task_id) 
                DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    status = 'received',
                    assigned_to = EXCLUDED.assigned_to,
                    priority = EXCLUDED.priority,
                    deadline = EXCLUDED.deadline,
                    source_server = EXCLUDED.source_server,
                    updated_at = CURRENT_TIMESTAMP,
                    metadata = EXCLUDED.metadata
            """, (
                task_id, title, description, assigned_to, priority, 
                deadline, source_server, json.dumps(metadata) if metadata else None
            ))

            self.connection.commit()
            cursor.close()

            print(f"✅ Received task stored: {task_id}")
            return True
        except Exception as e:
            print(f"❌ Error storing received task: {e}")
            self.connection.rollback()
            return False

    def store_submitted_task(self, task_id: str, title: str, description: str,
                           target_server: str, priority: str = "medium",
                           deadline: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store a submitted task in the database"""
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                INSERT INTO tasks (task_id, title, description, status, target_server, priority, deadline, metadata)
                VALUES (%s, %s, %s, 'submitted', %s, %s, %s, %s)
                ON CONFLICT (task_id) 
                DO UPDATE SET
                    title = EXCLUDED.title,
                    description = EXCLUDED.description,
                    status = 'submitted',
                    target_server = EXCLUDED.target_server,
                    priority = EXCLUDED.priority,
                    deadline = EXCLUDED.deadline,
                    updated_at = CURRENT_TIMESTAMP,
                    metadata = EXCLUDED.metadata
            """, (
                task_id, title, description, target_server, priority, 
                deadline, json.dumps(metadata) if metadata else None
            ))

            self.connection.commit()
            cursor.close()

            print(f"✅ Submitted task stored: {task_id}")
            return True
        except Exception as e:
            print(f"❌ Error storing submitted task: {e}")
            self.connection.rollback()
            return False

    def update_task_status(self, task_id: str, status: str, result: Optional[str] = None) -> bool:
        """Update the status of a task"""
        try:
            cursor = self.connection.cursor()

            if result:
                cursor.execute("""
                    UPDATE tasks
                    SET status = %s, result = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = %s
                """, (status, result, task_id))
            else:
                cursor.execute("""
                    UPDATE tasks
                    SET status = %s, updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = %s
                """, (status, task_id))

            affected_rows = cursor.rowcount
            self.connection.commit()
            cursor.close()

            if affected_rows > 0:
                print(f"✅ Task status updated: {task_id} -> {status}")
                return True
            else:
                print(f"⚠️ Task not found for status update: {task_id}")
                return False
        except Exception as e:
            print(f"❌ Error updating task status: {e}")
            self.connection.rollback()
            return False

    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a specific task by ID"""
        try:
            cursor = self.connection.cursor(cursor_factory=self.extras.RealDictCursor)

            cursor.execute("""
                SELECT id, task_id, title, description, status, assigned_to, priority, 
                       deadline, created_at, updated_at, source_server, target_server, 
                       result, metadata
                FROM tasks
                WHERE task_id = %s
            """, (task_id,))

            row = cursor.fetchone()
            cursor.close()

            if row:
                return {
                    "id": row['id'],
                    "task_id": row['task_id'],
                    "title": row['title'],
                    "description": row['description'],
                    "status": row['status'],
                    "assigned_to": row['assigned_to'],
                    "priority": row['priority'],
                    "deadline": row['deadline'].isoformat() if row['deadline'] else None,
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                    "source_server": row['source_server'],
                    "target_server": row['target_server'],
                    "result": row['result'],
                    "metadata": row['metadata']
                }

            return None
        except Exception as e:
            print(f"❌ Error getting task: {e}")
            return None

    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all tasks with a specific status"""
        try:
            cursor = self.connection.cursor(cursor_factory=self.extras.RealDictCursor)

            cursor.execute("""
                SELECT id, task_id, title, description, status, assigned_to, priority, 
                       deadline, created_at, updated_at, source_server, target_server, 
                       result, metadata
                FROM tasks
                WHERE status = %s
                ORDER BY created_at DESC
            """, (status,))

            rows = cursor.fetchall()
            cursor.close()

            tasks = []
            for row in rows:
                tasks.append({
                    "id": row['id'],
                    "task_id": row['task_id'],
                    "title": row['title'],
                    "description": row['description'],
                    "status": row['status'],
                    "assigned_to": row['assigned_to'],
                    "priority": row['priority'],
                    "deadline": row['deadline'].isoformat() if row['deadline'] else None,
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                    "source_server": row['source_server'],
                    "target_server": row['target_server'],
                    "result": row['result'],
                    "metadata": row['metadata']
                })

            return tasks
        except Exception as e:
            print(f"❌ Error getting tasks by status: {e}")
            return []

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks"""
        try:
            cursor = self.connection.cursor(cursor_factory=self.extras.RealDictCursor)

            cursor.execute("""
                SELECT id, task_id, title, description, status, assigned_to, priority, 
                       deadline, created_at, updated_at, source_server, target_server, 
                       result, metadata
                FROM tasks
                ORDER BY created_at DESC
            """)

            rows = cursor.fetchall()
            cursor.close()

            tasks = []
            for row in rows:
                tasks.append({
                    "id": row['id'],
                    "task_id": row['task_id'],
                    "title": row['title'],
                    "description": row['description'],
                    "status": row['status'],
                    "assigned_to": row['assigned_to'],
                    "priority": row['priority'],
                    "deadline": row['deadline'].isoformat() if row['deadline'] else None,
                    "created_at": row['created_at'].isoformat() if row['created_at'] else None,
                    "updated_at": row['updated_at'].isoformat() if row['updated_at'] else None,
                    "source_server": row['source_server'],
                    "target_server": row['target_server'],
                    "result": row['result'],
                    "metadata": row['metadata']
                })

            return tasks
        except Exception as e:
            print(f"❌ Error getting all tasks: {e}")
            return []

    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            print("🔒 Task storage database connection closed")