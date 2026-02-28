"""
Document Store Registry Integration
Integrates Document Store MCP Server with base project service registry (port 3031)
"""
import sys
import os
import threading
import time
from datetime import datetime

# Add mcp-std-skeleton to path for ServiceRegistryDB
MCP_STD_SKELETON = "/root/qwen/base/mcp-std-coder/mcp-std-skeleton"
sys.path.insert(0, MCP_STD_SKELETON)

try:
    from mcp_std_server.utils.service_registry_db import ServiceRegistryDB
    REGISTRY_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  Warning: Could not import service registry DB: {e}")
    REGISTRY_AVAILABLE = False


class DocumentStoreRegistryIntegration:
    """Integrates Document Store with base project service registry"""

    def __init__(self, host: str = "127.0.0.1", port: int = 3031):
        self.host = host
        self.port = port
        self.db_path = f"/root/qwen/base/mcp-std-skeleton/mcp_registry_{port}.db"
        self.registry_db = None
        self.service_id = None
        self.heartbeat_thread = None
        self.running = False

        if REGISTRY_AVAILABLE:
            self.registry_db = ServiceRegistryDB(self.db_path)
    
    def register(
        self,
        service_host: str = "127.0.0.1",
        service_port: int = 3070,
        ttl_seconds: int = 60
    ) -> bool:
        """Register Document Store with base project registry."""
        
        if not REGISTRY_AVAILABLE or not self.registry_db:
            print("⚠️  Registry DB not available, skipping registration")
            return False
        
        try:
            # Create service ID in format: document-store-{host}:{port}
            self.service_id = f"document-store-{service_host}:{service_port}"

            # Prepare service info with all required fields
            service_info = {
                "id": self.service_id,
                "name": "Document Store MCP Server",
                "description": "Store and retrieve documents from ingestion jobs. Supports 8 tools: list_ingestion_jobs, list_documents, get_document, get_document_batch, get_document_metadata, search_documents, delete_job_documents, store_document.",
                "endpoint": f"http://{service_host}:{service_port}/mcp",
                "capabilities": {
                    "tools": [
                        "list_ingestion_jobs",
                        "list_documents", 
                        "get_document",
                        "get_document_batch",
                        "get_document_metadata",
                        "search_documents",
                        "delete_job_documents",
                        "store_document"
                    ],
                    "resources": [],
                    "prompts": []
                },
                "metadata": {
                    "service_type": "mcp-server",
                    "storage_path": "/root/qwen/base/document-store-mcp-server/data/ingested/",
                    "max_doc_size_mb": 50,
                    "batch_limit": 100
                }
            }

            # Register with registry DB
            print(f"📝 Registering Document Store at {self.host}:{self.port}...")
            success = self.registry_db.register_service(service_info)

            if success:
                self.service_id = service_info["id"]  # Use the registered ID
                print(f"✅ Registered as '{self.service_id}'")
                
                # Start heartbeat thread to keep registration alive
                self._start_heartbeat(ttl_seconds)
                return True
            else:
                print("❌ Registration failed")
                return False

        except Exception as e:
            print(f"❌ Registration error: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def _start_heartbeat(self, ttl_seconds: int):
        """Start heartbeat thread to keep service registered."""
        
        self.running = True
        interval = max(10, ttl_seconds // 2)  # Send at half TTL (min 10s)

        def send_heartbeat():
            while self.running and self.service_id:
                try:
                    if self.registry_db:
                        self.registry_db.update_last_seen(self.service_id)
                    
                    time.sleep(interval)
                    
                except Exception as e:
                    print(f"⚠️  Heartbeat error: {e}")
                    time.sleep(5)

        self.heartbeat_thread = threading.Thread(target=send_heartbeat, daemon=True)
        self.heartbeat_thread.start()
        print(f"💓 Heartbeat started (interval: {interval}s)")
    
    def unregister(self):
        """Unregister from registry."""
        
        self.running = False
        
        if self.registry_db and self.service_id:
            try:
                print(f"📝 Unregistering '{self.service_id}'...")
                
                # Remove the service record
                conn = __import__('sqlite3').connect(self.db_path)
                cursor = conn.cursor()
                cursor.execute("DELETE FROM services WHERE id = ?", (self.service_id,))
                conn.commit()
                conn.close()
                
                print(f"✅ Unregistered successfully")
            except Exception as e:
                print(f"⚠️  Unregister error: {e}")
    
    def get_service_info(self) -> dict:
        """Get current service registration info."""
        
        if not self.registry_db or not self.service_id:
            return {}

        try:
            conn = __import__('sqlite3').connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM services WHERE id = ?", (self.service_id,))
            row = cursor.fetchone()
            
            if row:
                result = {
                    "id": row[0],
                    "name": row[1],
                    "description": row[2],
                    "endpoint": row[3],
                    "capabilities": __import__('json').loads(row[4]) if row[4] else {},
                    "registered_at": row[5],
                    "last_seen": row[6]
                }
            else:
                result = {}

            conn.close()
            return result
            
        except Exception as e:
            print(f"⚠️  Error getting service info: {e}")
            return {}
    
    def __del__(self):
        """Cleanup on object destruction."""
        self.unregister()
