# MCP Result Storage - Implementation Guide

## Quick Start

This guide provides a step-by-step implementation of the Git-enabled result storage system for MCP agent outputs.

---

## Architecture Overview

```
Task → IT Lead → Agent → Result → Router → Storage Backends
                                    ↓
                            +--------------+
                            |  Result      |
                            |  Storage     |
                            +--------------+
                            | Git (Code)   |
                            | S3 (Files)   |
                            | Local (Dev)  |
                            +--------------+
                                    ↓
                            +--------------+
                            |  Database    |
                            |  (References)|
                            +--------------+
```

---

## Implementation Steps

### Step 1: Install GitPython

```bash
pip install GitPython
```

### Step 2: Create Storage Modules

#### `it-lead-mcp-server/utils/git_result_storage.py`

```python
"""
Git-based Result Storage for MCP Agent Outputs
Stores agent-generated code, configs, and documents in Git repositories
"""
import os
import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class GitResultStorage:
    """
    Stores MCP agent results in Git repositories with full version control.
    
    Each task result is stored in a dedicated directory:
    /results/{task_id}/result.py  (code)
    /results/{task_id}/result.md  (documentation)
    /results/{task_id}/result.json (metadata)
    
    The Git history provides full audit trail and versioning.
    """
    
    def __init__(
        self,
        repo_path: str = "/var/mcp-results",
        commit_user: str = "mcp-bot",
        commit_email: str = "mcp-bot@localhost"
    ):
        """
        Initialize Git storage.
        
        Args:
            repo_path: Path to the Git repository for storing results
            commit_user: Git commit author name
            commit_email: Git commit author email
        """
        self.repo_path = Path(repo_path)
        self.commit_user = commit_user
        self.commit_email = commit_email
        self._ensure_repo()
    
    def _ensure_repo(self) -> None:
        """Ensure Git repository exists and is initialized"""
        try:
            from git import Repo, GitCommandError
        except ImportError:
            logger.warning("GitPython not installed. Install with: pip install GitPython")
            return
        
        # Create directory if it doesn't exist
        self.repo_path.mkdir(parents=True, exist_ok=True)
        
        try:
            # Check if it's already a Git repo
            Repo(self.repo_path)
            logger.info(f"Git repository found at {self.repo_path}")
        except Exception:
            # Initialize new repo
            try:
                Repo.init(self.repo_path)
                # Configure user for commits
                repo = Repo(self.repo_path)
                with repo.config_writer() as cw:
                    cw.set_value("user", "name", self.commit_user)
                    cw.set_value("user", "email", self.commit_email)
                logger.info(f"Initialized new Git repository at {self.repo_path}")
            except Exception as e:
                logger.error(f"Failed to initialize Git repo: {e}")
    
    def _get_git_repo(self) -> Optional[Any]:
        """Get Git repository handle"""
        try:
            from git import Repo
            return Repo(self.repo_path)
        except ImportError:
            logger.error("GitPython not installed")
            return None
        except Exception as e:
            logger.error(f"Failed to open Git repo: {e}")
            return None
    
    def _git_commit(self, message: str, files: list) -> Optional[str]:
        """
        Create a Git commit with the specified files.
        
        Args:
            message: Commit message
            files: List of file paths to add and commit
            
        Returns:
            Commit SHA or None if commit failed
        """
        repo = self._get_git_repo()
        if not repo:
            return None
        
        try:
            # Add all files
            repo.index.add(files)
            
            # Create commit
            commit = repo.index.commit(message)
            
            logger.info(f"Created commit {commit.hexsha}: {message}")
            return commit.hexsha
            
        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            return None
    
    def _git_push(self) -> bool:
        """
        Push commits to remote repository if configured.
        
        Returns:
            True if push succeeded (or no remote configured)
        """
        repo = self._get_git_repo()
        if not repo:
            return False
        
        try:
            origin = repo.remote(name='origin')
            if origin:
                origin.push()
                logger.info("Pushed to remote repository")
            return True
        except Exception as e:
            logger.warning(f"Git push failed (non-critical): {e}")
            return True  # Don't fail if push fails
    
    def store_code_result(
        self,
        task_id: str,
        code: str,
        language: str = "python",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store generated code in Git repository.
        
        Args:
            task_id: Unique task identifier
            code: Generated code content
            language: Programming language
            metadata: Additional metadata
            
        Returns:
            Storage reference with commit SHA
        """
        # Create task directory
        task_dir = self.repo_path / "results" / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file extension
        ext_map = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs",
            "html": ".html",
            "css": ".css",
            "sql": ".sql",
        }
        ext = ext_map.get(language.lower(), ".txt")
        
        # Write code file
        code_file = task_dir / f"result{ext}"
        code_file.write_text(code)
        
        # Write metadata
        meta_file = task_dir / "result.metadata.json"
        meta_data = {
            "task_id": task_id,
            "storage_type": "git",
            "created_at": datetime.now().isoformat(),
            "language": language,
            **(metadata or {})
        }
        meta_file.write_text(json.dumps(meta_data, indent=2))
        
        # Commit to Git
        commit_sha = self._git_commit(
            f"Task {task_id}: {metadata.get('agent', 'agent')} generated code",
            [str(code_file), str(meta_file)]
        )
        
        return {
            "storage_type": "git",
            "commit_sha": commit_sha,
            "code_file": str(code_file),
            "metadata_file": str(meta_file),
            "path": f"results/{task_id}/",
            "language": language,
            "file_extension": ext
        }
    
    def store_document_result(
        self,
        task_id: str,
        content: str,
        document_type: str = "markdown",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store document or report in Git repository.
        
        Args:
            task_id: Unique task identifier
            content: Document content
            document_type: Type of document (markdown, text, etc.)
            metadata: Additional metadata
            
        Returns:
            Storage reference with commit SHA
        """
        # Create task directory
        task_dir = self.repo_path / "results" / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file extension
        ext_map = {
            "markdown": ".md",
            "text": ".txt",
            "json": ".json",
            "html": ".html",
            "yaml": ".yaml",
        }
        ext = ext_map.get(document_type.lower(), ".md")
        
        # Write document
        doc_file = task_dir / f"result{ext}"
        doc_file.write_text(content)
        
        # Write metadata
        meta_file = task_dir / "result.metadata.json"
        meta_data = {
            "task_id": task_id,
            "storage_type": "git",
            "created_at": datetime.now().isoformat(),
            "document_type": document_type,
            **(metadata or {})
        }
        meta_file.write_text(json.dumps(meta_data, indent=2))
        
        # Commit to Git
        commit_sha = self._git_commit(
            f"Task {task_id}: {metadata.get('agent', 'agent')} generated document",
            [str(doc_file), str(meta_file)]
        )
        
        return {
            "storage_type": "git",
            "commit_sha": commit_sha,
            "document_file": str(doc_file),
            "metadata_file": str(meta_file),
            "path": f"results/{task_id}/",
            "document_type": document_type,
            "file_extension": ext
        }
    
    def store_config_result(
        self,
        task_id: str,
        config: str,
        config_type: str = "yaml",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store configuration files (Terraform, CI/CD, etc.).
        
        Args:
            task_id: Unique task identifier
            config: Configuration content
            config_type: Type of config (yaml, json, tf, etc.)
            metadata: Additional metadata
            
        Returns:
            Storage reference with commit SHA
        """
        # Create task directory
        task_dir = self.repo_path / "results" / task_id / "configs"
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Determine file extension and name
        ext_map = {
            "yaml": ".yaml",
            "yml": ".yaml",
            "json": ".json",
            "terraform": ".tf",
            "tf": ".tf",
            "docker": "Dockerfile",
            "dockerfile": "Dockerfile",
        }
        ext = ext_map.get(config_type.lower(), ".yaml")
        
        # Determine filename
        if ext == "Dockerfile":
            filename = "Dockerfile"
        elif ext == ".tf":
            filename = "main.tf"
        else:
            filename = f"config{ext}"
        
        # Write config
        config_file = task_dir / filename
        config_file.write_text(config)
        
        # Write metadata
        meta_file = task_dir / "result.metadata.json"
        meta_data = {
            "task_id": task_id,
            "storage_type": "git",
            "created_at": datetime.now().isoformat(),
            "config_type": config_type,
            **(metadata or {})
        }
        meta_file.write_text(json.dumps(meta_data, indent=2))
        
        # Commit to Git
        commit_sha = self._git_commit(
            f"Task {task_id}: {metadata.get('agent', 'agent')} generated config",
            [str(config_file), str(meta_file)]
        )
        
        return {
            "storage_type": "git",
            "commit_sha": commit_sha,
            "config_file": str(config_file),
            "metadata_file": str(meta_file),
            "path": f"results/{task_id}/configs/",
            "config_type": config_type,
            "file_name": filename
        }
    
    def get_result(
        self,
        task_id: str,
        result_type: str = "code",
        result_index: int = 0
    ) -> Optional[str]:
        """
        Retrieve a stored result.
        
        Args:
            task_id: Task identifier
            result_type: Type of result to retrieve
            result_index: Index of result (for multiple results)
            
        Returns:
            Result content or None if not found
        """
        task_dir = self.repo_path / "results" / task_id
        
        if not task_dir.exists():
            logger.warning(f"Task directory not found: {task_dir}")
            return None
        
        # Find the result file
        if result_type == "code":
            pattern = "result*.py"
        elif result_type == "document":
            pattern = "result*.md"
        elif result_type == "config":
            pattern = "**/config*"
        else:
            pattern = "result*"
        
        # Simple implementation - return first matching file
        from glob import glob
        files = glob(str(task_dir / pattern))
        
        if files:
            return Path(files[0]).read_text()
        
        return None
    
    def list_results(
        self,
        task_id: Optional[str] = None,
        agent: Optional[str] = None,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None
    ) -> list:
        """
        List stored results with optional filtering.
        
        Args:
            task_id: Filter by task ID
            agent: Filter by agent name
            start_date: Filter by start date
            end_date: Filter by end date
            
        Returns:
            List of result references
        """
        results = []
        results_dir = self.repo_path / "results"
        
        if not results_dir.exists():
            return results
        
        # Get all task directories
        task_dirs = list(results_dir.iterdir())
        
        for task_dir in task_dirs:
            if not task_dir.is_dir():
                continue
            
            task_id_match = task_id is None or task_dir.name == task_id
            
            if not task_id_match:
                continue
            
            # Read metadata
            meta_file = task_dir / "result.metadata.json"
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text())
                    meta["task_id"] = task_dir.name
                    meta["path"] = f"results/{task_dir.name}/"
                    results.append(meta)
                except Exception as e:
                    logger.warning(f"Failed to read metadata for {task_dir}: {e}")
        
        # Sort by created_at descending
        results.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        
        return results


# Global instance (can be configured via environment)
_git_storage = None


def get_git_storage() -> GitResultStorage:
    """Get or create global Git storage instance"""
    global _git_storage
    
    if _git_storage is None:
        repo_path = os.environ.get(
            "MCP_GIT_REPO_PATH",
            "/var/mcp-results"
        )
        _git_storage = GitResultStorage(repo_path=repo_path)
    
    return _git_storage
```

#### `it-lead-mcp-server/utils/file_result_storage.py`

```python
"""
File-based Result Storage for MCP Agent Outputs
Stores large files and binary artifacts on local disk or S3
"""
import os
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import io

logger = logging.getLogger(__name__)


class FileResultStorage:
    """
    Stores MCP agent results as files on disk or in cloud storage.
    
    Large files (images, binaries, large documents) are stored here.
    Small text files and code go to Git storage instead.
    """
    
    def __init__(
        self,
        base_path: str = "/var/mcp-results/files",
        max_file_size_mb: int = 100,
        storage_backend: str = "local"  # "local" or "s3"
    ):
        """
        Initialize file storage.
        
        Args:
            base_path: Base directory for storing files
            max_file_size_mb: Maximum file size in MB
            storage_backend: Storage backend ("local" or "s3")
        """
        self.base_path = Path(base_path)
        self.max_file_size_mb = max_file_size_mb
        self.storage_backend = storage_backend
        self._ensure_base_path()
        
        # S3 client (lazy loaded)
        self._s3_client = None
    
    def _ensure_base_path(self) -> None:
        """Ensure base path exists"""
        self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _get_s3_client(self):
        """Get or create S3 client"""
        if self.storage_backend != "s3":
            return None
        
        if self._s3_client is None:
            try:
                import boto3
                self._s3_client = boto3.client('s3')
            except ImportError:
                logger.warning("boto3 not installed. Install with: pip install boto3")
        
        return self._s3_client
    
    def _calculate_checksum(self, content: bytes) -> str:
        """Calculate SHA256 checksum of content"""
        return hashlib.sha256(content).hexdigest()
    
    def store_file(
        self,
        task_id: str,
        file_content: bytes,
        filename: str,
        content_type: str = "application/octet-stream",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store a file (binary or large text).
        
        Args:
            task_id: Unique task identifier
            file_content: File content as bytes
            filename: Original filename
            content_type: MIME type
            metadata: Additional metadata
            
        Returns:
            Storage reference with file path/URL
        """
        # Check file size
        file_size_mb = len(file_content) / (1024 * 1024)
        if file_size_mb > self.max_file_size_mb:
            raise ValueError(
                f"File too large: {file_size_mb:.2f}MB > {self.max_file_size_mb}MB"
            )
        
        # Create task directory
        task_dir = self.base_path / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        # Calculate checksum
        checksum = self._calculate_checksum(file_content)
        
        # Generate unique filename if needed
        name, ext = os.path.splitext(filename)
        if not ext:
            # Try to infer from content type
            ext_map = {
                "text/plain": ".txt",
                "text/markdown": ".md",
                "application/json": ".json",
                "text/html": ".html",
                "application/yaml": ".yaml",
                "application/pdf": ".pdf",
                "image/png": ".png",
                "image/jpeg": ".jpg",
            }
            ext = ext_map.get(content_type, "")
        
        # Use checksum as filename for deduplication
        unique_filename = f"{checksum}{ext}"
        filepath = task_dir / unique_filename
        
        # Store file
        if self.storage_backend == "s3":
            return self._store_s3(task_id, file_content, unique_filename, metadata)
        else:
            filepath.write_bytes(file_content)
        
        # Write metadata
        meta_file = task_dir / "file.metadata.json"
        meta_data = {
            "task_id": task_id,
            "storage_type": "local" if self.storage_backend == "local" else "s3",
            "filename": unique_filename,
            "original_filename": filename,
            "content_type": content_type,
            "file_size": len(file_content),
            "checksum": checksum,
            "created_at": datetime.now().isoformat(),
            **(metadata or {})
        }
        meta_file.write_text(json.dumps(meta_data, indent=2))
        
        return {
            "storage_type": self.storage_backend,
            "file_path": str(filepath),
            "file_size": len(file_content),
            "checksum": checksum,
            "filename": unique_filename,
            "original_filename": filename,
            "content_type": content_type,
            "metadata_file": str(meta_file)
        }
    
    def _store_s3(
        self,
        task_id: str,
        file_content: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store file in S3"""
        s3 = self._get_s3_client()
        if not s3:
            raise RuntimeError("S3 storage not available")
        
        bucket = os.environ.get("MCP_S3_BUCKET", "mcp-results")
        key = f"results/{task_id}/{filename}"
        
        # Upload to S3
        s3.put_object(
            Bucket=bucket,
            Key=key,
            Body=file_content,
            ContentType=metadata.get("content_type", "application/octet-stream")
        )
        
        return {
            "storage_type": "s3",
            "bucket": bucket,
            "key": key,
            "file_size": len(file_content),
            "url": f"s3://{bucket}/{key}",
            **(metadata or {})
        }
    
    def get_file(
        self,
        task_id: str,
        filename: str
    ) -> Optional[bytes]:
        """
        Retrieve a stored file.
        
        Args:
            task_id: Task identifier
            filename: Filename to retrieve
            
        Returns:
            File content as bytes or None if not found
        """
        filepath = self.base_path / task_id / filename
        
        if filepath.exists():
            return filepath.read_bytes()
        
        return None
    
    def store_code_if_large(
        self,
        task_id: str,
        code: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store code file if it's large (>100KB).
        Small files go to Git storage instead.
        
        Args:
            task_id: Task identifier
            code: Code content
            metadata: Additional metadata
            
        Returns:
            Storage reference
        """
        code_bytes = code.encode()
        
        # If file is large, store in file system
        if len(code_bytes) > 100 * 1024:  # 100KB threshold
            return self.store_file(
                task_id=task_id,
                file_content=code_bytes,
                filename=f"result.py",
                content_type="text/plain",
                metadata=metadata
            )
        
        # Small files not stored here (go to Git)
        return {
            "storage_type": "skip",
            "reason": "small_file",
            "size": len(code_bytes)
        }


# Global instance
_file_storage = None


def get_file_storage() -> FileResultStorage:
    """Get or create global file storage instance"""
    global _file_storage
    
    if _file_storage is None:
        base_path = os.environ.get(
            "MCP_FILE_STORAGE_PATH",
            "/var/mcp-results/files"
        )
        max_size = int(os.environ.get("MCP_MAX_FILE_SIZE_MB", 100))
        backend = os.environ.get("MCP_STORAGE_BACKEND", "local")
        
        _file_storage = FileResultStorage(
            base_path=base_path,
            max_file_size_mb=max_size,
            storage_backend=backend
        )
    
    return _file_storage
```

#### `it-lead-mcp-server/utils/result_router.py`

```python
"""
Result Router for MCP Agent Outputs
Routes results to appropriate storage backends based on content type
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

from .git_result_storage import get_git_storage, GitResultStorage
from .file_result_storage import get_file_storage, FileResultStorage

logger = logging.getLogger(__name__)


class ResultRouter:
    """
    Routes MCP agent results to appropriate storage backends.
    
    Routing rules:
    - Code (Python, JS, etc.) → Git storage
    - Documentation (Markdown, etc.) → Git storage  
    - Configuration (Terraform, YAML, etc.) → Git storage
    - Large files (>100KB) → File storage
    - Binaries (images, PDFs) → File storage
    - Small text (<100KB) → Git storage or inline in DB
    """
    
    def __init__(
        self,
        git_storage: Optional[GitResultStorage] = None,
        file_storage: Optional[FileResultStorage] = None,
        max_inline_size: int = 100 * 1024  # 100KB
    ):
        """
        Initialize result router.
        
        Args:
            git_storage: Git storage instance for text/code
            file_storage: File storage instance for large/binary files
            max_inline_size: Maximum size for inline DB storage
        """
        self.git_storage = git_storage or get_git_storage()
        self.file_storage = file_storage or get_file_storage()
        self.max_inline_size = max_inline_size
    
    def _classify_result(self, result_data: Any) -> Dict[str, Any]:
        """
        Classify result type and content.
        
        Args:
            result_data: Raw result data
            
        Returns:
            Dict with classification info
        """
        # Handle different result types
        if isinstance(result_data, str):
            # Text content
            content = result_data
            length = len(content.encode())
            
            # Detect language/type by content patterns
            if "#!/usr/bin/env python" in content or "import " in content:
                return {
                    "type": "code",
                    "subtype": "python",
                    "content": content,
                    "length": length,
                    "to_git": length <= self.max_inline_size
                }
            
            if "```" in content or "# " in content[:100]:
                return {
                    "type": "document",
                    "subtype": "markdown",
                    "content": content,
                    "length": length,
                    "to_git": True
                }
            
            return {
                "type": "document",
                "subtype": "text",
                "content": content,
                "length": length,
                "to_git": True
            }
        
        elif isinstance(result_data, dict):
            # Check for code patterns
            if "code" in result_data:
                content = result_data.get("code", "")
                return {
                    "type": "code",
                    "subtype": result_data.get("language", "unknown"),
                    "content": content,
                    "length": len(content.encode()) if isinstance(content, str) else 0,
                    "metadata": result_data,
                    "to_git": True
                }
            
            if "result" in result_data:
                return self._classify_result(result_data.get("result"))
            
            # Default to document
            content = json.dumps(result_data, indent=2)
            return {
                "type": "document",
                "subtype": "json",
                "content": content,
                "length": len(content.encode()),
                "metadata": result_data,
                "to_git": True
            }
        
        elif isinstance(result_data, bytes):
            # Binary content
            return {
                "type": "binary",
                "content": result_data,
                "length": len(result_data),
                "to_git": False
            }
        
        else:
            # Convert to string
            content = str(result_data)
            return {
                "type": "document",
                "subtype": "text",
                "content": content,
                "length": len(content.encode()),
                "to_git": True
            }
    
    def route_result(
        self,
        task_id: str,
        result_data: Any,
        agent: str,
        tool: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Route result to appropriate storage backend.
        
        Args:
            task_id: Task identifier
            result_data: Result data from agent
            agent: Agent name that generated result
            tool: Tool that was executed
            metadata: Additional metadata
            
        Returns:
            Storage reference with location info
        """
        classification = self._classify_result(result_data)
        
        # Add agent/tool metadata
        if metadata is None:
            metadata = {}
        metadata.update({
            "agent": agent,
            "tool": tool,
            "classified_type": classification["type"],
            "classified_subtype": classification.get("subtype", "unknown"),
        })
        
        # Route based on classification
        if classification["type"] == "code":
            return self._store_code(task_id, classification, metadata)
        
        elif classification["type"] == "document":
            return self._store_document(task_id, classification, metadata)
        
        elif classification["type"] == "binary":
            return self._store_binary(task_id, classification, metadata)
        
        else:
            # Fallback: store in database
            return {
                "storage_type": "database",
                "path": "inline",
                "result": str(result_data)[:1000]  # Truncate for DB
            }
    
    def _store_code(
        self,
        task_id: str,
        classification: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store code result in Git"""
        content = classification["content"]
        
        return self.git_storage.store_code_result(
            task_id=task_id,
            code=content,
            language=classification.get("subtype", "python"),
            metadata=metadata
        )
    
    def _store_document(
        self,
        task_id: str,
        classification: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store document result in Git"""
        content = classification["content"]
        
        return self.git_storage.store_document_result(
            task_id=task_id,
            content=content,
            document_type=classification.get("subtype", "markdown"),
            metadata=metadata
        )
    
    def _store_binary(
        self,
        task_id: str,
        classification: Dict[str, Any],
        metadata: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Store binary result in file storage"""
        content = classification["content"]
        
        return self.file_storage.store_file(
            task_id=task_id,
            file_content=content,
            filename="result.bin",
            content_type="application/octet-stream",
            metadata=metadata
        )
    
    def get_result(
        self,
        task_id: str,
        result_type: str = "code",
        result_index: int = 0
    ) -> Optional[str]:
        """Retrieve a stored result"""
        return self.git_storage.get_result(task_id, result_type, result_index)
    
    def list_results(
        self,
        task_id: Optional[str] = None,
        agent: Optional[str] = None
    ) -> list:
        """List stored results with optional filtering"""
        return self.git_storage.list_results(task_id, agent)


# Global instance
_result_router = None


def get_result_router() -> ResultRouter:
    """Get or create global result router instance"""
    global _result_router
    
    if _result_router is None:
        _result_router = ResultRouter()
    
    return _result_router
```

### Step 3: Update TaskStorage

Modify `it-lead-mcp-server/utils/task_storage.py`:

```python
# Add to TaskStorage class

def update_task_result_reference(
    self,
    task_id: str,
    storage_ref: Dict[str, Any],
    metadata: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Update task with result storage reference.
    
    Args:
        task_id: Task identifier
        storage_ref: Storage reference dict from ResultRouter
        metadata: Additional metadata
        
    Returns:
        True if update succeeded
    """
    try:
        cursor = self.connection.cursor()
        
        # Build result JSON
        result_data = {
            "storage_type": storage_ref.get("storage_type", "inline"),
            "path": storage_ref.get("path", ""),
            "commit_sha": storage_ref.get("commit_sha"),
            "file_path": storage_ref.get("file_path"),
            "metadata": metadata
        }
        
        if self.use_sqlite:
            cursor.execute("""
                UPDATE task_registry
                SET result = ?, metadata = ?,
                    updated_at = CURRENT_TIMESTAMP,
                    completed_at = CURRENT_TIMESTAMP
                WHERE task_id = ?
            """, (json.dumps(result_data), json.dumps(metadata or {}), task_id))
        else:
            cursor.execute("""
                UPDATE task_registry
                SET result = %s, metadata = jsonb_set(
                    COALESCE(metadata, '{}'::jsonb),
                    '{result_reference}', %s::jsonb
                ),
                    updated_at = CURRENT_TIMESTAMP,
                    completed_at = CURRENT_TIMESTAMP
                WHERE task_id = %s
            """, (json.dumps(result_data), json.dumps(storage_ref), task_id))
        
        self.connection.commit()
        cursor.close()
        
        print(f"✅ Task result reference updated: {task_id}")
        return True
        
    except Exception as e:
        print(f"❌ Error updating task result: {e}")
        self.connection.rollback()
        return False
```

### Step 4: Update TaskAssignmentManager

Modify `it-lead-mcp-server/utils/task_assignment.py`:

```python
# Add to imports
from .result_router import get_result_router

# In TaskAssignmentManager.__init__(), add:
self.result_router = get_result_router()

# In assign_and_forward_task(), after getting agent response:
# Route result to appropriate storage
if forward_result.get("success"):
    agent_response = forward_result.get("response", {})
    
    # Extract result from agent response
    result_data = agent_response.get("result", {})
    
    if result_data:
        # Route result to storage
        storage_ref = self.result_router.route_result(
            task_id=task_id,
            result_data=result_data,
            agent=primary_agent,
            tool=tool,
            metadata={
                "tool_call": "assign_task",
                "agent_response": agent_response
            }
        )
        
        # Update task with storage reference
        if self.task_storage:
            self.task_storage.update_task_result_reference(
                task_id=task_id,
                storage_ref=storage_ref,
                metadata={
                    "storage_reference": storage_ref,
                    "routing_decision": routing_decision.to_dict() if hasattr(routing_decision, 'to_dict') else {}
                }
            )
```

### Step 5: Add API Endpoints

Add to `it-lead-mcp-server/web-ui/backend/main.py`:

```python
from ..utils.result_router import get_result_router
from ..utils.git_result_storage import get_git_storage
from ..utils.file_result_storage import get_file_storage

@app.get("/api/results/list")
async def list_results(
    task_id: Optional[str] = None,
    agent: Optional[str] = None,
    limit: int = 100
):
    """List stored results with optional filtering"""
    router = get_result_router()
    results = router.list_results(task_id=task_id, agent=agent)
    
    # Limit results
    return {"results": results[:limit]}


@app.get("/api/results/get")
async def get_result(task_id: str, result_type: str = "code"):
    """Get a specific stored result"""
    router = get_result_router()
    content = router.get_result(task_id, result_type)
    
    if content is None:
        raise HTTPException(status_code=404, detail=f"Result not found: {task_id}")
    
    return {"task_id": task_id, "result": content, "type": result_type}


@app.get("/api/results/git/history")
async def get_git_history(task_id: str):
    """Get Git history for a task result"""
    storage = get_git_storage()
    repo = storage._get_git_repo()
    
    if not repo:
        raise HTTPException(status_code=404, detail="Git repository not available")
    
    try:
        from git import Git
        git = Git(storage.repo_path)
        
        # Get log for task directory
        log = git.log("--oneline", f"results/{task_id}/")
        
        return {
            "task_id": task_id,
            "history": [
                {"sha": line.split()[0], "message": " ".join(line.split()[1:])}
                for line in log.strip().split("\n") if line
            ]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get git history: {e}")
```

---

## Usage Examples

### Storing a Result

```python
from it_lead_mcp_server.utils.result_router import get_result_router

# Get the router
router = get_result_router()

# Route a result
result_ref = router.route_result(
    task_id="task-123",
    result_data={
        "code": "def hello():\n    print('Hello, World!')",
        "language": "python",
        "explanation": "This function prints Hello World"
    },
    agent="Implementation Engineer",
    tool="vibe_code"
)

print(result_ref)
# {
#     "storage_type": "git",
#     "commit_sha": "a1b2c3d4...",
#     "code_file": "/var/mcp-results/results/task-123/result.py",
#     ...
# }
```

### Retrieving a Result

```python
from it_lead_mcp_server.utils.result_router import get_result_router

router = get_result_router()

# Get result content
content = router.get_result("task-123", result_type="code")

print(content)
# def hello():
#     print('Hello, World!')
```

### Listing Results

```python
from it_lead_mcp_server.utils.result_router import get_result_router

router = get_result_router()

# List all results
results = router.list_results()

# Filter by task
results = router.list_results(task_id="task-123")

# Filter by agent
results = router.list_results(agent="Implementation Engineer")
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

### Docker Setup

```dockerfile
# Add to Dockerfile
RUN apt-get update && apt-get install -y git

# Mount volume for results
VOLUME /var/mcp-results

# Set environment
ENV MCP_GIT_REPO_PATH=/var/mcp-results
ENV MCP_FILE_STORAGE_PATH=/var/mcp-results/files
```

---

## Testing

### Unit Tests

```python
# test_result_router.py
import pytest
from it_lead_mcp_server.utils.result_router import ResultRouter, get_result_router
from it_lead_mcp_server.utils.git_result_storage import GitResultStorage


def test_route_code_result():
    router = ResultRouter()
    
    result = router.route_result(
        task_id="test-task-1",
        result_data={
            "code": "print('hello')",
            "language": "python"
        },
        agent="Test Agent",
        tool="test_tool"
    )
    
    assert result["storage_type"] == "git"
    assert result["commit_sha"] is not None


def test_route_document_result():
    router = ResultRouter()
    
    result = router.route_result(
        task_id="test-task-2",
        result_data="# Test Document\n\nThis is a test.",
        agent="Test Agent",
        tool="test_tool"
    )
    
    assert result["storage_type"] == "git"
    assert result["document_type"] == "markdown"
```

---

## Deployment

### Step 1: Create Storage Directory

```bash
mkdir -p /var/mcp-results
mkdir -p /var/mcp-results/files
chown www-data:www-data /var/mcp-results  # Or appropriate user
```

### Step 2: Initialize Git Repo

```bash
cd /var/mcp-results
git init
git config user.name "mcp-bot"
git config user.email "mcp-bot@company.com"

# Optional: Add remote
git remote add origin git@github.com:company/mcp-results.git
```

### Step 3: Start Application

```bash
# The router will auto-initialize on first use
python -m it_lead_mcp_server.server
```

---

## Migration from Old System

### Script: Migrate Existing Results

```python
# migrate_results.py
import json
from pathlib import Path
from it_lead_mcp_server.utils.result_router import ResultRouter
from it_lead_mcp_server.utils.task_storage import TaskStorage


def migrate_existing_results():
    """Migrate results from database to new storage"""
    
    # Initialize components
    db = TaskStorage(use_sqlite=True, database="mcp_registry.db")
    router = ResultRouter()
    
    # Get all tasks with results
    tasks = db.get_all_tasks()
    
    migrated = 0
    for task in tasks:
        # Check if task has result in DB
        result = task.get("result")
        if result and isinstance(result, str):
            try:
                # Parse result JSON
                result_data = json.loads(result)
                
                # Migrate to new storage
                storage_ref = router.route_result(
                    task_id=task["task_id"],
                    result_data=result_data,
                    agent=task.get("assigned_to", "unknown"),
                    tool="migration"
                )
                
                # Update task with storage reference
                db.update_task_result_reference(
                    task_id=task["task_id"],
                    storage_ref=storage_ref
                )
                
                migrated += 1
                print(f"Migrated: {task['task_id']}")
                
            except Exception as e:
                print(f"Failed to migrate {task['task_id']}: {e}")
    
    print(f"\nMigrated {migrated} tasks")


if __name__ == "__main__":
    migrate_existing_results()
```

---

## Next Steps

1. **Implement Phase 1** (Foundation) - Create storage modules
2. **Test locally** - Run with sample tasks
3. **Integrate with agents** - Update agent handlers
4. **Add web UI** - Result viewer component
5. **Deploy to production** - Configure S3, backups, etc.

---

## Support

For issues or questions:
- Check Git logs: `tail -f /var/mcp-results/results/*/result.metadata.json`
- Check file storage: `ls -la /var/mcp-results/files/`
- Review database: `psql mcp_registry -c "SELECT * FROM task_results;"`
