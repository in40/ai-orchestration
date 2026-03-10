with open('/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py', 'r') as f:
    content = f.read()

# Find sections
main_block = content.find('if __name__ == "__main__":')
git_section = content.find('# ===== HTTP Git File Access Endpoints =====')

print(f"Main block at: {main_block}")
print(f"Git section at: {git_section}")

if main_block > 0 and git_section > main_block:
    # Extract git section
    git_code = content[git_section:]
    
    # Remove from end
    content = content[:git_section]
    
    # Insert before main block
    content = content + '\n\n' + git_code + '\n\n' + 'if __name__ == "__main__":'
    
    # Add back the uvicorn part (find it in original)
    uvicorn_part_start = content.find('import uvicorn', main_block)
    if uvicorn_part_start > 0:
        # Already included
        pass
    
    with open('/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py', 'w') as f:
        f.write(content)
    
    print("✅ Fixed - Git endpoints now before if __name__")
else:
    print("❌ Could not fix")
