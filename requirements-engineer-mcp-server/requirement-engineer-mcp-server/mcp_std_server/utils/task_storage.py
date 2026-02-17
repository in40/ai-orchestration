"""
Task Storage Module for MCP Server
Provides storage for tasks with both SQLite and PostgreSQL backends
"""
import sqlite3
import json
import time
from typing import Dict, Any, Optional
import psycopg2
from psycopg2.extras import RealDictCursor


class TaskStorage:
    """Storage for tasks with both SQLite and PostgreSQL backends"""
    
    def __init__(self, use_postgres: bool = False, postgres_config: Optional[Dict[str, Any]] = None):
        self.use_postgres = use_postgres
        self.postgres_config = postgres_config or {}
        
        if self.use_postgres and self.postgres_config:
            self._init_postgres()
        else:
            self._init_sqlite()
    
    def _init_sqlite(self):
        """Initialize SQLite database for task storage"""
        self.conn = sqlite3.connect('tasks.db', check_same_thread=False)
        self.conn.row_factory = sqlite3.Row  # Enable dict-like access
        self.cursor = self.conn.cursor()
        
        # Create tasks table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                arguments TEXT,
                status TEXT DEFAULT 'created',
                result TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create requirements specifications table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS requirements_specifications (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requirement_id TEXT UNIQUE,
                description TEXT,
                status TEXT DEFAULT 'draft',
                priority TEXT DEFAULT 'medium',
                category TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create traceability matrix table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS traceability_matrix (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                requirement_id TEXT,
                artifact_type TEXT,  -- design, code, test
                artifact_id TEXT,
                relationship TEXT,   -- specifies_design, implemented_by, validated_by
                confidence REAL DEFAULT 0.5,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Create ambiguity log table
        self.cursor.execute('''
            CREATE TABLE IF NOT EXISTS ambiguity_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ambiguity_id TEXT UNIQUE,
                requirement_id TEXT,
                description TEXT,
                severity TEXT DEFAULT 'medium',
                status TEXT DEFAULT 'open',  -- open, in_review, resolved, wont_fix
                resolution TEXT,
                date_identified DATE,
                date_resolved DATE,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        self.conn.commit()
    
    def _init_postgres(self):
        """Initialize PostgreSQL database for task storage"""
        try:
            self.conn = psycopg2.connect(
                host=self.postgres_config.get("host", "localhost"),
                port=self.postgres_config.get("port", 5432),
                database=self.postgres_config.get("database", "mcp_registry"),
                user=self.postgres_config.get("user", "postgres"),
                password=self.postgres_config.get("password", "")
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
                    artifact_type VARCHAR(50),  -- design, code, test
                    artifact_id VARCHAR(255),
                    relationship VARCHAR(50),   -- specifies_design, implemented_by, validated_by
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
                    status VARCHAR(50) DEFAULT 'open',  -- open, in_review, resolved, wont_fix
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
            # Fall back to SQLite
            self.use_postgres = False
            self._init_sqlite()
    
    def create_task(self, task_id: str, name: str, arguments: Dict[str, Any], status: str = "created"):
        """Create a new task record"""
        try:
            if self.use_postgres:
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
            else:
                query = """
                    INSERT OR REPLACE INTO tasks (id, name, arguments, status)
                    VALUES (?, ?, ?, ?)
                """
                self.cursor.execute(query, (task_id, name, json.dumps(arguments), status))
            
            self.conn.commit()
        except Exception as e:
            print(f"Error creating task: {e}")
    
    def update_task_status(self, task_id: str, status: str, result: Optional[Dict[str, Any]] = None):
        """Update task status and optionally result"""
        try:
            if self.use_postgres:
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
            else:
                if result:
                    query = """
                        UPDATE tasks
                        SET status = ?, result = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """
                    self.cursor.execute(query, (status, json.dumps(result), task_id))
                else:
                    query = """
                        UPDATE tasks
                        SET status = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                    """
                    self.cursor.execute(query, (status, task_id))
            
            self.conn.commit()
        except Exception as e:
            print(f"Error updating task status: {e}")
    
    def get_task(self, task_id: str) -> Optional[Dict[str, Any]]:
        """Get a task by ID"""
        try:
            if self.use_postgres:
                query = "SELECT * FROM tasks WHERE id = %s"
                self.cursor.execute(query, (task_id,))
            else:
                query = "SELECT * FROM tasks WHERE id = ?"
                self.cursor.execute(query, (task_id,))
            
            row = self.cursor.fetchone()
            if row:
                if self.use_postgres:
                    # Convert RealDictRow to regular dict
                    row_dict = dict(row)
                    if row_dict['arguments']:
                        row_dict['arguments'] = json.loads(row_dict['arguments'])
                    if row_dict['result']:
                        row_dict['result'] = json.loads(row_dict['result'])
                    return row_dict
                else:
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
            if self.use_postgres:
                query = "SELECT * FROM tasks ORDER BY created_at DESC LIMIT %s OFFSET %s"
                self.cursor.execute(query, (limit, offset))
            else:
                query = "SELECT * FROM tasks ORDER BY created_at DESC LIMIT ? OFFSET ?"
                self.cursor.execute(query, (limit, offset))
            
            rows = self.cursor.fetchall()
            tasks = []
            for row in rows:
                if self.use_postgres:
                    row_dict = dict(row)
                    if row_dict['arguments']:
                        row_dict['arguments'] = json.loads(row_dict['arguments'])
                    if row_dict['result']:
                        row_dict['result'] = json.loads(row_dict['result'])
                    tasks.append(row_dict)
                else:
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
    
    # Requirement Engineering Specific Methods
    
    def store_requirement_specification(self, requirement_id: str, description: str, status: str = "draft", 
                                       priority: str = "medium", category: str = ""):
        """Store a requirement specification"""
        try:
            if self.use_postgres:
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
            else:
                query = """
                    INSERT OR REPLACE INTO requirements_specifications 
                    (requirement_id, description, status, priority, category)
                    VALUES (?, ?, ?, ?, ?)
                """
                self.cursor.execute(query, (requirement_id, description, status, priority, category))
            
            self.conn.commit()
        except Exception as e:
            print(f"Error storing requirement specification: {e}")
    
    def get_requirement_specifications(self, limit: int = 100, offset: int = 0) -> list:
        """Get requirement specifications"""
        try:
            if self.use_postgres:
                query = "SELECT * FROM requirements_specifications ORDER BY created_at DESC LIMIT %s OFFSET %s"
                self.cursor.execute(query, (limit, offset))
            else:
                query = "SELECT * FROM requirements_specifications ORDER BY created_at DESC LIMIT ? OFFSET ?"
                self.cursor.execute(query, (limit, offset))
            
            rows = self.cursor.fetchall()
            specs = []
            for row in rows:
                if self.use_postgres:
                    specs.append(dict(row))
                else:
                    specs.append(dict(row))
            return specs
        except Exception as e:
            print(f"Error getting requirement specifications: {e}")
            return []
    
    def store_traceability_link(self, requirement_id: str, artifact_type: str, artifact_id: str, 
                               relationship: str, confidence: float = 0.7):
        """Store a traceability link"""
        try:
            if self.use_postgres:
                query = """
                    INSERT INTO traceability_matrix 
                    (requirement_id, artifact_type, artifact_id, relationship, confidence)
                    VALUES (%s, %s, %s, %s, %s)
                """
                self.cursor.execute(query, (requirement_id, artifact_type, artifact_id, relationship, confidence))
            else:
                query = """
                    INSERT INTO traceability_matrix 
                    (requirement_id, artifact_type, artifact_id, relationship, confidence)
                    VALUES (?, ?, ?, ?, ?)
                """
                self.cursor.execute(query, (requirement_id, artifact_type, artifact_id, relationship, confidence))
            
            self.conn.commit()
        except Exception as e:
            print(f"Error storing traceability link: {e}")
    
    def get_traceability_links(self, requirement_id: str = None, limit: int = 100, offset: int = 0) -> list:
        """Get traceability links"""
        try:
            if requirement_id:
                if self.use_postgres:
                    query = "SELECT * FROM traceability_matrix WHERE requirement_id = %s ORDER BY created_at DESC LIMIT %s OFFSET %s"
                    self.cursor.execute(query, (requirement_id, limit, offset))
                else:
                    query = "SELECT * FROM traceability_matrix WHERE requirement_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?"
                    self.cursor.execute(query, (requirement_id, limit, offset))
            else:
                if self.use_postgres:
                    query = "SELECT * FROM traceability_matrix ORDER BY created_at DESC LIMIT %s OFFSET %s"
                    self.cursor.execute(query, (limit, offset))
                else:
                    query = "SELECT * FROM traceability_matrix ORDER BY created_at DESC LIMIT ? OFFSET ?"
                    self.cursor.execute(query, (limit, offset))
            
            rows = self.cursor.fetchall()
            links = []
            for row in rows:
                if self.use_postgres:
                    links.append(dict(row))
                else:
                    links.append(dict(row))
            return links
        except Exception as e:
            print(f"Error getting traceability links: {e}")
            return []
    
    def store_ambiguity(self, ambiguity_id: str, requirement_id: str, description: str, 
                       severity: str = "medium", status: str = "open", resolution: str = ""):
        """Store an ambiguity entry"""
        try:
            if self.use_postgres:
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
            else:
                # For SQLite, we need to handle the date differently
                # First insert the record without date_resolved
                query = """
                    INSERT OR REPLACE INTO ambiguity_log
                    (ambiguity_id, requirement_id, description, severity, status, resolution, date_identified)
                    VALUES (?, ?, ?, ?, ?, ?, date('now'))
                """
                self.cursor.execute(query, (ambiguity_id, requirement_id, description, severity, status, resolution))
                
                # Then update date_resolved if status is resolved
                if status == 'resolved':
                    update_query = """
                        UPDATE ambiguity_log
                        SET date_resolved = date('now'), updated_at = datetime('now')
                        WHERE ambiguity_id = ?
                    """
                    self.cursor.execute(update_query, (ambiguity_id,))
                else:
                    update_query = """
                        UPDATE ambiguity_log
                        SET updated_at = datetime('now')
                        WHERE ambiguity_id = ?
                    """
                    self.cursor.execute(update_query, (ambiguity_id,))
            
            self.conn.commit()
        except Exception as e:
            print(f"Error storing ambiguity: {e}")
    
    def get_ambiguities(self, requirement_id: str = None, status: str = None, limit: int = 100, offset: int = 0) -> list:
        """Get ambiguities"""
        try:
            conditions = []
            params = []
            
            if requirement_id:
                conditions.append("requirement_id = ?" if not self.use_postgres else "requirement_id = %s")
                params.append(requirement_id)
            if status:
                conditions.append("status = ?" if not self.use_postgres else "status = %s")
                params.append(status)
            
            base_query = "SELECT * FROM ambiguity_log"
            if conditions:
                base_query += " WHERE " + " AND ".join(conditions)
            
            base_query += " ORDER BY created_at DESC LIMIT ? OFFSET ?" if not self.use_postgres else " ORDER BY created_at DESC LIMIT %s OFFSET %s"
            params.extend([limit, offset])
            
            if self.use_postgres:
                query = base_query.replace("?", "%s")
                self.cursor.execute(query, params)
            else:
                self.cursor.execute(base_query, params)
            
            rows = self.cursor.fetchall()
            ambiguities = []
            for row in rows:
                if self.use_postgres:
                    ambiguities.append(dict(row))
                else:
                    ambiguities.append(dict(row))
            return ambiguities
        except Exception as e:
            print(f"Error getting ambiguities: {e}")
            return []
    
    def close(self):
        """Close the database connection"""
        if self.conn:
            self.conn.close()