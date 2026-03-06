with open('/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py', 'r') as f:
    lines = f.readlines()

# Find if __name__ line
main_line = -1
for i, line in enumerate(lines):
    if 'if __name__ == "__main__":' in line:
        main_line = i
        break

print(f"Found if __name__ at line {main_line + 1}")

if main_line > 0:
    git_endpoints = '''

# ============================================================================
# HTTP Git File Access Endpoints  
# ============================================================================

@app.get("/api/git/files/{task_id:path}")
async def get_git_file(task_id: str):
    """Serve files from Git repository via HTTP"""
    logger.info(f"Serving Git file: {task_id}")
    try:
        parts = task_id.split("/", 1)
        if len(parts) != 2:
            raise HTTPException(status_code=400, detail="Invalid path. Use: {task_uuid}/{filename}")
        task_uuid, filename = parts
        file_path = f"/tmp/mcp-vibe-coding-git/repo/results/{task_uuid}/{filename}"
        import os
        if not os.path.exists(file_path):
            file_path = f"/root/qwen/base/mcp-results/results/{task_uuid}/{filename}"
            if not os.path.exists(file_path):
                raise HTTPException(status_code=404, detail="File not found")
        with open(file_path, 'rb') as f:
            content = f.read()
        ext = '.' + filename.split('.')[-1] if '.' in filename else ''
        ct = {'.md':'text/markdown','.html':'text/html','.css':'text/css','.js':'application/javascript','.json':'application/json','.yaml':'text/yaml','.yml':'text/yaml','.py':'text/x-python','.txt':'text/plain'}.get(ext, 'application/octet-stream')
        from fastapi.responses import Response
        return Response(content=content, media_type=ct, headers={"Content-Disposition": f"inline; filename={filename}"})
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error serving Git file: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/git/browse/{task_id}")
async def browse_git_directory(task_id: str):
    """Browse task directory"""
    logger.info(f"Browsing Git directory: {task_id}")
    try:
        import os
        dir_path = f"/tmp/mcp-vibe-coding-git/repo/results/{task_id}"
        if not os.path.exists(dir_path):
            dir_path = f"/root/qwen/base/mcp-results/results/{task_id}"
            if not os.path.exists(dir_path):
                raise HTTPException(status_code=404, detail="Task not found")
        files = []
        for item in os.listdir(dir_path):
            item_path = os.path.join(dir_path, item)
            files.append({"name": item, "type": "dir" if os.path.isdir(item_path) else "file", "size": os.path.getsize(item_path) if os.path.isfile(item_path) else 0, "url": f"/api/git/files/{task_id}/{item}"})
        return {"task_id": task_id, "files": files}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error browsing directory: {e}")
        raise HTTPException(status_code=500, detail=str(e))

'''
    
    lines.insert(main_line, git_endpoints)
    
    with open('/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py', 'w') as f:
        f.writelines(lines)
    
    print("✅ Git endpoints added before if __name__")
