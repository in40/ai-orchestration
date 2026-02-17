import sqlite3
import json
from datetime import datetime
from typing import Dict, List, Optional
import uuid

class TaskStorage:
    """Handles storage and retrieval of tasks in the database"""
    
    def __init__(self, db_path: str = "team_management.db"):
        self.db_path = db_path
        self.init_db()
    
    def init_db(self):
        """Initialize the database with required tables"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                title TEXT NOT NULL,
                description TEXT,
                assignee_id TEXT,
                due_date TEXT,
                status TEXT DEFAULT 'todo',
                priority TEXT DEFAULT 'medium',
                tags TEXT,
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        # Create team_members table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS team_members (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                role TEXT,
                skills TEXT,
                availability TEXT DEFAULT 'full_time',
                created_at TEXT,
                updated_at TEXT
            )
        """)
        
        conn.commit()
        conn.close()
    
    def create_task(self, task_data: Dict) -> Dict:
        """Create a new task in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        task_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        tags_json = json.dumps(task_data.get('tags', []))
        
        cursor.execute("""
            INSERT INTO tasks (id, title, description, assignee_id, due_date, 
                             priority, tags, created_at, updated_at, status)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task_id,
            task_data['title'],
            task_data.get('description'),
            task_data['assignee_id'],
            task_data.get('due_date'),
            task_data.get('priority', 'medium'),
            tags_json,
            now,
            now,
            'todo'  # default status
        ))
        
        conn.commit()
        conn.close()
        
        # Return the created task
        return {
            "id": task_id,
            "title": task_data['title'],
            "description": task_data.get('description'),
            "assignee_id": task_data['assignee_id'],
            "due_date": task_data.get('due_date'),
            "status": 'todo',
            "priority": task_data.get('priority', 'medium'),
            "tags": task_data.get('tags', []),
            "created_at": now
        }
    
    def get_task(self, task_id: str) -> Optional[Dict]:
        """Retrieve a task by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM tasks WHERE id = ?", (task_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "assignee_id": row[3],
                "due_date": row[4],
                "status": row[5],
                "priority": row[6],
                "tags": json.loads(row[7]),
                "created_at": row[8],
                "updated_at": row[9]
            }
        return None
    
    def update_task(self, task_id: str, update_data: Dict) -> Optional[Dict]:
        """Update a task in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current task
        current_task = self.get_task(task_id)
        if not current_task:
            conn.close()
            return None
        
        # Merge update data with current data
        updated_task = {**current_task, **update_data}
        updated_task['updated_at'] = datetime.now().isoformat()
        
        tags_json = json.dumps(updated_task.get('tags', []))
        
        cursor.execute("""
            UPDATE tasks SET title=?, description=?, assignee_id=?, due_date=?, 
                          status=?, priority=?, tags=?, updated_at=?
            WHERE id=?
        """, (
            updated_task['title'],
            updated_task.get('description'),
            updated_task.get('assignee_id', updated_task['assignee_id']),
            updated_task.get('due_date'),
            updated_task.get('status', updated_task['status']),
            updated_task.get('priority', updated_task['priority']),
            tags_json,
            updated_task['updated_at'],
            task_id
        ))
        
        conn.commit()
        conn.close()
        
        return updated_task
    
    def delete_task(self, task_id: str) -> bool:
        """Delete a task from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("DELETE FROM tasks WHERE id=?", (task_id,))
        rows_affected = cursor.rowcount
        
        conn.commit()
        conn.close()
        
        return rows_affected > 0
    
    def list_tasks(self, filters: Optional[Dict] = None) -> List[Dict]:
        """List tasks with optional filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM tasks"
        params = []
        
        if filters:
            conditions = []
            if filters.get('assignee_id'):
                conditions.append("assignee_id = ?")
                params.append(filters['assignee_id'])
            if filters.get('status'):
                conditions.append("status = ?")
                params.append(filters['status'])
            if filters.get('priority'):
                conditions.append("priority = ?")
                params.append(filters['priority'])
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        tasks = []
        for row in rows:
            task = {
                "id": row[0],
                "title": row[1],
                "description": row[2],
                "assignee_id": row[3],
                "due_date": row[4],
                "status": row[5],
                "priority": row[6],
                "tags": json.loads(row[7]),
                "created_at": row[8],
                "updated_at": row[9]
            }
            tasks.append(task)
        
        return tasks
    
    def create_team_member(self, member_data: Dict) -> Dict:
        """Create a new team member in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        member_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        skills_json = json.dumps(member_data.get('skills', []))
        
        cursor.execute("""
            INSERT INTO team_members (id, name, email, role, skills, availability, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            member_id,
            member_data['name'],
            member_data['email'],
            member_data.get('role'),
            skills_json,
            member_data.get('availability', 'full_time'),
            now,
            now
        ))
        
        conn.commit()
        conn.close()
        
        # Return the created member
        return {
            "id": member_id,
            "name": member_data['name'],
            "email": member_data['email'],
            "role": member_data.get('role'),
            "skills": member_data.get('skills', []),
            "availability": member_data.get('availability', 'full_time'),
            "created_at": now
        }
    
    def get_team_member(self, member_id: str) -> Optional[Dict]:
        """Retrieve a team member by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM team_members WHERE id = ?", (member_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if row:
            return {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "role": row[3],
                "skills": json.loads(row[4]),
                "availability": row[5],
                "created_at": row[6],
                "updated_at": row[7]
            }
        return None
    
    def update_team_member(self, member_id: str, update_data: Dict) -> Optional[Dict]:
        """Update a team member in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get current member
        current_member = self.get_team_member(member_id)
        if not current_member:
            conn.close()
            return None
        
        # Merge update data with current data
        updated_member = {**current_member, **update_data}
        updated_member['updated_at'] = datetime.now().isoformat()
        
        skills_json = json.dumps(updated_member.get('skills', []))
        
        cursor.execute("""
            UPDATE team_members SET name=?, email=?, role=?, skills=?, availability=?, updated_at=?
            WHERE id=?
        """, (
            updated_member.get('name', updated_member['name']),
            updated_member.get('email', updated_member['email']),
            updated_member.get('role'),
            skills_json,
            updated_member.get('availability', updated_member['availability']),
            updated_member['updated_at'],
            member_id
        ))
        
        conn.commit()
        conn.close()
        
        return updated_member
    
    def list_team_members(self, filters: Optional[Dict] = None) -> List[Dict]:
        """List team members with optional filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT * FROM team_members"
        params = []
        
        if filters:
            conditions = []
            if filters.get('role'):
                conditions.append("role = ?")
                params.append(filters['role'])
            if filters.get('availability'):
                conditions.append("availability = ?")
                params.append(filters['availability'])
            if conditions:
                query += " WHERE " + " AND ".join(conditions)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        conn.close()
        
        members = []
        for row in rows:
            member = {
                "id": row[0],
                "name": row[1],
                "email": row[2],
                "role": row[3],
                "skills": json.loads(row[4]),
                "availability": row[5],
                "created_at": row[6],
                "updated_at": row[7]
            }
            members.append(member)
        
        return members
    
    def get_team_queues(self) -> Dict[str, List[Dict]]:
        """Get tasks organized by status (queues)"""
        all_tasks = self.list_tasks()
        
        queues = {
            "todo": [],
            "in_progress": [],
            "review": [],
            "done": []
        }
        
        # Get team member names for display
        members = {m['id']: m['name'] for m in self.list_team_members()}
        
        for task in all_tasks:
            assignee_name = members.get(task['assignee_id'], 'Unassigned')
            task_display = {
                "id": task['id'],
                "title": task['title'],
                "assignee": assignee_name
            }
            queues[task['status']].append(task_display)
        
        return queues