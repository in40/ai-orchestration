# ✅ HTTP Git File Access - Implementation Complete

## Overview
Added HTTP endpoints to access Git repository files directly via HTTP, eliminating the need for SSH access.

## New Endpoints

### 1. GET `/api/git/files/{task_uuid}/{filename}`
**Purpose**: Download/view file content from Git repository

**Example**:
```bash
# View Python file
curl http://localhost:8000/api/git/files/ae01686a-e9a7-4825-9022-7d6c3c1801a0/result.py

# View HTML file
curl http://localhost:8000/api/git/files/{task_id}/result.html

# View Markdown
curl http://localhost:8000/api/git/files/{task_id}/result.md

# Download with filename
curl -O -J http://localhost:8000/api/git/files/{task_id}/result.py
```

**Response**:
- Raw file content with appropriate Content-Type
- Headers: `Content-Disposition: inline; filename={filename}`

**Content Types Supported**:
- `.md` → `text/markdown`
- `.html` → `text/html`
- `.css` → `text/css`
- `.js` → `application/javascript`
- `.json` → `application/json`
- `.yaml/.yml` → `text/yaml`
- `.py` → `text/x-python`
- `.txt` → `text/plain`

### 2. GET `/api/git/browse/{task_uuid}`
**Purpose**: List files in a task's directory

**Example**:
```bash
curl http://localhost:8000/api/git/browse/ae01686a-e9a7-4825-9022-7d6c3c1801a0
```

**Response**:
```json
{
  "task_id": "ae01686a-e9a7-4825-9022-7d6c3c1801a0",
  "files": [
    {
      "name": "result.py",
      "type": "file",
      "size": 1234,
      "url": "/api/git/files/ae01686a-e9a7-4825-9022-7d6c3c1801a0/result.py"
    },
    {
      "name": "result.metadata.json",
      "type": "file",
      "size": 567,
      "url": "/api/git/files/ae01686a-e9a7-4825-9022-7d6c3c1801a0/result.metadata.json"
    }
  ]
}
```

## Usage Examples

### 1. Access Generated Code
```bash
# Get task from database
TASK_ID=$(psql -h 127.0.0.1 -U postgres -d mcp_registry -t -c \
  "SELECT metadata->>'git_url' FROM task_registry WHERE status='done' LIMIT 1;" | \
  grep -oP '[a-f0-9-]{36}')

# View the code
curl "http://localhost:8000/api/git/files/${TASK_ID}/result.py"

# Or in browser:
# http://localhost:8000/api/git/files/${TASK_ID}/result.py
```

### 2. Access HTML Game
```bash
# For HTML tasks
curl "http://localhost:8000/api/git/files/{task_id}/result.html"

# Open in browser
firefox "http://localhost:8000/api/git/files/{task_id}/result.html"
```

### 3. List All Files
```bash
curl "http://localhost:8000/api/git/browse/{task_id}" | python -m json.tool
```

## Integration with Web UI

### Update Web UI to Use HTTP Links

In `TaskManagement.jsx`, replace SSH Git URL with HTTP:

**Before**:
```javascript
<Button
  href={selectedTaskHistory.git_url}  // ssh://...
  target="_blank"
>
  View Code
</Button>
```

**After**:
```javascript
// Extract task ID from Git URL
const taskId = selectedTaskHistory.git_url.match(/results\/([a-f0-9-]+)\//)[1];
const httpUrl = `http://localhost:8000/api/git/files/${taskId}/result.py`;

<Button
  href={httpUrl}
  target="_blank"
>
  View Code
</Button>
```

## File Locations

The endpoints check these paths in order:
1. `/tmp/mcp-vibe-coding-git/repo/results/{task_id}/{filename}`
2. `/root/qwen/base/mcp-results/results/{task_id}/{filename}`

## Benefits

1. **No SSH Required**: Access files via simple HTTP GET
2. **Browser Compatible**: Open files directly in browser
3. **Proper Content Types**: HTML renders, Python shows syntax highlighting
4. **CORS Ready**: Can be accessed from Web UI frontend
5. **Download Support**: Use `-O -J` flags to download with original filename

## Security Notes

- Currently no authentication - anyone with network access can view files
- Consider adding authentication for production use
- Files are served from local Git clone, not directly from remote

## Testing

```bash
# 1. List files
curl http://localhost:8000/api/git/browse/ae01686a-e9a7-4825-9022-7d6c3c1801a0

# 2. View file
curl http://localhost:8000/api/git/files/ae01686a-e9a7-4825-9022-7d6c3c1801a0/result.py

# 3. Check content type
curl -I http://localhost:8000/api/git/files/ae01686a-e9a7-4825-9022-7d6c3c1801a0/result.py
```

## Files Modified

1. `/root/qwen/base/it-lead-mcp-server/web-ui/backend/main.py`
   - Added `get_git_file()` endpoint
   - Added `browse_git_directory()` endpoint

## Next Steps

1. ✅ Endpoints implemented
2. ⏳ Test with actual task IDs
3. ⏳ Update Web UI to use HTTP links instead of SSH
4. ⏳ Add authentication if needed
