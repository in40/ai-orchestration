"""
File-based Result Storage for MCP Agent Outputs
Stores large files and binary artifacts on local disk or SSH remote
"""
import os
import uuid
import hashlib
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging
import json
import subprocess
import tempfile

logger = logging.getLogger(__name__)


class FileResultStorage:
    """
    Stores MCP agent results as files on disk or in remote storage via SSH.
    
    Large files (images, binaries, large documents) are stored here.
    Small text files and code go to Git storage instead.
    """
    
    def __init__(
        self,
        base_path: str = "/var/mcp-results/files",
        max_file_size_mb: int = 100,
        storage_backend: str = "local",  # "local" or "ssh"
        ssh_host: Optional[str] = None,
        ssh_user: Optional[str] = None,
        ssh_password: Optional[str] = None
    ):
        """
        Initialize file storage.
        
        Args:
            base_path: Base directory for storing files
            max_file_size_mb: Maximum file size in MB
            storage_backend: Storage backend ("local" or "ssh")
            ssh_host: SSH host for remote storage (required if backend is "ssh")
            ssh_user: SSH user for remote storage (required if backend is "ssh")
            ssh_password: SSH password for remote storage
        """
        self.base_path = Path(base_path)
        self.max_file_size_mb = max_file_size_mb
        self.storage_backend = storage_backend
        self.ssh_host = ssh_host
        self.ssh_user = ssh_user
        self.ssh_password = ssh_password
        self._ensure_base_path()
    
    def _ensure_base_path(self) -> None:
        """Ensure base path exists"""
        if self.storage_backend == "local":
            self.base_path.mkdir(parents=True, exist_ok=True)
    
    def _run_ssh_command(self, command: str) -> subprocess.CompletedProcess:
        """Run a command on remote server via SSH"""
        if self.storage_backend != "ssh":
            raise RuntimeError("SSH backend not configured")
        
        cmd = [
            "sshpass", "-e", "ssh",
            "-o", "StrictHostKeyChecking=no",
            f"{self.ssh_user}@{self.ssh_host}",
            command
        ]
        
        env = os.environ.copy()
        env["SSHPASS"] = self.ssh_password or ""
        
        return subprocess.run(cmd, env=env, capture_output=True, text=True, check=False)
    
    def _run_ssh_scp(self, local_path: Path, remote_path: str) -> bool:
        """Copy file to remote via SCP"""
        if self.storage_backend != "ssh":
            raise RuntimeError("SSH backend not configured")
        
        cmd = [
            "sshpass", "-e", "scp",
            "-o", "StrictHostKeyChecking=no",
            str(local_path),
            f"{self.ssh_user}@{self.ssh_host}:{remote_path}"
        ]
        
        env = os.environ.copy()
        env["SSHPASS"] = self.ssh_password or ""
        
        result = subprocess.run(cmd, env=env, capture_output=True, text=True)
        return result.returncode == 0
    
    def _calculate_checksum(self, content: bytes) -> str:
        """Calculate SHA256 checksum of content"""
        return hashlib.sha256(content).hexdigest()
    
    def _get_remote_path(self, task_id: str, filename: str) -> str:
        """Get remote file path"""
        return f"/home/{self.ssh_user}/mcp-files/{task_id}/{filename}"
    
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
        
        # Calculate checksum
        checksum = self._calculate_checksum(file_content)
        
        # Generate unique filename
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
        
        if self.storage_backend == "ssh":
            # Store on remote server
            return self._store_ssh(task_id, file_content, unique_filename, metadata)
        else:
            # Store locally
            return self._store_local(task_id, file_content, unique_filename, metadata)
    
    def _store_local(
        self,
        task_id: str,
        file_content: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store file locally"""
        # Create task directory
        task_dir = self.base_path / task_id
        task_dir.mkdir(parents=True, exist_ok=True)
        
        filepath = task_dir / filename
        filepath.write_bytes(file_content)
        
        # Write metadata
        meta_file = task_dir / "file.metadata.json"
        meta_data = {
            "task_id": task_id,
            "storage_type": "local",
            "filename": filename,
            "original_filename": os.path.basename(filename),
            "content_type": content_type,
            "file_size": len(file_content),
            "checksum": checksum,
            "created_at": datetime.now().isoformat(),
            **(metadata or {})
        }
        meta_file.write_text(json.dumps(meta_data, indent=2))
        
        return {
            "storage_type": "local",
            "file_path": str(filepath),
            "file_size": len(file_content),
            "checksum": checksum,
            "filename": filename,
            "original_filename": os.path.basename(filename),
            "content_type": content_type,
            "metadata_file": str(meta_file)
        }
    
    def _store_ssh(
        self,
        task_id: str,
        file_content: bytes,
        filename: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store file on remote server via SSH/SCP"""
        # Calculate checksum
        checksum = self._calculate_checksum(file_content)
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(mode='wb', delete=False, suffix=f"_{filename}") as tmp:
            tmp.write(file_content)
            tmp_path = Path(tmp.name)
        
        try:
            # Create remote directory
            remote_dir = f"/home/{self.ssh_user}/mcp-files/{task_id}"
            self._run_ssh_command(f"mkdir -p {remote_dir}")
            
            # Copy file via SCP
            remote_path = f"/home/{self.ssh_user}/mcp-files/{task_id}/{filename}"
            if not self._run_ssh_scp(tmp_path, remote_path):
                raise RuntimeError(f"Failed to copy file to {remote_path}")
            
            # Write metadata on remote
            meta_data = {
                "task_id": task_id,
                "storage_type": "ssh",
                "filename": filename,
                "original_filename": os.path.basename(filename),
                "content_type": content_type,
                "file_size": len(file_content),
                "checksum": checksum,
                "created_at": datetime.now().isoformat(),
                **(metadata or {})
            }
            
            meta_json = json.dumps(meta_data, indent=2)
            self._run_ssh_command(f"mkdir -p /home/{self.ssh_user}/mcp-files/{task_id}")
            self._run_ssh_command(f"echo '{meta_json}' > /home/{self.ssh_user}/mcp-files/{task_id}/file.metadata.json")
            
            return {
                "storage_type": "ssh",
                "ssh_host": self.ssh_host,
                "file_path": remote_path,
                "file_size": len(file_content),
                "checksum": checksum,
                "filename": filename,
                "original_filename": os.path.basename(filename),
                "content_type": content_type,
                "remote_metadata": f"/home/{self.ssh_user}/mcp-files/{task_id}/file.metadata.json"
            }
        finally:
            # Clean up temp file
            tmp_path.unlink(missing_ok=True)
    
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
        if self.storage_backend == "ssh":
            return self._get_ssh_file(task_id, filename)
        else:
            return self._get_local_file(task_id, filename)
    
    def _get_local_file(
        self,
        task_id: str,
        filename: str
    ) -> Optional[bytes]:
        """Get file from local storage"""
        filepath = self.base_path / task_id / filename
        
        if filepath.exists():
            return filepath.read_bytes()
        
        return None
    
    def _get_ssh_file(
        self,
        task_id: str,
        filename: str
    ) -> Optional[bytes]:
        """Get file from remote storage via SCP"""
        remote_path = f"/home/{self.ssh_user}/mcp-files/{task_id}/{filename}"
        
        # Use SCP to copy to temp location
        with tempfile.NamedTemporaryFile(delete=True) as tmp:
            cmd = [
                "sshpass", "-e", "scp",
                "-o", "StrictHostKeyChecking=no",
                f"{self.ssh_user}@{self.ssh_host}:{remote_path}",
                tmp.name
            ]
            
            env = os.environ.copy()
            env["SSHPASS"] = self.ssh_password or ""
            
            result = subprocess.run(cmd, env=env, capture_output=True, text=True)
            
            if result.returncode == 0:
                return Path(tmp.name).read_bytes()
        
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


def get_file_storage(
    base_path: Optional[str] = None,
    ssh_host: Optional[str] = None,
    ssh_user: Optional[str] = None,
    ssh_password: Optional[str] = None
) -> FileResultStorage:
    """Get or create global file storage instance"""
    global _file_storage
    
    if _file_storage is None:
        base = base_path or os.environ.get(
            "MCP_FILE_STORAGE_PATH",
            "/var/mcp-results/files"
        )
        backend = os.environ.get("MCP_STORAGE_BACKEND", "local")
        max_size = int(os.environ.get("MCP_MAX_FILE_SIZE_MB", 100))
        
        _file_storage = FileResultStorage(
            base_path=base,
            max_file_size_mb=max_size,
            storage_backend=backend,
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password
        )
    
    return _file_storage
