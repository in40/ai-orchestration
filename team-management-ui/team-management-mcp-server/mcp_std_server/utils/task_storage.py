import psycopg2
import psycopg2.extras
import json
from datetime import datetime
from typing import Dict, List, Optional
import logging

logger = logging.getLogger(__name__)


class TaskStorage:
    """Handles storage and retrieval of tasks in PostgreSQL mcp_registry database"""

    def __init__(self, host: str = "127.0.0.1", port: int = 5432, database: str = "mcp_registry",
                 user: str = "postgres", password: str = "postgres"):
        self.host = host
        self.port = port
        self.database = database
        self.user = user
        self.password = password
        self.connection = None
        self._connect()
        self._init_db()

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
            logger.info(f"✅ Successfully connected to PostgreSQL: {self.database}")
        except Exception as e:
            logger.error(f"❌ Failed to connect to PostgreSQL: {e}")
            raise

    def _init_db(self):
        """Initialize database - no table creation needed, uses existing task_registry and task_deployments"""
        pass

    def _get_deployment_info(self, task_id: str) -> Dict:
        """Fetch deployment info from task_deployments table"""
        try:
            cur = self.connection.cursor()
            cur.execute("""
                SELECT deployment_url, git_commit_sha, docker_image, status, container_id, container_port, host_port
                FROM task_deployments WHERE task_id = %s
            """, (task_id,))
            row = cur.fetchone()
            cur.close()

            if row:
                return {
                    "deployment_url": row[0],
                    "git_commit_sha": row[1],
                    "docker_image": row[2],
                    "deployment_status": row[3],
                    "container_id": row[4],
                    "container_port": row[5],
                    "host_port": row[6]
                }
            return {
                "deployment_url": None,
                "git_commit_sha": None,
                "docker_image": None,
                "deployment_status": None,
                "container_id": None,
                "container_port": None,
                "host_port": None
            }
        except Exception as e:
            logger.error(f"Error fetching deployment info: {e}")
            return {
                "deployment_url": None,
                "git_commit_sha": None,
                "docker_image": None,
                "deployment_status": None,
                "container_id": None,
                "container_port": None,
                "host_port": None
            }

    def create_task(self, task_data: Dict) -> Dict:
        """Create a new task in the task_registry table"""
        try:
            cur = self.connection.cursor()
            now = datetime.now().isoformat()

            cur.execute("""
                INSERT INTO task_registry
                (task_id, title, description, submitter, submitter_type, transport_channel,
                 assigned_to, status, priority, deadline, source_server, target_server, metadata, created_at, updated_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                RETURNING task_id
            """, (
                task_data.get('id') or f"task-{int(datetime.now().timestamp() * 1000)}",
                task_data.get('title', ''),
                task_data.get('description', ''),
                task_data.get('submitter', 'api'),
                task_data.get('submitter_type', 'api'),
                task_data.get('transport_channel', 'api'),
                task_data.get('assigned_to', 'unassigned'),
                task_data.get('status', 'received'),
                task_data.get('priority', 'medium'),
                task_data.get('due_date'),
                task_data.get('source_server'),
                task_data.get('target_server'),
                json.dumps(task_data.get('metadata', {})),
                now,
                now
            ))

            task_id = cur.fetchone()[0]
            self.connection.commit()
            cur.close()

            return {
                "id": task_id,
                "title": task_data.get('title', ''),
                "description": task_data.get('description'),
                "assignee_id": task_data.get('assigned_to'),
                "due_date": task_data.get('due_date'),
                "status": task_data.get('status', 'received'),
                "priority": task_data.get('priority', 'medium'),
                "tags": task_data.get('tags', []),
                "created_at": now
            }
        except Exception as e:
            logger.error(f"Error creating task: {e}")
            self.connection.rollback()
            raise

    def get_task(self, task_id: str) -> Optional[Dict]:
        """Retrieve a task by ID from task_registry with deployment info"""
        try:
            cur = self.connection.cursor()
            cur.execute("""
                SELECT task_id, title, description, assigned_to, priority, deadline,
                       status, created_at, updated_at, metadata
                FROM task_registry WHERE task_id = %s
            """, (task_id,))
            row = cur.fetchone()
            cur.close()

            if row:
                task = {
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "assignee_id": row[3],
                    "due_date": row[4],
                    "priority": row[5],
                    "status": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                    "tags": [],
                    "metadata": row[9]
                }
                # Add deployment info
                deployment_info = self._get_deployment_info(task_id)
                task.update(deployment_info)
                return task
            return None
        except Exception as e:
            logger.error(f"Error getting task: {e}")
            return None

    def update_task(self, task_id: str, update_data: Dict) -> Optional[Dict]:
        """Update a task in task_registry"""
        try:
            cur = self.connection.cursor()

            # Build dynamic update query
            updates = []
            params = []

            if 'title' in update_data:
                updates.append("title = %s")
                params.append(update_data['title'])
            if 'description' in update_data:
                updates.append("description = %s")
                params.append(update_data['description'])
            if 'assigned_to' in update_data:
                updates.append("assigned_to = %s")
                params.append(update_data['assigned_to'])
            if 'due_date' in update_data:
                updates.append("deadline = %s")
                params.append(update_data['due_date'])
            if 'status' in update_data:
                updates.append("status = %s")
                params.append(update_data['status'])
            if 'priority' in update_data:
                updates.append("priority = %s")
                params.append(update_data['priority'])
            if 'metadata' in update_data:
                updates.append("metadata = %s")
                params.append(json.dumps(update_data['metadata']))

            if not updates:
                return self.get_task(task_id)

            updates.append("updated_at = CURRENT_TIMESTAMP")
            params.append(task_id)

            cur.execute(f"""
                UPDATE task_registry
                SET {', '.join(updates)}
                WHERE task_id = %s
            """, params)

            self.connection.commit()
            cur.close()

            return self.get_task(task_id)
        except Exception as e:
            logger.error(f"Error updating task: {e}")
            self.connection.rollback()
            return None

    def delete_task(self, task_id: str) -> bool:
        """Delete a task from task_registry"""
        try:
            cur = self.connection.cursor()
            cur.execute("DELETE FROM task_registry WHERE task_id = %s", (task_id,))
            rows_affected = cur.rowcount
            self.connection.commit()
            cur.close()
            return rows_affected > 0
        except Exception as e:
            logger.error(f"Error deleting task: {e}")
            self.connection.rollback()
            return False

    def list_tasks(self, filters: Optional[Dict] = None) -> List[Dict]:
        """List tasks from task_registry with deployment info"""
        try:
            cur = self.connection.cursor()

            query = """
                SELECT task_id, title, description, assigned_to, priority, deadline,
                       status, created_at, updated_at, metadata
                FROM task_registry
            """
            params = []

            if filters:
                conditions = []
                if filters.get('assigned_to'):
                    conditions.append("assigned_to = %s")
                    params.append(filters['assigned_to'])
                if filters.get('status'):
                    conditions.append("status = %s")
                    params.append(filters['status'])
                if filters.get('priority'):
                    conditions.append("priority = %s")
                    params.append(filters['priority'])
                if conditions:
                    query += " WHERE " + " AND ".join(conditions)

            query += " ORDER BY created_at DESC"

            cur.execute(query, params)
            rows = cur.fetchall()
            cur.close()

            tasks = []
            for row in rows:
                metadata = row[9] or '{}'
                if isinstance(metadata, str):
                    try:
                        metadata = json.loads(metadata)
                    except:
                        metadata = {}

                task = {
                    "id": row[0],
                    "title": row[1],
                    "description": row[2],
                    "assignee_id": row[3],
                    "due_date": row[4],
                    "priority": row[5],
                    "status": row[6],
                    "created_at": row[7],
                    "updated_at": row[8],
                    "tags": metadata.get('tags', []),
                    "metadata": metadata
                }

                # Add deployment info from task_deployments table
                deployment_info = self._get_deployment_info(row[0])
                task.update(deployment_info)

                # Extract git_url from metadata if available
                task["git_url"] = metadata.get("git_url") or metadata.get("result_reference", {}).get("path")

                tasks.append(task)

            return tasks
        except Exception as e:
            logger.error(f"Error listing tasks: {e}")
            return []

    def list_team_members(self, filters: Optional[Dict] = None) -> List[Dict]:
        """List team members from registry services"""
        # This should be handled by the registry query in api_server.py
        return []

    def get_team_member(self, member_id: str) -> Optional[Dict]:
        """Get a team member from registry"""
        return None

    def create_team_member(self, member_data: Dict) -> Dict:
        """Create a team member (not stored in PostgreSQL, handled by registry)"""
        return member_data

    def update_team_member(self, member_id: str, update_data: Dict) -> Optional[Dict]:
        """Update a team member"""
        return update_data

    def get_team_queues(self) -> Dict[str, List[Dict]]:
        """Get tasks organized by status"""
        all_tasks = self.list_tasks()

        queues = {
            "received": [],
            "assigned": [],
            "in_progress": [],
            "done": [],
            "failed": []
        }

        for task in all_tasks:
            status = task.get('status', 'received')
            if status in queues:
                queues[status].append({
                    "id": task['id'],
                    "title": task['title'],
                    "assignee": task.get('assignee_id', 'Unassigned')
                })

        return queues

    def close(self):
        """Close database connection"""
        if self.connection:
            self.connection.close()
            logger.info("Database connection closed")
