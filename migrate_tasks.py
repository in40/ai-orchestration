#!/usr/bin/env python3
"""Migrate tasks from SQLite to PostgreSQL for IT Lead server"""

import sqlite3
import json
from datetime import datetime

# SQLite database path
SQLITE_DB = "/root/qwen/base/it-lead-mcp-server/mcp_registry.db"
# PostgreSQL connection info
PG_HOST = "localhost"
PG_PORT = 5432
PG_DB = "mcp_registry"
PG_USER = "postgres"
PG_PASSWORD = "postgres"

def get_postgres_connection():
    import psycopg2
    return psycopg2.connect(
        host=PG_HOST,
        port=PG_PORT,
        database=PG_DB,
        user=PG_USER,
        password=PG_PASSWORD
    )

def migrate_tasks():
    # Connect to SQLite
    sqlite_conn = sqlite3.connect(SQLITE_DB)
    sqlite_cursor = sqlite_conn.cursor()
    
    # Get all tasks from SQLite (except task-1772479429144 which is already in PostgreSQL)
    sqlite_cursor.execute("""
        SELECT task_id, title, description, submitter, submitter_type, transport_channel,
               assigned_to, status, status_reason, priority, deadline, 
               source_server, target_server, metadata, status_history,
               created_at, updated_at, assigned_at, started_at, completed_at
        FROM task_registry
        WHERE task_id != 'task-1772479429144'
    """)
    
    tasks = sqlite_cursor.fetchall()
    sqlite_cursor.close()
    sqlite_conn.close()
    
    print(f"Found {len(tasks)} tasks to migrate from SQLite")
    
    # Connect to PostgreSQL
    pg_conn = get_postgres_connection()
    pg_cursor = pg_conn.cursor()
    
    for task in tasks:
        task_id, title, description, submitter, submitter_type, transport_channel, \
        assigned_to, status, status_reason, priority, deadline, \
        source_server, target_server, metadata, status_history, \
        created_at, updated_at, assigned_at, started_at, completed_at = task
        
        # Convert JSON strings
        metadata_json = json.loads(metadata) if metadata else {}
        status_history_json = json.loads(status_history) if status_history else []
        
        # Handle None values for timestamp fields
        deadline_val = datetime.fromisoformat(deadline) if deadline else None
        created_at_val = datetime.fromisoformat(created_at) if created_at else datetime.now()
        updated_at_val = datetime.fromisoformat(updated_at) if updated_at else datetime.now()
        assigned_at_val = datetime.fromisoformat(assigned_at) if assigned_at else None
        started_at_val = datetime.fromisoformat(started_at) if started_at else None
        completed_at_val = datetime.fromisoformat(completed_at) if completed_at else None
        
        try:
            pg_cursor.execute("""
                INSERT INTO task_registry
                (task_id, title, description, submitter, submitter_type, transport_channel,
                 assigned_to, status, status_reason, priority, deadline,
                 source_server, target_server, metadata, status_history,
                 created_at, updated_at, assigned_at, started_at, completed_at)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (task_id) DO UPDATE SET
                    status = EXCLUDED.status,
                    updated_at = CURRENT_TIMESTAMP,
                    status_history = task_registry.status_history || EXCLUDED.status_history
            """, (
                task_id, title, description, submitter, submitter_type, transport_channel,
                assigned_to, status, status_reason, priority, deadline_val,
                source_server, target_server, json.dumps(metadata_json), json.dumps(status_history_json),
                created_at_val, updated_at_val, assigned_at_val, started_at_val, completed_at_val
            ))
            print(f"  ✓ Migrated task: {task_id} (status: {status})")
        except Exception as e:
            print(f"  ✗ Failed to migrate task {task_id}: {e}")
    
    pg_conn.commit()
    pg_cursor.close()
    pg_conn.close()
    
    print(f"\n✅ Successfully migrated {len(tasks)} tasks from SQLite to PostgreSQL")

if __name__ == "__main__":
    migrate_tasks()
