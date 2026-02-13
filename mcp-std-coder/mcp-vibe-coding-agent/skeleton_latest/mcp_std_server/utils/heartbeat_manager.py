"""
Heartbeat Manager for MCP Server Registry
Manages service health and heartbeat monitoring for registry functionality
"""
import threading
import time
import requests
from typing import Dict, Any, Optional
from .service_registry_db import ServiceRegistryDB
from .postgres_registry_db import PostgresServiceRegistry


class HeartbeatManager:
    """Manages heartbeats for services registered in the local registry.
    
    This class handles:
    1. Periodic heartbeat updates to refresh the last_seen timestamp
    2. Cleanup of stale services that haven't been seen within the max_age_minutes
    """
    
    def __init__(self, service_registry: ServiceRegistryDB, service_id: str, 
                 heartbeat_interval: int = 30, max_age_minutes: int = 10):
        """
        Args:
            service_registry: The registry instance (SQLite or PostgreSQL)
            service_id: The ID of the service to manage heartbeats for
            heartbeat_interval: Interval in seconds between heartbeats (default 30)
            max_age_minutes: Max age in minutes before a service is considered stale (default 10)
        """
        self.service_registry = service_registry
        self.service_id = service_id
        self.heartbeat_interval = heartbeat_interval
        self.max_age_minutes = max_age_minutes
        self.running = False
        self.heartbeat_thread: Optional[threading.Thread] = None
        self.cleanup_thread: Optional[threading.Thread] = None

    def start(self):
        """Start the heartbeat process."""
        if self.running:
            return
            
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        
        self.heartbeat_thread.start()
        self.cleanup_thread.start()
        print(f" heartbeat manager started for service {self.service_id}")

    def stop(self):
        """Stop the heartbeat process."""
        self.running = False
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=2.0)
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            self.cleanup_thread.join(timeout=2.0)
        print(f" heartbeat manager stopped for service {self.service_id}")

    def _heartbeat_worker(self):
        """Worker thread that sends periodic heartbeats to update last_seen."""
        while self.running:
            try:
                # Update the last_seen timestamp for this service
                success = self.service_registry.update_last_seen(self.service_id)
                if success:
                    print(f" heartbeat sent for service {self.service_id}")
                else:
                    print(f"❌ Failed to send heartbeat for service {self.service_id}")
                
                # Sleep for the heartbeat interval
                for _ in range(self.heartbeat_interval):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"❌ Error in heartbeat worker: {e}")
                time.sleep(self.heartbeat_interval)  # Wait before retrying

    def _cleanup_worker(self):
        """Worker thread that periodically cleans up stale services."""
        while self.running:
            try:
                # Clean up stale services
                deleted_count = self.service_registry.cleanup_stale_services(self.max_age_minutes)
                if deleted_count > 0:
                    print(f" cleanup: removed {deleted_count} stale services")
                
                # Sleep for a period before next cleanup (e.g., every 5 minutes)
                for _ in range(300):  # 300 seconds = 5 minutes
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"❌ Error in cleanup worker: {e}")
                time.sleep(300)  # Wait before retrying


class RemoteHeartbeatManager:
    """Manages heartbeats for services that register with a remote registry.
    
    This class handles:
    1. Periodic heartbeat checks by contacting the remote registry
    2. Maintaining registration status with the remote registry
    3. Graceful deregistration when stopping
    """
    
    def __init__(self, registry_url: str, service_info: Dict[str, Any], 
                 heartbeat_interval: int = 30, max_age_minutes: int = 10):
        """
        Args:
            registry_url: URL of the registry server (e.g., "http://localhost:3031")
            service_info: Information about the service being registered
            heartbeat_interval: Interval in seconds between heartbeats (default 30)
            max_age_minutes: Max age in minutes before a service is considered stale (default 10)
        """
        self.registry_url = registry_url.rstrip('/')
        self.service_info = service_info
        self.service_id = service_info['id']
        self.heartbeat_interval = heartbeat_interval
        self.max_age_minutes = max_age_minutes
        self.running = False
        self.heartbeat_thread: Optional[threading.Thread] = None

    def start(self):
        """Start the heartbeat process."""
        if self.running:
            return
            
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        print(f" remote heartbeat manager started for service {self.service_id}")

    def stop(self):
        """Stop the heartbeat process and deregister from the registry."""
        print(f"Stopping remote heartbeat manager for service {self.service_id}...")
        
        self.running = False
        if self.heartbeat_thread and self.heartbeat_thread.is_alive():
            self.heartbeat_thread.join(timeout=2.0)
        
        # Try to deregister from the registry
        self._deregister_from_registry()
        print(f" remote heartbeat manager stopped for service {self.service_id}")

    def _heartbeat_worker(self):
        """Worker thread that sends periodic heartbeats to the remote registry."""
        while self.running:
            try:
                # Send heartbeat by re-registering the service (which updates last_seen)
                payload = {
                    "jsonrpc": "2.0",
                    "id": f"heartbeat-{int(time.time())}",
                    "method": "registry/register",
                    "params": self.service_info
                }
                
                response = requests.post(
                    f"{self.registry_url}/mcp",  # Use the standard /mcp endpoint
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                if response.status_code == 200:
                    print(f" heartbeat sent to registry for service {self.service_id}")
                else:
                    print(f"❌ Failed to send heartbeat to registry for service {self.service_id}: {response.status_code}")
                
                # Sleep for the heartbeat interval
                for _ in range(self.heartbeat_interval):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"❌ Error in remote heartbeat worker: {e}")
                time.sleep(self.heartbeat_interval)  # Wait before retrying

    def _deregister_from_registry(self):
        """Deregister the service from the remote registry."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": f"deregister-{int(time.time())}",
                "method": "registry/unregister",
                "params": {
                    "id": self.service_id
                }
            }
            
            print(f"📤 Attempting to deregister service {self.service_id} from registry...")
            response = requests.post(
                f"{self.registry_url}/mcp",  # Use the standard /mcp endpoint
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully deregistered service {self.service_id} from registry")
            else:
                print(f"❌ Failed to deregister service {self.service_id} from registry: {response.status_code}")
        except Exception as e:
            print(f"❌ Error deregistering from registry: {e}")