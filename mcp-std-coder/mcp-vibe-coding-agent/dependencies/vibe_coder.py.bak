import httpx
from pydantic import BaseModel, Field
from typing import Optional
from config import settings


class CodingTask(BaseModel):
    task_description: str = Field(..., description="What code should be generated?")
    language: Optional[str] = Field("python", description="Programming language")
    vibe_level: Optional[int] = Field(5, description="Creativity level 1-10")
    style_guide: Optional[str] = Field("", description="Additional style hints")


import requests

def call_llm_sync(prompt: str, vibe: int, server_handlers=None) -> str:
    """Call LM Studio's OpenAI-compatible endpoint using synchronous requests."""
    # Get the system prompt from the server handlers if available, otherwise use default
    system_prompt = "You are a vibe coding assistant. Generate clean, working code with brief explanations."
    
    if server_handlers:
        # Look for the system prompt in the available prompts
        for p in server_handlers.prompts:
            if p.get("name") == "vibe_coding_system_prompt":
                # Use the prompt content if arguments are provided, otherwise use the content directly
                if "content" in p:
                    system_prompt = p["content"]
                break
    
    response = requests.post(
        f"{settings.llm_base_url}/chat/completions",
        json={
            "model": settings.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": prompt}
            ],
            "temperature": vibe / 10,  # 0.1 to 1.0
            "max_tokens": 2048
        },
        timeout=60
    )
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


def create_vibe_code_prompt(arguments: dict) -> str:
    """Create the prompt for the LLM based on arguments."""
    task_desc = arguments.get("task_description", "")
    language = arguments.get("language", "python")
    vibe_level = arguments.get("vibe_level", 5)
    style_guide = arguments.get("style_guide", "")
    
    prompt = f"""Generate code for the following task:
Task: {task_desc}
Language: {language}
Vibe level (creativity): {vibe_level}/10
Style guide: {style_guide if style_guide else 'No specific style'}

Please output the code in a markdown code block, and include a short 'vibe check' comment."""
    
    return prompt


import asyncio
from concurrent.futures import ThreadPoolExecutor
import threading

# Global thread pool executor for async operations
executor = ThreadPoolExecutor(max_workers=10)

def register_vibe_coding_tool(server_handlers):
    """Register the vibe coding tools with the server handlers."""
    # Import the task manager (could be in-memory or PostgreSQL-based)
    from .postgres_task_manager import create_task_manager, TaskStatus
    
    # Create task manager based on server configuration
    # Check if PostgreSQL is configured for task storage (separate from registry)
    # Prioritize server_handlers postgres_config if available, otherwise use settings
    try:
        # First check if server_handlers has postgres_config
        server_postgres_config = getattr(server_handlers, 'postgres_config', {})
        if server_postgres_config and server_postgres_config.get('host'):
            # Use server's postgres configuration
            task_postgres_config = server_postgres_config
            use_postgres = True
        else:
            # Fall back to settings configuration
            from ..config import settings
            task_postgres_config = {
                "host": settings.postgres_host,
                "port": settings.postgres_port,
                "database": settings.postgres_db,
                "user": settings.postgres_user,
                "password": settings.postgres_password
            }
            # Use PostgreSQL for tasks if it's configured and available
            use_postgres = bool(settings.postgres_password and settings.postgres_password.strip())
    except Exception as e:
        # If config is not available, use in-memory storage
        print(f"Error configuring PostgreSQL task storage: {e}")
        task_postgres_config = {}
        use_postgres = False
    
    task_manager = create_task_manager(use_postgres=use_postgres, **task_postgres_config)
    
    # Define the synchronous vibe_code tool
    vibe_code_tool = {
        "name": "vibe_code",
        "description": "Accept a natural language coding task, invoke the local LLM (LM Studio), and return the generated code with any explanation. This tool implements the 'vibe coding' methodology.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {"type": "string", "description": "What code should be generated?"},
                "language": {"type": "string", "description": "Programming language", "default": "python"},
                "vibe_level": {"type": "integer", "description": "Creativity level 1-10", "default": 5},
                "style_guide": {"type": "string", "description": "Additional style hints", "default": ""}
            },
            "required": ["task_description"]
        }
    }
    
    # Define the asynchronous vibe_code tool
    vibe_code_async_tool = {
        "name": "vibe_code_async",
        "description": "Submit a natural language coding task to be processed asynchronously. Returns a task ID for tracking progress. Use tasks/get to check status and tasks/result to retrieve the generated code.",
        "inputSchema": {
            "type": "object",
            "properties": {
                "task_description": {"type": "string", "description": "What code should be generated?"},
                "language": {"type": "string", "description": "Programming language", "default": "python"},
                "vibe_level": {"type": "integer", "description": "Creativity level 1-10", "default": 5},
                "style_guide": {"type": "string", "description": "Additional style hints", "default": ""}
            },
            "required": ["task_description"]
        }
    }
    
    # Define the tasks/list tool
    tasks_list_tool = {
        "name": "tasks/list",
        "description": "List all async tasks with optional status filtering",
        "inputSchema": {
            "type": "object",
            "properties": {
                "status": {"type": "string", "description": "Filter tasks by status (submitted, working, completed, failed, cancelled)"},
                "limit": {"type": "integer", "description": "Maximum number of tasks to return", "default": 100}
            }
        }
    }
    
    # Define the tasks/get tool
    tasks_get_tool = {
        "name": "tasks/get",
        "description": "Get the status of a specific async task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "taskId": {"type": "string", "description": "The ID of the task to get status for"}
            },
            "required": ["taskId"]
        }
    }
    
    # Define the tasks/result tool
    tasks_result_tool = {
        "name": "tasks/result",
        "description": "Retrieve the result of a completed async task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "taskId": {"type": "string", "description": "The ID of the task to get result for"}
            },
            "required": ["taskId"]
        }
    }
    
    # Define the tasks/cancel tool
    tasks_cancel_tool = {
        "name": "tasks/cancel",
        "description": "Cancel a running async task",
        "inputSchema": {
            "type": "object",
            "properties": {
                "taskId": {"type": "string", "description": "The ID of the task to cancel"}
            },
            "required": ["taskId"]
        }
    }
    
    # Replace the example tools with the vibe coding tools
    server_handlers.tools = [
        vibe_code_tool,
        vibe_code_async_tool,
        tasks_list_tool,
        tasks_get_tool,
        tasks_result_tool,
        tasks_cancel_tool
    ]
    
    # Notify that tools have changed
    if hasattr(server_handlers, 'notification_manager') and server_handlers.notification_manager:
        server_handlers.notification_manager.mark_tools_changed()
    
    # Add the tool execution logic to the _execute_tool method by extending it
    original_execute_tool = server_handlers._execute_tool
    
    def enhanced_execute_tool(tool, arguments):
        if tool["name"] == "vibe_code":
            # Construct prompt with style and vibe
            prompt = create_vibe_code_prompt(arguments)
            
            try:
                # Call the synchronous LLM function
                llm_response = call_llm_sync(prompt, arguments.get("vibe_level", 5), server_handlers)
                return {"result": llm_response}
            except Exception as e:
                return {"error": f"Failed to call LLM: {str(e)}"}
        
        elif tool["name"] == "vibe_code_async":
            # Create an async task
            try:
                task_id = task_manager.create_task(arguments)
                
                # Submit for background processing
                def llm_call_wrapper(input_args):
                    prompt = create_vibe_code_prompt(input_args)
                    return {"result": call_llm_sync(prompt, input_args.get("vibe_level", 5), server_handlers)}

                task_manager.submit_for_processing(task_id, llm_call_wrapper)
                
                return {"taskId": task_id, "status": "submitted"}
            except Exception as e:
                return {"error": f"Failed to create async task: {str(e)}"}
        
        elif tool["name"] == "tasks/list":
            # List tasks
            try:
                status_filter = arguments.get("status")
                limit = arguments.get("limit", 100)
                
                tasks = task_manager.list_tasks(status_filter=status_filter, limit=limit)
                result_tasks = []
                
                for task in tasks:
                    result_tasks.append({
                        "taskId": task.taskId,
                        "status": task.status.value,
                        "createdAt": task.createdAt,
                        "updatedAt": task.updatedAt,
                        "progress": task.progress,
                        "input": task.input
                    })
                
                return {"tasks": result_tasks}
            except Exception as e:
                return {"error": f"Failed to list tasks: {str(e)}"}
        
        elif tool["name"] == "tasks/get":
            # Get specific task status
            try:
                task_id = arguments.get("taskId")
                task = task_manager.get_task(task_id)
                
                if not task:
                    return {"error": "Task not found"}
                
                return {
                    "taskId": task.taskId,
                    "status": task.status.value,
                    "createdAt": task.createdAt,
                    "updatedAt": task.updatedAt,
                    "progress": task.progress,
                    "input": task.input
                }
            except Exception as e:
                return {"error": f"Failed to get task: {str(e)}"}
        
        elif tool["name"] == "tasks/result":
            # Get task result
            try:
                task_id = arguments.get("taskId")
                task = task_manager.get_task(task_id)
                
                if not task:
                    return {"error": "Task not found"}
                
                if task.status != TaskStatus.COMPLETED:
                    return {"error": f"Task is not completed. Current status: {task.status.value}"}
                
                return {"result": task.result}
            except Exception as e:
                return {"error": f"Failed to get task result: {str(e)}"}
        
        elif tool["name"] == "tasks/cancel":
            # Cancel a task
            try:
                task_id = arguments.get("taskId")
                success = task_manager.cancel_task(task_id)
                
                if success:
                    return {"status": "cancelled", "taskId": task_id}
                else:
                    return {"error": "Task not found or could not be cancelled"}
            except Exception as e:
                return {"error": f"Failed to cancel task: {str(e)}"}
        
        else:
            # Call the original method for other tools
            return original_execute_tool(tool, arguments)
    
    server_handlers._execute_tool = enhanced_execute_tool