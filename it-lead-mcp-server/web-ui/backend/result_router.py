"""
Result Router for MCP Agent Outputs
Routes results to appropriate storage backends based on content type
"""
import os
import json
from pathlib import Path
from typing import Dict, Any, Optional
import logging

# Import storage modules
from git_result_storage import get_git_storage, GitResultStorage
from file_result_storage import get_file_storage, FileResultStorage

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
        max_inline_size: int = 100 * 1024,  # 100KB
        ssh_host: Optional[str] = None,
        ssh_user: Optional[str] = None,
        ssh_password: Optional[str] = None
    ):
        """
        Initialize result router.
        
        Args:
            git_storage: Git storage instance for text/code
            file_storage: File storage instance for large/binary files
            max_inline_size: Maximum size for inline DB storage
            ssh_host: SSH host for remote file storage
            ssh_user: SSH user for remote file storage
            ssh_password: SSH password for remote file storage
        """
        self.git_storage = git_storage or get_git_storage()
        self.file_storage = file_storage or get_file_storage(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password
        )
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
            
            # Check for code-like patterns
            if any(pattern in content for pattern in ["def ", "class ", "function", "const ", "let ", "var "]):
                return {
                    "type": "code",
                    "subtype": "unknown",
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
                    "subtype": result_data.get("language", result_data.get("subtype", "unknown")),
                    "content": content,
                    "length": len(content.encode()) if isinstance(content, str) else 0,
                    "metadata": result_data,
                    "to_git": True
                }
            
            if "result" in result_data:
                return self._classify_result(result_data.get("result"))
            
            # Check if it looks like code
            content_str = json.dumps(result_data, indent=2)
            if any(pattern in content_str for pattern in ["def ", "class ", "function", "const ", "let ", "var "]):
                return {
                    "type": "code",
                    "subtype": "json",
                    "content": content_str,
                    "length": len(content_str.encode()),
                    "metadata": result_data,
                    "to_git": True
                }
            
            # Default to document
            return {
                "type": "document",
                "subtype": "json",
                "content": content_str,
                "length": len(content_str.encode()),
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


def get_result_router(
    ssh_host: Optional[str] = None,
    ssh_user: Optional[str] = None,
    ssh_password: Optional[str] = None
) -> ResultRouter:
    """Get or create global result router instance"""
    global _result_router
    
    if _result_router is None:
        _result_router = ResultRouter(
            ssh_host=ssh_host,
            ssh_user=ssh_user,
            ssh_password=ssh_password
        )
    
    return _result_router
