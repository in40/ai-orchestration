import sys
import time

sys.path.insert(0, '/root/qwen/base/it-lead-mcp-server')

start = time.time()
print(f"[{time.time()-start:.2f}] Starting import...")

print(f"[{time.time()-start:.2f}] Importing server module...")
from it_lead_mcp_server.server import ItLeadMcpServer

print(f"[{time.time()-start:.2f}] Creating server...")
server = ItLeadMcpServer(enable_registry=True, use_postgres=True)

print(f"[{time.time()-start:.2f}] Server created successfully!")
print(f"Total startup time: {time.time()-start:.2f}s")
