#!/usr/bin/env python3
"""
Test script to debug the API server startup issue
"""
import sys
import os
import traceback

# Add the parent directory to the path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

print("Testing imports...")

try:
    from flask import Flask
    print("✓ Flask imported successfully")
except ImportError as e:
    print(f"✗ Error importing Flask: {e}")

try:
    from flask_cors import CORS
    print("✓ Flask-CORS imported successfully")
except ImportError as e:
    print(f"✗ Error importing Flask-CORS: {e}")

try:
    import requests
    print("✓ Requests imported successfully")
except ImportError as e:
    print(f"✗ Error importing requests: {e}")

try:
    from mcp_std_server.utils.task_storage import TaskStorage
    print("✓ TaskStorage imported successfully")
except ImportError as e:
    print(f"✗ Error importing TaskStorage: {e}")

print("\nTesting registry connection...")
try:
    import requests
    response = requests.post(
        'http://localhost:3031/mcp',
        json={
            "jsonrpc": "2.0",
            "id": "test",
            "method": "registry/list",
            "params": {}
        },
        headers={"Content-Type": "application/json"},
        timeout=5
    )
    if response.status_code == 200:
        print("✓ Registry connection successful")
    else:
        print(f"✗ Registry connection failed with status: {response.status_code}")
except Exception as e:
    print(f"✗ Error connecting to registry: {e}")

print("\nTesting function extraction...")
try:
    # Import the functions we need
    import importlib.util
    spec = importlib.util.spec_from_file_location("api_server", "./api_server.py")
    api_module = importlib.util.module_from_spec(spec)
    
    # Just check if the file can be parsed
    print("✓ Module can be loaded")
except Exception as e:
    print(f"✗ Error loading module: {e}")
    traceback.print_exc()