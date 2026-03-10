"""
Task Storage for IT Lead MCP Server
Handles storage of received and submitted tasks in PostgreSQL or SQLite
"""
import json
import time
import sqlite3
from datetime import datetime
from typing import Dict, List, Any, Optional
import logging


def format_datetime_value(val):
    """Helper function to safely convert datetime values from SQLite or PostgreSQL"""
    if val is None:
        return None
    # If it's already a string (from SQLite), return as-is
    if isinstance(val, str):
        return val
    # Otherwise try isoformat() for datetime objects
    try:
        return val.isoformat()
    except AttributeError:
        return str(val)


class TaskStorage:
    """Handles storage of tasks in PostgreSQL or SQLite database"""

    def __init__(self, host: str = "localhost", port: int = 5432, database: str = "mcp_registry.db",
                 user: str = "postgres", password: str = "", use_sqlite: bool = True):  # Changed default to True
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.use_sqlite = use_sqlite  # Use SQLite by default
        self.connection = None

        print(f"DEBUG: TaskStorage initializing with host={host}, port={port}, database={database}, user={user}, use_sqlite={use_sqlite}")

        try:
            if use_sqlite:
                self._connect_sqlite()
                self._init_db_sqlite()
            else:
                import psycopg2
                import psycopg2.extras
                self.psycopg2 = psycopg2
                self.extras = psycopg2.extras
                self._connect_postgres()
                self._init_db_postgres()
            print("✅ TaskStorage initialized successfully")
        except ImportError:
            if not use_sqlite:
                raise ImportError("psycopg2 is required for PostgreSQL task storage. Install it with: pip install psycopg2-binary")
            else:
                # If using SQLite and there's an import error, it's likely not psycopg2 related
                # Re-raise if it's a different import error
                raise
        except Exception as e:
            print(f"❌ Failed to initialize task storage: {e}")
            raise

    def _connect_postgres(self):
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

    def _connect_sqlite(self):
        """Establish connection to SQLite database"""
        try:
            # Make sure we're using a proper database file path
            db_path = self.database if self.database.endswith('.db') else f"{self.database}.db"
            self.connection = sqlite3.connect(db_path, check_same_thread=False)
            print(f"✅ Successfully connected to SQLite task storage database: {db_path}")
        except Exception as e:
            print(f"❌ Failed to connect to SQLite: {e}")
            raise

    def _init_db_postgres(self):
        """Initialize the PostgreSQL database and create task_registry table if it doesn't exist"""
        try:
            cursor = self.connection.cursor()

            # Create task_registry table with full lifecycle tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_registry (
                    id SERIAL PRIMARY KEY,
                    task_id VARCHAR(255) UNIQUE NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    submitter VARCHAR(255) NOT NULL,
                    submitter_type VARCHAR(50) NOT NULL CHECK (submitter_type IN ('human', 'agent', 'system', 'api')),
                    transport_channel VARCHAR(50) NOT NULL DEFAULT 'unknown' CHECK (transport_channel IN ('http', 'stdio', 'streamable-http', 'api', 'websocket', 'unknown')),
                    assigned_to VARCHAR(255) DEFAULT 'unassigned',
                    status VARCHAR(50) NOT NULL DEFAULT 'received' CHECK (status IN ('submitted', 'received', 'pending_assignment', 'assigned', 'requirements_collection', 'in_progress', 'blocked', 'review', 'done', 'failed', 'cancelled')),
                    status_reason TEXT,
                    priority VARCHAR(20) NOT NULL DEFAULT 'medium' CHECK (priority IN ('low', 'medium', 'high', 'critical')),
                    deadline TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    assigned_at TIMESTAMP,
                    started_at TIMESTAMP,
                    completed_at TIMESTAMP,
                    source_server VARCHAR(255),
                    target_server VARCHAR(255),
                    result TEXT,
                    metadata JSONB DEFAULT '{}',
                    status_history JSONB DEFAULT '[]'
                )
            """)

            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_id ON tasks(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON tasks(status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_assigned_to ON tasks(assigned_to)")

            self.connection.commit()
            cursor.close()

            # Update constraint if needed (to add 'submitted' status)
            print("Updating task_registry status constraint if needed...")
            try:
                cursor = self.connection.cursor()
                cursor.execute("""
                    SELECT conname
                    FROM pg_constraint
                    WHERE conrelid = 'task_registry'::regclass
                      AND conname = 'task_registry_status_check'
                """)
                constraint = cursor.fetchone()
                if constraint:
                    # Drop and recreate the constraint with updated allowed statuses
                    print("  Dropping existing status constraint...")
                    cursor.execute("""
                        ALTER TABLE task_registry DROP CONSTRAINT IF EXISTS task_registry_status_check
                    """)
                    self.connection.commit()

                # Recreate or create new constraint
                print("  Creating/updating status constraint...")
                cursor.execute("""
                    ALTER TABLE task_registry ADD CONSTRAINT task_registry_status_check 
                    CHECK (status IN ('submitted', 'received', 'pending_assignment', 'assigned', 'requirements_collection', 'in_progress', 'blocked', 'review', 'done', 'failed', 'cancelled'))
                """)
                self.connection.commit()
                cursor.close()
                print("✅ Status constraint updated successfully")
            except Exception as e:
                print(f"  Note: Could not update status constraint (may already exist or user lacks permissions): {e}")

        except Exception as e:
            print(f"❌ Error initializing PostgreSQL task storage database: {e}")
            raise

    def _init_db_sqlite(self):
        """Initialize the SQLite database and create task_registry table if it doesn't exist"""
        try:
            cursor = self.connection.cursor()

            # Create task_registry table for full lifecycle tracking
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS task_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    title TEXT,
                    description TEXT,
                    submitter TEXT DEFAULT 'unknown',
                    submitter_type TEXT DEFAULT 'system',
                    transport_channel TEXT DEFAULT 'unknown',
                    assigned_to TEXT DEFAULT 'unassigned',
                    status TEXT DEFAULT 'received',
                    status_reason TEXT,
                    priority TEXT DEFAULT 'medium',
                    deadline TEXT,
                    source_server TEXT,
                    target_server TEXT,
                    metadata TEXT,
                    status_history TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Create tasks table for backward compatibility
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    task_id TEXT UNIQUE NOT NULL,
                    title TEXT,
                    description TEXT,
                    status TEXT DEFAULT 'received',
                    assigned_to TEXT,
                    priority TEXT DEFAULT 'medium',
                    deadline TEXT,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                    source_server TEXT,
                    target_server TEXT,
                    result TEXT,
                    metadata TEXT
                )
            """)

            # Create indexes for better performance
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_task_id ON task_registry(task_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_status ON task_registry(status)")

            self.connection.commit()
            cursor.close()
            print("✅ SQLite task storage database initialized")
        except Exception as e:
            print(f"❌ Error initializing SQLite task storage database: {e}")
            raise

    def store_received_task(self, task_id: str, title: str, description: str,
                          submitter: str = "unknown", submitter_type: str = "system",
                          transport_channel: str = "unknown", assigned_to: Optional[str] = "unassigned",
                          priority: str = "medium", deadline: Optional[str] = None,
                          source_server: Optional[str] = None, target_server: Optional[str] = None,
                          metadata: Optional[Dict[str, Any]] = None,
                          status: str = "received", status_reason: Optional[str] = None) -> bool:
        """Store a received task in the database with full lifecycle tracking"""
        try:
            cursor = self.connection.cursor()
            
            # Prepare status history entry
            status_history_entry = {
                "status": status,
                "timestamp": time.time(),
                "reason": status_reason
            }

            if self.use_sqlite:
                # For SQLite, use INSERT OR REPLACE since it doesn't support ON CONFLICT
                cursor.execute("""
                    INSERT OR REPLACE INTO task_registry
                    (task_id, title, description, submitter, submitter_type, transport_channel,
                     assigned_to, status, status_reason, priority, deadline, source_server, target_server,
                     metadata, status_history)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    task_id, title, description, submitter, submitter_type, transport_channel,
                    assigned_to, status, status_reason, priority, deadline, source_server, target_server,
                    json.dumps(metadata) if metadata else '{}', json.dumps([status_history_entry])
                ))
            else:
                # For PostgreSQL, use ON CONFLICT
                # First check if this status already exists in history to avoid duplicates
                cursor.execute("""
                    INSERT INTO task_registry
                    (task_id, title, description, submitter, submitter_type, transport_channel,
                     assigned_to, status, status_reason, priority, deadline, source_server, target_server,
                     metadata, status_history)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (task_id)
                    DO UPDATE SET
                        title = EXCLUDED.title,
                        description = EXCLUDED.description,
                        submitter = EXCLUDED.submitter,
                        submitter_type = EXCLUDED.submitter_type,
                        transport_channel = EXCLUDED.transport_channel,
                        assigned_to = EXCLUDED.assigned_to,
                        status = EXCLUDED.status,
                        status_reason = EXCLUDED.status_reason,
                        priority = EXCLUDED.priority,
                        deadline = EXCLUDED.deadline,
                        source_server = EXCLUDED.source_server,
                        target_server = EXCLUDED.target_server,
                        updated_at = CURRENT_TIMESTAMP,
                        metadata = EXCLUDED.metadata,
                        status_history = CASE 
                            WHEN EXISTS (
                                SELECT 1 FROM jsonb_array_elements(task_registry.status_history) AS elem 
                                WHERE elem->>'status' = %s
                            ) 
                            THEN task_registry.status_history 
                            ELSE COALESCE(task_registry.status_history, '[]'::jsonb) || EXCLUDED.status_history 
                        END
                """, (
                    task_id, title, description, submitter, submitter_type, transport_channel,
                    assigned_to, status, status_reason, priority, deadline, source_server, target_server,
                    json.dumps(metadata) if metadata else '{}', json.dumps([status_history_entry]),
                    status  # Additional parameter for the EXISTS check
                ))

            self.connection.commit()
            cursor.close()

            print(f"✅ Received task stored: {task_id} (submitter: {submitter}, assigned_to: {assigned_to}, status: {status})")
            return True
        except Exception as e:
            print(f"❌ Error storing received task: {e}")
            import traceback
            traceback.print_exc()
            self.connection.rollback()
            return False

    def store_submitted_task(self, task_id: str, title: str, description: str,
                           target_server: str, priority: str = "medium",
                           deadline: Optional[str] = None, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """Store a submitted task in the database"""
        try:
            cursor = self.connection.cursor()

            if self.use_sqlite:
                # For SQLite, use INSERT OR REPLACE since it doesn't support ON CONFLICT
                cursor.execute("""
                    INSERT OR REPLACE INTO tasks 
                    (task_id, title, description, status, target_server, priority, deadline, metadata, updated_at)
                    VALUES (?, ?, ?, 'submitted', ?, ?, ?, ?, datetime('now'))
                """, (
                    task_id, title, description, target_server, priority,
                    deadline, json.dumps(metadata) if metadata else None
                ))
            else:
                # For PostgreSQL, use ON CONFLICT
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

            if self.use_sqlite:
                if result:
                    cursor.execute("""
                        UPDATE tasks
                        SET status = ?, result = ?, updated_at = datetime('now')
                        WHERE task_id = ?
                    """, (status, result, task_id))
                else:
                    cursor.execute("""
                        UPDATE tasks
                        SET status = ?, updated_at = datetime('now')
                        WHERE task_id = ?
                    """, (status, task_id))
            else:
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
        """Get a specific task by ID from task_registry table"""
        try:
            cursor = self.connection.cursor()

            if self.use_sqlite:
                cursor.execute("""
                    SELECT id, task_id, title, description, submitter, submitter_type, transport_channel,
                           status, status_reason, assigned_to, priority, deadline,
                           created_at, updated_at, assigned_at, started_at, completed_at,
                           source_server, target_server, result, metadata, status_history
                    FROM task_registry
                    WHERE task_id = ?
                """, (task_id,))
            else:
                cursor.execute("""
                    SELECT id, task_id, title, description, submitter, submitter_type, transport_channel,
                           status, status_reason, assigned_to, priority, deadline,
                           created_at, updated_at, assigned_at, started_at, completed_at,
                           source_server, target_server, result, metadata, status_history
                    FROM task_registry
                    WHERE task_id = %s
                """, (task_id,))

            row = cursor.fetchone()
            cursor.close()

            if row:
                return {
                    "id": row[0],
                    "task_id": row[1],
                    "title": row[2],
                    "description": row[3],
                    "submitter": row[4],
                    "submitter_type": row[5],
                    "transport_channel": row[6],
                    "status": row[7],
                    "status_reason": row[8],
                    "assigned_to": row[9],
                    "priority": row[10],
                    "deadline": format_datetime_value(row[11]),
                    "created_at": format_datetime_value(row[12]),
                    "updated_at": format_datetime_value(row[13]),
                    "assigned_at": format_datetime_value(row[14]),
                    "started_at": format_datetime_value(row[15]),
                    "completed_at": format_datetime_value(row[16]),
                    "source_server": row[17],
                    "target_server": row[18],
                    "result": row[19],
                    "metadata": row[20],
                    "status_history": row[21]
                }

            return None
        except Exception as e:
            print(f"❌ Error getting task: {e}")
            import traceback
            traceback.print_exc()
            return None

    def get_tasks_by_status(self, status: str) -> List[Dict[str, Any]]:
        """Get all tasks with a specific status"""
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                SELECT id, task_id, title, description, submitter, submitter_type, transport_channel,
                       status, status_reason, assigned_to, priority, deadline,
                       created_at, updated_at, assigned_at, started_at, completed_at,
                       source_server, target_server, result, metadata, status_history
                FROM task_registry
                WHERE status = %s
                ORDER BY created_at DESC
            """, (status,))

            rows = cursor.fetchall()
            cursor.close()

            tasks = []
            for row in rows:
                tasks.append({
                    "id": row[0],
                    "task_id": row[1],
                    "title": row[2],
                    "description": row[3],
                    "submitter": row[4],
                    "submitter_type": row[5],
                    "transport_channel": row[6],
                    "status": row[7],
                    "status_reason": row[8],
                    "assigned_to": row[9],
                    "priority": row[10],
                    "deadline": format_datetime_value(row[11]),
                    "created_at": format_datetime_value(row[12]),
                    "updated_at": format_datetime_value(row[13]),
                    "assigned_at": format_datetime_value(row[14]),
                    "started_at": format_datetime_value(row[15]),
                    "completed_at": format_datetime_value(row[16]),
                    "source_server": row[17],
                    "target_server": row[18],
                    "result": row[19],
                    "metadata": row[20],
                    "status_history": row[21]
                })

            return tasks
        except Exception as e:
            print(f"❌ Error getting tasks by status: {e}")
            import traceback
            traceback.print_exc()
            return []

    def get_all_tasks(self) -> List[Dict[str, Any]]:
        """Get all tasks from the registry"""
        try:
            cursor = self.connection.cursor()

            cursor.execute("""
                SELECT id, task_id, title, description, submitter, submitter_type, transport_channel,
                       status, status_reason, assigned_to, priority, deadline,
                       created_at, updated_at, assigned_at, started_at, completed_at,
                       source_server, target_server, result, metadata, status_history
                FROM task_registry
                ORDER BY created_at DESC
            """)

            rows = cursor.fetchall()
            cursor.close()

            tasks = []
            for row in rows:
                tasks.append({
                    "id": row[0],
                    "task_id": row[1],
                    "title": row[2],
                    "description": row[3],
                    "submitter": row[4],
                    "submitter_type": row[5],
                    "transport_channel": row[6],
                    "status": row[7],
                    "status_reason": row[8],
                    "assigned_to": row[9],
                    "priority": row[10],
                    "deadline": format_datetime_value(row[11]),
                    "created_at": format_datetime_value(row[12]),
                    "updated_at": format_datetime_value(row[13]),
                    "assigned_at": format_datetime_value(row[14]),
                    "started_at": format_datetime_value(row[15]),
                    "completed_at": format_datetime_value(row[16]),
                    "source_server": row[17],
                    "target_server": row[18],
                    "result": row[19],
                    "metadata": row[20],
                    "status_history": row[21]
                })

            return tasks
        except Exception as e:
            print(f"❌ Error getting all tasks: {e}")
            import traceback
            traceback.print_exc()
            return []

    def delete_task(self, task_id: str) -> bool:
        """Delete a specific task from the registry. Returns True if deleted, False if not found."""
        try:
            if self.use_sqlite:
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM task_registry WHERE task_id = ?", (task_id,))
                deleted = cursor.rowcount > 0
                self.connection.commit()
                cursor.close()
            else:
                import psycopg2
                cursor = self.connection.cursor()
                cursor.execute("DELETE FROM task_registry WHERE task_id = %s", (task_id,))
                deleted = cursor.rowcount > 0
                self.connection.commit()
                cursor.close()

            if deleted:
                print(f"Successfully deleted task: {task_id}")
            else:
                print(f"Task not found for deletion: {task_id}")
            return deleted
        except Exception as e:
            print(f"Error deleting task {task_id}: {e}")
            import traceback
            traceback.print_exc()
            return False

    def update_task_result_reference(
        self,
        task_id: str,
        storage_ref: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None,
        update_status: bool = True  # NEW: Allow skipping status update for workflow sequences
    ) -> bool:
        """
        Update task with result storage reference.

        Instead of storing full result in DB, stores reference in metadata:
        {
            "storage_type": "git",  # or "s3", "local", "ssh"
            "path": "results/task-123/",
            "commit_sha": "a1b2c3d4...",
            "file_path": "/var/mcp-results/results/task-123/result.py"
        }

        Args:
            task_id: Task identifier
            storage_ref: Storage reference dict from ResultRouter
            metadata: Additional metadata
            update_status: If True, updates status to 'done'. Set to False for workflow sequences.

        Returns:
            True if update succeeded
        """
        try:
            cursor = self.connection.cursor()

            # Build result reference JSON
            result_ref = {
                "storage_type": storage_ref.get("storage_type", "inline"),
                "path": storage_ref.get("path", ""),
                "commit_sha": storage_ref.get("commit_sha"),
                "file_path": storage_ref.get("code_file") or storage_ref.get("file_path")
            }
            
            # Merge with existing metadata
            existing_meta = {}
            task = self.get_task(task_id)
            if task and task.get("metadata"):
                try:
                    existing_meta = json.loads(task["metadata"]) if isinstance(task["metadata"], str) else task["metadata"]
                except:
                    pass
            
            # Update metadata with result reference
            existing_meta["result_reference"] = result_ref
            existing_meta["completed_at"] = datetime.now().isoformat() if self.use_sqlite else "CURRENT_TIMESTAMP"
            
            if self.use_sqlite:
                cursor.execute("""
                    UPDATE task_registry
                    SET metadata = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = ?
                """, (json.dumps(existing_meta), task_id))
            else:
                cursor.execute("""
                    UPDATE task_registry
                    SET metadata = jsonb_set(
                        COALESCE(metadata, '{}'::jsonb),
                        '{result_reference}', %s::jsonb
                    ),
                        updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = %s
                """, (json.dumps(result_ref), task_id))

            affected_rows = cursor.rowcount

            if affected_rows > 0:
                print(f"✅ Task result reference updated: {task_id}")
                # Update status to done (PostgreSQL) or completed (SQLite) BEFORE closing cursor
                # ONLY if update_status is True (for workflow sequences, keep status as in_progress)
                if update_status:
                    status_value = "done" if not self.use_sqlite else "completed"
                    if self.use_sqlite:
                        cursor.execute("UPDATE task_registry SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE task_id = ?",
                                      (status_value, task_id))
                    else:
                        cursor.execute("UPDATE task_registry SET status = %s, updated_at = CURRENT_TIMESTAMP WHERE task_id = %s",
                                      (status_value, task_id))
                    self.connection.commit()
                    print(f"✅ Task {task_id} status updated to {status_value}, call_source=task_storage")
                else:
                    self.connection.commit()
                    print(f"✅ Task {task_id} result reference updated (status NOT updated - workflow in progress)")
            else:
                print(f"⚠️ Task not found for result reference update: {task_id}")

            cursor.close()
            return affected_rows > 0
        except Exception as e:
            print(f"❌ Error updating task result reference: {e}")
            import traceback
            traceback.print_exc()
            self.connection.rollback()
            return False

    def update_task_with_git_url(self, task_id: str, git_url: str, deployment_url: str = None) -> bool:
        """
        Update task with Git URL result (for background thread updates).

        This method is called by background threads to update task status
        when async processing completes.

        Args:
            task_id: Task identifier
            git_url: Git URL from the agent
            deployment_url: Optional deployment URL if app was deployed

        Returns:
            True if update succeeded
        """
        try:
            cursor = self.connection.cursor()

            # Build metadata update
            metadata_update = {
                "storage_type": "git",
                "git_url": git_url,
                "path": git_url
            }
            if deployment_url:
                metadata_update["deployment_url"] = deployment_url

            # Update status to done and add Git URL to metadata
            cursor.execute("""
                UPDATE task_registry
                SET status = %s,
                    status_reason = %s,
                    metadata = metadata || %s::jsonb,
                    updated_at = CURRENT_TIMESTAMP
                WHERE task_id = %s
            """, (
                "done",
                "Task completed successfully. Result stored at: " + git_url,
                json.dumps(metadata_update),
                task_id
            ))

            affected_rows = cursor.rowcount
            self.connection.commit()
            cursor.close()

            if affected_rows > 0:
                msg = f"✅ Task {task_id} updated with Git URL"
                if deployment_url:
                    msg += f" and deployment URL: {deployment_url}"
                print(msg)
                return True
            else:
                print(f"⚠️ Task {task_id} not found for Git URL update")
                return False
                
        except Exception as e:
            print(f"❌ Error updating task with Git URL: {e}")
            import traceback
            traceback.print_exc()
            self.connection.rollback()
            return False

    def close(self):
        """Close the database connection"""
        if self.connection:
            self.connection.close()
            print("🔒 Task storage database connection closed")
    def update_task_status_only(self, task_id: str, status: str, status_reason: str,
                               metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update task status without adding duplicate history entries.
        
        This method is used by _update_task_status to update status
        without duplicating entries in the status history.
        
        Args:
            task_id: Task identifier
            status: New status
            status_reason: Reason for status change
            metadata: Optional metadata to update
            
        Returns:
            True if update succeeded
        """
        try:
            cursor = self.connection.cursor()
            
            # Prepare metadata update
            if metadata:
                if self.use_sqlite:
                    import json as json_module
                    current_metadata = self._get_task_metadata(task_id)
                    if current_metadata:
                        merged_metadata = json_module.loads(current_metadata)
                        merged_metadata.update(metadata)
                        metadata_json = json_module.dumps(merged_metadata)
                    else:
                        metadata_json = json.dumps(metadata)
                else:
                    # For PostgreSQL, use || operator to merge JSONB
                    metadata_json = None  # Will be handled in SQL
            else:
                metadata_json = None
            
            if self.use_sqlite:
                cursor.execute("""
                    UPDATE task_registry
                    SET status = ?,
                        status_reason = ?,
                        metadata = COALESCE(metadata, '{}') || ?
                    WHERE task_id = ?
                """, (status, status_reason, json.dumps(metadata) if metadata else '{}', task_id))
            else:
                # PostgreSQL: merge metadata properly
                if metadata:
                    cursor.execute("""
                        UPDATE task_registry
                        SET status = %s,
                            status_reason = %s,
                            metadata = COALESCE(metadata, '{}'::jsonb) || %s::jsonb
                        WHERE task_id = %s
                    """, (status, status_reason, json.dumps(metadata), task_id))
                else:
                    cursor.execute("""
                        UPDATE task_registry
                        SET status = %s,
                            status_reason = %s
                        WHERE task_id = %s
                    """, (status, status_reason, task_id))
            
            affected_rows = cursor.rowcount
            self.connection.commit()
            cursor.close()
            
            if affected_rows > 0:
                print(f"✅ Task {task_id} status updated to {status}")
                return True
            else:
                print(f"⚠️ Task {task_id} not found for status update")
                return False
                
        except Exception as e:
            print(f"❌ Error updating task status: {e}")
            import traceback
            traceback.print_exc()
            self.connection.rollback()
            return False
