"""
PostgreSQL-based Task Manager for Vibe Coding MCP Server
Implements persistent storage for async tasks using PostgreSQL
"""
import json
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import threading


class TaskStatus(Enum):
    SUBMITTED = "submitted"
    WORKING = "working"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class AsyncTask:
    taskId: str
    status: TaskStatus
    input: Dict[str, Any]
    createdAt: float
    updatedAt: float
    progress: int = 0
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    expiresAt: Optional[float] = None


class PostgresTaskManager:
    # Reference to TaskStatus enum for internal use
    TaskStatus = TaskStatus
    def __init__(self, host: str = "localhost", port: int = 5432, database: str = "mcp_registry",
                 user: str = "postgres", password: str = "", cleanup_interval: int = 300):  # 5 minutes
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.cleanup_interval = cleanup_interval
        self.executor = ThreadPoolExecutor(max_workers=10)
        
        # Establish connection to PostgreSQL
        print(f"DEBUG: PostgresTaskManager initializing with host={host}, port={port}, database={database}, user={user}")
        
        try:
            import psycopg2
            import psycopg2.extras
            self.psycopg2 = psycopg2
            self.extras = psycopg2.extras
            self._connect()
            self._init_db()
            self._start_cleanup_task()
        except ImportError:
            raise ImportError("psycopg2 is required for PostgreSQL task storage support. Install it with: pip install psycopg2-binary")

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
            print("✅ Successfully connected to PostgreSQL task database")
        except Exception as e:
            print(f"❌ Failed to connect to PostgreSQL: {e}")
            raise

    def _init_db(self):
        """Initialize the database and create tasks table if it doesn't exist"""
        try:
            cursor = self.connection.cursor()

            # Create tasks table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS async_tasks (
                    task_id VARCHAR(255) PRIMARY KEY,
                    status VARCHAR(50) NOT NULL,
                    input_data JSONB NOT NULL,
                    created_at DOUBLE PRECISION NOT NULL,
                    updated_at DOUBLE PRECISION NOT NULL,
                    progress INTEGER DEFAULT 0,
                    result_data JSONB,
                    error_message TEXT,
                    expires_at DOUBLE PRECISION
                )
            """)

            self.connection.commit()
            cursor.close()
            print("✅ Async tasks database initialized")
        except Exception as e:
            print(f"❌ Error initializing tasks database: {e}")
            raise

    def _start_cleanup_task(self):
        """Start background cleanup of expired tasks"""
        def cleanup_loop():
            while True:
                time.sleep(self.cleanup_interval)
                self._cleanup_expired_tasks()

        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()

    def _cleanup_expired_tasks(self):
        """Remove expired tasks from database"""
        current_time = time.time()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                DELETE FROM async_tasks
                WHERE expires_at IS NOT NULL AND expires_at < %s
            """, (current_time,))
            
            deleted_count = cursor.rowcount
            self.connection.commit()
            cursor.close()
            
            if deleted_count > 0:
                print(f"🧹 Cleaned up {deleted_count} expired tasks")
        except Exception as e:
            print(f"❌ Error cleaning up expired tasks: {e}")
            self.connection.rollback()

    def create_task(self, input_data: Dict[str, Any]) -> str:
        """Create a new async task in the database"""
        task_id = str(uuid.uuid4())
        current_time = time.time()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                INSERT INTO async_tasks 
                (task_id, status, input_data, created_at, updated_at, expires_at)
                VALUES (%s, %s, %s, %s, %s, %s)
            """, (
                task_id,
                TaskStatus.SUBMITTED.value,
                json.dumps(input_data),
                current_time,
                current_time,
                current_time + (60 * 60 * 24)  # Expires in 24 hours
            ))
            
            self.connection.commit()
            cursor.close()
            return task_id
        except Exception as e:
            print(f"❌ Error creating task: {e}")
            self.connection.rollback()
            raise

    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """Get task by ID from the database"""
        try:
            cursor = self.connection.cursor(cursor_factory=self.extras.RealDictCursor)
            cursor.execute("""
                SELECT task_id, status, input_data, created_at, updated_at, progress, result_data, error_message, expires_at
                FROM async_tasks
                WHERE task_id = %s
            """, (task_id,))
            
            row = cursor.fetchone()
            cursor.close()
            
            if not row:
                return None
                
            # Handle JSON data properly
            input_data = row['input_data']
            if isinstance(input_data, str):
                input_parsed = json.loads(input_data) if input_data else {}
            else:
                input_parsed = input_data if input_data else {}
                
            result_data = row['result_data']
            if isinstance(result_data, str):
                result_parsed = json.loads(result_data) if result_data else None
            else:
                result_parsed = result_data
            
            return AsyncTask(
                taskId=row['task_id'],
                status=TaskStatus(row['status']),
                input=input_parsed,
                createdAt=row['created_at'],
                updatedAt=row['updated_at'],
                progress=row['progress'] or 0,
                result=result_parsed,
                error=row['error_message'],
                expiresAt=row['expires_at']
            )
        except Exception as e:
            print(f"❌ Error getting task: {e}")
            return None

    def update_task_status(self, task_id: str, status: TaskStatus, progress: int = None):
        """Update task status in the database"""
        current_time = time.time()
        
        try:
            cursor = self.connection.cursor()
            
            if progress is not None:
                cursor.execute("""
                    UPDATE async_tasks
                    SET status = %s, progress = %s, updated_at = %s
                    WHERE task_id = %s
                """, (status.value, progress, current_time, task_id))
            else:
                cursor.execute("""
                    UPDATE async_tasks
                    SET status = %s, updated_at = %s
                    WHERE task_id = %s
                """, (status.value, current_time, task_id))
            
            self.connection.commit()
            cursor.close()
        except Exception as e:
            print(f"❌ Error updating task status: {e}")
            self.connection.rollback()

    def update_task_result(self, task_id: str, result: Dict[str, Any]):
        """Update task with result in the database"""
        current_time = time.time()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE async_tasks
                SET status = %s, progress = 100, result_data = %s, updated_at = %s, expires_at = %s
                WHERE task_id = %s
            """, (
                TaskStatus.COMPLETED.value,
                json.dumps(result),
                current_time,
                current_time + (60 * 60 * 24 * 7),  # Keep results for 7 days
                task_id
            ))
            
            self.connection.commit()
            cursor.close()
        except Exception as e:
            print(f"❌ Error updating task result: {e}")
            self.connection.rollback()

    def update_task_error(self, task_id: str, error: str):
        """Update task with error in the database"""
        current_time = time.time()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE async_tasks
                SET status = %s, error_message = %s, updated_at = %s
                WHERE task_id = %s
            """, (TaskStatus.FAILED.value, error, current_time, task_id))
            
            self.connection.commit()
            cursor.close()
        except Exception as e:
            print(f"❌ Error updating task error: {e}")
            self.connection.rollback()

    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task in the database"""
        current_time = time.time()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute("""
                UPDATE async_tasks
                SET status = %s, updated_at = %s
                WHERE task_id = %s AND status IN (%s, %s)
            """, (
                TaskStatus.CANCELLED.value,
                current_time,
                task_id,
                TaskStatus.SUBMITTED.value,
                TaskStatus.WORKING.value
            ))
            
            affected_rows = cursor.rowcount
            self.connection.commit()
            cursor.close()
            
            return affected_rows > 0
        except Exception as e:
            print(f"❌ Error cancelling task: {e}")
            self.connection.rollback()
            return False

    def list_tasks(self, status_filter: Optional[str] = None, limit: int = 100) -> List[AsyncTask]:
        """List tasks with optional filtering from the database"""
        try:
            cursor = self.connection.cursor(cursor_factory=self.extras.RealDictCursor)
            
            query = """
                SELECT task_id, status, input_data, created_at, updated_at, progress, result_data, error_message, expires_at
                FROM async_tasks
            """
            params = []
            
            if status_filter:
                query += " WHERE status = %s"
                params.append(status_filter.lower())
            
            query += " ORDER BY created_at DESC LIMIT %s"
            params.append(limit)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            cursor.close()
            
            tasks = []
            for row in rows:
                # Handle JSON data properly
                input_data = row['input_data']
                if isinstance(input_data, str):
                    input_parsed = json.loads(input_data) if input_data else {}
                else:
                    input_parsed = input_data if input_data else {}
                    
                result_data = row['result_data']
                if isinstance(result_data, str):
                    result_parsed = json.loads(result_data) if result_data else None
                else:
                    result_parsed = result_data
                
                task = AsyncTask(
                    taskId=row['task_id'],
                    status=TaskStatus(row['status']),
                    input=input_parsed,
                    createdAt=row['created_at'],
                    updatedAt=row['updated_at'],
                    progress=row['progress'] or 0,
                    result=result_parsed,
                    error=row['error_message'],
                    expiresAt=row['expires_at']
                )
                tasks.append(task)
            
            return tasks
        except Exception as e:
            print(f"❌ Error listing tasks: {e}")
            return []

    def submit_for_processing(self, task_id: str, llm_call_func):
        """Submit task for background processing"""
        
        def process_task():
            try:
                # First update status to working
                self.update_task_status(task_id, TaskStatus.WORKING, 10)
                
                # Get the task input data
                task = self.get_task(task_id)
                if not task:
                    return

                # Call the LLM function with the input data
                result = llm_call_func(task.input)
                self.update_task_result(task_id, result)
            except Exception as e:
                self.update_task_error(task_id, str(e))

        # Submit to thread pool for background processing
        self.executor.submit(process_task)


# Global task manager instance - can be configured to use either in-memory or PostgreSQL
def create_task_manager(use_postgres=False, **postgres_config):
    """Factory function to create appropriate task manager"""
    if use_postgres:
        from config import settings
        # Use PostgreSQL task manager with settings from config
        pg_config = postgres_config or {
            "host": getattr(settings, 'postgres_host', 'localhost'),
            "port": getattr(settings, 'postgres_port', 5432),
            "database": getattr(settings, 'postgres_db', 'mcp_registry'),
            "user": getattr(settings, 'postgres_user', 'postgres'),
            "password": getattr(settings, 'postgres_password', '')
        }
        return PostgresTaskManager(**pg_config)
    else:
        # PostgreSQL is required - this should never be reached
        from config import settings
        pg_config = {
            "host": getattr(settings, 'postgres_host', 'localhost'),
            "port": getattr(settings, 'postgres_port', 5432),
            "database": getattr(settings, 'postgres_db', 'mcp_registry'),
            "user": getattr(settings, 'postgres_user', 'postgres'),
            "password": getattr(settings, 'postgres_password', '')
        }
        return PostgresTaskManager(**pg_config)