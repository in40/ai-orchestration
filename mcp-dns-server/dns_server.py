"""
DNS Resolving MCP Server Implementation
Implements DNS resolution functionality as an MCP server
"""
import socket
import dns.resolver  # type: ignore
import dns.reversename  # type: ignore
from typing import Dict, Any, List
from mcp_server.server import McpServer
from mcp_server.handlers.server_handlers import McpServerHandlers


class DnsResolvingMcpServer(McpServer):
    """MCP Server specialized for DNS resolution operations"""

    def __init__(self, transport_type="stdio", host="127.0.0.1", port=3030, enable_registry=False,
                 register_with_registry=False, registry_host="127.0.0.1", registry_port=3031,
                 use_postgres=False, postgres_host="localhost", postgres_port=5432,
                 postgres_db="mcp_registry", postgres_user="postgres", postgres_password=""):
        # Initialize the parent class with a temporary handler, then replace
        super().__init__(
            transport_type=transport_type, host=host, port=port, enable_registry=enable_registry,
            register_with_registry=register_with_registry, registry_host=registry_host, 
            registry_port=registry_port, use_postgres=use_postgres, postgres_host=postgres_host,
            postgres_port=postgres_port, postgres_db=postgres_db, postgres_user=postgres_user,
            postgres_password=postgres_password
        )
        
        # Create custom DNS server handlers
        dns_handlers = DnsServerHandlers(
            enable_registry=enable_registry,
            use_postgres=use_postgres,
            postgres_config={
                "host": postgres_host,
                "port": postgres_port,
                "database": postgres_db,
                "user": postgres_user,
                "password": postgres_password
            } if use_postgres else {}
        )
        
        # Replace the server handlers with our DNS-specific ones
        self.server_handlers = dns_handlers
        
        # Re-register all handlers with the new DNS handlers
        self._register_handlers()


class DnsServerHandlers(McpServerHandlers):
    """Custom server handlers for DNS resolution functionality"""

    def __init__(self, enable_registry=False, use_postgres=False, postgres_config=None):
        super().__init__(enable_registry=enable_registry, use_postgres=use_postgres, postgres_config=postgres_config)

        # Clear default example tools and replace with DNS-specific tools
        self.tools = [
            {
                "name": "dns_resolve",
                "description": "Resolve DNS records for a given domain name",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "Domain name to resolve"
                        },
                        "record_type": {
                            "type": "string",
                            "description": "DNS record type (A, AAAA, CNAME, MX, NS, TXT, etc.)",
                            "default": "A"
                        }
                    },
                    "required": ["domain"]
                }
            },
            {
                "name": "dns_reverse_lookup",
                "description": "Perform reverse DNS lookup for an IP address",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "ip_address": {
                            "type": "string",
                            "description": "IP address to perform reverse lookup on"
                        }
                    },
                    "required": ["ip_address"]
                }
            },
            {
                "name": "dns_check_domain_availability",
                "description": "Check if a domain is available by attempting to resolve it",
                "inputSchema": {
                    "type": "object",
                    "properties": {
                        "domain": {
                            "type": "string",
                            "description": "Domain name to check"
                        }
                    },
                    "required": ["domain"]
                }
            }
        ]

        # Add DNS-related resources
        self.resources = [
            {
                "uri": "dns://resolver/configuration",
                "name": "DNS Resolver Configuration",
                "description": "Current DNS resolver configuration and settings"
            }
        ]

        # Add DNS-related prompts
        self.prompts = [
            {
                "name": "dns_resolution_summary",
                "description": "Template for summarizing DNS resolution results",
                "arguments": [
                    {
                        "name": "domain",
                        "type": "string",
                        "description": "Domain that was resolved"
                    },
                    {
                        "name": "results",
                        "type": "string",
                        "description": "Resolution results"
                    }
                ]
            }
        ]

    def handle_tools_call(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle tools/call request with DNS-specific functionality
        """
        tool_name = params.get('name')
        tool_arguments = params.get('arguments', {})

        # Find the requested tool
        tool = None
        for t in self.tools:
            if t['name'] == tool_name:
                tool = t
                break

        if not tool:
            raise ValueError(f"Tool '{tool_name}' not found")

        # Execute DNS-specific tools
        if tool_name == "dns_resolve":
            return self._handle_dns_resolve(tool_arguments)
        elif tool_name == "dns_reverse_lookup":
            return self._handle_dns_reverse_lookup(tool_arguments)
        elif tool_name == "dns_check_domain_availability":
            return self._handle_dns_check_domain_availability(tool_arguments)
        else:
            # For other tools, use parent implementation
            return super().handle_tools_call(params, request_id)

    def _handle_dns_resolve(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle DNS resolution request"""
        domain = arguments.get('domain')
        record_type = arguments.get('record_type', 'A')

        try:
            # Use dnspython to resolve the domain
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(domain, record_type)
            
            results = []
            for rdata in answers:
                results.append(str(rdata))
                
            return {
                "output": {
                    "domain": domain,
                    "record_type": record_type,
                    "results": results,
                    "count": len(results)
                },
                "isError": False
            }
        except dns.resolver.NXDOMAIN:
            return {
                "output": {
                    "domain": domain,
                    "record_type": record_type,
                    "error": "Domain does not exist",
                    "results": []
                },
                "isError": False  # Not an error in the tool execution, just no records
            }
        except dns.resolver.NoAnswer:
            return {
                "output": {
                    "domain": domain,
                    "record_type": record_type,
                    "error": f"No {record_type} records found for domain",
                    "results": []
                },
                "isError": False  # Not an error in the tool execution, just no records
            }
        except Exception as e:
            return {
                "output": {
                    "domain": domain,
                    "record_type": record_type,
                    "error": str(e),
                    "results": []
                },
                "isError": True
            }

    def _handle_dns_reverse_lookup(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Handle reverse DNS lookup"""
        ip_address = arguments.get('ip_address')

        try:
            # Use dnspython for reverse lookup
            reversename = dns.reversename.from_address(ip_address)
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(reversename, "PTR")
            
            results = []
            for rdata in answers:
                results.append(str(rdata))
                
            return {
                "output": {
                    "ip_address": ip_address,
                    "results": results,
                    "count": len(results)
                },
                "isError": False
            }
        except dns.resolver.NXDOMAIN:
            return {
                "output": {
                    "ip_address": ip_address,
                    "error": "No PTR record found for IP address",
                    "results": []
                },
                "isError": False  # Not an error in the tool execution, just no records
            }
        except Exception as e:
            return {
                "output": {
                    "ip_address": ip_address,
                    "error": str(e),
                    "results": []
                },
                "isError": True
            }

    def _handle_dns_check_domain_availability(self, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Check if a domain is available by attempting to resolve it"""
        domain = arguments.get('domain')

        try:
            # Try to resolve the domain with A record
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(domain, "A")
            
            # If we get answers, the domain exists
            results = []
            for rdata in answers:
                results.append(str(rdata))
                
            return {
                "output": {
                    "domain": domain,
                    "available": False,
                    "reason": "Domain resolves to IP addresses",
                    "results": results
                },
                "isError": False
            }
        except dns.resolver.NXDOMAIN:
            # Domain does not exist, so it's available
            return {
                "output": {
                    "domain": domain,
                    "available": True,
                    "reason": "Domain does not exist"
                },
                "isError": False
            }
        except Exception as e:
            return {
                "output": {
                    "domain": domain,
                    "available": None,  # Unknown due to error
                    "reason": f"Error checking domain: {str(e)}"
                },
                "isError": True
            }

    def handle_resources_read(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle resources/read request with DNS-specific resources
        """
        uri = params.get('uri')

        if uri == "dns://resolver/configuration":
            # Return DNS resolver configuration
            import dns.version
            
            content = {
                "uri": uri,
                "contents": [
                    {
                        "type": "text",
                        "text": f"""DNS Resolver Configuration:
Library Version: {dns.version.version}
Default Nameservers: {dns.resolver.get_default_resolver().nameservers}
Search domains: {dns.resolver.get_default_resolver().search}
Timeout: {dns.resolver.get_default_resolver().timeout}s
Lifetime: {dns.resolver.get_default_resolver().lifetime}s"""
                    }
                ],
                "version": dns.version.version
            }
            return content
        else:
            # For other resources, use parent implementation
            return super().handle_resources_read(params, request_id)

    def handle_ping(self, params: Dict[str, Any], request_id: str) -> Dict[str, Any]:
        """
        Handle ping request for health check.
        """
        import datetime
        return {
            "timestamp": datetime.datetime.now().isoformat(),
            "status": "healthy",
            "service": "DNS Resolving MCP Server",
            "version": "1.0.0"
        }

    def register_handlers(self, rpc_handler):
        """Register all standard handlers with the RPC handler"""
        # Server initialization
        rpc_handler.register_request_handler('initialize', self.handle_initialize)
        rpc_handler.register_request_handler('shutdown', self.handle_shutdown)
        rpc_handler.register_request_handler('ping', self.handle_ping)  # Health check endpoint

        # Tools
        rpc_handler.register_request_handler('tools/list', self.handle_tools_list)
        rpc_handler.register_request_handler('tools/call', self.handle_tools_call)

        # Resources
        rpc_handler.register_request_handler('resources/list', self.handle_resources_list)
        rpc_handler.register_request_handler('resources/read', self.handle_resources_read)

        # Prompts
        rpc_handler.register_request_handler('prompts/list', self.handle_prompts_list)
        rpc_handler.register_request_handler('prompts/get', self.handle_prompts_get)

        # Registry handlers - available when registry is enabled
        if hasattr(self, 'enable_registry') and self.enable_registry:
            rpc_handler.register_request_handler('registry/register', self.handle_register_service)
            rpc_handler.register_request_handler('registry/list', self.handle_list_services)
            rpc_handler.register_request_handler('registry/unregister', self.handle_unregister_service)