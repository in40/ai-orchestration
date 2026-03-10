"""
Agent Git Helper Module for MCP Agent Outputs
Shared helper for agents to push results directly to Git

Each agent pushes to their own branch:
- Implementation Engineer: agent/impl/
- Requirements Engineer: agent/reqs/
- DevOps Engineer: agent/devops/
- Test Engineer: agent/test/
- Security Engineer: agent/security/
- Architect: agent/arch/
"""

import os
import json
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class AgentGitHelper:
    """
    Helper class for MCP agents to push results directly to Git.
    
    Each agent works on their own branch and commits results to:
    /results/{task_id}/ files in their branch
    """

    def __init__(
        self,
        repo_url: str,
        repo_path: str = "/var/mcp-results",
        commit_user: str = "mcp-agent",
        commit_email: str = "mcp-agent@localhost",
        ssh_key_path: Optional[str] = None,
        branch_prefix: str = "agent/"
    ):
        """
        Initialize agent Git helper.

        Args:
            repo_url: Git repository URL (SSH or HTTPS)
            repo_path: Local path for Git clone
            commit_user: Git commit author name
            commit_email: Git commit author email
            ssh_key_path: Optional path to SSH private key
            branch_prefix: Prefix for agent branches (e.g., "agent/")
        """
        self.repo_url = repo_url
        self.repo_path = Path(repo_path)
        self.commit_user = commit_user
        self.commit_email = commit_email
        self.ssh_key_path = ssh_key_path
        self.branch_prefix = branch_prefix
        self.agent_branch: Optional[str] = None

        # Ensure repo path exists
        self.repo_path.mkdir(parents=True, exist_ok=True)

    def _set_git_env(self) -> Dict[str, str]:
        """Set up environment variables for Git operations"""
        env = os.environ.copy()
        env["GIT_AUTHOR_NAME"] = self.commit_user
        env["GIT_AUTHOR_EMAIL"] = self.commit_email
        env["GIT_COMMITTER_NAME"] = self.commit_user
        env["GIT_COMMITTER_EMAIL"] = self.commit_email

        if self.ssh_key_path:
            env["GIT_SSH_COMMAND"] = f"ssh -i {self.ssh_key_path} -o StrictHostKeyChecking=no"

        return env

    def initialize_repo(self, agent_name: str) -> bool:
        """
        Initialize Git repository for agent.

        Args:
            agent_name: Name of the agent (e.g., "implementation-engineer")

        Returns:
            True if initialization successful, False otherwise
        """
        try:
            # Set up branch name for this agent
            self.agent_branch = f"{self.branch_prefix}{agent_name.lower().replace(' ', '-')}"

            # Check if repo already cloned
            if not (self.repo_path / ".git").exists():
                logger.info(f"Cloning repository {self.repo_url} to {self.repo_path}")
                env = self._set_git_env()
                result = subprocess.run(
                    ["git", "clone", self.repo_url, str(self.repo_path)],
                    env=env,
                    capture_output=True,
                    text=True
                )
                if result.returncode != 0:
                    logger.error(f"Failed to clone repo: {result.stderr}")
                    return False

            # Configure user for commits
            env = self._set_git_env()
            subprocess.run(
                ["git", "config", "user.name", self.commit_user],
                cwd=str(self.repo_path),
                env=env,
                capture_output=True
            )
            subprocess.run(
                ["git", "config", "user.email", self.commit_email],
                cwd=str(self.repo_path),
                env=env,
                capture_output=True
            )

            # Checkout/create agent branch
            self._checkout_branch(self.agent_branch)

            logger.info(f"Repository initialized for agent {agent_name} on branch {self.agent_branch}")
            return True

        except Exception as e:
            logger.error(f"Failed to initialize repo for agent {agent_name}: {e}")
            return False

    def _checkout_branch(self, branch_name: str) -> bool:
        """
        Checkout or create a branch.

        Args:
            branch_name: Name of the branch

        Returns:
            True if checkout successful, False otherwise
        """
        try:
            env = self._set_git_env()

            # Try to checkout existing branch
            result = subprocess.run(
                ["git", "checkout", branch_name],
                cwd=str(self.repo_path),
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                logger.debug(f"Checked out existing branch {branch_name}")
                return True

            # Branch doesn't exist, create it
            logger.info(f"Branch {branch_name} doesn't exist, creating...")
            result = subprocess.run(
                ["git", "checkout", "-b", branch_name],
                cwd=str(self.repo_path),
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"Failed to create branch {branch_name}: {result.stderr}")
                return False

            # Push branch to remote
            result = subprocess.run(
                ["git", "push", "-u", "origin", branch_name],
                cwd=str(self.repo_path),
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.warning(f"Failed to push branch {branch_name}: {result.stderr}")
                # Continue anyway - branch may exist remotely

            logger.info(f"Created and checked out branch {branch_name}")
            return True

        except Exception as e:
            logger.error(f"Failed to checkout branch {branch_name}: {e}")
            return False

    def store_result(
        self,
        task_id: str,
        content: str,
        filename: str,
        content_type: str = "code",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Store a result file and commit to Git.

        Args:
            task_id: Task identifier
            content: Content to store
            filename: Filename for the result
            content_type: Type of content (code, document, config, etc.)
            metadata: Additional metadata to store

        Returns:
            Dict with storage reference including Git URL
        """
        try:
            # Create result directory
            result_dir = self.repo_path / "results" / task_id
            result_dir.mkdir(parents=True, exist_ok=True)

            # Determine file extension based on content type
            extension_map = {
                "code": ".py",
                "document": ".md",
                "config": ".json",
                "terraform": ".tf",
                "yaml": ".yaml",
                "markdown": ".md",
            }
            extension = extension_map.get(content_type, ".txt")
            filepath = result_dir / f"{filename}{extension}"

            # Write content to file
            with open(filepath, "w") as f:
                f.write(content)

            # Store metadata if provided
            if metadata:
                metadata_file = result_dir / "metadata.json"
                metadata_with_timestamp = {
                    **metadata,
                    "stored_at": datetime.utcnow().isoformat(),
                    "agent_branch": self.agent_branch
                }
                with open(metadata_file, "w") as f:
                    json.dump(metadata_with_timestamp, f, indent=2)

            # Git operations
            env = self._set_git_env()

            # Stage the file
            subprocess.run(
                ["git", "add", str(filepath.relative_to(self.repo_path))],
                cwd=str(self.repo_path),
                env=env,
                capture_output=True
            )

            # Commit with message
            commit_msg = f"[{self.agent_branch}] Add result for task {task_id}: {filename}"
            result = subprocess.run(
                ["git", "commit", "-m", commit_msg],
                cwd=str(self.repo_path),
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                # No changes to commit
                if "nothing to commit" in result.stderr.lower():
                    logger.info(f"No changes to commit for task {task_id}")
                else:
                    logger.error(f"Git commit failed: {result.stderr}")

            # Push to remote
            result = subprocess.run(
                ["git", "push", "origin", self.agent_branch],
                cwd=str(self.repo_path),
                env=env,
                capture_output=True,
                text=True
            )

            if result.returncode != 0:
                logger.error(f"Git push failed: {result.stderr}")
                return {
                    "success": False,
                    "error": f"Failed to push to Git: {result.stderr}"
                }

            # Construct Git URL for the stored file
            git_url = f"{self.repo_url}/tree/{self.agent_branch}/results/{task_id}/{filename}{extension}"

            logger.info(f"Result stored and pushed: {git_url}")
            return {
                "success": True,
                "git_url": git_url,
                "file_path": str(filepath.relative_to(self.repo_path)),
                "commit_msg": commit_msg
            }

        except Exception as e:
            logger.error(f"Failed to store result for task {task_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }

    def store_code_result(
        self,
        task_id: str,
        code: str,
        language: str,
        filename: str = "result",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store a code result."""
        extension_map = {
            "python": ".py",
            "javascript": ".js",
            "typescript": ".ts",
            "java": ".java",
            "go": ".go",
            "rust": ".rs",
            "ruby": ".rb",
            "php": ".php",
            "swift": ".swift",
            "kotlin": ".kt",
            "terraform": ".tf",
            "yaml": ".yaml",
            "json": ".json",
        }
        extension = extension_map.get(language.lower(), ".py")
        return self.store_result(
            task_id=task_id,
            content=code,
            filename=filename,
            content_type="code",
            metadata=metadata
        )

    def store_document_result(
        self,
        task_id: str,
        content: str,
        document_type: str = "markdown",
        filename: str = "result",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store a document result."""
        extension_map = {
            "markdown": ".md",
            "text": ".txt",
            "html": ".html",
        }
        extension = extension_map.get(document_type.lower(), ".md")
        return self.store_result(
            task_id=task_id,
            content=content,
            filename=filename,
            content_type="document",
            metadata=metadata
        )

    def store_config_result(
        self,
        task_id: str,
        content: str,
        config_type: str = "json",
        filename: str = "config",
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Store a configuration result."""
        extension_map = {
            "json": ".json",
            "yaml": ".yaml",
            "yml": ".yaml",
            "terraform": ".tf",
            "xml": ".xml",
            "ini": ".ini",
        }
        extension = extension_map.get(config_type.lower(), ".json")
        return self.store_result(
            task_id=task_id,
            content=content,
            filename=filename,
            content_type="config",
            metadata=metadata
        )


# Global instance cache
_agent_git_helpers: Dict[str, AgentGitHelper] = {}


def get_agent_git_helper(
    agent_name: str,
    repo_url: Optional[str] = None,
    **kwargs
) -> AgentGitHelper:
    """
    Get or create agent Git helper instance.

    Args:
        agent_name: Name of the agent
        repo_url: Git repository URL (uses env var if not provided)
        **kwargs: Additional arguments for AgentGitHelper

    Returns:
        AgentGitHelper instance
    """
    # Get repo URL from kwargs or environment
    repo_url = repo_url or os.environ.get("MCP_GIT_REPO_URL")

    if not repo_url:
        raise ValueError(
            "MCP_GIT_REPO_URL environment variable not set and no repo_url provided"
        )

    # Create cache key
    cache_key = f"{agent_name}:{repo_url}"

    if cache_key not in _agent_git_helpers:
        # Get agent-specific branch prefix
        branch_prefix = kwargs.pop("branch_prefix", "agent/")

        helper = AgentGitHelper(
            repo_url=repo_url,
            branch_prefix=branch_prefix,
            **kwargs
        )

        # Initialize the repo
        if not helper.initialize_repo(agent_name):
            logger.warning(f"Failed to initialize Git repo for agent {agent_name}")

        _agent_git_helpers[cache_key] = helper

    return _agent_git_helpers[cache_key]
