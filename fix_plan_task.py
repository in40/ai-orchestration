with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'r') as f:
    lines = f.readlines()

new_lines = []
i = 0
while i < len(lines):
    line = lines[i]
    new_lines.append(line)
    
    # When we find the llm_reason line, add the available_tools call after it
    if 'llm_reason = routing_context.get("llm_reason", "UNKNOWN")' in line:
        new_lines.append('\n')
        new_lines.append('        # Get available tools for each agent\n')
        new_lines.append('        available_tools = self._get_available_tools()\n')
        i += 1
        continue
    
    # Update the prompt calls to pass available_tools
    if 'prompt = self._build_no_match_prompt(task_description, routing_context)' in line:
        new_lines[-1] = '            prompt = self._build_no_match_prompt(task_description, routing_context, available_tools)\n'
        i += 1
        continue
    if 'prompt = self._build_low_confidence_prompt(task_description, routing_context)' in line:
        new_lines[-1] = '            prompt = self._build_low_confidence_prompt(task_description, routing_context, available_tools)\n'
        i += 1
        continue
    if 'prompt = self._build_conflict_prompt(task_description, routing_context)' in line:
        new_lines[-1] = '            prompt = self._build_conflict_prompt(task_description, routing_context, available_tools)\n'
        i += 1
        continue
    if 'prompt = self._build_general_prompt(task_description, routing_context)' in line:
        new_lines[-1] = '            prompt = self._build_general_prompt(task_description, routing_context, available_tools)\n'
        i += 1
        continue
    
    i += 1

with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'w') as f:
    f.writelines(new_lines)

print("✅ Updated plan_task_assignment to use available_tools")
