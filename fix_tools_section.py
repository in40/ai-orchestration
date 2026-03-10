with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'r') as f:
    content = f.read()

# Replace the tools section placeholder with actual code
old_tools = '''## Available Tools
'''

new_tools = '''## Available Tools
'''

# Find the conflict prompt and add tools generation
old_conflict_section = '''## Available Agents
1. **implementation-engineer**: Writes code, implements features, generates code from specs - **ALL CODING TASKS MUST GO HERE**
2. **requirements-engineer**: Analyzes requirements, resolves ambiguities
3. **code-reviewer**: Reviews code quality
4. **qa-test-engineer**: Testing and validation

## Available Tools
'''

new_conflict_section = '''## Available Agents
1. **implementation-engineer**: Writes code, implements features, generates code from specs - **ALL CODING TASKS MUST GO HERE**
2. **requirements-engineer**: Analyzes requirements, resolves ambiguities
3. **code-reviewer**: Reviews code quality
4. **qa-test-engineer**: Testing and validation

{tools_section}

## CRITICAL INSTRUCTION: 
- ALL coding, development, implementation, frontend, web, JavaScript, Python, React, HTML, CSS tasks MUST go to implementation-engineer
- ONLY use tools listed under "Available Tools" above - DO NOT invent tool names
- For implementation-engineer coding tasks, use `vibe_code_async`
'''

# We need to build the tools_section in the function
# For now, let's just add a simpler version
content = content.replace(old_conflict_section, new_conflict_section)

with open('/root/qwen/base/it-lead-mcp-server/it_lead_mcp_server/utils/llm_task_planner.py', 'w') as f:
    f.write(content)

print("✅ Added tools section placeholder")
