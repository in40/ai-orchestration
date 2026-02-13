"""
Heartbeat Manager for MCP Server
Manages service heartbeat and health monitoring
"""
import threading
import time
from typing import Dict, Any
from ..utils.service_registry_db import ServiceRegistryDB


class HeartbeatManager:
    """Manages local service heartbeat and health monitoring for registry server"""

    def __init__(self, service_registry, service_id: str, heartbeat_interval: int = 30, max_age_minutes: int = 10):
        self.service_registry = service_registry
        self.service_id = service_id
        self.heartbeat_interval = heartbeat_interval  # seconds
        self.max_age = max_age_minutes * 60  # seconds
        self.running = False
        self.heartbeat_thread = None

    def start(self):
        """Start the heartbeat manager"""
        if not self.running:
            self.running = True
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()

    def stop(self):
        """Stop the heartbeat manager"""
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2.0)  # Wait up to 2 seconds for thread to finish

    def _heartbeat_loop(self):
        """Main heartbeat loop"""
        while self.running:
            try:
                # Update the last_seen timestamp for this service
                self.service_registry.update_last_seen(self.service_id)
                
                # Clean up stale services
                removed_count = self.service_registry.cleanup_stale_services(self.max_age // 60)
                if removed_count > 0:
                    print(f"HeartbeatManager: Removed {removed_count} stale services")
                
                # Sleep for the heartbeat interval
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                print(f"HeartbeatManager error: {e}")
                time.sleep(min(self.heartbeat_interval, 5))  # Brief pause before retrying


class RemoteHeartbeatManager:
    """Manages heartbeat for services registered with a remote registry"""

    def __init__(self, registry_url: str, service_info: Dict[str, Any], 
                 heartbeat_interval: int = 30, max_age_minutes: int = 10):
        self.registry_url = registry_url
        self.service_info = service_info
        self.heartbeat_interval = heartbeat_interval  # seconds
        self.max_age = max_age_minutes * 60  # seconds
        self.running = False
        self.heartbeat_thread = None

    def start(self):
        """Start the remote heartbeat manager"""
        if not self.running:
            self.running = True
            self.heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
            self.heartbeat_thread.start()

    def stop(self):
        """Stop the remote heartbeat manager"""
        self.running = False
        if self.heartbeat_thread:
            self.heartbeat_thread.join(timeout=2.0)  # Wait up to 2 seconds for thread to finish

    def _heartbeat_loop(self):
        """Main remote heartbeat loop"""
        import requests
        import json
        
        while self.running:
            try:
                # Re-register the service to update its last_seen timestamp
                import time
                payload = {
                    "jsonrpc": "2.0",
                    "id": f"heartbeat-{int(time.time())}",
                    "method": "registry/register",
                    "params": self.service_info
                }
                
                response = requests.post(f"{self.registry_url}/mcp", json=payload)
                
                if response.status_code == 200:
                    print(f"RemoteHeartbeatManager: Successfully updated registration for {self.service_info['name']}")
                else:
                    print(f"RemoteHeartbeatManager: Failed to update registration: {response.status_code} - {response.text}")
                
                # Sleep for the heartbeat interval
                time.sleep(self.heartbeat_interval)
            except Exception as e:
                print(f"RemoteHeartbeatManager error: {e}")
                time.sleep(min(self.heartbeat_interval, 5))  # Brief pause before retrying