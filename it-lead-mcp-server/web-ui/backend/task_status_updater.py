#!/usr/bin/env python3
"""
Script to update task status directly in PostgreSQL
"""
import json
import sys
import os

# Add paths
sys.path.insert(0, '/root/qwen/base/it-lead-mcp-server')
sys.path.insert(0, '/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server')
sys.path.insert(0, '/root/qwen/base')

from utils.task_storage import TaskStorage

def update_task_to_done(task_id):
    """Update a task to done status with completion result"""
    task_storage = TaskStorage(
        host="localhost",
        port=5432,
        database="mcp_registry",
        user="postgres",
        password="postgres"
    )

    # Update task to done status with completion result
    result = json.dumps({
        "completed": True,
        "message": "Task completed successfully",
        "output": "The task has been completed and is ready for review"
    })

    success = task_storage.update_task_status(
        task_id=task_id,
        status="done",
        result=result
    )

    if success:
        print(f"Successfully updated task {task_id} to done status")

        # Verify the update
        task = task_storage.get_task(task_id)
        if task:
            print(f"Task status after update: {task['status']}")
            print(f"Task result: {task['result']}")
    else:
        print(f"Failed to update task {task_id} to done status")

    task_storage.close()

if __name__ == "__main__":
    task_id = sys.argv[1] if len(sys.argv) > 1 else "task-1775482254845"
    print(f"Updating task {task_id} to done status...")
    update_task_to_done(task_id)
