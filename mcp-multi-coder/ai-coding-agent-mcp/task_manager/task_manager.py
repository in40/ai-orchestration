import asyncio
import uuid
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class TaskStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class Task(BaseModel):
    id: str
    status: TaskStatus
    task_description: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    result: Optional[str] = None
    error: Optional[str] = None
    created_at: float
    updated_at: float


class TaskManager:
    """
    Task management service with async queue and concurrent workers.

    This service manages coding tasks submitted to the AI coding agent,
    processing them asynchronously with configurable concurrency.
    """

    def __init__(self, num_workers: int = 2, lmstudio_client=None, prompt_manager=None):
        # In-memory store for all tasks
        self.tasks: Dict[str, Task] = {}

        # Async queue for pending tasks
        self.queue: asyncio.Queue = asyncio.Queue()

        # Lock to protect shared dictionary access
        self.lock = asyncio.Lock()

        # Number of concurrent workers
        self.num_workers = num_workers

        # Set of cancelled tasks
        self.cancelled_tasks = set()

        # Track worker tasks
        self.worker_tasks = []

        # Dependencies
        self.lmstudio_client = lmstudio_client
        self.prompt_manager = prompt_manager
        
    async def start_workers(self):
        """Start the worker coroutines."""
        logger.info(f"Starting {self.num_workers} worker(s)")
        for i in range(self.num_workers):
            worker_task = asyncio.create_task(self._worker_loop(i))
            self.worker_tasks.append(worker_task)
    
    async def stop_workers(self):
        """Stop all worker coroutines."""
        logger.info("Stopping workers...")
        for task in self.worker_tasks:
            task.cancel()
        
        # Wait for all workers to finish
        if self.worker_tasks:
            await asyncio.gather(*self.worker_tasks, return_exceptions=True)
    
    async def _worker_loop(self, worker_id: int):
        """
        Background worker loop that processes tasks from the queue.
        
        Args:
            worker_id: Unique identifier for this worker
        """
        logger.info(f"Worker {worker_id} started")
        
        while True:
            try:
                # Get a task ID from the queue
                task_id = await self.queue.get()
                
                # Check if task was cancelled before processing
                if task_id in self.cancelled_tasks:
                    logger.info(f"Task {task_id} was cancelled before processing")
                    self.queue.task_done()
                    continue
                
                # Fetch task record from store (under lock)
                async with self.lock:
                    if task_id not in self.tasks:
                        logger.warning(f"Task {task_id} not found in store")
                        self.queue.task_done()
                        continue
                    
                    task = self.tasks[task_id]
                    
                    # Double-check if task was cancelled
                    if task.status == TaskStatus.CANCELLED or task_id in self.cancelled_tasks:
                        logger.info(f"Task {task_id} was cancelled during processing check")
                        self.queue.task_done()
                        continue
                
                # Update status to processing
                await self.update_task(task_id, status=TaskStatus.PROCESSING)
                
                try:
                    # Process the task (this would typically call the LM Studio client)
                    result = await self._process_task(task)
                    
                    # Update task with successful result
                    await self.update_task(
                        task_id, 
                        status=TaskStatus.COMPLETED, 
                        result=result
                    )
                    
                    logger.info(f"Task {task_id} completed successfully")
                    
                except Exception as e:
                    # Update task with error
                    error_msg = str(e)
                    logger.error(f"Task {task_id} failed: {error_msg}")
                    
                    await self.update_task(
                        task_id, 
                        status=TaskStatus.FAILED, 
                        error=error_msg
                    )
                
                # Mark queue task as done
                self.queue.task_done()
                
            except asyncio.CancelledError:
                logger.info(f"Worker {worker_id} was cancelled")
                break
            except Exception as e:
                logger.error(f"Worker {worker_id} encountered unexpected error: {str(e)}")
                # Continue the loop despite errors
    
    async def _process_task(self, task: Task) -> str:
        """
        Process a single task.

        This calls the LM Studio client to generate code or explanations
        based on the task description.

        Args:
            task: The task to process

        Returns:
            Result of the task processing
        """
        # Use injected dependencies if available, otherwise create new instances
        if self.lmstudio_client:
            lmstudio_client = self.lmstudio_client
        else:
            from ..lmstudio_client.lmstudio_client import LMStudioClient
            lmstudio_client = LMStudioClient()

        if self.prompt_manager:
            prompt_manager = self.prompt_manager
        else:
            from ..prompt_manager import PromptManager
            prompt_manager = PromptManager()

        try:
            # Get the language and max_tokens from parameters
            language = task.parameters.get('language', 'python')
            max_tokens = task.parameters.get('max_tokens', 512)

            # Try to render the coding task prompt template
            try:
                prompt = prompt_manager.render_prompt(
                    "coding_task",
                    {
                        "task_description": task.task_description,
                        "language": language
                    }
                )
            except Exception:
                # If template doesn't exist, use a default prompt
                prompt = f"Write code in {language} to: {task.task_description}\n\nProvide a complete, working solution with appropriate comments."

            # Call the LM Studio client to generate the response
            result = await lmstudio_client.generate(
                prompt=prompt,
                max_tokens=max_tokens,
                temperature=0.7
            )

            return result

        except Exception as e:
            logger.error(f"Error processing task {task.id}: {str(e)}")
            raise e
        finally:
            # Only close the LM Studio client if we created it ourselves
            # Don't close the injected client as the server owns it
            if not self.lmstudio_client and lmstudio_client:
                try:
                    await lmstudio_client.close()
                except RuntimeError as e:
                    if "Event loop is closed" in str(e):
                        # The event loop is already closed, which is fine
                        logger.debug(f"Event loop already closed when trying to close LM Studio client: {e}")
                    else:
                        raise
    
    async def create_task(self, task_description: str, parameters: Dict[str, Any] = None) -> str:
        """
        Create a new task and add it to the queue.
        
        Args:
            task_description: Description of the coding task
            parameters: Additional parameters for the task
            
        Returns:
            Task ID
        """
        if parameters is None:
            parameters = {}
        
        task_id = str(uuid.uuid4())
        timestamp = time.time()
        
        task = Task(
            id=task_id,
            status=TaskStatus.PENDING,
            task_description=task_description,
            parameters=parameters,
            created_at=timestamp,
            updated_at=timestamp
        )
        
        # Store the task
        async with self.lock:
            self.tasks[task_id] = task
        
        # Add to queue for processing
        await self.queue.put(task_id)
        
        logger.info(f"Created task {task_id}: {task_description}")
        
        return task_id
    
    async def get_task(self, task_id: str) -> Optional[Task]:
        """
        Retrieve a task by ID.
        
        Args:
            task_id: ID of the task to retrieve
            
        Returns:
            Task object or None if not found
        """
        async with self.lock:
            return self.tasks.get(task_id)
    
    async def list_tasks(self, status_filter: Optional[TaskStatus] = None) -> List[Task]:
        """
        List all tasks, optionally filtered by status.
        
        Args:
            status_filter: Optional status to filter by
            
        Returns:
            List of task objects
        """
        async with self.lock:
            if status_filter:
                return [task for task in self.tasks.values() 
                       if task.status == status_filter]
            else:
                return list(self.tasks.values())
    
    async def update_task(
        self, 
        task_id: str, 
        status: Optional[TaskStatus] = None, 
        result: Optional[str] = None, 
        error: Optional[str] = None
    ):
        """
        Update a task's status and/or result/error.
        
        Args:
            task_id: ID of the task to update
            status: New status (if provided)
            result: New result (if provided)
            error: New error message (if provided)
        """
        async with self.lock:
            if task_id not in self.tasks:
                raise ValueError(f"Task {task_id} not found")
            
            task = self.tasks[task_id]
            
            # Update fields if provided
            if status is not None:
                task.status = status
            if result is not None:
                task.result = result
            if error is not None:
                task.error = error
            
            # Update timestamp
            task.updated_at = time.time()
    
    async def cancel_task(self, task_id: str) -> bool:
        """
        Cancel a pending task.
        
        Args:
            task_id: ID of the task to cancel
            
        Returns:
            True if task was successfully cancelled, False otherwise
        """
        async with self.lock:
            if task_id not in self.tasks:
                return False
            
            task = self.tasks[task_id]
            
            # Only allow cancellation of pending tasks
            if task.status != TaskStatus.PENDING:
                return False
            
            # Mark as cancelled
            task.status = TaskStatus.CANCELLED
            task.updated_at = time.time()
            
            # Add to cancelled set to prevent processing
            self.cancelled_tasks.add(task_id)
            
            logger.info(f"Cancelled task {task_id}")
            
            return True
    
    def get_queue_info(self) -> Dict[str, Any]:
        """
        Get information about the task queue.
        
        Returns:
            Dictionary with queue statistics
        """
        return {
            "pending_tasks": self.queue.qsize(),
            "total_tasks": len(self.tasks),
            "concurrent_workers": self.num_workers,
            "cancelled_tasks_count": len(self.cancelled_tasks)
        }


# Example usage
async def main():
    # Create task manager with 3 workers
    task_manager = TaskManager(num_workers=3)
    
    # Start workers
    await task_manager.start_workers()
    
    # Create some sample tasks
    task_ids = []
    for i in range(5):
        task_id = await task_manager.create_task(
            f"Sample coding task #{i+1}",
            {"language": "python", "difficulty": "medium"}
        )
        task_ids.append(task_id)
        print(f"Created task: {task_id}")
    
    # Wait a bit for processing
    await asyncio.sleep(2)
    
    # Check task statuses
    for task_id in task_ids:
        task = await task_manager.get_task(task_id)
        print(f"Task {task_id} status: {task.status}")
    
    # Get queue info
    info = task_manager.get_queue_info()
    print("Queue info:", info)
    
    # Stop workers
    await task_manager.stop_workers()

if __name__ == "__main__":
    asyncio.run(main())