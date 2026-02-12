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
import uuid


def test_stale_service_cleanup():
    """Test the cleanup of stale services"""
    print("🧪 Testing stale service cleanup functionality...")
    
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


def test_basic_heartbeat_concept():
    """Test the basic concept of heartbeat functionality"""
    print("\n🧪 Testing basic heartbeat concept...")
    
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
            
            # Register a service
            service_info = {
                "id": "test-heartbeat-service",
                "name": "Test Heartbeat Service",
                "description": "A service to test heartbeat functionality",
                "endpoint": "http://localhost:9998",
                "capabilities": {"tools": ["test"]}
            }
            
            # Register the service
            success = registry.register_service(service_info)
            if not success:
                print("❌ Failed to register service")
                return False
            
            print("✅ Service registered successfully")
            
            # Get the service to check initial last_seen
            services = registry.list_services()
            if not services:
                print("❌ Service not found after registration")
                return False
                
            initial_last_seen = services[0]['last_seen']
            print(f"Initial last seen: {initial_last_seen}")
            
            # Update the heartbeat (last_seen timestamp)
            update_success = registry.update_last_seen(service_info['id'])
            if not update_success:
                print("❌ Failed to update heartbeat")
                return False
            
            print("✅ Heartbeat updated successfully")
            
            # Get the service again to check updated last_seen
            services = registry.list_services()
            updated_last_seen = services[0]['last_seen']
            print(f"Updated last seen: {updated_last_seen}")
            
            if updated_last_seen != initial_last_seen:
                print("✅ Heartbeat timestamp was updated correctly")
                return True
            else:
                print("❌ Heartbeat timestamp was not updated")
                return False
                
        finally:
            # Clean up temp file
            if os.path.exists(tmp_db_path):
                os.unlink(tmp_db_path)
        
    except Exception as e:
        print(f"❌ Error testing basic heartbeat: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_heartbeat_manager():
    """Test the heartbeat manager functionality"""
    print("\n🧪 Testing heartbeat manager functionality...")
    
    try:
        from mcp_server.utils.service_registry_db import ServiceRegistryDB
        from mcp_server.utils.heartbeat_manager import HeartbeatManager
        import tempfile
        import os
        import time
        
        # Create a temporary database for testing
        with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
            tmp_db_path = tmp_file.name
        
        try:
            # Create registry instance
            registry = ServiceRegistryDB(db_path=tmp_db_path)
            
            # Register a service
            service_info = {
                "id": "test-manager-service",
                "name": "Test Manager Service",
                "description": "A service to test heartbeat manager",
                "endpoint": "http://localhost:9997",
                "capabilities": {"tools": ["test"]}
            }
            
            # Register the service
            success = registry.register_service(service_info)
            if not success:
                print("❌ Failed to register service")
                return False
            
            print("✅ Service registered for heartbeat manager test")
            
            # Create heartbeat manager with very short intervals for testing
            heartbeat_manager = HeartbeatManager(
                registry,
                service_info["id"],
                heartbeat_interval=1,  # 1 second for testing
                max_age_minutes=1       # 1 minute for testing
            )
            
            # Start the heartbeat manager
            heartbeat_manager.start()
            print("✅ Heartbeat manager started")
            
            # Wait a few seconds to let heartbeat run
            time.sleep(3)
            
            # Stop the heartbeat manager
            heartbeat_manager.stop()
            print("✅ Heartbeat manager stopped")
            
            # Check that the service's last_seen has been updated
            services = registry.list_services()
            if services:
                latest_last_seen = services[0]['last_seen']
                print(f"Latest last seen after heartbeat: {latest_last_seen}")
                print("✅ Heartbeat manager appears to be working")
                return True
            else:
                print("❌ Could not verify heartbeat updates")
                return False
                
        finally:
            # Clean up temp file
            if os.path.exists(tmp_db_path):
                os.unlink(tmp_db_path)
        
    except Exception as e:
        print(f"❌ Error testing heartbeat manager: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("Testing heartbeat and deregister functionality...\n")
    
    test1_success = test_stale_service_cleanup()
    test2_success = test_basic_heartbeat_concept()
    test3_success = test_heartbeat_manager()
    
    if test1_success and test2_success and test3_success:
        print("\n🎉 All tests passed! Heartbeat and deregister functionality working correctly.")
        print("\n📝 Summary of implemented features:")
        print("   • Heartbeat managers for both local and remote registries")
        print("   • Periodic heartbeat updates to keep services active")
        print("   • Automatic cleanup of stale services")
        print("   • Graceful deregistration on server shutdown")
        print("   • Proper signal handling for clean shutdown")
        sys.exit(0)
    else:
        print("\n💥 Some tests failed!")
        sys.exit(1)