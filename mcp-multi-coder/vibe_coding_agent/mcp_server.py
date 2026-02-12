"""
Vibe Coding AI Agent - MCP Server
Production-ready MCP server for AI coding agents with LM Studio integration
Built on top of the MCP Standard Skeleton
"""
import os
import yaml
from datetime import datetime
from typing import Dict, Any, Optional
import asyncio
import logging
from pathlib import Path

# Import the skeleton components
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'mcp-std-skeleton'))

from mcp_std_server.server import McpServer as BaseMcpServer
from mcp_std_server.handlers.server_handlers import McpServerHandlers as BaseMcpServerHandlers
from mcp_std_server.utils.json_rpc import JsonRpcHandler
from mcp_std_server.utils.notifications import NotificationManager
from mcp_std_server.handlers.client_handlers import ClientMethodsHandlers

# Import our coding tools
from .lmstudio_client import LMStudioClient
from . import tools

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('./logs/server.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class VibeCodingServerHandlers(BaseMcpServerHandlers):
    """Extended server handlers with coding agent tools"""
    
    def __init__(self, enable_registry: bool = False, use_postgres: bool = False,
                 postgres_config: Optional[Dict[str, Any]] = None):
        # Initialize the base class
        super().__init__(enable_registry, use_postgres, postgres_config)
        
        # Initialize LM Studio client for health checks
        self.lm_client = LMStudioClient()
        
        # Clear the example tools and add our coding agent tools
        self.tools = [
            {
                "name": "accept_task",
                "description": "Accepts a natural language task description and optional context files. Uses LM Studio to break down into subtasks, generate a plan (JSON schema output). Returns plan_id and structured plan.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "task_description": {"type": "string", "description": "Natural language description of the development task"},
                        "context_files": {
                            "type": "array", 
                            "items": {"type": "string"}, 
                            "description": "Optional list of file paths for context"
                        }
                    },
                    "required": ["task_description"]
                }
            },
            {
                "name": "get_plan_status",
                "description": "Retrieves status of an ongoing plan.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "plan_id": {"type": "string", "description": "Unique identifier of the plan"}
                    },
                    "required": ["plan_id"]
                }
            },
            {
                "name": "analyze_code",
                "description": "Analyzes code for bugs, optimization opportunities, explanations, or refactoring suggestions.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file to analyze"},
                        "analysis_type": {
                            "type": "string", 
                            "enum": ["bugs", "optimization", "explanation", "refactor"],
                            "description": "Type of analysis to perform"
                        },
                        "code_snippet": {"type": "string", "description": "Optional code snippet to analyze instead of file"}
                    },
                    "required": ["analysis_type"]
                }
            },
            {
                "name": "explain_code",
                "description": "Provides line-by-line or high-level explanation of code.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path to the file to explain"},
                        "code_snippet": {"type": "string", "description": "Optional code snippet to explain instead of file"},
                        "detail_level": {
                            "type": "string",
                            "enum": ["high_level", "detailed", "line_by_line"],
                            "default": "detailed"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "generate_code",
                "description": "Generates code from plan or natural language specification.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "specification": {"type": "string", "description": "Natural language specification or plan"},
                        "file_path": {"type": "string", "description": "Suggested file path for the generated code"},
                        "language": {"type": "string", "description": "Programming language for the code"}
                    },
                    "required": ["specification"]
                }
            },
            {
                "name": "write_file_content",
                "description": "Writes content to a file with security validation. Validates path is inside project root, prevents directory traversal, requires explicit confirmation flag.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path where to write the file"},
                        "content": {"type": "string", "description": "Content to write to the file"},
                        "confirm_write": {
                            "type": "boolean", 
                            "default": False,
                            "description": "Must be True to confirm the write operation"
                        },
                        "line_start": {"type": "integer", "description": "Optional start line for partial writes"},
                        "line_end": {"type": "integer", "description": "Optional end line for partial writes"}
                    },
                    "required": ["file_path", "content", "confirm_write"]
                }
            },
            {
                "name": "read_file_content",
                "description": "Reads file content with line-range support and encoding detection.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "file_path": {"type": "string", "description": "Path of the file to read"},
                        "start_line": {"type": "integer", "description": "Optional start line to read from"},
                        "end_line": {"type": "integer", "description": "Optional end line to read to"},
                        "encoding": {"type": "string", "description": "Optional encoding to use (auto-detected if not specified)"}
                    },
                    "required": ["file_path"]
                }
            },
            {
                "name": "execute_code",
                "description": "Executes code in a sandboxed environment with timeout protection and resource limits.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "code": {"type": "string", "description": "Code to execute"},
                        "language": {
                            "type": "string",
                            "enum": ["python", "bash"],
                            "description": "Programming language of the code"
                        },
                        "timeout": {
                            "type": "integer",
                            "default": 30,
                            "description": "Execution timeout in seconds"
                        },
                        "allow_network": {
                            "type": "boolean",
                            "default": False,
                            "description": "Whether to allow network access during execution"
                        }
                    },
                    "required": ["code", "language"]
                }
            },
            {
                "name": "run_tests",
                "description": "Discovers and runs tests, returning JUnit-style summary.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "test_pattern": {"type": "string", "description": "Pattern to match test files (e.g., 'test_*.py')"},
                        "test_directory": {"type": "string", "description": "Directory to search for tests"},
                        "framework": {
                            "type": "string",
                            "enum": ["pytest", "unittest", "custom"],
                            "default": "pytest"
                        }
                    },
                    "required": []
                }
            },
            {
                "name": "store_memory",
                "description": "Stores persistent key-value memory with categorization support.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Unique key for the memory"},
                        "value": {"type": "string", "description": "Value to store"},
                        "category": {"type": "string", "description": "Category for organizing memories"},
                        "metadata": {"type": "object", "description": "Optional metadata for the memory"}
                    },
                    "required": ["key", "value"]
                }
            },
            {
                "name": "retrieve_memory",
                "description": "Retrieves memory with semantic search capabilities.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "key": {"type": "string", "description": "Specific key to retrieve (exact match)"},
                        "query": {"type": "string", "description": "Semantic search query"},
                        "category": {"type": "string", "description": "Filter by category"},
                        "limit": {"type": "integer", "default": 5, "description": "Maximum number of results"}
                    },
                    "required": []
                }
            },
            {
                "name": "debug_error",
                "description": "Analyzes error messages and code to generate hypotheses and fixes.",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "error_message": {"type": "string", "description": "Error message to analyze"},
                        "code_snippet": {"type": "string", "description": "Code snippet related to the error"},
                        "context": {"type": "string", "description": "Additional context for debugging"}
                    },
                    "required": ["error_message"]
                }
            },
            {
                "name": "health",
                "description": "Returns health status of the server and LM Studio connectivity.",
                "inputSchema": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }
        ]
        
        # Clear example resources and prompts, or keep them if needed
        self.resources = []  # Clear example resources
        self.prompts = []    # Clear example prompts
        
        # Add our own resources and prompts if needed
        self.resources.extend([
            {
                "uri": "coding://memory/store",
                "name": "Memory Store",
                "description": "Persistent memory storage for the coding agent"
            }
        ])
        
        self.prompts.extend([
            {
                "name": "code_generation_prompt",
                "description": "Template for code generation tasks",
                "arguments": [
                    {
                        "name": "specification",
                        "type": "string",
                        "description": "Code specification"
                    },
                    {
                        "name": "language",
                        "type": "string", 
                        "description": "Target programming language"
                    }
                ]
            }
        ])

    def _execute_tool(self, tool: Dict[str, Any], arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Execute coding agent tools - sync version"""
        tool_name = tool["name"]
        
        # For async tools, we need to run them in an event loop
        import asyncio
        
        try:
            if tool_name == "accept_task":
                return asyncio.run(tools.accept_task(arguments))
            elif tool_name == "get_plan_status":
                return asyncio.run(tools.get_plan_status(arguments))
            elif tool_name == "analyze_code":
                return asyncio.run(tools.analyze_code(arguments))
            elif tool_name == "explain_code":
                return asyncio.run(tools.explain_code(arguments))
            elif tool_name == "generate_code":
                return asyncio.run(tools.generate_code(arguments))
            elif tool_name == "write_file_content":
                return asyncio.run(tools.write_file_content(arguments))
            elif tool_name == "read_file_content":
                return asyncio.run(tools.read_file_content(arguments))
            elif tool_name == "execute_code":
                return asyncio.run(tools.execute_code(arguments))
            elif tool_name == "run_tests":
                return asyncio.run(tools.run_tests(arguments))
            elif tool_name == "store_memory":
                return asyncio.run(tools.store_memory(arguments))
            elif tool_name == "retrieve_memory":
                return asyncio.run(tools.retrieve_memory(arguments))
            elif tool_name == "debug_error":
                return asyncio.run(tools.debug_error(arguments))
            elif tool_name == "health":
                # Health check - run the async method
                async def run_health_check():
                    lm_status = await self.lm_client.health_check()
                    return {
                        "status": "healthy" if lm_status.get("connected", False) else "unhealthy",
                        "timestamp": datetime.utcnow().isoformat(),
                        "uptime": "active",
                        "lm_studio_connected": lm_status.get("connected", False),
                        "model_loaded": lm_status.get("model_loaded", False),
                        "model_name": lm_status.get("model_name", "unknown"),
                        "recent_errors": 0
                    }
                
                return asyncio.run(run_health_check())
            else:
                # Call parent method for any other tools
                return super()._execute_tool(tool, arguments)
                
        except Exception as e:
            logger.error(f"Error executing tool {tool_name}: {str(e)}")
            raise


class VibeCodingMcpServer(BaseMcpServer):
    """Vibe Coding AI Agent MCP Server that extends the skeleton"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 3050, enable_registry: bool = True,
                 register_with_registry: bool = False, registry_host: str = "127.0.0.1", 
                 registry_port: int = 3031, use_postgres: bool = False, 
                 postgres_host: str = "localhost", postgres_port: int = 5432,
                 postgres_db: str = "mcp_registry", postgres_user: str = "postgres", 
                 postgres_password: str = "", max_concurrent_requests: int = 10):
        # Initialize with streamable-http transport and our custom handlers
        super().__init__(
            transport_type="streamable-http",
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
        
        # Replace the server handlers with our extended version
        self.server_handlers = VibeCodingServerHandlers(
            enable_registry=enable_registry,
            use_postgres=use_postgres,
            postgres_config=getattr(self, 'postgres_config', {})
        )
        
        # Re-register handlers with our custom handlers
        self._register_handlers()
        
        logger.info(f"Vibe Coding AI Agent server initialized on {host}:{port} with registry {'enabled' if enable_registry else 'disabled'}")


def main():
    """Main entry point for the Vibe Coding AI Agent server"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Vibe Coding AI Agent MCP Server')
    parser.add_argument('--transport', choices=['stdio', 'http', 'streamable-http'], 
                       default='streamable-http', help='Transport mechanism to use (default: streamable-http)')
    parser.add_argument('--host', default='0.0.0.0', help='Host for HTTP transport (default: 0.0.0.0)')
    parser.add_argument('--port', type=int, default=3050, help='Port for HTTP transport (default: 3050)')
    parser.add_argument('--enable-registry', action='store_true', default=True, help='Enable registry functionality (default: True)')
    parser.add_argument('--disable-registry', action='store_false', dest='enable_registry', help='Disable registry functionality')
    parser.add_argument('--register-with-registry', action='store_true', help='Register this server with a registry server (requires --registry-host and --registry-port)')
    parser.add_argument('--registry-host', default='127.0.0.1', help='Registry server host to register with (default: 127.0.0.1)')
    parser.add_argument('--registry-port', type=int, default=3031, help='Registry server port to register with (default: 3031)')
    parser.add_argument('--use-postgres', action='store_true', help='Use PostgreSQL for registry storage instead of SQLite (optional)')
    parser.add_argument('--postgres-host', default='localhost', help='PostgreSQL host (default: localhost)')
    parser.add_argument('--postgres-port', type=int, default=5432, help='PostgreSQL port (default: 5432)')
    parser.add_argument('--postgres-db', default='mcp_registry', help='PostgreSQL database name (default: mcp_registry)')
    parser.add_argument('--postgres-user', default='postgres', help='PostgreSQL username (default: postgres)')
    parser.add_argument('--postgres-password', default='', help='PostgreSQL password (default: empty)')
    parser.add_argument('--max-concurrent-requests', type=int, default=10, help='Maximum number of concurrent requests (default: 10)')

    args = parser.parse_args()
    
    # Create and start the server
    server = VibeCodingMcpServer(
        host=args.host,
        port=args.port,
        enable_registry=args.enable_registry,
        register_with_registry=args.register_with_registry,
        registry_host=args.registry_host,
        registry_port=args.registry_port,
        use_postgres=args.use_postgres,
        postgres_host=args.postgres_host,
        postgres_port=args.postgres_port,
        postgres_db=args.postgres_db,
        postgres_user=args.postgres_user,
        postgres_password=args.postgres_password,
        max_concurrent_requests=args.max_concurrent_requests
    )
    
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
        server.stop()