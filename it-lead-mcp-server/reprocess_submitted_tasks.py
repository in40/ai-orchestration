#!/usr/bin/env python3
"""
Reprocess submitted tasks from the database.
This script picks up tasks in 'submitted' status and triggers processing.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from it_lead_mcp_server.utils.task_storage import TaskStorage
from it_lead_mcp_server.utils.task_assignment import TaskAssignmentManager
from it_lead_mcp_server.utils.mcp_registry_client import McpRegistryClient
from it_lead_mcp_server.utils.llm_client import MockLlmClient
import json


def reprocess_submitted_tasks():
    """Reprocess all tasks in 'submitted' status"""

    print("=== Reprocessing Submitted Tasks ===\n")

    # Initialize task storage
    task_storage = TaskStorage(
        host="localhost",
        port=5432,
        database="mcp_registry",
        user="postgres",
        password="postgres"
    )

    # Initialize LLM client
    llm_client = MockLlmClient(
        llm_provider_url="http://192.168.51.105:1234/v1/chat/completions",
        llm_model="qwen3.5-122b-a10b"
    )

    # Initialize task assignment manager
    assignment_manager = TaskAssignmentManager(
        llm_client=llm_client,
        mcp_registry_endpoint="http://127.0.0.1:3031/mcp",
        task_storage=task_storage
    )

    # Get all submitted tasks
    submitted_tasks = task_storage.get_tasks_by_status("submitted")

    if not submitted_tasks:
        print("No submitted tasks found to reprocess.")
        return

    print(f"Found {len(submitted_tasks)} submitted tasks to reprocess\n")

    processed = 0
    failed = 0

    for task in submitted_tasks:
        task_id = task["task_id"]
        assigned_to = task["assigned_to"]
        description = task["description"]

        print(f"Processing task: {task_id}")
        print(f"  Assigned to: {assigned_to}")
        print(f"  Description: {description[:80]}...")

        try:
            # Update status to in_progress
            task_storage.update_task_status(task_id, "in_progress")

            # Call the assignment manager to process the task
            result = assignment_manager.assign_and_forward_task(
                task_id=task_id,
                task_description=description,
                assignee=assigned_to,
                priority=task.get("priority", "medium"),
                deadline=task.get("deadline"),
                metadata={"tool_call": "reprocess", "source": "reprocess_script"}
            )

            print(f"  Result: {result.get('status', 'unknown')}")
            processed += 1

        except Exception as e:
            print(f"  Error: {e}")
            failed += 1

        print()

    print(f"=== Reprocessing Complete ===")
    print(f"Processed: {processed}")
    print(f"Failed: {failed}")

    task_storage.close()


if __name__ == "__main__":
    reprocess_submitted_tasks()
