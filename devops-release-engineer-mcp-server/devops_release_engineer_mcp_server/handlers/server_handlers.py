"""
DevOps Release Engineer Server Handlers for MCP Server
Implements DevOps Release Engineer specific functionality for CI/CD, IaC, and deployment orchestration
"""
import time
import json
import os
import re
import requests
from typing import Dict, Any, List, Optional
from devops_release_engineer_mcp_server.utils.json_rpc import JsonRpcHandler, JsonRpcMessage


class DevOpsReleaseEngineerHandlers:
    """Handles DevOps Release Engineer specific MCP server methods"""

    def __init__(self, enable_registry: bool = False, use_postgres: bool = False,
                 postgres_config: Optional[Dict[str, Any]] = None, client_handlers=None,
                 llm_provider_url: Optional[str] = None,
                 llm_model: Optional[str] = None,
                 prompts_dir: str = "."):
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
        
        try:
            # Extract UUID from git URL
            # Format: ssh://sorokin@192.168.51.187/home/sorokin/mcp-results/tree/main/results/<uuid>/result.py
            uuid_match = re.search(r'/results/([a-f0-9-]+)/', git_url)
            if not uuid_match:
                return {"error": "Could not extract UUID from git URL"}
            
            result_uuid = uuid_match.group(1)
            
            # Extract base git repo URL
            # Convert ssh://user@host/path/to/repo/tree/main/results/uuid/file.py to ssh://user@host/path/to/repo.git
            # Match everything up to the repo name (before /tree/main/)
            if "/tree/main/" in git_url:
                git_repo_url = git_url.split("/tree/main/")[0] + ".git"
            else:
                git_repo_url = "ssh://sorokin@192.168.51.187/home/sorokin/mcp-results.git"
            
            print(f"Deploying from repo: {git_repo_url}, UUID: {result_uuid}")
            
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
            
            # Copy result.py to deploy directory
            result_file = os.path.join(git_workdir, "results", result_uuid, "result.py")
            if not os.path.exists(result_file):
                return {"error": f"result.py not found at {result_file}"}
            
            import shutil
            shutil.copy(result_file, os.path.join(deploy_dir, "result.py"))
            
            # Detect dependencies from imports
            with open(os.path.join(deploy_dir, "result.py"), 'r') as f:
                content = f.read()

            dependencies = ["flask"]  # Default
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

            # Create Dockerfile with detected port
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
            image_name = f"deploy-{task_id}"
            container_name = f"deploy-{task_id}"

            subprocess.run([
                "docker", "build", "-t", image_name, deploy_dir
            ], check=True, capture_output=True, timeout=120)

            # Run container
            subprocess.run([
                "docker", "run", "-d",
                "--name", container_name,
                "-p", f"{host_port}:{container_port}",
                "--memory", memory_limit,
                "--cpus", cpu_limit,
                "--restart", "unless-stopped",
                image_name
            ], check=True, capture_output=True, timeout=30)

            # Store deployment in database
            deployment_url = f"http://{deployment_host}:{host_port}/"
            self._store_deployment(task_id, container_name, container_port, host_port, 
                                   deployment_url, git_url, image_name, memory_limit, cpu_limit)
            
            # Cleanup
            subprocess.run(["rm", "-rf", git_workdir], check=True)
            subprocess.run(["rm", "-rf", deploy_dir], check=True)
            
            return {
                "success": True,
                "task_id": task_id,
                "container_id": container_name,
                "host_port": host_port,
                "deployment_url": deployment_url,
                "message": f"Application deployed successfully at {deployment_url}"
            }
            
        except subprocess.TimeoutExpired as e:
            return {"error": f"Docker command timed out: {str(e)}"}
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if e.stderr else str(e)
            return {"error": f"Docker command failed: {stderr}"}
        except Exception as e:
            return {"error": f"Deployment failed: {str(e)}"}

    def _stop_deployment(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Stop a deployment (keep container for restart)"""
        import subprocess

        task_id = arguments.get("task_id")
        container_name = f"deploy-{task_id}"

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
        container_name = f"deploy-{task_id}"
        
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
            print(f"Warning: Could not store deployment: {e}")

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
                container_name = f"deploy-{task_id}"

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
            "temperature": 0.7,
            "max_tokens": 4096
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
