"""
DevOps Release Engineer Server Handlers for MCP Server
Implements DevOps Release Engineer specific functionality for CI/CD, IaC, and deployment orchestration
"""
import time
import json
import os
import re
import subprocess
import requests
import logging
from typing import Dict, Any, List, Optional
from devops_release_engineer_mcp_server.utils.json_rpc import JsonRpcHandler, JsonRpcMessage

# Configure deployment logging
DEPLOYMENT_LOG_FILE = "/tmp/devops_deployment.log"
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(DEPLOYMENT_LOG_FILE),
        logging.StreamHandler()
    ]
)
deployment_logger = logging.getLogger(__name__)

# Default Git repository URL for deployment results
DEFAULT_GIT_REPO_URL = os.environ.get("MCP_GIT_REPO_URL", "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git")


class DevOpsReleaseEngineerHandlers:
    """Handles DevOps Release Engineer specific MCP server methods"""

    def __init__(self, enable_registry: bool = False, use_postgres: bool = False,
                 postgres_config: Optional[Dict[str, Any]] = None, client_handlers=None,
                 llm_provider_url: Optional[str] = None,
                 llm_model: Optional[str] = None,
                 prompts_dir: str = ".",
                 task_storage: Any = None):
        # DevOps Release Engineer tools - no example tools for this domain-specific server
        self.tools: List[Dict[str, Any]] = [
            {
                "name": "git_commit_and_push",
                "description": "Perform Git commit and push operations for code changes",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "repository_path": {"type": "string", "description": "Path to the Git repository"},
                        "files_to_commit": {"type": "array", "items": {"type": "string"}, "description": "Files to include in the commit"},
                        "commit_message": {"type": "string", "description": "Commit message describing the changes"},
                        "branch_name": {"type": "string", "description": "Branch to commit to (defaults to current branch)"},
                        "push_to_remote": {"type": "boolean", "default": True, "description": "Whether to push changes to remote repository"},
                        "remote_name": {"type": "string", "default": "origin", "description": "Remote repository name to push to"}
                    },
                    "required": ["repository_path", "files_to_commit", "commit_message"]
                }
            },
            {
                "name": "configure_ci_cd_pipeline",
                "description": "Configure and maintain CI/CD pipelines for automated software delivery",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "source_repository": {"type": "string", "description": "Source code repository"},
                        "target_platform": {"type": "string", "enum": ["github", "gitlab", "jenkins", "azure-devops"], "description": "Target CI/CD platform"},
                        "build_requirements": {"type": "array", "items": {"type": "string"}, "description": "Build requirements and dependencies"},
                        "deployment_targets": {"type": "array", "items": {"type": "string"}, "description": "Target deployment environments"},
                        "security_requirements": {"type": "array", "items": {"type": "string"}, "description": "Security requirements for the pipeline"}
                    },
                    "required": ["source_repository", "target_platform", "build_requirements", "deployment_targets"]
                }
            },
            {
                "name": "manage_infrastructure_provisioning",
                "description": "Manage infrastructure provisioning using Infrastructure as Code (IaC)",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "infrastructure_requirements": {"type": "array", "items": {"type": "object"}, "description": "Requirements for infrastructure provisioning"},
                        "target_platform": {"type": "string", "enum": ["aws", "azure", "gcp", "kubernetes", "on-premises"], "description": "Target infrastructure platform"},
                        "iac_tool": {"type": "string", "enum": ["terraform", "cloudformation", "arm-templates", "pulumi"], "description": "Infrastructure as Code tool to use"},
                        "scaling_requirements": {"type": "object", "description": "Auto-scaling and load balancing requirements"},
                        "security_configurations": {"type": "array", "items": {"type": "string"}, "description": "Security configurations for infrastructure"}
                    },
                    "required": ["infrastructure_requirements", "target_platform", "iac_tool"]
                }
            },
            {
                "name": "orchestrate_deployments",
                "description": "Orchestrate deployments across different environments",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "application_artifacts": {"type": "string", "description": "Application artifacts to deploy"},
                        "target_environments": {"type": "array", "items": {"type": "string", "enum": ["development", "staging", "production"]}, "description": "Target environments for deployment"},
                        "deployment_strategy": {"type": "string", "enum": ["blue-green", "rolling", "canary", "recycle"], "default": "rolling", "description": "Deployment strategy to use"},
                        "environment_configurations": {"type": "object", "description": "Environment-specific configurations"},
                        "rollback_procedures": {"type": "object", "description": "Rollback procedures for each environment"}
                    },
                    "required": ["application_artifacts", "target_environments"]
                }
            },
            {
                "name": "monitor_deployment_health",
                "description": "Monitor deployment health and perform rollbacks on failures",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "deployed_application": {"type": "string", "description": "Application being monitored"},
                        "target_environment": {"type": "string", "description": "Environment being monitored"},
                        "health_metrics": {"type": "array", "items": {"type": "string"}, "description": "Health metrics to monitor"},
                        "failure_thresholds": {"type": "object", "description": "Thresholds that trigger rollback"},
                        "monitoring_duration": {"type": "string", "description": "Duration to monitor after deployment"},
                        "rollback_criteria": {"type": "array", "items": {"type": "string"}, "description": "Criteria for triggering rollback"}
                    },
                    "required": ["deployed_application", "target_environment", "health_metrics"]
                }
            },
            {
                "name": "optimize_build_processes",
                "description": "Optimize build times and resource utilization",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "build_configuration": {"type": "string", "description": "Current build configuration"},
                        "build_metrics": {"type": "object", "description": "Current build metrics and performance data"},
                        "resource_constraints": {"type": "object", "description": "Resource constraints and limitations"},
                        "optimization_goals": {"type": "array", "items": {"type": "string", "enum": ["speed", "cost", "reliability", "resource_efficiency"]}, "description": "Goals for optimization"},
                        "pipeline_history": {"type": "array", "items": {"type": "object"}, "description": "Historical data about previous builds"}
                    },
                    "required": ["build_configuration", "build_metrics", "optimization_goals"]
                }
            },
            {
                "name": "generate_terraform_config",
                "description": "Generate Terraform configuration files for infrastructure provisioning",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "resource_type": {"type": "string", "description": "Type of AWS resource to provision"},
                        "resource_config": {"type": "object", "description": "Resource configuration details"},
                        "output_file": {"type": "string", "description": "Output Terraform file path"},
                        "variable_definitions": {"type": "array", "items": {"type": "object"}, "description": "Variable definitions for the configuration"}
                    },
                    "required": ["resource_type", "resource_config", "output_file"]
                }
            },
            {
                "name": "generate_pipeline_config",
                "description": "Generate CI/CD pipeline configuration for various platforms",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "platform": {"type": "string", "enum": ["github", "gitlab", "jenkins"], "description": "CI/CD platform"},
                        "stages": {"type": "array", "items": {"type": "string"}, "description": "Pipeline stages"},
                        "trigger_branch": {"type": "string", "description": "Branch that triggers the pipeline"},
                        "docker_image": {"type": "string", "description": "Docker image to use for build"},
                        "test_command": {"type": "string", "description": "Test command to run"},
                        "deploy_command": {"type": "string", "description": "Deployment command"}
                    },
                    "required": ["platform", "stages"]
                }
            },
            {
                "name": "deploy_web_application",
                "description": "Deploy a Python web application from Git repository using Docker container isolation",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task identifier"},
                        "git_url": {"type": "string", "description": "Git URL to fetch result.py from"},
                        "result_path": {"type": "string", "description": "Path to result.py in git repo"},
                        "memory_limit": {"type": "string", "default": "256m", "description": "Memory limit for container"},
                        "cpu_limit": {"type": "string", "default": "0.5", "description": "CPU limit for container"}
                    },
                    "required": ["task_id", "git_url", "result_path"]
                }
            },
            {
                "name": "stop_deployment",
                "description": "Stop and remove a deployed application container",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task identifier of deployment to stop"}
                    },
                    "required": ["task_id"]
                }
            },
            {
                "name": "start_deployment",
                "description": "Start a stopped deployment container",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "container_id": {"type": "string", "description": "Container ID or name to start"}
                    },
                    "required": ["container_id"]
                }
            },
            {
                "name": "delete_deployment",
                "description": "Permanently delete a deployment container and its data",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "container_id": {"type": "string", "description": "Container ID or name to delete"}
                    },
                    "required": ["container_id"]
                }
            },
            {
                "name": "list_deployments",
                "description": "List all active deployments with their status and URLs",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "status_filter": {"type": "string", "default": "running", "description": "Filter by status (running, stopped, all)"}
                    }
                }
            },
            {
                "name": "get_deployment_status",
                "description": "Get status and health of a specific deployment",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_id": {"type": "string", "description": "Task identifier"}
                    },
                    "required": ["task_id"]
                }
            }
        ]

        # DevOps Release Engineer resources
        self.resources: List[Dict[str, Any]] = [
            {
                "uri": "devops://resource/deployment-status",
                "name": "Deployment Status Dashboard",
                "description": "Current deployment status across all environments"
            },
            {
                "uri": "devops://resource/build-metrics",
                "name": "Build Metrics Report",
                "description": "Build performance metrics and statistics"
            },
            {
                "uri": "devops://resource/infrastructure-status",
                "name": "Infrastructure Status",
                "description": "Current infrastructure provisioning status"
            },
            {
                "uri": "devops://resource/deployment-history",
                "name": "Deployment History",
                "description": "Historical deployment records with status and timestamps"
            }
        ]

        # DevOps Release Engineer prompts
        self.prompts: List[Dict[str, Any]] = [
            {
                "name": "deployment_prompt",
                "description": "Prompt for orchestrating deployments with LLM assistance",
                "arguments": [
                    {
                        "name": "application_name",
                        "type": "string",
                        "description": "Name of the application to deploy"
                    },
                    {
                        "name": "target_environment",
                        "type": "string",
                        "description": "Target environment for deployment"
                    },
                    {
                        "name": "deployment_strategy",
                        "type": "string",
                        "description": "Deployment strategy to use"
                    }
                ]
            },
            {
                "name": "pipeline_config_prompt",
                "description": "Prompt for generating CI/CD pipeline configurations",
                "arguments": [
                    {
                        "name": "project_type",
                        "type": "string",
                        "description": "Type of project (e.g., python, node, java)"
                    },
                    {
                        "name": "platform",
                        "type": "string",
                        "description": "CI/CD platform to use"
                    }
                ]
            },
            {
                "name": "infrastructure_prompt",
                "description": "Prompt for generating infrastructure provisioning configurations",
                "arguments": [
                    {
                        "name": "infrastructure_type",
                        "type": "string",
                        "description": "Type of infrastructure (e.g., web-server, database, load-balancer)"
                    },
                    {
                        "name": "cloud_provider",
                        "type": "string",
                        "description": "Cloud provider to use (aws, azure, gcp)"
                    }
                ]
            }
        ]

        # Optional registry functionality
        self.enable_registry = enable_registry
        self.service_registry = None
        self.postgres_config = postgres_config or {}

        # Task storage for updating task registry after deployments
        self.task_storage = task_storage

        # Client handlers for server-initiated requests
        self.client_handlers = client_handlers

        # LLM Configuration - MUST come from environment or command line, NO defaults
        import os
        if not llm_provider_url:
            llm_provider_url = os.environ.get("LLM_PROVIDER_URL")
            if not llm_provider_url:
                raise ValueError("LLM_PROVIDER_URL environment variable not set - must be defined in .env file")
        if not llm_model:
            llm_model = os.environ.get("LLM_MODEL")
            if not llm_model:
                raise ValueError("LLM_MODEL environment variable not set - must be defined in .env file")
        
        self.llm_provider_url = llm_provider_url
        self.llm_model = llm_model
        self.prompts_dir = prompts_dir

        if self.enable_registry:
            self._initialize_registry(use_postgres)

    def _initialize_registry(self, use_postgres: bool):
        """Initialize the service registry - PostgreSQL required"""
        try:
            if use_postgres and self.postgres_config:
                from devops_release_engineer_mcp_server.utils.postgres_registry_db import PostgresServiceRegistry
                self.service_registry = PostgresServiceRegistry(
                    host=self.postgres_config.get("host", "localhost"),
                    port=self.postgres_config.get("port", 5432),
                    database=self.postgres_config.get("database", "mcp_registry"),
                    user=self.postgres_config.get("user", "postgres"),
                    password=self.postgres_config.get("password", "")
                )
            else:
                from devops_release_engineer_mcp_server.utils.service_registry_db import ServiceRegistryDB
                self.service_registry = ServiceRegistryDB()
        except Exception as e:
            print(f"❌ Failed to initialize registry (PostgreSQL required): {e}")
            raise

    def _validate_git_repository(self, git_url: str = None) -> dict:
        """
        Validate that the Git repository is accessible and operational.

        Args:
            git_url: Git repository URL to validate (uses default if not provided)

        Returns:
            Dictionary with 'success' boolean and 'message' with details
        """
        import subprocess
        import tempfile
        import os

        git_repo_url = git_url or DEFAULT_GIT_REPO_URL

        deployment_logger.info(f"Validating Git repository: {git_repo_url}")

        try:
            # Create a temporary directory for the test clone
            with tempfile.TemporaryDirectory() as temp_dir:
                # Try to clone the repository (shallow clone for speed)
                result = subprocess.run(
                    ["git", "clone", "--depth", "1", git_repo_url, temp_dir],
                    capture_output=True,
                    text=True,
                    timeout=30
                )

                if result.returncode == 0:
                    deployment_logger.info(f"✅ Git repository is accessible: {git_repo_url}")
                    return {
                        "success": True,
                        "message": f"Git repository is accessible: {git_repo_url}"
                    }
                else:
                    error_msg = f"Git clone failed: {result.stderr}"
                    deployment_logger.error(f"❌ Git repository not accessible: {error_msg}")
                    return {
                        "success": False,
                        "message": error_msg
                    }

        except subprocess.TimeoutExpired:
            error_msg = f"Git repository connection timed out: {git_repo_url}"
            deployment_logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }
        except Exception as e:
            error_msg = f"Git repository validation failed: {str(e)}"
            deployment_logger.error(f"❌ {error_msg}")
            return {
                "success": False,
                "message": error_msg
            }

    def register_handlers(self, rpc_handler: JsonRpcHandler):
        """Register all server handlers with the RPC handler"""
        # Standard MCP methods
        rpc_handler.register_request_handler('initialize', self.handle_initialize)
        rpc_handler.register_request_handler('tools/list', self.handle_tools_list)
        rpc_handler.register_request_handler('tools/call', self.handle_tools_call)
        rpc_handler.register_request_handler('resources/list', self.handle_resources_list)
        rpc_handler.register_request_handler('resources/read', self.handle_resources_read)
        rpc_handler.register_request_handler('prompts/list', self.handle_prompts_list)
        rpc_handler.register_request_handler('prompts/get', self.handle_prompts_get)
        rpc_handler.register_request_handler('shutdown', self.handle_shutdown)
        rpc_handler.register_request_handler('ping', self.handle_ping)

    def handle_initialize(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle initialize request"""
        client_info = params.get("clientInfo", {})
        print(f"Initializing DevOps Release Engineer connection with client: {client_info.get('name', 'Unknown')} v{client_info.get('version', 'Unknown')}")

        return {
            "protocolVersion": "2024-11-05",
            "serverInfo": {
                "name": "devops-release-engineer-mcp-server",
                "version": "1.0.0"
            },
            "capabilities": {
                "tools": {
                    "listChanged": True
                },
                "resources": {
                    "listChanged": True
                },
                "prompts": {
                    "listChanged": True
                }
            }
        }

    def handle_tools_list(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tools/list request"""
        if params is None:
            params = {}

        pagination = params.get("pagination", {})
        cursor = pagination.get("cursor")
        limit = min(pagination.get("limit", len(self.tools)), 100)

        if cursor:
            pass

        return {
            "tools": self.tools[:limit],
            "pagination": {
                "hasMore": len(self.tools) > limit,
                "nextCursor": f"cursor_{limit}" if len(self.tools) > limit else None
            } if limit < len(self.tools) else {}
        }

    def handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle tools/call request"""
        if params is None:
            params = {}

        tool_name = params.get("name") or params.get("tool")
        tool_arguments = params.get("arguments", {})

        tool = None
        for t in self.tools:
            if t["name"] == tool_name:
                tool = t
                break

        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        return self._execute_tool(tool, tool_arguments)

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a specific tool with given arguments"""
        tool_name = tool["name"]

        # Handle deployment tools directly (no LLM)
        if tool_name == "deploy_web_application":
            return self._deploy_web_application(arguments)
        elif tool_name == "stop_deployment":
            return self._stop_deployment(arguments)
        elif tool_name == "start_deployment":
            return self._start_deployment(arguments)
        elif tool_name == "delete_deployment":
            return self._delete_deployment(arguments)
        elif tool_name == "list_deployments":
            return self._list_deployments(arguments)
        elif tool_name == "get_deployment_status":
            return self._get_deployment_status(arguments)

        # Execute other tools using LLM via LM Studio API
        try:
            result = self._execute_tool_with_llm(tool_name, arguments)
            return {"result": result}
        except Exception as e:
            return {"error": f"Failed to execute tool: {str(e)}"}

    def _contract_from_cache(self, task_id):
        """QA run-contract cache is canonical (same host); used when the caller
        (e.g. web-ui redeploy) did not pass a run_contract."""
        try:
            p = f"/tmp/qa-contracts/{task_id}.json"
            if os.path.exists(p):
                with open(p) as f:
                    c = json.load(f)
                if isinstance(c, dict) and c.get("kind"):
                    return c
        except Exception:
            pass
        return None

    def _edge_route(self, task_id, host_port):
        """Expose a deployment behind the nginx edge (:3080/<task>/) instead of
        publishing its container port on all interfaces. Returns URL or None
        (caller falls back to the direct URL)."""
        try:
            d = "/etc/nginx/mcp-deployments"
            os.makedirs(d, exist_ok=True)
            safe = re.sub(r"[^A-Za-z0-9_.-]", "-", str(task_id))
            path = os.path.join(d, safe + ".conf")
            with open(path, "w") as f:
                f.write(f"location /{safe}/ {{\n"
                        f"    proxy_pass http://127.0.0.1:{host_port}/;\n"
                        "    proxy_set_header Host $host;\n"
                        "    proxy_read_timeout 300s;\n}\n")
            t = subprocess.run(["/usr/sbin/nginx", "-t"], capture_output=True, timeout=20)
            if t.returncode != 0:
                os.remove(path)
                return None
            subprocess.run(["/usr/sbin/nginx", "-s", "reload"], capture_output=True, timeout=20)
            return "http://%s:3080/%s/" % (os.environ.get("DEPLOYMENT_HOST", "127.0.0.1"), safe)
        except Exception as e:
            deployment_logger.warning(f"edge route failed: {type(e).__name__}: {e}")
            return None

    def _edge_remove(self, task_id):
        try:
            safe = re.sub(r"[^A-Za-z0-9_.-]", "-", str(task_id))
            path = f"/etc/nginx/mcp-deployments/{safe}.conf"
            if os.path.exists(path):
                os.remove(path)
                subprocess.run(["/usr/sbin/nginx", "-t"], capture_output=True, timeout=20)
                subprocess.run(["/usr/sbin/nginx", "-s", "reload"], capture_output=True, timeout=20)
        except Exception:
            pass

    def _deploy_web_application(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy a Python web application using Docker"""
        import subprocess
        import uuid
        import os
        import tempfile
        import re

        task_id = arguments.get("task_id")
        git_url = arguments.get("git_url")
        result_path = arguments.get("result_path")
        memory_limit = arguments.get("memory_limit", "256m")
        cpu_limit = arguments.get("cpu_limit", "0.5")

        deployment_logger.info(f"=== Deployment Started ===")
        deployment_logger.info(f"Task ID: {task_id}")
        deployment_logger.info(f"Git URL: {git_url}")

        try:
            # Validate git_url is present
            if not git_url:
                error_msg = "Git URL is required for deployment"
                deployment_logger.error(error_msg)
                self._update_task_status_on_deployment_failure(task_id, error_msg)
                return {"error": error_msg}

            # Extract UUID from git URL
            # Format: ssh://sorokin@192.168.51.187/home/sorokin/mcp-results/tree/main/results/<uuid>/result.py
            uuid_match = re.search(r'/results/([^/]+)(?:/|$)', git_url)
            if not uuid_match:
                error_msg = f"Could not extract UUID from git URL: {git_url}"
                deployment_logger.error(error_msg)
                self._update_task_status_on_deployment_failure(task_id, error_msg)
                return {"error": error_msg}

            result_uuid = uuid_match.group(1)
            deployment_logger.info(f"Extracted result UUID: {result_uuid}")

            # Extract base git repo URL
            # Convert ssh://user@host/path/to/repo/tree/main/results/uuid/file.py to ssh://user@host/path/to/repo.git
            # Match everything up to the repo name (before /tree/main/)
            if "/tree/main/" in git_url:
                git_repo_url = git_url.split("/tree/main/")[0] + ".git"
            else:
                git_repo_url = "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"

            deployment_logger.info(f"Deploying from repo: {git_repo_url}, UUID: {result_uuid}")

            # Validate Git repository accessibility before proceeding
            git_validation = self._validate_git_repository(git_repo_url)
            if not git_validation.get("success"):
                error_msg = f"Git repository not accessible: {git_validation.get('message')}"
                deployment_logger.error(error_msg)
                self._update_task_status_on_deployment_failure(task_id, error_msg)
                return {"error": error_msg}

            # Create temp directory for deployment
            deploy_dir = f"/tmp/deploy-{task_id}"
            os.makedirs(deploy_dir, exist_ok=True)
            
            # Clone/fetch from git (shallow clone for speed)
            git_workdir = f"/tmp/git-fetch-{task_id}"
            subprocess.run(["rm", "-rf", git_workdir], check=True)
            subprocess.run([
                "git", "clone", "--depth", "1",
                git_repo_url,
                git_workdir
            ], check=True, capture_output=True, timeout=30)
            
            # Multi-file artifact tree (coder 'files' envelope): anything beyond
            # the single-file result.* / response.json convention
            result_root = os.path.join(git_workdir, "results", result_uuid)
            tree_entries = [f for f in os.listdir(result_root)
                            if f not in ("result.py", "result.json", "result.html", "response.json")]
            if tree_entries:
                deployment_logger.info(f"Multi-file artifact detected: {tree_entries}")
                return self._deploy_multi_file(task_id, result_root, deploy_dir, 5000,
                                               deployment_logger, git_url, git_workdir,
                                               memory_limit, cpu_limit,
                                               run_contract=arguments.get("run_contract")
                                               or self._contract_from_cache(task_id))

            # Copy result file to deploy directory (could be .py, .json, or .html)
            # Try result.py first, then result.json, then result.html
            result_file_py = os.path.join(git_workdir, "results", result_uuid, "result.py")
            result_file_json = os.path.join(git_workdir, "results", result_uuid, "result.json")
            result_file_html = os.path.join(git_workdir, "results", result_uuid, "result.html")

            result_file = None
            if os.path.exists(result_file_py):
                result_file = result_file_py
                deployment_logger.info(f"Found result.py at: {result_file}")
            elif os.path.exists(result_file_json):
                result_file = result_file_json
                deployment_logger.info(f"Found result.json at: {result_file}")
            elif os.path.exists(result_file_html):
                result_file = result_file_html
                deployment_logger.info(f"Found result.html at: {result_file}")

            if not result_file:
                error_msg = f"result.py, result.json, or result.html not found in git repo. Git clone may have succeeded but result file is missing. Checked: {result_file_py}, {result_file_json}, {result_file_html}"
                deployment_logger.error(error_msg)
                self._update_task_status_on_deployment_failure(task_id, error_msg)
                return {"error": error_msg}

            import shutil
            import json
            import re

            # Handle result.json and result.html files that contain code in a "code" field
            if result_file.endswith(".json") or result_file.endswith(".html"):
                if result_file.endswith(".json"):
                    deployment_logger.info(f"Processing result.json file: {result_file}")
                else:
                    deployment_logger.info(f"Processing result.html file: {result_file}")
                with open(result_file, 'r') as f:
                    json_content = f.read()

                if json_content.lstrip().lower().startswith(("<!doctype html", "<html")):
                    deployment_logger.info("Static HTML artifact detected; deploying via http.server")
                    return self._deploy_static_html(task_id, deploy_dir, 5000, json_content,
                                                    deployment_logger, git_url, git_workdir,
                                                    memory_limit, cpu_limit)

                code_content = ""
                parsed_successfully = False

                # Try standard JSON parsing first
                try:
                    data = json.loads(json_content)
                    code_content = data.get("code", "")
                    if code_content:
                        parsed_successfully = True
                        deployment_logger.info("Successfully parsed JSON and extracted code field")
                except json.JSONDecodeError:
                    deployment_logger.warning("Standard JSON parsing failed, trying alternative extraction methods")

                # If JSON parsing failed, try to extract the code field manually
                if not parsed_successfully:
                    code_content = self._extract_code_field(json_content, result_file, deployment_logger)

                # If code_content is a string, use it directly as Python code
                if isinstance(code_content, str):
                    final_content = code_content
                else:
                    final_content = json.dumps(code_content, indent=2)

                if final_content.lstrip().lower().startswith(("<!doctype html", "<html")):
                    deployment_logger.info("Static HTML artifact detected; deploying via http.server")
                    return self._deploy_static_html(task_id, deploy_dir, 5000, final_content,
                                                    deployment_logger, git_url, git_workdir,
                                                    memory_limit, cpu_limit)

                with open(os.path.join(deploy_dir, "result.py"), 'w') as f:
                    f.write(final_content)
                if result_file.endswith(".json"):
                    deployment_logger.info(f"Extracted Python code from result.json and saved to result.py")
                else:
                    deployment_logger.info(f"Extracted Python code from result.html and saved to result.py")
            else:
                shutil.copy(result_file, os.path.join(deploy_dir, "result.py"))

            # Detect dependencies from imports
            with open(os.path.join(deploy_dir, "result.py"), 'r') as f:
                content = f.read()

            dependencies = ["flask"]  # Default

            # Check if code uses render_template() (external templates)
            # This requires either creating a templates directory or converting to render_template_string()
            uses_render_template = 'render_template(' in content and 'render_template_string(' not in content

            # Handle template files that need to be copied to templates directory
            # Check if there's a templates directory in the git result
            templates_git_dir = os.path.join(git_workdir, "results", result_uuid, "templates")
            if os.path.isdir(templates_git_dir):
                deployment_logger.info(f"Found templates directory in git repo: {templates_git_dir}")

                # Create templates directory in deploy dir
                templates_dir = os.path.join(deploy_dir, "templates")
                os.makedirs(templates_dir, exist_ok=True)

                # Copy all template files to deploy directory
                for template_file in os.listdir(templates_git_dir):
                    src_path = os.path.join(templates_git_dir, template_file)
                    dst_path = os.path.join(deploy_dir, "templates", template_file)
                    if os.path.isfile(src_path):
                        shutil.copy(src_path, dst_path)
                        deployment_logger.info(f"Copied template: {template_file}")
                uses_render_template = False  # Templates are now available

            # Fallback: if render_template() is used but no templates exist,
            # create minimal template files
            if uses_render_template:
                deployment_logger.warning("render_template() is used but no templates directory found - creating minimal templates")

                # Create templates directory in deploy dir
                templates_dir = os.path.join(deploy_dir, "templates")
                os.makedirs(templates_dir, exist_ok=True)
                deployment_logger.info(f"Created templates directory: {templates_dir}")

                # Extract template names from render_template() calls
                template_names = set(re.findall(r"render_template\(['\"]([^'\"]+)['\"]", content))
                if not template_names:
                    template_names = set(re.findall(r'render_template\(["\']([^"\']+)["\']', content))

                deployment_logger.info(f"Found template references: {template_names}")

                # Create minimal template files for each referenced template
                for template_name in template_names:
                    template_path = os.path.join(templates_dir, template_name)
                    # Create a minimal HTML template with basic structure
                    template_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{template_name.replace('.html', '').title()}</title>
</head>
<body>
    <h1>{template_name.replace('.html', '').title()}</h1>
    <p>Template content would be generated by the Flask app.</p>
</body>
</html>
"""
                    with open(template_path, 'w') as f:
                        f.write(template_content)
                    deployment_logger.info(f"Created minimal template: {template_name}")
                uses_render_template = False  # Templates are now available

            if "fastapi" in content:
                dependencies.append("fastapi")
                dependencies.append("uvicorn")
            if "django" in content:
                dependencies.append("django")

            # Detect PORT from generated code
            # Look for patterns like: PORT = 8080, PORT=3000, port = 5000, etc.
            container_port = 5000  # Default fallback
            port_patterns = [
                r'PORT\s*=\s*(\d+)',           # PORT = 8080
                r'port\s*=\s*(\d+)',           # port = 8080
                r'PORT\s*=\s*int\(os\.environ\.get\(["\']PORT["\']\s*,\s*(\d+)\)\)',  # PORT = int(os.environ.get("PORT", 8080))
                r'server\.listen\((\d+)\)',    # server.listen(3000) - Node.js style
                r'app\.run\(.*port\s*=\s*(\d+)',  # app.run(port=5000) - Flask
                # Python http.server and socketserver patterns
                r'HTTPServer\([^,]+,\s*(\d+)',  # HTTPServer(('0.0.0.0', 8000), Handler)
                r'TCPServer\([^,]+,\s*(\d+)',   # TCPServer(("0.0.0.0", 9000), ...)
                r'UDPServer\([^,]+,\s*(\d+)',   # UDPServer(("0.0.0.0", 9000), ...)
                r'run_simple\([^,]+,\s*(\d+)',  # Werkzeug: run_simple('0.0.0.0', 5000, app)
                r'uvicorn\.run\([^,]+,\s*port\s*=\s*(\d+)',  # uvicorn.run(app, port=8000)
            ]
            for pattern in port_patterns:
                port_match = re.search(pattern, content)
                if port_match:
                    detected_port = int(port_match.group(1))
                    print(f"✅ Detected PORT={detected_port} from result.py (pattern: {pattern})")
                    container_port = detected_port
                    break

            # ✅ CRITICAL VALIDATION: Check for localhost binding in Flask/web apps
            # This prevents deployment of apps that won't be accessible from outside container
            localhost_binding_detected = False
            code_modified = False
            
            # Check for Flask app.run() without host='0.0.0.0'
            if 'app.run(' in content:
                if 'host=' not in content:
                    # Fix: Add host='0.0.0.0' to app.run()
                    localhost_binding_detected = True
                    code_modified = True
                    print(f"⚠️  DETECTED: Flask app.run() missing host='0.0.0.0'")
                    print(f"   Auto-fixing: Adding host='0.0.0.0' to app.run()...")
                    # Replace app.run(...) with app.run(host='0.0.0.0', ...)
                    import re
                    content = re.sub(
                        r'app\.run\(([^)]*)\)',
                        lambda m: f"app.run(host='0.0.0.0', {m.group(1)})" if m.group(1).strip() else "app.run(host='0.0.0.0')",
                        content
                    )
                    print(f"   ✅ Fixed: app.run() now includes host='0.0.0.0'")
                elif "host='0.0.0.0'" not in content and 'host="0.0.0.0"' not in content:
                    # Check if host is set to localhost or 127.0.0.1
                    if "host='127.0.0.1'" in content or 'host="127.0.0.1"' in content:
                        localhost_binding_detected = True
                        code_modified = True
                        print(f"⚠️  DETECTED: Flask app.run(host='127.0.0.1')")
                        print(f"   Auto-fixing: Replacing host='127.0.0.1' with host='0.0.0.0'...")
                        content = content.replace("host='127.0.0.1'", "host='0.0.0.0'")
                        content = content.replace('host="127.0.0.1"', 'host="0.0.0.0"')
                        print(f"   ✅ Fixed: host changed to '0.0.0.0'")
                    elif "host='localhost'" in content or 'host="localhost"' in content:
                        localhost_binding_detected = True
                        code_modified = True
                        print(f"⚠️  DETECTED: Flask app.run(host='localhost')")
                        print(f"   Auto-fixing: Replacing host='localhost' with host='0.0.0.0'...")
                        content = content.replace("host='localhost'", "host='0.0.0.0'")
                        content = content.replace('host="localhost"', 'host="0.0.0.0"')
                        print(f"   ✅ Fixed: host changed to '0.0.0.0'")
            
            # Check for http.server/TCPServer binding to localhost
            if "HTTPServer(('localhost'" in content or 'HTTPServer(("localhost"' in content:
                localhost_binding_detected = True
                code_modified = True
                print(f"⚠️  DETECTED: HTTPServer binding to localhost")
                print(f"   Auto-fixing: Replacing 'localhost' with '0.0.0.0'...")
                content = content.replace("HTTPServer(('localhost'", "HTTPServer(('0.0.0.0',")
                content = content.replace('HTTPServer(("localhost"', 'HTTPServer(("0.0.0.0",')
                print(f"   ✅ Fixed: HTTPServer now binds to '0.0.0.0'")
            if "HTTPServer(('127.0.0.1'" in content or 'HTTPServer(("127.0.0.1"' in content:
                localhost_binding_detected = True
                code_modified = True
                print(f"⚠️  DETECTED: HTTPServer binding to 127.0.0.1")
                print(f"   Auto-fixing: Replacing '127.0.0.1' with '0.0.0.0'...")
                content = content.replace("HTTPServer(('127.0.0.1'", "HTTPServer(('0.0.0.0',")
                content = content.replace('HTTPServer(("127.0.0.1"', 'HTTPServer(("0.0.0.0",')
                print(f"   ✅ Fixed: HTTPServer now binds to '0.0.0.0'")
            
            # If code was modified, save the fixed version
            if code_modified:
                print(f"💾 Saving fixed code to result.py...")
                with open(os.path.join(deploy_dir, "result.py"), 'w') as f:
                    f.write(content)
                print(f"   ✅ Code fixed and saved")
                
                # Also update the git result with the fix
                print(f"📝 Note: Code was auto-fixed for Docker compatibility")
                print(f"   Original code had localhost binding, which would fail in Docker")
                print(f"   Fixed code now binds to 0.0.0.0 for proper container networking")
            
            if container_port != 5000:
                print(f"⚠️  Non-standard port detected: {container_port} (default is 5000)")
            else:
                print(f"ℹ️  Using default PORT=5000 (no custom port detected in code)")

            # ✅ Validate Python syntax before building Docker image
            try:
                import py_compile
                import tempfile
                with tempfile.NamedTemporaryFile(suffix='.py', delete=False) as tmp_file:
                    tmp_file.write(content.encode('utf-8'))
                    tmp_file_path = tmp_file.name
                try:
                    py_compile.compile(tmp_file_path, doraise=True)
                    print(f"✅ Python syntax validation passed for result.py")
                except py_compile.PyCompileError as e:
                    error_msg = str(e)
                    print(f"❌ Python syntax error detected in result.py: {error_msg}")
                    os.unlink(tmp_file_path)
                    return {"error": f"Python syntax error in result.py: {error_msg}. Please regenerate the code with correct syntax."}
                os.unlink(tmp_file_path)
            except Exception as e:
                print(f"⚠️  Could not validate Python syntax: {e}")

            # Check if templates directory exists and add COPY instruction if needed
            templates_exist = os.path.isdir(os.path.join(deploy_dir, "templates"))

            # Create Dockerfile with detected port
            if templates_exist:
                dockerfile_content = f"""FROM python:3.11-slim
WORKDIR /app
COPY result.py .
COPY templates/ ./templates/
RUN pip install {' '.join(dependencies)}
EXPOSE {container_port}
CMD ["python", "result.py"]
"""
            else:
                dockerfile_content = f"""FROM python:3.11-slim
WORKDIR /app
COPY result.py .
RUN pip install {' '.join(dependencies)}
EXPOSE {container_port}
CMD ["python", "result.py"]
"""
            with open(os.path.join(deploy_dir, "Dockerfile"), 'w') as f:
                f.write(dockerfile_content)

            # Find available host port
            host_port = self._find_available_port()

            # Get deployment host from environment
            deployment_host = os.environ.get("DEPLOYMENT_HOST", "127.0.0.1")

            # Build Docker image
            image_name = f"deploy-{task_id}".lower()
            container_name = f"deploy-{task_id}".lower()

            subprocess.run([
                "docker", "build", "-t", image_name, deploy_dir
            ], check=True, capture_output=True, timeout=120)

            # Run container
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
            subprocess.run([
                "docker", "run", "-d",
                "--name", container_name,
                "-p", f"127.0.0.1:{host_port}:{container_port}",
                "--memory", memory_limit,
                "--cpus", cpu_limit,
                "--restart", "unless-stopped",
                image_name
            ], check=True, capture_output=True, timeout=30)

            # Store deployment in database
            deployment_url = self._edge_route(task_id, host_port) or f"http://{deployment_host}:{host_port}/"
            self._store_deployment(task_id, container_name, container_port, host_port, 
                                   deployment_url, git_url, image_name, memory_limit, cpu_limit)
            deployment_logger.info(f"Docker image built and container started successfully")

            # Cleanup
            subprocess.run(["rm", "-rf", git_workdir], check=True)
            subprocess.run(["rm", "-rf", deploy_dir], check=True)

            deployment_logger.info(f"=== Deployment Completed Successfully ===")
            deployment_logger.info(f"Deployment URL: {deployment_url}")

            # Update task registry with deployment URL
            self._update_task_with_deployment_url(task_id, git_url, deployment_url)

            return {
                "success": True,
                "task_id": task_id,
                "container_id": container_name,
                "host_port": host_port,
                "deployment_url": deployment_url,
                "message": f"Application deployed successfully at {deployment_url}"
            }

        except subprocess.TimeoutExpired as e:
            error_msg = f"Docker command timed out: {str(e)}"
            deployment_logger.error(f"Deployment timeout: {error_msg}")
            self._update_task_status_on_deployment_failure(task_id, error_msg)
            return {"error": error_msg}

        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            error_msg = f"Docker command failed: {stderr}"
            deployment_logger.error(f"Docker command failed: {error_msg}")
            self._update_task_status_on_deployment_failure(task_id, error_msg)
            return {"error": error_msg}

        except Exception as e:
            error_msg = f"Deployment failed: {str(e)}"
            deployment_logger.error(f"Unexpected deployment error: {error_msg}")
            self._update_task_status_on_deployment_failure(task_id, error_msg)
            return {"error": error_msg}

    @staticmethod
    def _dockerfile_from_contract(rc, container_port):
        kind = rc.get("kind")
        if kind == "static":
            return f"""FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE {container_port}
CMD ["python", "-m", "http.server", "{container_port}"]
"""
        install = rc.get("install")
        install_line = f"RUN {install}\n" if install else ""
        env_lines = "".join(f'ENV {k}="{v}"\n' for k, v in (rc.get("env") or {}).items())
        cwd = str(rc.get("cwd") or "").strip("/")
        work = f"/app/{cwd}" if cwd else "/app"
        hc = rc.get("healthcheck") or {}
        port = hc.get("port") or container_port
        run = str(rc.get("run") or "").replace('"', '\\"')
        return f"""FROM python:3.11-slim
WORKDIR /app
COPY . .
{install_line}{env_lines}WORKDIR {work}
EXPOSE {port}
CMD ["/bin/sh", "-c", "{run}"]
"""

    def _deploy_multi_file(self, task_id, result_root, deploy_dir, container_port,
                           deployment_logger, git_url, git_workdir, memory_limit, cpu_limit,
                           run_contract=None):
        """Deploy a multi-file artifact tree: static site if index.html, else python entry."""
        import subprocess
        import shutil
        shutil.rmtree(deploy_dir, ignore_errors=True)
        os.makedirs(deploy_dir, exist_ok=True)
        for item in os.listdir(result_root):
            if item == "response.json":
                continue
            src = os.path.join(result_root, item)
            dst = os.path.join(deploy_dir, item)
            shutil.copytree(src, dst) if os.path.isdir(src) else shutil.copy(src, dst)

        all_files = []
        for root, _, files in os.walk(deploy_dir):
            all_files += [os.path.relpath(os.path.join(root, f), deploy_dir) for f in files]

        rc = run_contract or {}
        if rc.get("kind") in ("service", "cli", "static"):
            hc = rc.get("healthcheck") or {}
            if hc.get("port"):
                container_port = int(hc["port"])
            dockerfile = self._dockerfile_from_contract(rc, container_port)
            deployment_logger.info(f"Dockerfile from run contract (source={rc.get('source', '?')})")
        elif "index.html" in all_files:
            dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
COPY . .
EXPOSE {container_port}
CMD ["python", "-m", "http.server", "{container_port}"]
"""
        else:
            main_pkg = next((f for f in all_files if f.endswith("__main__.py")), None)
            if main_pkg:
                pkg_dir = os.path.dirname(main_pkg)      # e.g. src/mcp_service
                pkg_name = os.path.basename(pkg_dir)     # e.g. mcp_service
                parent = os.path.dirname(pkg_dir)        # e.g. src or ""
                work_root = f"/app/{parent}" if parent else "/app"
                pip_line = ("RUN pip install -r /app/requirements.txt\n"
                            if "requirements.txt" in all_files else "")
                dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
COPY . .
{pip_line}WORKDIR {work_root}
EXPOSE {container_port}
CMD ["python", "-m", "{pkg_name}"]
"""
                entry = main_pkg
            else:
                entry = next((f for f in all_files
                              if os.path.basename(f) in ("main.py", "app.py", "server.py")
                              and not f.endswith("__init__.py")),
                             next((f for f in all_files if f.endswith(".py")
                                   and not f.endswith("__init__.py")), None))
                if not entry:
                    return {"error": "multi-file artifact has no index.html and no python entry point"}
                pip_line = ("RUN pip install -r /app/requirements.txt\n"
                            if "requirements.txt" in all_files else "")
                entry_dir = os.path.dirname(entry)
                workdir_line = f"WORKDIR /app/{entry_dir}\n" if entry_dir else ""
                dockerfile = f"""FROM python:3.11-slim
WORKDIR /app
COPY . .
{pip_line}{workdir_line}EXPOSE {container_port}
CMD ["python", "{os.path.basename(entry)}"]
"""
        with open(os.path.join(deploy_dir, "Dockerfile"), 'w') as f:
            f.write(dockerfile)
        host_port = self._find_available_port()
        deployment_host = os.environ.get("DEPLOYMENT_HOST", "127.0.0.1")
        image_name = f"deploy-{task_id}".lower()
        container_name = f"deploy-{task_id}".lower()
        subprocess.run(["docker", "build", "-t", image_name, deploy_dir],
                       check=True, capture_output=True, timeout=300)
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        subprocess.run([
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"127.0.0.1:{host_port}:{container_port}",
            "--memory", memory_limit,
            "--cpus", cpu_limit,
            "--restart", "unless-stopped",
            image_name
        ], check=True, capture_output=True, timeout=30)
        time.sleep(6)
        st = subprocess.run(["docker", "inspect", "-f",
                             "{{.State.Status}} {{.RestartCount}}", container_name],
                            capture_output=True, text=True)
        state = (st.stdout or "").strip()
        parts = state.split()
        restarts = parts[1] if len(parts) > 1 else "0"
        if "running" not in state or restarts != "0":
            logs = subprocess.run(["docker", "logs", "--tail", "30", container_name],
                                  capture_output=True, text=True)
            tail = ((logs.stdout or "") + (logs.stderr or ""))[-1200:]
            subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
            return {"error": f"container unhealthy after start ({state}): {tail}"}
        deployment_url = self._edge_route(task_id, host_port) or f"http://{deployment_host}:{host_port}/"
        self._store_deployment(task_id, container_name, container_port, host_port,
                               deployment_url, git_url, image_name, memory_limit, cpu_limit)
        subprocess.run(["rm", "-rf", git_workdir], check=True)
        subprocess.run(["rm", "-rf", deploy_dir], check=True)
        self._update_task_with_deployment_url(task_id, git_url, deployment_url)
        deployment_logger.info(f"Multi-file app deployed at {deployment_url}")
        return {
            "success": True, "task_id": task_id, "container_id": container_name,
            "host_port": host_port, "deployment_url": deployment_url,
            "files": all_files,
            "message": f"Multi-file application deployed at {deployment_url}"
        }

    def _deploy_static_html(self, task_id, deploy_dir, container_port, html_content,
                            deployment_logger, git_url, git_workdir, memory_limit, cpu_limit):
        """Serve a static HTML artifact via python http.server in Docker."""
        import subprocess
        with open(os.path.join(deploy_dir, "index.html"), 'w') as f:
            f.write(html_content)
        dockerfile_content = f"""FROM python:3.11-slim
WORKDIR /app
COPY index.html .
EXPOSE {container_port}
CMD ["python", "-m", "http.server", "{container_port}"]
"""
        with open(os.path.join(deploy_dir, "Dockerfile"), 'w') as f:
            f.write(dockerfile_content)
        host_port = self._find_available_port()
        deployment_host = os.environ.get("DEPLOYMENT_HOST", "127.0.0.1")
        image_name = f"deploy-{task_id}".lower()
        container_name = f"deploy-{task_id}".lower()
        subprocess.run(["docker", "build", "-t", image_name, deploy_dir], check=True, capture_output=True, timeout=120)
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        subprocess.run([
            "docker", "run", "-d",
            "--name", container_name,
            "-p", f"127.0.0.1:{host_port}:{container_port}",
            "--memory", memory_limit,
            "--cpus", cpu_limit,
            "--restart", "unless-stopped",
            image_name
        ], check=True, capture_output=True, timeout=30)
        deployment_url = self._edge_route(task_id, host_port) or f"http://{deployment_host}:{host_port}/"
        self._store_deployment(task_id, container_name, container_port, host_port,
                               deployment_url, git_url, image_name, memory_limit, cpu_limit)
        subprocess.run(["rm", "-rf", git_workdir], check=True)
        subprocess.run(["rm", "-rf", deploy_dir], check=True)
        self._update_task_with_deployment_url(task_id, git_url, deployment_url)
        deployment_logger.info(f"Static HTML deployed at {deployment_url}")
        return {
            "success": True,
            "task_id": task_id,
            "container_id": container_name,
            "host_port": host_port,
            "deployment_url": deployment_url,
            "message": f"Static application deployed at {deployment_url}"
        }

    def _stop_deployment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Stop a deployment (keep container for restart)"""
        import subprocess

        task_id = arguments.get("task_id")
        container_name = f"deploy-{task_id}".lower()

        try:
            # Check if container exists
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
                capture_output=True, text=True
            )
            if not result.stdout.strip():
                return {"error": f"Container {container_name} not found"}
            
            # Check if already stopped
            if "Exited" in result.stdout:
                return {
                    "success": True,
                    "task_id": task_id,
                    "message": f"Deployment {task_id} was already stopped"
                }
            
            # Stop container (don't remove - keep for restart)
            subprocess.run(["docker", "stop", container_name], check=True, capture_output=True)

            # Update database
            self._update_deployment_status(task_id, "stopped")
            self._edge_remove(task_id)

            return {
                "success": True,
                "task_id": task_id,
                "message": f"Deployment {task_id} stopped successfully"
            }
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            return {"error": f"Docker command failed: {stderr}"}
        except Exception as e:
            return {"error": f"Failed to stop deployment: {str(e)}"}

    def _start_deployment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Start a stopped deployment"""
        import subprocess

        container_id = arguments.get("container_id")

        try:
            # Check if container exists
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={container_id}", "--format", "{{.Status}}"],
                capture_output=True, text=True
            )
            if not result.stdout.strip():
                return {"error": f"Container {container_id} not found"}
            
            # Check if already running
            if "Up" in result.stdout:
                return {
                    "success": True,
                    "container_id": container_id,
                    "message": f"Deployment {container_id} was already running"
                }
            
            # Start container
            subprocess.run(["docker", "start", container_id], check=True, capture_output=True)

            return {
                "success": True,
                "container_id": container_id,
                "message": f"Deployment {container_id} started successfully"
            }
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            return {"error": f"Docker command failed: {stderr}"}
        except Exception as e:
            return {"error": f"Failed to start deployment: {str(e)}"}

    def _delete_deployment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Delete a deployment permanently"""
        import subprocess

        container_id = arguments.get("container_id")

        try:
            # Check if container exists
            result = subprocess.run(
                ["docker", "ps", "-a", "--filter", f"name={container_id}", "--format", "{{.ID}}"],
                capture_output=True, text=True
            )
            if not result.stdout.strip():
                return {"error": f"Container {container_id} not found"}
            
            # Stop if running
            subprocess.run(["docker", "stop", container_id], capture_output=True)
            
            # Remove container
            subprocess.run(["docker", "rm", container_id], check=True, capture_output=True)

            return {
                "success": True,
                "container_id": container_id,
                "message": f"Deployment {container_id} deleted successfully"
            }
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            return {"error": f"Docker command failed: {stderr}"}
        except Exception as e:
            return {"error": f"Failed to delete deployment: {str(e)}"}

    def _list_deployments(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """List all deployments"""
        status_filter = arguments.get("status_filter", "running")
        
        try:
            deployments = self._get_deployments(status_filter)
            return {
                "deployments": deployments,
                "count": len(deployments)
            }
        except Exception as e:
            return {"error": f"Failed to list deployments: {str(e)}"}

    def _get_deployment_status(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Get deployment status"""
        import subprocess
        
        task_id = arguments.get("task_id")
        container_name = f"deploy-{task_id}".lower()
        
        try:
            # Check if container is running
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", container_name],
                capture_output=True, text=True
            )
            
            status = result.stdout.strip() if result.returncode == 0 else "not_found"
            
            # Get deployment info from database
            deployment = self._get_deployment(task_id)
            
            return {
                "task_id": task_id,
                "container_status": status,
                "deployment_status": deployment.get("status", "unknown") if deployment else "not_found",
                "deployment_url": deployment.get("deployment_url") if deployment else None
            }
        except Exception as e:
            return {"error": f"Failed to get status: {str(e)}"}

    def _find_available_port(self, min_port=5001, max_port=5100) -> int:
        """Find an available port"""
        import socket
        
        for port in range(min_port, max_port):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(1)
                result = sock.connect_ex(('127.0.0.1', port))
                sock.close()
                if result != 0:
                    return port
            except:
                return port
        raise Exception("No available ports")

    def _store_deployment(self, task_id, container_id, container_port, host_port,
                          deployment_url, git_url, docker_image, memory_limit, cpu_limit):
        """Store deployment in database"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host="127.0.0.1",
                database="mcp_registry",
                user="postgres",
                password="postgres"
            )
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO task_deployments
                (task_id, container_id, container_port, host_port, deployment_url,
                 git_commit_sha, docker_image, memory_limit, cpu_limit)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (task_id) DO UPDATE SET
                    container_id = EXCLUDED.container_id,
                    host_port = EXCLUDED.host_port,
                    deployment_url = EXCLUDED.deployment_url,
                    status = 'running',
                    created_at = CURRENT_TIMESTAMP
            """, (task_id, container_id, container_port, host_port, deployment_url,
                  git_url.split('/')[-2] if git_url else None, docker_image, memory_limit, cpu_limit))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            deployment_logger.error(f"Failed to store deployment in database: {e}")
            print(f"Warning: Could not store deployment: {e}")

    def _update_task_status_on_deployment_failure(self, task_id: str, error_message: str):
        """
        Update task status to 'failed' with error details when deployment fails.
        This ensures deployment failures are properly tracked in the task registry.
        """
        try:
            import psycopg2
            import json

            conn = psycopg2.connect(
                host="127.0.0.1",
                database="mcp_registry",
                user="postgres",
                password="postgres"
            )
            cursor = conn.cursor()

            # Get current task data
            cursor.execute("""
                SELECT status, status_history, metadata
                FROM task_registry
                WHERE task_id = %s
            """, (task_id,))

            row = cursor.fetchone()
            if row:
                current_status, status_history, metadata = row

                # Only update if task is not already in a terminal state
                if current_status in ('in_progress', 'assigned', 'review'):
                    # Parse and update status_history
                    if isinstance(status_history, str):
                        status_history = json.loads(status_history) if status_history else []
                    elif not isinstance(status_history, list):
                        status_history = []

                    # Add failure entry to status_history
                    failure_entry = {
                        "status": "failed",
                        "timestamp": time.time(),
                        "reason": f"Deployment failed: {error_message}"
                    }
                    status_history.append(failure_entry)

                    # Parse and update metadata to include error
                    if isinstance(metadata, str):
                        metadata = json.loads(metadata) if metadata else {}
                    elif not isinstance(metadata, dict):
                        metadata = {}

                    metadata['deployment_error'] = error_message
                    metadata['deployment_failed_at'] = time.time()

                    # Update task status
                    cursor.execute("""
                        UPDATE task_registry
                        SET status = 'failed',
                            status_history = %s,
                            metadata = %s
                        WHERE task_id = %s
                    """, (json.dumps(status_history), json.dumps(metadata), task_id))

                    conn.commit()
                    deployment_logger.info(f"Updated task {task_id} status to 'failed' due to deployment error")

            cursor.close()
            conn.close()

        except Exception as e:
            deployment_logger.error(f"Failed to update task status for {task_id}: {e}")

    def _update_task_with_deployment_url(self, task_id: str, git_url: str, deployment_url: str = None):
        """
        Update task in task registry with deployment URL using task_storage.
        Falls back to direct database update if task_storage is not available.
        """
        try:
            if self.task_storage:
                # Use task_storage if available
                self.task_storage.update_task_with_git_url(task_id, git_url, deployment_url)
            else:
                # Fallback: direct database update
                import psycopg2
                import json

                conn = psycopg2.connect(
                    host="127.0.0.1",
                    database="mcp_registry",
                    user="postgres",
                    password="postgres"
                )
                cursor = conn.cursor()

                # Build metadata update
                metadata_update = {
                    "storage_type": "git",
                    "git_url": git_url,
                    "path": git_url
                }
                if deployment_url:
                    metadata_update["deployment_url"] = deployment_url

                # Update status to done and add Git URL to metadata
                cursor.execute("""
                    UPDATE task_registry
                    SET status = %s,
                        status_reason = %s,
                        metadata = metadata || %s::jsonb,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE task_id = %s
                """, (
                    "done",
                    "Task completed successfully. Result stored at: " + git_url,
                    json.dumps(metadata_update),
                    task_id
                ))

                affected_rows = cursor.rowcount
                conn.commit()
                cursor.close()
                conn.close()

                if affected_rows > 0:
                    msg = f"Task {task_id} updated with Git URL"
                    if deployment_url:
                        msg += f" and deployment URL: {deployment_url}"
                    deployment_logger.info(msg)
        except Exception as e:
            deployment_logger.error(f"Failed to update task {task_id} with deployment URL: {e}")

    def _update_deployment_status(self, task_id, status):
        """Update deployment status in database"""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host="127.0.0.1",
                database="mcp_registry",
                user="postgres",
                password="postgres"
            )
            cursor = conn.cursor()
            if status == "stopped":
                cursor.execute("""
                    UPDATE task_deployments
                    SET status = %s, stopped_at = CURRENT_TIMESTAMP
                    WHERE task_id = %s
                """, (status, task_id))
            else:
                cursor.execute("""
                    UPDATE task_deployments SET status = %s WHERE task_id = %s
                """, (status, task_id))
            conn.commit()
            cursor.close()
            conn.close()
        except Exception as e:
            print(f"Warning: Could not update deployment status: {e}")

    def _get_deployments(self, status_filter="running"):
        """Get deployments from database with actual Docker status"""
        import subprocess
        import psycopg2
        from datetime import datetime, date
        
        try:
            conn = psycopg2.connect(
                host="127.0.0.1",
                database="mcp_registry",
                user="postgres",
                password="postgres"
            )
            cursor = conn.cursor()
            if status_filter == "all":
                cursor.execute("SELECT * FROM task_deployments ORDER BY created_at DESC")
            else:
                cursor.execute("SELECT * FROM task_deployments WHERE status = %s ORDER BY created_at DESC",
                             (status_filter,))
            columns = [desc[0] for desc in cursor.description]
            deployments = []
            
            for row in cursor.fetchall():
                dep_dict = dict(zip(columns, row))
                # Convert datetime objects to ISO format strings for JSON serialization
                for key, value in dep_dict.items():
                    if isinstance(value, (datetime, date)):
                        dep_dict[key] = value.isoformat()
                
                # Get actual Docker status
                task_id = dep_dict.get("task_id", "")
                container_name = f"deploy-{task_id}".lower()

                try:
                    # Check container status from Docker
                    result = subprocess.run(
                        ["docker", "ps", "-a", "--filter", f"name={container_name}", "--format", "{{.Status}}"],
                        capture_output=True, text=True, timeout=5
                    )

                    docker_status = result.stdout.strip()

                    if docker_status:
                        # Update status based on actual Docker state
                        if "Up" in docker_status:
                            dep_dict["status"] = "running"
                            # Update database if it was wrong
                            if dep_dict.get("status") != "running":
                                self._update_deployment_status(task_id, "running")
                        elif "Exited" in docker_status:
                            dep_dict["status"] = "stopped"
                            # Update database if it was wrong
                            if dep_dict.get("status") != "stopped":
                                self._update_deployment_status(task_id, "stopped")
                        else:
                            dep_dict["status"] = "unknown"
                    else:
                        # Container doesn't exist - mark as deleted and skip
                        dep_dict["status"] = "deleted"
                        # Update database
                        self._update_deployment_status(task_id, "deleted")

                except Exception as e:
                    print(f"Warning: Could not check Docker status for {container_name}: {e}")
                    # Keep database status if Docker check fails

                # Skip deleted deployments - don't show them in the list
                if dep_dict.get("status") != "deleted":
                    deployments.append(dep_dict)

            cursor.close()
            conn.close()
            return deployments
        except Exception as e:
            print(f"Warning: Could not get deployments: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _get_deployment(self, task_id):
        """Get single deployment from database"""
        deployments = self._get_deployments("all")
        for d in deployments:
            if d.get("task_id") == task_id:
                return d
        return None

    def _execute_tool_with_llm(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a tool using LLM API through LM Studio"""
        # Build the prompt for the LLM
        system_prompt = """You are an expert DevOps Release Engineer AI assistant. 
Your task is to help with CI/CD pipeline configuration, infrastructure provisioning, 
deployment orchestration, and build optimization. 

Provide concrete, actionable output in the appropriate format for the requested operation.
For code/config generation, provide complete, valid configuration files or scripts.
For analysis tasks, provide detailed analysis with specific recommendations."""

        user_prompt = f"""Task: {tool_name}

Arguments:
{json.dumps(arguments, indent=2)}

Please process this DevOps task and provide appropriate output.
For configuration generation tasks, provide complete configuration files.
For analysis tasks, provide detailed analysis with specific recommendations."""

        payload = {
            "model": self.llm_model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.7
        }

        try:
            response = requests.post(
                self.llm_provider_url,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            return {"output": content, "tool_used": tool_name, "arguments": arguments}
        except Exception as e:
            return {"error": f"LLM API call failed: {str(e)}"}

    def handle_resources_list(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle resources/list request"""
        if params is None:
            params = {}

        pagination = params.get("pagination", {})
        cursor = pagination.get("cursor")
        limit = min(pagination.get("limit", len(self.resources)), 100)

        if cursor:
            pass

        return {
            "resources": self.resources[:limit],
            "pagination": {
                "hasMore": len(self.resources) > limit,
                "nextCursor": f"cursor_{limit}" if len(self.resources) > limit else None
            } if limit < len(self.resources) else {}
        }

    def handle_resources_read(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle resources/read request"""
        if params is None:
            params = {}

        uri = params.get("uri")

        resource = None
        for r in self.resources:
            if r["uri"] == uri:
                resource = r
                break

        if not resource:
            raise ValueError(f"Resource '{uri}' not found")

        return self._read_resource(resource)

    def _read_resource(self, resource: Dict[str, Any]) -> Dict[str, Any]:
        """Read content from a specific resource"""
        uri = resource["uri"]

        # Return static content for resources
        content_map = {
            "devops://resource/deployment-status": {
                "contents": [{
                    "uri": uri,
                    "text": "# Deployment Status Dashboard\n\nNo active deployments currently.\n\n## Environment Status:\n- Development: Ready\n- Staging: Ready\n- Production: Ready"
                }]
            },
            "devops://resource/build-metrics": {
                "contents": [{
                    "uri": uri,
                    "text": "# Build Metrics Report\n\n## Current Performance:\n- Average Build Time: 5m 23s\n- Success Rate: 98.5%\n- Failure Rate: 1.5%\n\n## Recent Builds:\n- Build #1234: Success (4m 52s)\n- Build #1235: Success (5m 10s)\n- Build #1236: Failed (3m 45s)"
                }]
            },
            "devops://resource/infrastructure-status": {
                "contents": [{
                    "uri": uri,
                    "text": "# Infrastructure Status\n\n## Provisioned Resources:\n- AWS EC2 Instances: 5\n- AWS RDS Databases: 2\n- Kubernetes Clusters: 1\n\n## Capacity:\n- CPU: 40% utilized\n- Memory: 35% utilized\n- Storage: 28% utilized"
                }]
            },
            "devops://resource/deployment-history": {
                "contents": [{
                    "uri": uri,
                    "text": "# Deployment History\n\n## Recent Deployments:\n| Version | Environment | Timestamp | Status |\n|---------|-------------|-----------|--------|\n| v2.1.0 | Production | 2024-03-01 14:30:00 | Success |\n| v2.0.9 | Staging | 2024-03-01 10:15:00 | Success |\n| v2.0.8 | Development | 2024-02-29 16:00:00 | Success |\n\n## Deployment Frequency:\n- Daily: 3 deployments\n- Weekly: 15 deployments\n- Monthly: 60 deployments"
                }]
            }
        }

        if uri in content_map:
            return content_map[uri]

        return {
            "contents": [{
                "uri": uri,
                "text": f"Content for resource: {uri}"
            }]
        }

    def handle_prompts_list(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle prompts/list request"""
        if params is None:
            params = {}

        pagination = params.get("pagination", {})
        cursor = pagination.get("cursor")
        limit = min(pagination.get("limit", len(self.prompts)), 100)

        if cursor:
            pass

        return {
            "prompts": self.prompts[:limit],
            "pagination": {
                "hasMore": len(self.prompts) > limit,
                "nextCursor": f"cursor_{limit}" if len(self.prompts) > limit else None
            } if limit < len(self.prompts) else {}
        }

    def handle_prompts_get(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle prompts/get request"""
        if params is None:
            params = {}

        prompt_name = params.get("name")
        prompt_arguments = params.get("arguments", {})

        prompt = None
        for p in self.prompts:
            if p["name"] == prompt_name:
                prompt = p
                break

        if not prompt:
            raise ValueError(f"Prompt '{prompt_name}' not found")

        return self._resolve_prompt(prompt, prompt_arguments)

    def _resolve_prompt(self, prompt: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Resolve a prompt with given arguments"""
        prompt_name = prompt["name"]

        # Generate prompt content with arguments
        resolved_content = f"# {prompt_name.replace('_', ' ').title()}\n\n"
        resolved_content += "## Arguments:\n"
        for arg_name, arg_value in arguments.items():
            resolved_content += f"- **{arg_name}**: {arg_value}\n"

        resolved_content += "\n## DevOps Release Engineer Guidance:\n"
        resolved_content += "Based on the provided arguments, here are recommended actions and considerations:\n\n"
        resolved_content += "1. Review the provided arguments for completeness\n"
        resolved_content += "2. Consider infrastructure and environment requirements\n"
        resolved_content += "3. Verify deployment targets and strategies\n"
        resolved_content += "4. Plan rollback procedures and rollback criteria\n"
        resolved_content += "5. Set up health monitoring and alerting"

        return {
            "contents": [{
                "type": "text",
                "text": resolved_content
            }]
        }

    def handle_shutdown(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle shutdown request"""
        print("Shutdown request received, preparing to shut down DevOps Release Engineer server...")
        return {}

    def handle_ping(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle ping request for health check"""
        if params is None:
            params = {}

        return {
            "timestamp": time.time(),
            "status": "healthy",
            "server": "devops-release-engineer",
            "version": "1.0.0"
        }

    def _extract_code_field(self, content: str, result_file: str, logger: logging.Logger) -> str:
        """
        Extract the 'code' field value from a JSON-like string that may contain
        non-JSON content (like triple-quoted strings) inside the code value.

        Handles truncated files where the code value ends mid-structure.

        Args:
            content: The raw file content
            result_file: Path to the result file (for logging)
            logger: Logger instance

        Returns:
            The extracted code string, or empty string if extraction fails
        """
        import re

        logger.info(f"Attempting to extract 'code' field from non-JSON content")

        # Strategy 1: Try to find "code": " and extract the value
        code_start_match = re.search(r'"code"\s*:\s*"', content)
        if code_start_match:
            start = code_start_match.end()

            # Extract everything after "code": "
            code_value = content[start:]

            # Unescape JSON escape sequences
            code_value = code_value.replace('\\"', '"')
            code_value = code_value.replace("\\'", "'")
            code_value = code_value.replace("\\n", "\n")
            code_value = code_value.replace("\\t", "\t")
            code_value = code_value.replace("\\r", "\r")

            # The file may be truncated in the middle of the code
            # Check if the last line ends with \ (incomplete line)
            lines = code_value.split('\n')
            if lines and lines[-1].endswith('\\'):
                # Remove the incomplete last line
                code_value = '\n'.join(lines[:-1])
                logger.info("Removed incomplete last line due to truncation")

            # Check if the last triple quote has a closing
            # The HTML template in Python uses triple quotes: """
            last_triple = code_value.rfind('"""')
            if last_triple >= 0:
                # Check what's after the last triple quote
                after_triple = code_value[last_triple + 3:]

                # If there's content after the last triple quote and it doesn't contain
                # another triple quote, the HTML template is incomplete
                if after_triple and '"""' not in after_triple:
                    # The HTML template is incomplete - add closing brackets
                    # to complete the JavaScript structures and Python dict

                    # Check the last meaningful line to understand the structure
                    last_lines = after_triple.split('\n')
                    last_meaningful = ""
                    for i in range(len(last_lines) - 1, -1, -1):
                        line = last_lines[i].strip()
                        if line and not line.startswith('//'):
                            last_meaningful = line
                            break

                    # Determine what closing brackets are needed based on the structure
                    closing_needed = []

                    if 'const directions = [' in after_triple:
                        # Close the directions array
                        closing_needed.append('                ]')
                    if 'ghosts.forEach(ghost => {' in after_triple:
                        # Close the forEach block
                        closing_needed.append('            });')
                    if 'html": """' in after_triple or last_meaningful:
                        # Close the HTML template
                        closing_needed.append('        """')
                        # Close the "pacman" dict
                        closing_needed.append('    },')
                        # Close the GAME_TEMPLATES dict
                        closing_needed.append('}')

                    if closing_needed:
                        code_value = code_value.rstrip() + '\n' + '\n'.join(closing_needed) + '\n'
                        logger.info("Added closing brackets to complete truncated structure")
                    else:
                        # Just add closing """
                        code_value = code_value.rstrip() + '\n"""\n'
                        logger.info("Added closing \"\"\" to complete incomplete HTML template")

            if code_value:
                logger.info("Successfully extracted code field")
                return code_value

        # Strategy 2: Try standard JSON parsing first (file may not be truncated)
        try:
            import json
            data = json.loads(content)
            code_content = data.get("code", "")
            if code_content:
                logger.info("Successfully parsed JSON and extracted code field")
                return code_content
        except json.JSONDecodeError:
            logger.warning("Standard JSON parsing failed, trying alternative extraction")

        logger.error("Failed to extract code field from result file")
        return ""

    def _is_closing_quote(self, content: str, string_start: int, quote_pos: int) -> bool:
        """
        Determine if a quote at quote_pos is the closing quote of a string.
        Uses a simple state machine to track escape sequences.
        """
        # Check characters before the quote to see if it's escaped
        i = quote_pos - 1
        backslash_count = 0

        while i >= string_start and content[i] == '\\':
            backslash_count += 1
            i -= 1

        # If odd number of backslashes, this quote is escaped
        return backslash_count % 2 == 0
