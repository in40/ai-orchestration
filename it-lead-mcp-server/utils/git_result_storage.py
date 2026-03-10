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
import tempfile
import subprocess

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
        commit_email: str = "mcp-bot@localhost",
        remote_url: Optional[str] = None
    ):
        """
        Initialize Git storage.
        
        Args:
            repo_path: Path to the Git repository (local path or SSH URL for remote)
            commit_user: Git commit author name
            commit_email: Git commit author email
            remote_url: Optional remote URL for push/pull
        """
        self.repo_path = Path(repo_path)
        self.commit_user = commit_user
        self.commit_email = commit_email
        self.remote_url = remote_url
        self._is_remote = repo_path.startswith("ssh://") or repo_path.startswith("git@")
        self._local_clone_path = Path(tempfile.gettempdir()) / "mcp-git-clone"
        self._ensure_repo()
    
    def _is_git_repo(self, path: Path) -> bool:
        """Check if path is a Git repository"""
        return (path / ".git").exists()
    
    def _run_git_command(self, args: list, cwd: Path, check: bool = True) -> subprocess.CompletedProcess:
        """Run a git command with proper configuration"""
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = self.commit_user
        env["GIT_AUTHOR_EMAIL"] = self.commit_email
        env["GIT_COMMITTER_NAME"] = self.commit_user
        env["GIT_COMMITTER_EMAIL"] = self.commit_email
        
        cmd = ["git"] + args
        return subprocess.run(cmd, cwd=str(cwd), env=env, capture_output=True, text=True, check=check)
    
    def _ensure_repo(self) -> None:
        """Ensure Git repository exists and is initialized"""
        if self._is_remote:
            # For remote repos, clone to local temporary directory
            try:
                if self._is_git_repo(self._local_clone_path):
                    # Fetch latest changes
                    self._run_git_command(["fetch", "origin"], self._local_clone_path)
                    self._run_git_command(["reset", "--hard", "origin/master"], self._local_clone_path)
                else:
                    # Clone the remote repository
                    logger.info(f"Cloning remote Git repository to {self._local_clone_path}")
                    self._run_git_command(["clone", str(self.repo_path), str(self._local_clone_path)], Path(tempfile.gettempdir()))
                # Configure user for commits
                self._run_git_command(["config", "user.name", self.commit_user], self._local_clone_path, check=False)
                self._run_git_command(["config", "user.email", self.commit_email], self._local_clone_path, check=False)
                logger.info(f"Git repository initialized at {self._local_clone_path}")
            except subprocess.CalledProcessError as e:
                logger.error(f"Failed to initialize Git repo: {e.stderr}")
                raise
        else:
            # Local repository
            self.repo_path.mkdir(parents=True, exist_ok=True)
            
            if not self._is_git_repo(self.repo_path):
                try:
                    self._run_git_command(["init"], self.repo_path)
                    self._run_git_command(["config", "user.name", self.commit_user], self.repo_path)
                    self._run_git_command(["config", "user.email", self.commit_email], self.repo_path)
                    logger.info(f"Initialized new Git repository at {self.repo_path}")
                except subprocess.CalledProcessError as e:
                    logger.error(f"Failed to initialize Git repo: {e.stderr}")
                    raise
            
            # Add remote if configured
            if self.remote_url:
                try:
                    result = self._run_git_command(["remote", "get-url", "origin"], self.repo_path, check=False)
                    if result.returncode != 0:
                        self._run_git_command(["remote", "add", "origin", self.remote_url], self.repo_path)
                except subprocess.CalledProcessError:
                    pass
    
    def _get_local_path(self) -> Path:
        """Get the local path to work with (clone for remote repos)"""
        return self._local_clone_path if self._is_remote else self.repo_path
    
    def _push_to_remote(self) -> bool:
        """Push commits to remote repository"""
        if not self._is_remote:
            return True
        
        try:
            self._run_git_command(["add", "."], self._local_clone_path)
            self._run_git_command(["commit", "-m", "Update results", "--allow-empty"], self._local_clone_path, check=False)
            self._run_git_command(["push", "origin", "master"], self._local_clone_path)
            logger.info("Pushed to remote repository")
            return True
        except subprocess.CalledProcessError as e:
            logger.warning(f"Git push failed (non-critical): {e.stderr}")
            return True  # Don't fail if push fails
    
    def _git_commit(self, message: str, files: list) -> Optional[str]:
        """
        Create a Git commit with the specified files.
        
        Args:
            message: Commit message
            files: List of file paths to add and commit
            
        Returns:
            Commit SHA or None if commit failed
        """
        local_path = self._get_local_path()
        
        try:
            # Add all files
            self._run_git_command(["add"] + [str(f) for f in files], local_path)
            
            # Create commit
            result = self._run_git_command(["commit", "-m", message], local_path, check=False)
            
            if result.returncode == 0:
                # Get the commit SHA
                sha_result = self._run_git_command(["rev-parse", "HEAD"], local_path)
                commit_sha = sha_result.stdout.strip()
                logger.info(f"Created commit {commit_sha}: {message}")
                
                # Push to remote if configured
                self._push_to_remote()
                
                return commit_sha
            else:
                # Check if there's nothing to commit
                if "nothing to commit" in result.stdout + result.stderr:
                    logger.info("No changes to commit")
                    sha_result = self._run_git_command(["rev-parse", "HEAD"], local_path)
                    return sha_result.stdout.strip()
                else:
                    logger.error(f"Git commit failed: {result.stderr}")
                    return None
                    
        except Exception as e:
            logger.error(f"Git commit failed: {e}")
            return None
    
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
        local_path = self._get_local_path()
        
        # Create task directory
        task_dir = local_path / "results" / task_id
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
            "file_extension": ext,
            "is_remote": self._is_remote,
            "remote_url": str(self.repo_path) if self._is_remote else None
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
        local_path = self._get_local_path()
        
        # Create task directory
        task_dir = local_path / "results" / task_id
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
            "file_extension": ext,
            "is_remote": self._is_remote,
            "remote_url": str(self.repo_path) if self._is_remote else None
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
        local_path = self._get_local_path()
        
        # Create task directory
        task_dir = local_path / "results" / task_id / "configs"
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
            "file_name": filename,
            "is_remote": self._is_remote,
            "remote_url": str(self.repo_path) if self._is_remote else None
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
        local_path = self._get_local_path()
        task_dir = local_path / "results" / task_id
        
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
        local_path = self._get_local_path()
        results = []
        results_dir = local_path / "results"
        
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


def get_git_storage(repo_path: Optional[str] = None, remote_url: Optional[str] = None) -> GitResultStorage:
    """Get or create global Git storage instance"""
    global _git_storage
    
    if _git_storage is None:
        repo = repo_path or os.environ.get(
            "MCP_GIT_REPO_PATH",
            "/var/mcp-results"
        )
        _git_storage = GitResultStorage(repo_path=repo, remote_url=remote_url)
    
    return _git_storage
