with open('/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py', 'r') as f:
    lines = f.readlines()

# Find and remove the duplicate/broken lines
new_lines = []
skip_until = -1
for i, line in enumerate(lines):
    if skip_until > i:
        continue
    
    # Look for the broken section and fix it
    if '"arguments": {"status_filter": None}' in line and i > 1300:
        # Skip this duplicate line
        continue
    
    new_lines.append(line)

with open('/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py', 'w') as f:
    f.writelines(new_lines)

print("✅ Removed duplicate lines")
