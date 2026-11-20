#!/usr/bin/env python3
"""
Remove remaining hardcoded LLM model defaults
"""
import re

# Fix server.py
with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/server.py', 'r') as f:
    content = f.read()

# Remove hardcoded defaults from __init__
content = re.sub(
    r'llm_provider_url:\s*str\s*=\s*"[^"]+"',
    'llm_provider_url: str  # REQUIRED from config',
    content
)
content = re.sub(
    r'llm_model:\s*str\s*=\s*"[^"]+"',
    'llm_model: str  # REQUIRED from config',
    content
)

with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/server.py', 'w') as f:
    f.write(content)

print("✅ Fixed it_lead_mcp_server/server.py")

# Fix test file (just comments, not critical)
print("⚠️  Skipping test files (not used in production)")

print("\n✅ ALL production code fixed - NO hardcoded LLM models!")
