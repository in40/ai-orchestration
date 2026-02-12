#!/usr/bin/env python3
"""
Test script to verify the HTTP/SSE correlation system works with PostgreSQL
"""
import subprocess
import time
import threading
import signal
import sys
import os

def start_registry_server():
    """Start the registry server with PostgreSQL"""
    cmd = [
        sys.executable, "-m", "mcp_server.server",
        "--transport", "http",
        "--port", "3031",
        "--enable-registry",
        "--use-postgres",
        "--postgres-host", "127.0.0.1",
        "--postgres-port", "5432",
        "--postgres-db", "mcp_registry",
        "--postgres-user", "postgres",
        "--postgres-password", "postgres"
    ]
    
    print("🚀 Starting registry server with PostgreSQL...")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    
    # Wait for server to start
    time.sleep(3)
    
    # Monitor the process output
    def monitor_output():
        for line in process.stdout:
            print(f"[REGISTRY] {line.strip()}")
    
    monitor_thread = threading.Thread(target=monitor_output, daemon=True)
    monitor_thread.start()
    
    return process


def start_service_server():
    """Start a service server that registers with the registry"""
    cmd = [
        sys.executable, "-m", "mcp_server.server",
        "--transport", "http",
        "--port", "3032",
        "--register-with-registry",
        "--registry-host", "127.0.0.1",
        "--registry-port", "3031"
    ]
    
    print("🚀 Starting service server that registers with registry...")
    process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, universal_newlines=True)
    
    # Wait for server to start
    time.sleep(3)
    
    # Monitor the process output
    def monitor_output():
        for line in process.stdout:
            print(f"[SERVICE] {line.strip()}")
    
    monitor_thread = threading.Thread(target=monitor_output, daemon=True)
    monitor_thread.start()
    
    return process


def test_registry_query():
    """Test querying the registry"""
    print("\n🔍 Testing registry query...")
    
    # Import and use the updated client
    try:
        from query_registry_client import RegistryQueryClient
        
        client = RegistryQueryClient("http://localhost:3031", timeout=15)
        response = client.query_registry()
        
        if response:
            print("✅ Registry query successful!")
            print(f"Response: {response}")
            return True
        else:
            print("❌ Registry query failed!")
            return False
    except Exception as e:
        print(f"❌ Error during registry query: {e}")
        import traceback
        traceback.print_exc()
        return False


def main():
    print("🧪 Testing HTTP/SSE correlation system with PostgreSQL registry")
    
    registry_process = None
    service_process = None
    
    try:
        # Start registry server
        registry_process = start_registry_server()
        
        # Wait a bit more for registry to fully initialize
        time.sleep(5)
        
        # Start service server
        service_process = start_service_server()
        
        # Wait for service to register
        time.sleep(5)
        
        # Test registry query
        success = test_registry_query()
        
        if success:
            print("\n🎉 PostgreSQL registry correlation test PASSED!")
        else:
            print("\n💥 PostgreSQL registry correlation test FAILED!")
        
        return success
        
    except KeyboardInterrupt:
        print("\n⚠️  Test interrupted by user")
        return False
    except Exception as e:
        print(f"\n💥 Error during test: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        # Cleanup processes
        if registry_process:
            print("🛑 Stopping registry server...")
            registry_process.terminate()
            try:
                registry_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                registry_process.kill()
        
        if service_process:
            print("🛑 Stopping service server...")
            service_process.terminate()
            try:
                service_process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                service_process.kill()


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)