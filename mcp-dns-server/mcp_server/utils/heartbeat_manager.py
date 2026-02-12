"""
Heartbeat Manager for MCP Server Registry
Manages service heartbeats and automatic cleanup of stale services
"""
import threading
import time
from typing import TYPE_CHECKING, Any, Dict
import requests
import json

if TYPE_CHECKING:
    from .service_registry_db import ServiceRegistryDB
    from .postgres_registry_db import PostgresServiceRegistry


class HeartbeatManager:
    """
    Manages service heartbeats and automatic cleanup of stale services.
    
    This class handles:
    1. Periodic heartbeat updates for registered services
    2. Cleanup of stale services that haven't reported in a while
    3. Graceful shutdown of heartbeat processes
    """
    
    def __init__(self, service_registry, service_id: str, heartbeat_interval: int = 30, 
                 max_age_minutes: int = 10):
        """
        Initialize the heartbeat manager.
        
        Args:
            service_registry: The registry instance (SQLite or PostgreSQL)
            service_id: The ID of the service this manager is responsible for
            heartbeat_interval: Interval in seconds between heartbeats
            max_age_minutes: Maximum age in minutes before a service is considered stale
        """
        self.service_registry = service_registry
        self.service_id = service_id
        self.heartbeat_interval = heartbeat_interval
        self.max_age_minutes = max_age_minutes
        self.running = False
        self.heartbeat_thread = None
        self.cleanup_thread = None
        
    def start(self):
        """Start the heartbeat and cleanup processes."""
        if self.running:
            return
            
        self.running = True
        
        # Start heartbeat thread
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        
        # Start cleanup thread
        self.cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self.cleanup_thread.start()
        
        print(f"💓 Heartbeat manager started for service {self.service_id}")
        
    def stop(self):
        """Stop the heartbeat and cleanup processes."""
        self.running = False
        print(f"💔 Heartbeat manager stopped for service {self.service_id}")
        
    def _heartbeat_worker(self):
        """Worker thread that sends periodic heartbeats."""
        while self.running:
            try:
                # Update the last seen timestamp for this service
                success = self.service_registry.update_last_seen(self.service_id)
                if success:
                    print(f"💓 Heartbeat sent for service {self.service_id}")
                else:
                    print(f"⚠️  WARNING: Failed to update heartbeat for service {self.service_id}")
                
                # Sleep for the heartbeat interval
                for _ in range(self.heartbeat_interval):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"❌ Error in heartbeat worker: {e}")
                time.sleep(self.heartbeat_interval)  # Wait before retrying
                
    def _cleanup_worker(self):
        """Worker thread that cleans up stale services."""
        # Wait a bit before starting cleanup to allow other services to register
        time.sleep(30)
        
        while self.running:
            try:
                # Clean up stale services
                deleted_count = self.service_registry.cleanup_stale_services(self.max_age_minutes)
                if deleted_count > 0:
                    print(f"🧹 Cleaned up {deleted_count} stale services")
                else:
                    print(f"✅ No stale services to clean up")
                
                # Sleep for a longer interval between cleanups
                for _ in range(self.max_age_minutes * 60):  # Convert minutes to seconds
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"❌ Error in cleanup worker: {e}")
                time.sleep(self.max_age_minutes * 60)  # Wait before retrying


class RemoteHeartbeatManager:
    """
    Manages heartbeats for services that register with a remote registry.
    
    This class handles:
    1. Periodic heartbeat checks by contacting the remote registry
    2. Automatic deregistration on exit
    """
    
    def __init__(self, registry_url: str, service_info: Dict[str, Any], 
                 heartbeat_interval: int = 30, max_age_minutes: int = 10):
        """
        Initialize the remote heartbeat manager.
        
        Args:
            registry_url: URL of the registry server (e.g., "http://localhost:3031")
            service_info: Information about the service being managed
            heartbeat_interval: Interval in seconds between heartbeats
            max_age_minutes: Maximum age in minutes before a service is considered stale
        """
        self.registry_url = registry_url.rstrip('/')
        self.service_info = service_info
        self.service_id = service_info.get('id')
        self.heartbeat_interval = heartbeat_interval
        self.max_age_minutes = max_age_minutes
        self.running = False
        self.heartbeat_thread = None
        self.session = requests.Session()
        
    def start(self):
        """Start the heartbeat process."""
        if self.running:
            return
            
        self.running = True
        self.heartbeat_thread = threading.Thread(target=self._heartbeat_worker, daemon=True)
        self.heartbeat_thread.start()
        
        print(f"🌐 Remote heartbeat manager started for service {self.service_id}")
        
    def stop(self):
        """Stop the heartbeat process and deregister from the registry."""
        self.running = False
        
        # Try to deregister from the registry
        self._deregister_from_registry()
        
        print(f"📭 Remote heartbeat manager stopped for service {self.service_id}")
        
    def _heartbeat_worker(self):
        """Worker thread that sends periodic heartbeats to the remote registry."""
        while self.running:
            try:
                # Update the service registration (which updates last_seen)
                success = self._update_registration()
                if success:
                    print(f"🌐 Remote heartbeat sent for service {self.service_id}")
                else:
                    print(f"⚠️  WARNING: Failed to update heartbeat for service {self.service_id}")
                
                # Sleep for the heartbeat interval
                for _ in range(self.heartbeat_interval):
                    if not self.running:
                        break
                    time.sleep(1)
            except Exception as e:
                print(f"❌ Error in remote heartbeat worker: {e}")
                time.sleep(self.heartbeat_interval)  # Wait before retrying
                
    def _update_registration(self) -> bool:
        """Update the service registration to refresh the last_seen timestamp."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": f"heartbeat-{self.service_id}-{int(time.time())}",
                "method": "registry/register",
                "params": self.service_info
            }
            
            response = self.session.post(
                f"{self.registry_url}/send",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                result = response.json()
                if result.get("status") == "received":
                    return True
            return False
        except Exception as e:
            print(f"Error updating registration: {e}")
            return False
            
    def _deregister_from_registry(self):
        """Deregister the service from the remote registry."""
        try:
            payload = {
                "jsonrpc": "2.0",
                "id": f"deregister-{self.service_id}-{int(time.time())}",
                "method": "registry/unregister",
                "params": {
                    "id": self.service_id
                }
            }
            
            print(f"📤 Attempting to deregister service {self.service_id} from registry...")
            response = self.session.post(
                f"{self.registry_url}/send",
                json=payload,
                timeout=5
            )
            
            if response.status_code == 200:
                print(f"✅ Successfully deregistered service {self.service_id} from registry")
            else:
                print(f"❌ Failed to deregister service {self.service_id} from registry: {response.status_code}")
        except Exception as e:
            print(f"❌ Error deregistering from registry: {e}")