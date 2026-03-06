with open('/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py', 'r') as f:
    content = f.read()

# Fix the broken get_all_tasks_with_progress function
old_broken = '''                    "params": {
                        "name": "get_all_tasks",


@app.get("/api/git/files/{task_id:path}")'''

new_fixed = '''                    "params": {
                        "name": "get_all_tasks",
                        "arguments": {"status_filter": None}
                    }
                }
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to fetch tasks")
            
            result = response.json()
            if "result" in result and "result" in result["result"]:
                tasks_data = result["result"]["result"]
                return tasks_data.get("tasks", [])
            return []
            
    except Exception as e:
        logger.error(f"Error fetching tasks: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.get("/api/git/files/{task_id:path}")'''

if old_broken in content:
    content = content.replace(old_broken, new_fixed)
    print("✅ Fixed get_all_tasks_with_progress function")
else:
    print("❌ Could not find broken section")

with open('/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py', 'w') as f:
    f.write(content)

print("✅ main.py fixed")
