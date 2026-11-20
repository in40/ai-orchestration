#!/usr/bin/env python3
"""
Test script to check the server configuration and task storage
"""
from it_lead_mcp_server.server import ItLeadMcpServer

print("Creating server with PostgreSQL...")
try:
    server = ItLeadMcpServer(
        transport_type='streamable-http',
        port=3062,  # Use different port to avoid conflict
        register_with_registry=False,  # Don't register to avoid conflicts
        use_postgres=True,  # Use PostgreSQL
        postgres_host='localhost',
        postgres_port=5432,
        postgres_database='mcp_registry',
        postgres_user='postgres',
        postgres_password='postgres',
        llm_provider_url='http://asus-tus:1234/v1/chat/completions',
        llm_model='qwen3.5-35b-a3b@q5_k_xl'
    )

    print(f"Server created successfully")
    print(f"Task storage: {server.server_handlers.task_storage}")
    print(f"Task storage type: {type(server.server_handlers.task_storage)}")

    if server.server_handlers.task_storage:
        print(f"Database: {server.server_handlers.task_storage.database}")
        print(f"Host: {server.server_handlers.task_storage.host}")
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
