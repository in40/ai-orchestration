#!/usr/bin/env python3
"""Fix syntax errors in all server handler files"""
import re

files_to_fix = [
    '/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/handlers/extended_server_handlers.py',
    '/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/handlers/server_handlers.py',
    '/root/qwen/base/devops-release-engineer-mcp-server/devops_release_engineer_mcp_server/handlers/server_handlers.py',
    '/root/qwen/base/devops-release-engineer-mcp-server/devops_release_engineer_mcp_server/server.py',
    '/root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent/config.py',
]

for filepath in files_to_fix:
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Fix llm_provider_url and llm_model parameters - add = None for optional
    content = re.sub(
        r'llm_provider_url:\s*str\s*#\s*REQUIRED',
        'llm_provider_url: str = None  # REQUIRED from config',
        content
    )
    content = re.sub(
        r'llm_model:\s*str\s*#\s*REQUIRED',
        'llm_model: str = None  # REQUIRED from config',
        content
    )
    
    with open(filepath, 'w') as f:
        f.write(content)
    
    print(f"✅ Fixed {filepath}")

print("\n✅ All syntax errors fixed!")
