"""
AI Coding Agent MCP Server
Implements an MCP server that accepts coding tasks and processes them using an LLM
"""
import asyncio
import os
from typing import Dict, Any, Optional
import json
import uuid
from pathlib import Path

from openai import OpenAI
from mcp_server.server import McpServer
from mcp_server.handlers.server_handlers import McpServerHandlers
from mcp_server.utils.notifications import NotificationManager


class AiCodingAgentServer(McpServer):
    """AI Coding Agent MCP Server that integrates with LM Studio"""

    def __init__(self, transport_type="stdio", host="127.0.0.1", port=3050, enable_registry=False, 
                 register_with_registry=False, registry_host="127.0.0.1", registry_port=3031,
                 use_postgres=False, postgres_host="127.0.0.1", postgres_port=5432,
                 postgres_db="mcp_registry", postgres_user="postgres", postgres_password="",
                 max_concurrent_requests=10):
        import time
        # Set start time for health checks
        self._start_time = time.time()
        
        # Initialize with custom handlers
        # Use environment variables for configuration with fallback defaults
        llm_base_url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")  # Default to localhost for testing
        llm_api_key = os.getenv("LLM_API_KEY", "not-needed-for-local-llm")    # Default API key
        llm_model_name = os.getenv("LLM_MODEL_NAME", "qwen3-4b")              # Default model
        
        try:
            self.llm_client = OpenAI(
                base_url=llm_base_url,
                api_key=llm_api_key
            )
            self.model_name = llm_model_name
        except Exception as e:
            print(f"⚠️  Warning: Could not initialize LLM client: {e}")
            print("⚠️  The server will start but LLM functionality will be limited.")
            self.llm_client = None
            self.model_name = llm_model_name
        
        super().__init__(
            transport_type=transport_type,
            host=host,
            port=port,
            enable_registry=enable_registry,
            register_with_registry=register_with_registry,
            registry_host=registry_host,
            registry_port=registry_port,
            use_postgres=use_postgres,
            postgres_host=postgres_host,
            postgres_port=postgres_port,
            postgres_db=postgres_db,
            postgres_user=postgres_user,
            postgres_password=postgres_password,
            max_concurrent_requests=max_concurrent_requests
        )

        # Customize server handlers
        self._configure_coding_agent_handlers()

    def _configure_coding_agent_handlers(self):
        """Configure the server with coding agent specific tools, resources, and prompts"""
        
        # Clear default tools and add coding-specific ones
        self.server_handlers.tools = []
        self.server_handlers.resources = []
        self.server_handlers.prompts = []
        
        # Add coding agent tools
        coding_tools = [
            {
                "name": "execute_coding_task",
                "description": "Execute a coding task using an AI coding agent",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_description": {
                            "type": "string",
                            "description": "Detailed description of the coding task to be performed"
                        },
                        "context": {
                            "type": "string",
                            "description": "Additional context or requirements for the task",
                            "default": ""
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Path to file if the task involves modifying an existing file",
                            "default": ""
                        }
                    },
                    "required": ["task_description"]
                }
            },
            {
                "name": "generate_code_solution",
                "description": "Generate a complete code solution based on requirements",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "requirements": {
                            "type": "string",
                            "description": "Requirements for the code to be generated"
                        },
                        "language": {
                            "type": "string",
                            "description": "Programming language for the solution",
                            "default": "python"
                        },
                        "constraints": {
                            "type": "string",
                            "description": "Any constraints or limitations for the solution",
                            "default": ""
                        }
                    },
                    "required": ["requirements"]
                }
            },
            {
                "name": "review_code",
                "description": "Review code for quality, efficiency, and best practices",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {
                            "type": "string",
                            "description": "Code to be reviewed"
                        },
                        "review_criteria": {
                            "type": "string",
                            "description": "Specific criteria to focus on during review",
                            "default": "general quality, efficiency, best practices"
                        }
                    },
                    "required": ["code"]
                }
            }
        ]

        # Add coding resources
        coding_resources = [
            {
                "uri": "coding-agent://capabilities",
                "name": "AI Coding Agent Capabilities",
                "description": "Information about the AI coding agent's capabilities and supported languages"
            },
            {
                "uri": "coding-agent://status",
                "name": "AI Coding Agent Status",
                "description": "Current status of the AI coding agent service"
            }
        ]

        # Add coding prompts
        coding_prompts = [
            {
                "name": "coding_task_template",
                "description": "Template for processing coding tasks",
                "arguments": [
                    {
                        "name": "task_description",
                        "type": "string",
                        "description": "Description of the coding task"
                    },
                    {
                        "name": "context",
                        "type": "string",
                        "description": "Additional context for the task"
                    }
                ]
            },
            {
                "name": "code_review_template",
                "description": "Template for code review tasks",
                "arguments": [
                    {
                        "name": "code",
                        "type": "string",
                        "description": "Code to be reviewed"
                    },
                    {
                        "name": "criteria",
                        "type": "string",
                        "description": "Review criteria"
                    }
                ]
            }
        ]

        # Add all custom elements to handlers
        self.server_handlers.tools.extend(coding_tools)
        self.server_handlers.resources.extend(coding_resources)
        self.server_handlers.prompts.extend(coding_prompts)

        # Add health check functionality
        self._add_health_check_functionality()

        # Register custom handlers with the RPC handler after initialization
        self._register_custom_handlers()
        
        # Override resource and prompt handlers to handle custom ones
        self._override_resource_and_prompt_handlers()

    def _add_health_check_functionality(self):
        """Add health check tools and resources"""
        # Add health check tool
        health_check_tool = {
            "name": "health_check",
            "description": "Perform a health check on the AI coding agent service",
            "inputSchema": {
                "type": "object",
                "properties": {
                    "detailed": {
                        "type": "boolean",
                        "description": "Whether to return detailed health information",
                        "default": False
                    }
                }
            }
        }
        self.server_handlers.tools.append(health_check_tool)

        # Add health check resource
        health_check_resource = {
            "uri": "coding-agent://health",
            "name": "AI Coding Agent Health Status",
            "description": "Health status of the AI coding agent service"
        }
        self.server_handlers.resources.append(health_check_resource)

    def _register_custom_handlers(self):
        """Register custom handlers with the RPC handler"""
        # Store the original tools/call handler
        original_tools_call_handler = self.server_handlers.handle_tools_call
        
        # Create a wrapped handler that checks for custom tools first
        async def wrapped_tools_call_handler(params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
            tool_name = params.get('name')

            # Check if this is one of our custom tools
            if tool_name == "execute_coding_task":
                return await self._handle_execute_coding_task(params, request_id)
            elif tool_name == "generate_code_solution":
                return await self._handle_generate_code_solution(params, request_id)
            elif tool_name == "review_code":
                return await self._handle_review_code(params, request_id)
            elif tool_name == "health_check":
                return await self._handle_health_check(params, request_id)
            else:
                # Fall back to the original tools/call handler for other tools
                return await original_tools_call_handler(params, request_id)
        
        # Register the wrapped handler
        self.rpc_handler.register_request_handler('tools/call', wrapped_tools_call_handler)

    def _override_resource_and_prompt_handlers(self):
        """Override resource and prompt handlers to handle custom ones"""
        # Store original handlers
        original_resources_read_handler = self.server_handlers.handle_resources_read
        original_prompts_get_handler = self.server_handlers.handle_prompts_get
        
        # Create wrapped resource handler
        async def wrapped_resources_read_handler(params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
            uri = params.get('uri')
            
            # Check if this is one of our custom resources
            if uri == "coding-agent://capabilities":
                return {
                    "contents": json.dumps({
                        "name": "AI Coding Agent",
                        "version": "1.0.0",
                        "capabilities": [
                            "execute_coding_task",
                            "generate_code_solution", 
                            "review_code",
                            "health_check"
                        ],
                        "supported_languages": [
                            "Python", "JavaScript", "TypeScript", "Java", "C++", "Go", "Rust", "HTML", "CSS"
                        ],
                        "description": "An AI-powered coding assistant that can help with various programming tasks"
                    }, indent=2),
                    "uri": uri
                }
            elif uri == "coding-agent://health":
                return {
                    "contents": json.dumps({
                        "status": "online",
                        "model": self.model_name,
                        "llm_endpoint": "http://asus-tus:1234/v1",
                        "timestamp": str(uuid.uuid4())
                    }, indent=2),
                    "uri": uri
                }
            elif uri == "coding-agent://status":
                return {
                    "contents": json.dumps({
                        "status": "online",
                        "model": self.model_name,
                        "llm_endpoint": "http://asus-tus:1234/v1",
                        "timestamp": str(uuid.uuid4())
                    }, indent=2),
                    "uri": uri
                }
            else:
                # Fall back to the original handler for other resources
                return await original_resources_read_handler(params, request_id)
        
        # Create wrapped prompt handler
        async def wrapped_prompts_get_handler(params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
            prompt_name = params.get('name')
            arguments = params.get('arguments', {})
            
            # Check if this is one of our custom prompts
            if prompt_name == "coding_task_template":
                task_description = arguments.get("task_description", "")
                context = arguments.get("context", "")
                
                template = f"""
                You are an expert coding assistant. Please help with the following coding task:

                TASK: {task_description}

                CONTEXT: {context}

                Provide a complete solution with code, explanations, and any necessary steps.
                """
                
                return {
                    "prompt": template,
                    "name": prompt_name,
                    "resolved_arguments": arguments
                }
            elif prompt_name == "code_review_template":
                code = arguments.get("code", "")
                criteria = arguments.get("criteria", "general quality, efficiency, best practices")
                
                template = f"""
                You are an expert code reviewer. Please review the following code based on these criteria:
                CRITERIA: {criteria}

                CODE TO REVIEW:
                ```
                {code}
                ```

                Provide detailed feedback on code quality, efficiency, best practices, potential bugs, and suggestions for improvement.
                """
                
                return {
                    "prompt": template,
                    "name": prompt_name,
                    "resolved_arguments": arguments
                }
            else:
                # Fall back to the original handler for other prompts
                return await original_prompts_get_handler(params, request_id)
        
        # Register the wrapped handlers
        self.rpc_handler.register_request_handler('resources/read', wrapped_resources_read_handler)
        self.rpc_handler.register_request_handler('prompts/get', wrapped_prompts_get_handler)


    async def _handle_execute_coding_task(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle execute_coding_task requests"""
        task_description = params.get("task_description", "")
        context = params.get("context", "")
        file_path = params.get("file_path", "")

        # Check if LLM client is available
        if self.llm_client is None:
            return {
                "task_completed": False,
                "error": "LLM client is not available. Please check LLM configuration.",
                "task_description": task_description
            }

        # Construct the prompt for the LLM
        prompt = f"""
        You are an expert coding assistant. Please help with the following coding task:

        TASK: {task_description}

        CONTEXT: {context}

        If a file path is provided, consider the existing content:
        FILE PATH: {file_path}

        Provide a complete solution with code, explanations, and any necessary steps.
        """

        try:
            import httpx
            # Call the LM Studio API with timeout
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2048,
                timeout=30.0  # Add timeout to prevent hanging
            )

            result = {
                "task_completed": True,
                "solution": response.choices[0].message.content,
                "task_description": task_description,
                "timestamp": str(uuid.uuid4())
            }

            return result

        except Exception as e:
            return {
                "task_completed": False,
                "error": f"Failed to execute coding task: {str(e)}",
                "task_description": task_description
            }

    async def _handle_generate_code_solution(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle generate_code_solution requests"""
        requirements = params.get("requirements", "")
        language = params.get("language", "python")
        constraints = params.get("constraints", "")

        # Check if LLM client is available
        if self.llm_client is None:
            return {
                "solution_generated": False,
                "error": "LLM client is not available. Please check LLM configuration.",
                "requirements": requirements
            }

        # Construct the prompt for the LLM
        prompt = f"""
        You are an expert coding assistant. Generate a complete code solution based on the following requirements:

        REQUIREMENTS: {requirements}

        LANGUAGE: {language}

        CONSTRAINTS: {constraints}

        Provide the complete code solution with appropriate comments and documentation.
        """

        try:
            # Call the LM Studio API with timeout
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.7,
                max_tokens=2048,
                timeout=30.0  # Add timeout to prevent hanging
            )

            result = {
                "solution_generated": True,
                "code": response.choices[0].message.content,
                "language": language,
                "requirements": requirements,
                "timestamp": str(uuid.uuid4())
            }

            return result

        except Exception as e:
            return {
                "solution_generated": False,
                "error": f"Failed to generate code solution: {str(e)}",
                "requirements": requirements
            }

    async def _handle_review_code(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle review_code requests"""
        code = params.get("code", "")
        review_criteria = params.get("review_criteria", "general quality, efficiency, best practices")

        # Check if LLM client is available
        if self.llm_client is None:
            return {
                "review_completed": False,
                "error": "LLM client is not available. Please check LLM configuration.",
                "review_criteria": review_criteria
            }

        # Construct the prompt for the LLM
        prompt = f"""
        You are an expert code reviewer. Please review the following code based on these criteria:
        CRITERIA: {review_criteria}

        CODE TO REVIEW:
        ```
        {code}
        ```

        Provide detailed feedback on code quality, efficiency, best practices, potential bugs, and suggestions for improvement.
        """

        try:
            # Call the LM Studio API with timeout
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.5,
                max_tokens=1536,
                timeout=30.0  # Add timeout to prevent hanging
            )

            result = {
                "review_completed": True,
                "feedback": response.choices[0].message.content,
                "review_criteria": review_criteria,
                "timestamp": str(uuid.uuid4())
            }

            return result

        except Exception as e:
            return {
                "review_completed": False,
                "error": f"Failed to review code: {str(e)}",
                "review_criteria": review_criteria
            }

    async def _handle_health_check(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """Handle health check requests"""
        detailed = params.get("detailed", False)

        # Check if LLM client is available
        if self.llm_client is None:
            health_status = {
                "status": "unhealthy",
                "timestamp": str(uuid.uuid4()),
                "service": "AI Coding Agent",
                "version": "1.0.0",
                "llm_connection": {
                    "accessible": False,
                    "endpoint": os.getenv("LLM_BASE_URL", "http://localhost:1234/v1"),
                    "model": self.model_name,
                    "response": "LLM client not initialized"
                }
            }
        else:
            try:
                # Test the LLM connection
                test_result = self.llm_client.chat.completions.create(
                    model=self.model_name,
                    messages=[{"role": "user", "content": "Health check. Respond with 'OK'."}],
                    temperature=0.1,
                    max_tokens=10,
                    timeout=10.0  # Add timeout for health check
                )

                llm_accessible = True
                llm_response = test_result.choices[0].message.content.strip()
            except Exception as e:
                llm_accessible = False
                llm_response = f"Error: {str(e)}"

            health_status = {
                "status": "healthy" if llm_accessible else "unhealthy",
                "timestamp": str(uuid.uuid4()),
                "service": "AI Coding Agent",
                "version": "1.0.0",
                "llm_connection": {
                    "accessible": llm_accessible,
                    "endpoint": os.getenv("LLM_BASE_URL", "http://localhost:1234/v1"),
                    "model": self.model_name,
                    "response": llm_response
                }
            }

        if detailed:
            # Add more detailed information
            import psutil
            import time

            uptime = time.time() - getattr(self, '_start_time', time.time())
            health_status["detailed_info"] = {
                "uptime_seconds": uptime,
                "cpu_percent": psutil.cpu_percent(),
                "memory_percent": psutil.virtual_memory().percent,
                "active_requests": getattr(self.rpc_handler, 'get_active_request_count', lambda: 0)(),
                "total_requests_handled": getattr(self, 'request_counter', 0)
            }

        return health_status


def run_coding_agent_server(transport_type="http", host="127.0.0.1", port=3050, enable_registry=False, 
                           register_with_registry=False, registry_host="127.0.0.1", registry_port=3031,
                           max_concurrent_requests=10):
    """Run the AI Coding Agent server"""
    llm_base_url = os.getenv("LLM_BASE_URL", "http://localhost:1234/v1")
    llm_model_name = os.getenv("LLM_MODEL_NAME", "qwen3-4b")
    
    print(f"Starting AI Coding Agent MCP Server...")
    print(f"LLM Endpoint: {llm_base_url}")
    print(f"Model: {llm_model_name}")
    print(f"Transport: {transport_type}")
    print(f"Address: {host}:{port}")
    
    server = AiCodingAgentServer(
        transport_type=transport_type,
        host=host,
        port=port,
        enable_registry=enable_registry,
        register_with_registry=register_with_registry,
        registry_host=registry_host,
        registry_port=registry_port,
        max_concurrent_requests=max_concurrent_requests
    )
    server.start()


if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='AI Coding Agent MCP Server')
    parser.add_argument('--transport',
                       choices=['stdio', 'http'],
                       default='http',
                       help='Transport mechanism to use (default: http)')
    parser.add_argument('--host',
                       default='127.0.0.1',
                       help='Host for HTTP transport (default: 127.0.0.1)')
    parser.add_argument('--port',
                       type=int,
                       default=3050,
                       help='Port for HTTP transport (default: 3050)')
    parser.add_argument('--enable-registry',
                       action='store_true',
                       help='Enable registry functionality to track multiple MCP services (optional)')
    parser.add_argument('--register-with-registry',
                       action='store_true',
                       help='Register this server with a registry server (requires --registry-host and --registry-port)')
    parser.add_argument('--registry-host',
                       default='127.0.0.1',
                       help='Registry server host to register with (default: 127.0.0.1)')
    parser.add_argument('--registry-port',
                       type=int,
                       default=3031,
                       help='Registry server port to register with (default: 3031)')
    parser.add_argument('--max-concurrent-requests',
                       type=int,
                       default=10,
                       help='Maximum number of concurrent requests (default: 10)')

    args = parser.parse_args()

    run_coding_agent_server(
        transport_type=args.transport,
        host=args.host,
        port=args.port,
        enable_registry=args.enable_registry,
        register_with_registry=args.register_with_registry,
        registry_host=args.registry_host,
        registry_port=args.registry_port,
        max_concurrent_requests=args.max_concurrent_requests
    )