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
                 llm_provider_url: str = "http://192.168.51.237:1234/v1/chat/completions",
                 llm_model: str = "qwen3.5-35b-a3b@q5_k_xl",
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

        # LLM Configuration
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

        # Execute tool using LLM via LM Studio API
        try:
            result = self._execute_tool_with_llm(tool_name, arguments)
            return {"result": result}
        except Exception as e:
            return {"error": f"Failed to execute tool: {str(e)}"}

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
