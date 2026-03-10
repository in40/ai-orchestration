import sys
sys.path.insert(0, '/root/qwen/base/it-lead-mcp-server')

print('Importing server...')
from it_lead_mcp_server.server import ItLeadMcpServer

print('Creating server...')
server = ItLeadMcpServer(enable_registry=True, use_postgres=True)

print('Server created successfully!')
