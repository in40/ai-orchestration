with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'r') as f:
    content = f.read()

# Check current state
if "## Available Tools" in content:
    print("✅ '## Available Tools' found in file")
    
    # Check if tools_section variable is used
    if "tools_section = " in content:
        print("✅ tools_section variable found")
    else:
        print("❌ tools_section variable NOT found - need to add it")
else:
    print("❌ '## Available Tools' NOT found in file")
