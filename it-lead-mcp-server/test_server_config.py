#!/usr/bin/env python3
"""
Test script to check the server configuration and task storage
"""
from it_lead_mcp_server.server import ItLeadMcpServer

print("Creating server with default parameters (should use SQLite)...")
try:
    server = ItLeadMcpServer(
        transport_type='streamable-http',
        port=3062,  # Use different port to avoid conflict
        register_with_registry=False,  # Don't register to avoid conflicts
        use_postgres=False,  # Explicitly set to False to use SQLite
        llm_provider_url='http://asus-tus:1234/v1/chat/completions',
        llm_model='qwen3.5-35b-a3b@q5_k_xl'
    )
    
    print(f"Server created successfully")
    print(f"Task storage: {server.server_handlers.task_storage}")
    print(f"Task storage type: {type(server.server_handlers.task_storage)}")
    
    if server.server_handlers.task_storage:
        print(f"Using SQLite: {server.server_handlers.task_storage.use_sqlite}")
        print(f"Database file: {server.server_handlers.task_storage.database}")
    else:
        print("Task storage is None - tasks will not be stored!")
        
    # Test storing a task
    if server.server_handlers.task_storage:
        success = server.server_handlers.task_storage.store_received_task(
            task_id="test_task_1",
            title="Test Task",
            description="This is a test task to verify storage",
            assigned_to="Test Agent",
            priority="medium"
        )
        print(f"Task storage test: {'SUCCESS' if success else 'FAILED'}")
        
        # Try to retrieve the task
        task = server.server_handlers.task_storage.get_task("test_task_1")
        print(f"Task retrieval test: {'SUCCESS' if task else 'FAILED'}")
        if task:
            print(f"Retrieved task: {task['title']} - {task['status']}")
    
    print("Test completed.")
    
except Exception as e:
    print(f"Error creating server: {e}")
    import traceback
    traceback.print_exc()