# MCP Agent Result Storage System

## Overview

This document describes the new hybrid result storage system for MCP agent outputs.

**Problem**: Agent results were stored inline in PostgreSQL database as JSON strings, causing:
- No versioning of generated code
- No audit trail of LLM executions
- Database bloat from large files
- No way to diff or track result evolution

**Solution**: Hybrid storage with automatic routing:
- **Git** for code, documentation, configurations (versioned)
- **S3** for large files and binaries (scalable)
- **Database** for metadata and references (fast queries)

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    IT Lead Server (3061)                        │
│              Task Coordinator & Router                          │
└────────────────┬────────────────────────────────────────────────┘
                 │
        ┌────────┼───────────┐
        │        │          │
        │   ┌────▼────┐    │
        │   │ Database│    │
        │   │(PostgreSQL)│
        │   │  - Tasks  │
        │   │  - Status │
        │   └───────────┘
        │          │
        │          │ Result
        │          ▼
        │   ┌────────────────────┐
        │   │   Result Router    │
        │   └────────────────────┘
        │          │
        │    ┌─────┼───────┐
        │    │     │       │
        ▼    ▼     ▼       ▼
   ┌────────┐  ┌──────┐ ┌──────┐
   │Git Repo│  │  S3  │ │Local │
   │ (Code) │  │(Large│ │Disk  │
   │        │  │Files)│ │      │
   └────────┘  └──────┘ └──────┘
```

---

## Storage Backends

### 1. Git Storage (`git_result_storage.py`)

**Purpose**: Store agent-generated code, documentation, and configurations

**Structure**:
```
/var/mcp-results/
├── results/
│   ├── task-abc123/
│   │   ├── result.py          # Generated code
│   │   ├── result.md          # Documentation
│   │   └── result.metadata.json
│   └── task-def456/
│       └── result.tf          # Terraform config
```

**Features**:
- Full Git versioning
- Commit history for audit
- Easy to diff results
- Can checkout exact version

### 2. File Storage (`file_result_storage.py`)

**Purpose**: Store large files, binaries, and images

**Features**:
- Local disk (development)
- S3-compatible (production)
- Automatic checksums
- Size limits enforced

### 3. Database (`task_results` table)

**Purpose**: Store references to results

**Schema**:
```sql
CREATE TABLE task_results (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    result_type VARCHAR(50),     -- code, document, binary
    storage_type VARCHAR(50),    -- git, s3, local, database
    storage_path TEXT,            -- Git SHA, S3 key, local path
    file_size BIGINT,
    checksum VARCHAR(64),
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## Installation

### Prerequisites

```bash
# GitPython for Git operations
pip install GitPython

# boto3 for S3 (optional, for production)
pip install boto3
```

### Setup

```bash
# Create result storage directories
mkdir -p /var/mcp-results
mkdir -p /var/mcp-results/files
chmod 755 /var/mcp-results

# Initialize Git repository
cd /var/mcp-results
git init
git config user.name "mcp-bot"
git config user.email "mcp-bot@company.com"

# Add remote (optional, for backups)
git remote add origin git@github.com:company/mcp-results.git
```

---

## Configuration

### Environment Variables

```bash
# Git storage
export MCP_GIT_REPO_PATH="/var/mcp-results"
export MCP_COMMIT_USER="mcp-bot"
export MCP_COMMIT_EMAIL="mcp-bot@company.com"

# File storage
export MCP_FILE_STORAGE_PATH="/var/mcp-results/files"
export MCP_MAX_FILE_SIZE_MB=100
export MCP_STORAGE_BACKEND="local"  # or "s3"

# S3 (optional)
export MCP_S3_BUCKET="mcp-results-prod"
export AWS_ACCESS_KEY_ID="your_key"
export AWS_SECRET_ACCESS_KEY="your_secret"
```

---

## Usage

### Automatic Result Storage

Results are automatically stored when agents execute:

```python
from it_lead_mcp_server.utils.result_router import get_result_router

# Get the router
router = get_result_router()

# After agent execution, route the result
storage_ref = router.route_result(
    task_id="task-123",
    result_data={
        "code": "def hello():\n    print('Hello, World!')",
        "language": "python",
        "explanation": "This function prints Hello World"
    },
    agent="Implementation Engineer",
    tool="vibe_code"
)

print(storage_ref)
# {
#     "storage_type": "git",
#     "commit_sha": "a1b2c3d4e5f...",
#     "code_file": "/var/mcp-results/results/task-123/result.py"
# }
```

### Retrieve Results

```python
from it_lead_mcp_server.utils.result_router import get_result_router

router = get_result_router()

# Get result content
content = router.get_result("task-123", result_type="code")
print(content)

# List all results
results = router.list_results()

# Filter by task
results = router.list_results(task_id="task-123")

# Filter by agent
results = router.list_results(agent="Implementation Engineer")
```

### View Git History

```bash
# View commits for a specific task
cd /var/mcp-results
git log results/task-123/

# Show diff between versions
git show a1b2c3d4e5f

# List all task directories
ls -la results/
```

---

## API Endpoints

### List Results

```bash
curl http://localhost:8000/api/results/list?task_id=task-123
```

### Get Result

```bash
curl http://localhost:8000/api/results/get?task_id=task-123&result_type=code
```

### Git History

```bash
curl http://localhost:8000/api/results/git/history?task_id=task-123
```

---

## Migration from Old System

### Migration Script

```python
# migrate_results.py
import json
from it_lead_mcp_server.utils.result_router import ResultRouter
from it_lead_mcp_server.utils.task_storage import TaskStorage


def migrate_existing_results():
    """Migrate results from database to new storage"""
    
    db = TaskStorage(use_sqlite=True, database="mcp_registry.db")
    router = ResultRouter()
    
    tasks = db.get_all_tasks()
    
    for task in tasks:
        result = task.get("result")
        if result and isinstance(result, str):
            try:
                result_data = json.loads(result)
                
                storage_ref = router.route_result(
                    task_id=task["task_id"],
                    result_data=result_data,
                    agent=task.get("assigned_to", "unknown"),
                    tool="migration"
                )
                
                db.update_task_result_reference(
                    task_id=task["task_id"],
                    storage_ref=storage_ref
                )
                
                print(f"Migrated: {task['task_id']}")
                
            except Exception as e:
                print(f"Failed: {task['task_id']}: {e}")


if __name__ == "__main__":
    migrate_existing_results()
```

### Run Migration

```bash
python migrate_results.py
```

---

## Monitoring

### Check Storage Usage

```bash
# Git repo size
du -sh /var/mcp-results

# File storage size
du -sh /var/mcp-results/files

# Count tasks
ls /var/mcp-results/results/ | wc -l
```

### View Logs

```bash
# Check for errors
tail -f /tmp/it_lead.log | grep -i "result\|storage"

# Check Git activity
cd /var/mcp-results
git log --oneline -20
```

---

## Troubleshooting

### Git Not Working

```bash
# Check if GitPython is installed
python -c "import git; print('GitPython OK')"

# Check Git repo
cd /var/mcp-results
git status
git log --oneline -5
```

### File Storage Issues

```bash
# Check permissions
ls -la /var/mcp-results/files/

# Check disk space
df -h /var/mcp-results/files/
```

### Database References

```bash
# Query task results
psql mcp_registry -c "SELECT * FROM task_results WHERE task_id = 'task-123';"

# Check for orphaned results
psql mcp_registry -c "SELECT task_id FROM task_results WHERE task_id NOT IN (SELECT task_id FROM task_registry);"
```

---

## Best Practices

### 1. Clean Up Old Results

```bash
# Remove results older than 30 days
find /var/mcp-results/results -maxdepth 1 -mtime +30 -exec rm -rf {} \;
```

### 2. Backup Git Repository

```bash
# Backup to remote
git push origin master

# Or local backup
git bundle create /backup/mcp-results.bundle --all
```

### 3. Monitor S3 Costs

```bash
# Check S3 usage
aws s3 ls s3://mcp-results-prod --recursive | wc -l
```

### 4. Rotate API Keys

```bash
# Update S3 credentials
export AWS_ACCESS_KEY_ID="new_key"
export AWS_SECRET_ACCESS_KEY="new_secret"
```

---

## Performance

### Optimization Tips

1. **Use Git LFS** for large files in repository
2. **Enable S3 lifecycle policies** to move old files to glacier
3. **Regular vacuum** on PostgreSQL database
4. **Index monitoring** for slow queries

### Expected Performance

| Operation | Latency |
|-----------|---------|
| Store small result (<10KB) | ~100ms |
| Store large result (>1MB) | ~500ms |
| Retrieve result | ~50ms |
| List results | ~100ms |

---

## Security

### Best Practices

1. **Git repo permissions** - Restrict write access
2. **S3 encryption** - Enable at-rest encryption
3. **Secret scanning** - Add to CI/CD pipeline
4. **Access logging** - Enable S3 access logs

### Audit Trail

Every result is tracked with:
- Agent that generated it
- Tool that was used
- Timestamp of generation
- Git commit SHA (for review)
- Checksum (for integrity)

---

## Future Enhancements

- [ ] Auto-cleanup of old results
- [ ] Result deduplication (checksum-based)
- [ ] Result comparison UI
- [ ] Export results to archive
- [ ] Result analytics dashboard
- [ ] Machine learning for result classification

---

## Support

For issues:
1. Check logs: `/tmp/it_lead.log`
2. Check Git: `cd /var/mcp-results && git log`
3. Check storage: `ls -la /var/mcp-results/files/`
4. Review database: `psql mcp_registry -c "SELECT * FROM task_results;"`

---

**Version**: 1.0.0
**Last Updated**: 2026-03-02
