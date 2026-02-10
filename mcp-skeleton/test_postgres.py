#!/usr/bin/env python3
"""
Test PostgreSQL functionality for MCP Server
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

def test_postgres_connection():
    """Test PostgreSQL connection and table creation"""
    print("🔍 Testing PostgreSQL functionality...")
    
    try:
        from mcp_server.utils.postgres_registry_db import PostgresServiceRegistry
        print("✅ PostgreSQL module imported successfully")
    except ImportError as e:
        print(f"❌ Failed to import PostgreSQL module: {e}")
        return False
    
    try:
        # Try to connect to PostgreSQL
        print("\nAttempting to connect to PostgreSQL...")
        registry = PostgresServiceRegistry(
            host="localhost",
            port=5432,
            database="mcp_registry",
            user="postgres",
            password=""  # Empty password for local postgres
        )
        print("✅ Connected to PostgreSQL successfully")
        
        # Test registering a service
        print("\nTesting service registration...")
        test_service = {
            "id": "test-service-123",
            "name": "Test Service",
            "description": "A test service for verification",
            "endpoint": "http://localhost:8080",
            "capabilities": {
                "tools": ["test_tool"],
                "resources": ["test://resource"],
                "prompts": ["test_prompt"]
            }
        }
        
        success = registry.register_service(test_service)
        if success:
            print("✅ Service registered successfully")
        else:
            print("❌ Service registration failed")
            return False
        
        # Test listing services
        print("\nTesting service listing...")
        services = registry.list_services()
        print(f"✅ Found {len(services)} services in registry")
        
        # Look for our test service
        test_service_found = any(s['id'] == 'test-service-123' for s in services)
        if test_service_found:
            print("✅ Test service found in registry")
        else:
            print("❌ Test service not found in registry")
        
        # Test getting specific service
        print("\nTesting specific service retrieval...")
        service = registry.get_service("test-service-123")
        if service:
            print(f"✅ Retrieved service: {service['name']}")
        else:
            print("❌ Could not retrieve test service")
        
        # Test unregistering service
        print("\nTesting service unregistration...")
        unreg_success = registry.unregister_service("test-service-123")
        if unreg_success:
            print("✅ Service unregistered successfully")
        else:
            print("❌ Service unregistration failed")
        
        print("\n🎉 PostgreSQL functionality test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during PostgreSQL test: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_postgres_connection()
    if not success:
        sys.exit(1)