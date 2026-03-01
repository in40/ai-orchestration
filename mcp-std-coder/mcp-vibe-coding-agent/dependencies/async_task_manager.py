"""
Async Task Management System for Vibe Coding MCP Server
Implements the call-now-fetch-later pattern for long-running LLM operations
"""
import asyncio
import threading
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, Optional, Any, List
from dataclasses import dataclass, asdict
from concurrent.futures import ThreadPoolExecutor
import requests


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


class AsyncTaskManager:
    def __init__(self, cleanup_interval: int = 300):  # 5 minutes
        self.tasks: Dict[str, AsyncTask] = {}
        self.executor = ThreadPoolExecutor(max_workers=10)
        self.cleanup_interval = cleanup_interval
        self._start_cleanup_task()
        
    def _start_cleanup_task(self):
        """Start background cleanup of expired tasks"""
        def cleanup_loop():
            while True:
                time.sleep(self.cleanup_interval)
                self._cleanup_expired_tasks()
        
        cleanup_thread = threading.Thread(target=cleanup_loop, daemon=True)
        cleanup_thread.start()
    
    def _cleanup_expired_tasks(self):
        """Remove expired tasks from memory"""
        current_time = time.time()
        expired_task_ids = [
            task_id for task_id, task in self.tasks.items()
            if task.expiresAt and task.expiresAt < current_time
        ]
        
        for task_id in expired_task_ids:
            del self.tasks[task_id]
    
    def create_task(self, input_data: Dict[str, Any]) -> str:
        """Create a new async task"""
        task_id = str(uuid.uuid4())
        task = AsyncTask(
            taskId=task_id,
            status=TaskStatus.SUBMITTED,
            input=input_data,
            createdAt=time.time(),
            updatedAt=time.time(),
            expiresAt=time.time() + (60 * 60 * 24)  # Expires in 24 hours
        )
        self.tasks[task_id] = task
        return task_id
    
    def get_task(self, task_id: str) -> Optional[AsyncTask]:
        """Get task by ID"""
        return self.tasks.get(task_id)
    
    def update_task_status(self, task_id: str, status: TaskStatus, progress: int = None):
        """Update task status"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = status
            task.updatedAt = time.time()
            if progress is not None:
                task.progress = progress
    
    def update_task_result(self, task_id: str, result: Dict[str, Any]):
        """Update task with result"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.COMPLETED
            task.progress = 100  # Set progress to 100 for completed tasks
            task.result = result
            task.updatedAt = time.time()
            # Extend expiration for completed tasks
            task.expiresAt = time.time() + (60 * 60 * 24 * 7)  # Keep results for 7 days
    
    def update_task_error(self, task_id: str, error: str):
        """Update task with error"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            task.status = TaskStatus.FAILED
            task.error = error
            task.updatedAt = time.time()
    
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a task"""
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if task.status in [TaskStatus.SUBMITTED, TaskStatus.WORKING]:
                task.status = TaskStatus.CANCELLED
                task.updatedAt = time.time()
                return True
        return False
    
    def list_tasks(self, status_filter: Optional[str] = None, limit: int = 100) -> List[AsyncTask]:
        """List tasks with optional filtering"""
        tasks = list(self.tasks.values())
        
        if status_filter:
            status_enum = TaskStatus(status_filter.lower())
            tasks = [task for task in tasks if task.status == status_enum]
        
        # Sort by creation time, newest first
        tasks.sort(key=lambda x: x.createdAt, reverse=True)
        return tasks[:limit]
    
    def submit_for_processing(self, task_id: str, llm_call_func):
        """Submit task for background processing"""
        def process_task():
            if task_id not in self.tasks:
                return
            
            task = self.tasks[task_id]
            self.update_task_status(task_id, TaskStatus.WORKING, 10)
            
            try:
                # Call the LLM function with the input data
                result = llm_call_func(task.input)
                self.update_task_result(task_id, result)
            except Exception as e:
                self.update_task_error(task_id, str(e))
        
        # Submit to thread pool for background processing
        self.executor.submit(process_task)


# Global task manager instance
task_manager = AsyncTaskManager()