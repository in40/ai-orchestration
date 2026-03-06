with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'r') as f:
    lines = f.readlines()

# Find the line with conflicting_assignees and add tools generation after it
new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)
    
    # When we find the conflicting_assignees line, add tools generation
    if 'conflicting_assignees = routing_context.get("conflicting_assignees", [])' in line:
        new_lines.append('\n')
        new_lines.append('        # Build available tools section\n')
        new_lines.append('        if available_tools is None:\n')
        new_lines.append('            available_tools = {}\n')
        new_lines.append('        \n')
        new_lines.append('        tools_section = "## Available Tools\\n"\n')
        new_lines.append('        for agent, tools in available_tools.items():\n')
        new_lines.append('            tools_list = ", ".join(f"`{tool}`" for tool in tools)\n')
        new_lines.append('            tools_section += f"- **{agent}**: {tools_list}\\n"\n')
        i += 1
        continue
    
    i += 1

with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'w') as f:
    f.writelines(new_lines)

print("✅ Added tools generation to _build_conflict_prompt")
