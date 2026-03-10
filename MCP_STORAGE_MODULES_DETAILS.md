# MCP Storage Modules - Detailed Overview

## Module Architecture

```
it-lead-mcp-server/utils/
├── git_result_storage.py      # Git backend for code/docs
├── file_result_storage.py     # File/S3 backend for large files
├── result_router.py           # Smart routing between backends
└── task_storage.py            # Updated to use new storage
```

---

## 1. GitResultStorage (`git_result_storage.py`)

### Purpose
Store agent-generated code, documentation, and configurations in Git repositories.

### Key Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `store_code_result()` | `task_id`, `code`, `language`, `metadata` | `Dict` | Stores generated code |
| `store_document_result()` | `task_id`, `content`, `document_type`, `metadata` | `Dict` | Stores markdown/docs |
| `store_config_result()` | `task_id`, `config`, `config_type`, `metadata` | `Dict` | Stores Terraform/YAML |
| `get_result()` | `task_id`, `result_type` | `str` | Retrieves stored result |
| `list_results()` | `task_id`, `agent`, `start_date`, `end_date` | `list` | Lists all results |

### File Structure
```
/var/mcp-results/
├── results/
│   ├── task-abc123/           # Task-specific directory
│   │   ├── result.py          # Generated Python code
│   │   ├── result.md          # Documentation
│   │   ├── result.yaml        # YAML config
│   │   └── result.metadata.json  # Metadata (timestamp, agent, etc.)
│   └── task-def456/
│       └── main.tf            # Terraform config
```

### Git Integration
- Auto-initializes repository if needed
- Creates commits for each result
- Configurable commit user/email
- Optional remote push (non-critical)

### Example Usage
```python
from it_lead_mcp_server.utils.git_result_storage import get_git_storage

storage = get_git_storage()

# Store code
result = storage.store_code_result(
    task_id="task-123",
    code="def hello(): print('World')",
    language="python",
    metadata={"agent": "Implementation Engineer"}
)
# Returns: {"storage_type": "git", "commit_sha": "a1b2c3d...", ...}

# Get result
code = storage.get_result("task-123", result_type="code")
```

---

## 2. FileResultStorage (`file_result_storage.py`)

### Purpose
Store large files, binaries, and images on local disk or S3.

### Key Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `store_file()` | `task_id`, `file_content`, `filename`, `content_type`, `metadata` | `Dict` | Stores any file |
| `_store_s3()` | `task_id`, `file_content`, `filename`, `metadata` | `Dict` | S3-specific storage |
| `get_file()` | `task_id`, `filename` | `bytes` | Retrieves file |
| `store_code_if_large()` | `task_id`, `code`, `metadata` | `Dict` | Stores code if >100KB |

### File Structure
```
/var/mcp-results/files/
├── task-abc123/
│   ├── SHA256SUM.png          # File named by checksum
│   └── file.metadata.json     # Metadata
└── task-def456/
    └── SHA256SUM.pdf
```

### Features
- **Checksum deduplication**: Same content = same file
- **Size limits**: Configurable max file size
- **S3 support**: Optional cloud storage
- **Content-type inference**: Auto-detects file type

### Example Usage
```python
from it_lead_mcp_server.utils.file_result_storage import get_file_storage

storage = get_file_storage()

# Store binary file
result = storage.store_file(
    task_id="task-123",
    file_content=b"PDF content here...",
    filename="report.pdf",
    content_type="application/pdf"
)
# Returns: {"storage_type": "local", "file_path": "...", "checksum": "..."}
```

---

## 3. ResultRouter (`result_router.py`)

### Purpose
Smart routing of results to appropriate storage backends.

### Routing Rules

| Result Type | Content Pattern | Storage Backend |
|-------------|-----------------|-----------------|
| **Code** | Contains "import" or "#!/usr/bin/env python" | Git |
| **Markdown** | Contains "```" or starts with "# " | Git |
| **YAML/TOML** | Structured config format | Git |
| **Large files** | >100KB | File Storage |
| **Binary** | bytes type | File Storage |
| **JSON** | dict type | Git or DB (small) |

### Key Methods

| Method | Parameters | Returns | Description |
|--------|------------|---------|-------------|
| `route_result()` | `task_id`, `result_data`, `agent`, `tool`, `metadata` | `Dict` | Routes to best storage |
| `_classify_result()` | `result_data` | `Dict` | Determines result type |
| `_store_code()` | `task_id`, `classification`, `metadata` | `Dict` | Stores in Git |
| `_store_document()` | `task_id`, `classification`, `metadata` | `Dict` | Stores in Git |
| `_store_binary()` | `task_id`, `classification`, `metadata` | `Dict` | Stores in File |

### Classification Logic
```python
def _classify_result(self, result_data):
    if isinstance(result_data, str):
        if "#!/usr/bin/env python" in content or "import " in content:
            return {"type": "code", "subtype": "python", ...}
        if "```" in content:
            return {"type": "document", "subtype": "markdown", ...}
        return {"type": "document", "subtype": "text", ...}
    
    elif isinstance(result_data, dict):
        if "code" in result_data:
            return {"type": "code", "subtype": language, ...}
        return {"type": "document", "subtype": "json", ...}
    
    elif isinstance(result_data, bytes):
        return {"type": "binary", ...}
```

### Example Usage
```python
from it_lead_mcp_server.utils.result_router import get_result_router

router = get_result_router()

# Route a result automatically
storage_ref = router.route_result(
    task_id="task-123",
    result_data={
        "code": "def hello(): print('World')",
        "language": "python",
        "explanation": "This is the code"
    },
    agent="Implementation Engineer",
    tool="vibe_code"
)

# Returns storage reference with location info
# {
#     "storage_type": "git",
#     "commit_sha": "a1b2c3d4e5f...",
#     "code_file": "/var/mcp-results/results/task-123/result.py"
# }
```

---

## 4. TaskStorage Integration

### New Method
```python
def update_task_result_reference(
    self,
    task_id: str,
    storage_ref: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Update task with result storage reference.
    
    Instead of storing full result in DB, stores reference:
    {
        "storage_type": "git",  # or "s3", "local"
        "path": "results/task-123/",
        "commit_sha": "a1b2c3d4...",
        "file_path": "/var/mcp-results/results/task-123/result.py"
    }
    """
```

### Database Table (`task_results`)
```sql
CREATE TABLE task_results (
    id SERIAL PRIMARY KEY,
    task_id VARCHAR(255) UNIQUE NOT NULL,
    result_type VARCHAR(50),      -- code, document, config, binary
    storage_type VARCHAR(50),     -- git, s3, local, database
    storage_path TEXT,            -- Git SHA, S3 key, local path
    file_name TEXT,
    file_size BIGINT,
    checksum VARCHAR(64),
    metadata JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

---

## Integration Flow

### Complete Flow (Agent Execution)
```
1. Client submits task to IT Lead
   ↓
2. IT Lead stores task in PostgreSQL
   ↓
3. IT Lead routes task to appropriate agent
   ↓
4. Agent executes and returns result
   ↓
5. Result Router classifies result type
   ↓
6. Result stored in appropriate backend:
   - Code → Git
   - Large files → File Storage
   - Binary → File Storage
   ↓
7. TaskStorage updated with storage reference
   ↓
8. Response returned to client with storage reference
```

### Storage Reference Structure
```python
# Git storage reference
{
    "storage_type": "git",
    "commit_sha": "a1b2c3d4e5f67890...",
    "path": "results/task-123/",
    "code_file": "/var/mcp-results/results/task-123/result.py",
    "metadata_file": "/var/mcp-results/results/task-123/result.metadata.json"
}

# File storage reference
{
    "storage_type": "local",  # or "s3"
    "file_path": "/var/mcp-results/files/task-123/abc123def.pdf",
    "file_size": 123456,
    "checksum": "sha256:abc123def456...",
    "filename": "abc123def.pdf"
}

# DB reference (fallback)
{
    "storage_type": "database",
    "path": "inline",
    "result": "truncated content..."
}
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
export AWS_ACCESS_KEY_ID="..."
export AWS_SECRET_ACCESS_KEY="..."
```

### Global Instances
Each module provides a `get_*_storage()` function that:
- Creates instance on first use
- Reads configuration from environment
- Returns singleton instance

```python
# Use in any module
from it_lead_mcp_server.utils.git_result_storage import get_git_storage
from it_lead_mcp_server.utils.file_result_storage import get_file_storage
from it_lead_mcp_server.utils.result_router import get_result_router

git_storage = get_git_storage()
file_storage = get_file_storage()
router = get_result_router()
```

---

## Error Handling

### Graceful Degradation
- GitPython not installed → Logs warning, continues
- S3 not configured → Falls back to local storage
- Git commit fails → Logs error, doesn't fail task
- File too large → Raises ValueError with clear message

### Logging
All modules use Python's `logging` module:
```python
logger.info(f"Created commit {commit.hexsha}: {message}")
logger.warning(f"File too large: {size}MB")
logger.error(f"Git commit failed: {error}")
```

---

## Testing Strategy

### Unit Tests
```python
def test_git_storage():
    storage = GitResultStorage(repo_path="/tmp/test-git")
    result = storage.store_code_result("test-1", "print(1)", "python")
    assert result["storage_type"] == "git"
    assert result["commit_sha"] is not None

def test_file_storage():
    storage = FileResultStorage(base_path="/tmp/test-files")
    result = storage.store_file("test-1", b"content", "test.txt")
    assert result["storage_type"] == "local"
    assert result["checksum"] is not None

def test_router():
    router = ResultRouter()
    result = router.route_result("test-1", {"code": "x=1"}, "agent", "tool")
    assert result["storage_type"] == "git"
```

---

## Performance Characteristics

| Operation | Latency | Notes |
|-----------|---------|-------|
| Store small code (<10KB) | ~100ms | Git commit |
| Store large code (>100KB) | ~200ms | Git commit + large file |
| Store binary file | ~500ms | File write or S3 upload |
| Retrieve result | ~50ms | File read |
| List results | ~100ms | Directory scan |
| Git push | ~1s | Non-blocking |

---

## Security Considerations

1. **Input validation**: File size limits, content type checking
2. **Checksum verification**: SHA256 for integrity
3. **Path sanitization**: Git path traversal protection
4. **Secret scanning**: Should add to CI/CD pipeline

---

## Maintenance

### Backup Strategy
```bash
# Git backup
cd /var/mcp-results
git bundle create /backup/mcp-results.bundle --all

# File backup
tar -czf /backup/mcp-files.tar.gz /var/mcp-results/files/
```

### Cleanup
```bash
# Remove old results (30 days)
find /var/mcp-results/results -maxdepth 1 -mtime +30 -exec rm -rf {} \;
```

---

## Migration Path

### Step 1: Enable in parallel
- New tasks use Git + File storage
- Old tasks remain in DB

### Step 2: Migrate existing
```python
# Run migration script
python migrate_results.py
```

### Step 3: Cut over
- Stop storing inline in DB
- Use storage references only

---

## Summary

The three modules work together:

1. **GitResultStorage** - Versioned storage for text/code
2. **FileResultStorage** - Scalable storage for large files
3. **ResultRouter** - Smart routing between them

Each module is:
- ✅ Standalone (can be tested individually)
- ✅ Configurable via environment variables
- ✅ Gracefully handles errors
- ✅ Logs operations for debugging
- ✅ Produces consistent storage references

Would you like me to:
1. Create the actual Python files from the templates?
2. Show integration examples?
3. Explain the database schema in more detail?
4. Discuss security considerations?
