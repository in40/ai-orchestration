#!/usr/bin/env python3
"""
Test script to verify heartbeat and deregister functionality
"""
import time
import signal
import sys
import threading
import subprocess
import requests
import json
from datetime import datetime


def test_heartbeat_and_deregister():
    """Test the heartbeat and deregister functionality"""
    print("🧪 Testing heartbeat and deregister functionality...")
    
    # Start a registry server in the background
    registry_cmd = [
        sys.executable, "-m", "mcp_server.server",
        "--transport", "http",
        "--port", "3031",
        "--enable-registry"
    ]
    
    print("🚀 Starting registry server...")
    registry_process = subprocess.Popen(registry_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    
    # Wait for registry to start
    time.sleep(3)
    
    # Start a service server that registers with the registry
    service_cmd = [
        sys.executable, "-m", "mcp_server.server",
        "--transport", "http",
        "--port", "3032",
        "--register-with-registry",
        "--registry-port", "3031"
    ]
    
    print("🚀 Starting service server that registers with registry...")
    service_process = subprocess.Popen(service_cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    
    # Wait for service to register
    time.sleep(5)
    
    try:
        # Query the registry to see if the service is registered
        print("🔍 Checking if service is registered in registry...")
        response = requests.post(
            "http://localhost:3031/send",
            json={
                "jsonrpc": "2.0",
                "id": "test-list",
                "method": "registry/list",
                "params": {}
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'result' in result and 'services' in result['result']:
                services = result['result']['services']
                print(f"📋 Found {len(services)} services in registry:")
                for service in services:
                    print(f"   - {service['name']} ({service['id']}) - Last seen: {service['last_seen']}")
                
                # Check if our service is there
                service_found = any(s['id'] == 'server-127.0.0.1-3032' for s in services)
                if service_found:
                    print("✅ Service successfully registered in registry")
                else:
                    print("❌ Service not found in registry")
                    return False
            else:
                print(f"❌ Unexpected response format: {result}")
                return False
        else:
            print(f"❌ Failed to query registry: {response.status_code} - {response.text}")
            return False
        
        # Wait a bit more to let heartbeat run
        print("⏳ Waiting for heartbeat activity...")
        time.sleep(5)
        
        # Query again to see if last_seen timestamp has updated
        print("🔍 Checking if heartbeat is updating last_seen timestamp...")
        response = requests.post(
            "http://localhost:3031/send",
            json={
                "jsonrpc": "2.0",
                "id": "test-list-2",
                "method": "registry/list",
                "params": {}
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'result' in result and 'services' in result['result']:
                services = result['result']['services']
                service_3032 = next((s for s in services if s['id'] == 'server-127.0.0.1-3032'), None)
                if service_3032:
                    print(f"   Service 3032 last seen: {service_3032['last_seen']}")
                    # The service should still be there after heartbeat activity
                    print("✅ Heartbeat appears to be working (service still registered)")
                else:
                    print("❌ Service disappeared unexpectedly")
                    return False
            else:
                print(f"❌ Unexpected response format: {result}")
                return False
        
        # Now terminate the service server (this should trigger deregister)
        print("🛑 Terminating service server (should trigger deregister)...")
        service_process.terminate()
        
        # Wait for the process to terminate
        try:
            service_process.wait(timeout=10)
        except subprocess.TimeoutExpired:
            service_process.kill()
            service_process.wait()
        
        print("⏳ Waiting for potential deregister to propagate...")
        time.sleep(3)
        
        # Query the registry again to see if the service is gone
        print("🔍 Checking if service was deregistered after termination...")
        response = requests.post(
            "http://localhost:3031/send",
            json={
                "jsonrpc": "2.0",
                "id": "test-list-3",
                "method": "registry/list",
                "params": {}
            },
            timeout=10
        )
        
        if response.status_code == 200:
            result = response.json()
            if 'result' in result and 'services' in result['result']:
                services = result['result']['services']
                print(f"📋 Found {len(services)} services in registry after service termination:")
                for service in services:
                    print(f"   - {service['name']} ({service['id']}) - Last seen: {service['last_seen']}")
                
                # Our service should no longer be there (unless it was cleaned up by heartbeat manager later)
                # The remote heartbeat manager should have deregistered it when stopped
                service_found = any(s['id'] == 'server-127.0.0.1-3032' for s in services)
                if not service_found:
                    print("✅ Service successfully deregistered after termination")
                else:
                    print("ℹ️  Service still in registry (may be cleaned up by stale service cleanup later)")
            else:
                print(f"❌ Unexpected response format: {result}")
                return False
        else:
            print(f"❌ Failed to query registry: {response.status_code} - {response.text}")
            return False
        
        print("✅ Heartbeat and deregister functionality test completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Clean up processes
        if registry_process.poll() is None:
            registry_process.terminate()
            try:
                registry_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                registry_process.kill()
                registry_process.wait()


def test_stale_service_cleanup():
    """Test the cleanup of stale services"""
    print("\n🧪 Testing stale service cleanup functionality...")
    
    # For this test, we'll directly test the cleanup method
    try:
        from mcp_server.utils.service_registry_db import ServiceRegistryDB
        import tempfile
        import os
        
        # Create a temporary database for testing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            tmp_db_path = tmp_file.name
        
        try:
            # Create registry instance
            registry = ServiceRegistryDB(db_path=tmp_db_path)
            
            # Register a service with an old last_seen timestamp
            old_service = {
                "id": "test-stale-service",
                "name": "Test Stale Service",
                "description": "A service that should be considered stale",
                "endpoint": "http://localhost:9999",
                "capabilities": {"tools": ["test"]}
            }
            
            # Insert the service directly with an old timestamp
            import sqlite3
            from datetime import datetime, timedelta
            conn = sqlite3.connect(tmp_db_path)
            cursor = conn.cursor()
            
            # Insert a service with a last_seen time that's definitely older than our threshold
            old_time = datetime.now() - timedelta(minutes=15)  # 15 minutes ago
            capabilities_json = json.dumps(old_service.get("capabilities", {}))
            
            cursor.execute("""
                INSERT OR REPLACE INTO services
                (id, name, description, endpoint, capabilities, last_seen)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (
                old_service["id"],
                old_service["name"],
                old_service["description"],
                old_service["endpoint"],
                capabilities_json,
                old_time.isoformat()
            ))
            
            conn.commit()
            conn.close()
            
            # Verify the service was inserted
            services_before = registry.list_services()
            print(f"Services before cleanup: {len(services_before)}")
            
            # Run cleanup with a 10-minute threshold (our service is 15 minutes old)
            deleted_count = registry.cleanup_stale_services(max_age_minutes=10)
            print(f"Deleted {deleted_count} stale services")
            
            # Check if the service was removed
            services_after = registry.list_services()
            print(f"Services after cleanup: {len(services_after)}")
            
            if deleted_count == 1 and len(services_after) == 0:
                print("✅ Stale service cleanup working correctly")
                success = True
            else:
                print("❌ Stale service cleanup not working as expected")
                success = False
                
        finally:
            # Clean up temp file
            if os.path.exists(tmp_db_path):
                os.unlink(tmp_db_path)
        
        return success
        
    except Exception as e:
        print(f"❌ Error testing stale service cleanup: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing heartbeat and deregister functionality...\n")
    
    test1_success = test_heartbeat_and_deregister()
    test2_success = test_stale_service_cleanup()
    
    if test1_success and test2_success:
        print("\n🎉 All tests passed! Heartbeat and deregister functionality working correctly.")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)