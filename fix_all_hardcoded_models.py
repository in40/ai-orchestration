#!/usr/bin/env python3
"""
Remove hardcoded LLM model defaults from all server components
"""
import re
import os

files_to_fix = [
    '/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/handlers/server_handlers.py',
    '/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/handlers/extended_server_handlers.py',
    '/root/qwen/base/devops-release-engineer-mcp-server/devops_release_engineer_mcp_server/handlers/server_handlers.py',
    '/root/qwen/base/devops-release-engineer-mcp-server/devops_release_engineer_mcp_server/server.py',
    '/root/qwen/base/mcp-std-coder/mcp-vibe-coding-agent/config.py',
]

# Pattern to match hardcoded llm_model defaults
pattern = re.compile(r'llm_model:\s*str\s*=\s*"[^"]+"')
replacement = 'llm_model: str  # REQUIRED from config, NO hardcoded default'

for filepath in files_to_fix:
    if not os.path.exists(filepath):
        print(f"❌ File not found: {filepath}")
        continue
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Count replacements
    count = len(pattern.findall(content))
    
    if count > 0:
        # Replace hardcoded defaults
        new_content = pattern.sub(replacement, content)
        
        with open(filepath, 'w') as f:
            f.write(new_content)
        
        print(f"✅ Fixed {filepath}: removed {count} hardcoded llm_model default(s)")
    else:
        print(f"⚠️  No hardcoded llm_model found in {filepath}")

print("\n✅ All server components updated - NO hardcoded LLM models!")
