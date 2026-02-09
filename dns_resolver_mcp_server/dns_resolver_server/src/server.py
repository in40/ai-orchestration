"""
DNS Resolver MCP Server Implementation

This module defines a DNS resolver server that extends the BaseMCPServer class
to provide DNS resolution functionality through the Model Context Protocol.
"""
import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from datetime import datetime

import dns.resolver
import dns.reversename
import mcp.types as types
from mcp.server import Server
from mcp import stdio_server
from fastapi import FastAPI
import uvicorn

from .base_server import BaseMCPServer


class DNSResolverMCPServer(BaseMCPServer):
    """
    DNS Resolver MCP Server that extends BaseMCPServer with DNS resolution functionality.
    """

    def __init__(self, transport: str = "stdio", host: str = "0.0.0.0", port: int = 8080):
        super().__init__(transport, host, port)
        
        # Set DNS resolver server specific properties
        self.name = "dns-resolver-mcp-server"
        self.description = "An MCP server that provides DNS resolution services"
        
        # Set capabilities - this server will expose tools for DNS resolution
        self.capabilities = {
            "resources": False,  # We won't expose resources
            "tools": True,       # We will expose DNS resolution tools
            "prompts": False,    # We won't expose prompts
            "roots": False,      # We won't expose roots
            "sampling": False    # We won't expose sampling
        }
        
        # Add relevant tags
        self.tags.extend(["dns", "resolver", "network", "infrastructure"])
        
        # Set metadata
        self.metadata = {
            "category": "network-tools",
            "version": "1.0.0",
            "author": "Qwen Code",
            "purpose": "Provide DNS resolution services through MCP"
        }
        
        # Initialize the server with proper tool definitions
        self._initialize_server_with_tools()

    def _initialize_server_with_tools(self):
        """Initialize the server with DNS resolution tools."""
        # Call parent initialization first
        self._server = Server(self.name)
        
        # Define tools that this server provides
        self._define_tools()
        
        # Setup tool handlers
        self._setup_tool_handlers()

    def _define_tools(self):
        """Define the tools that this server provides."""
        # Define the DNS resolution tool
        dns_resolution_tool = types.Tool(
            name="resolve_dns",
            description="Resolve a hostname to IP address or vice versa",
            inputSchema={
                "type": "object",
                "properties": {
                    "hostname": {
                        "type": "string",
                        "description": "Hostname to resolve to IP address"
                    },
                    "ip_address": {
                        "type": "string", 
                        "description": "IP address to resolve to hostname (reverse lookup)"
                    },
                    "record_type": {
                        "type": "string",
                        "enum": ["A", "AAAA", "CNAME", "MX", "NS", "TXT", "PTR", "SRV", "SOA", "ANY"],
                        "default": "A",
                        "description": "DNS record type to query"
                    }
                },
                "oneOf": [
                    {"required": ["hostname"]},
                    {"required": ["ip_address"]}
                ]
            }
        )
        
        # Define the domain availability check tool
        domain_check_tool = types.Tool(
            name="check_domain_availability",
            description="Check if a domain is available by attempting to resolve it",
            inputSchema={
                "type": "object",
                "properties": {
                    "domain": {
                        "type": "string",
                        "description": "Domain name to check for availability"
                    }
                },
                "required": ["domain"]
            }
        )
        
        # Add tools to the server
        self._server.tool_definitions = [dns_resolution_tool, domain_check_tool]

    def _setup_tool_handlers(self):
        """Setup handlers for the tools."""
        # The actual tool handling will be done in the HTTP transport layer
        # when we override the _start_http method to handle tool calls
        pass

    async def _handle_resolve_dns(self, arguments: Dict[str, Any]) -> types.CallToolResult:
        """Handle the resolve_dns tool call."""
        try:
            hostname = arguments.get("hostname")
            ip_address = arguments.get("ip_address")
            record_type = arguments.get("record_type", "A")
            
            result_text = ""
            
            if hostname:
                # Forward DNS lookup
                result_text = await self._perform_forward_lookup(hostname, record_type)
            elif ip_address:
                # Reverse DNS lookup
                result_text = await self._perform_reverse_lookup(ip_address)
            else:
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text="Either hostname or ip_address must be provided")],
                    isError=True
                )
                
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=result_text)]
            )
            
        except Exception as e:
            self.logger.error(f"Error in DNS resolution: {e}")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"DNS resolution failed: {str(e)}")],
                isError=True
            )

    async def _handle_check_domain_availability(self, arguments: Dict[str, Any]) -> types.CallToolResult:
        """Handle the check_domain_availability tool call."""
        try:
            domain = arguments.get("domain")
            if not domain:
                return types.CallToolResult(
                    content=[types.TextContent(type="text", text="Domain parameter is required")],
                    isError=True
                )
                
            # Try to resolve the domain
            try:
                resolver = dns.resolver.Resolver()
                # Try A record first
                answers = resolver.resolve(domain, "A")
                addresses = [str(answer) for answer in answers]
                
                result_text = f"Domain {domain} is taken. Found A records: {', '.join(addresses)}"
            except dns.resolver.NXDOMAIN:
                result_text = f"Domain {domain} appears to be available (NXDOMAIN - does not exist)"
            except dns.resolver.NoAnswer:
                # Domain exists but no A record, try other record types
                try:
                    resolver = dns.resolver.Resolver()
                    answers = resolver.resolve(domain, "ANY")
                    result_text = f"Domain {domain} exists but has no A record. Found other records."
                except:
                    result_text = f"Domain {domain} appears to be available (NoAnswer)"
            except Exception as e:
                result_text = f"Error checking domain {domain}: {str(e)}"
                
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=result_text)]
            )
            
        except Exception as e:
            self.logger.error(f"Error checking domain availability: {e}")
            return types.CallToolResult(
                content=[types.TextContent(type="text", text=f"Domain availability check failed: {str(e)}")],
                isError=True
            )

    async def _perform_forward_lookup(self, hostname: str, record_type: str = "A") -> str:
        """Perform a forward DNS lookup."""
        try:
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(hostname, record_type)
            
            results = []
            for rdata in answers:
                if record_type in ["A", "AAAA"]:
                    results.append(str(rdata))
                elif record_type == "CNAME":
                    results.append(f"CNAME: {rdata.target}")
                elif record_type == "MX":
                    results.append(f"MX: {rdata.preference} {rdata.exchange}")
                elif record_type == "NS":
                    results.append(f"NS: {rdata.target}")
                elif record_type == "TXT":
                    results.append(f"TXT: {' '.join([s.decode() for s in rdata.strings])}")
                elif record_type == "SRV":
                    results.append(f"SRV: {rdata.priority} {rdata.weight} {rdata.port} {rdata.target}")
                elif record_type == "SOA":
                    results.append(f"SOA: {rdata.mname} {rdata.rname} {rdata.serial}")
                elif record_type == "PTR":
                    results.append(f"PTR: {rdata.target}")
                elif record_type == "ANY":
                    results.append(f"{rdata}")
                    
            if results:
                return f"DNS resolution for {hostname} ({record_type}): {', '.join(results)}"
            else:
                return f"No {record_type} records found for {hostname}"
                
        except dns.resolver.NXDOMAIN:
            return f"Hostname {hostname} does not exist"
        except dns.resolver.NoAnswer:
            return f"No {record_type} records found for {hostname}"
        except dns.resolver.Timeout:
            return f"DNS query for {hostname} timed out"
        except Exception as e:
            return f"Error resolving {hostname}: {str(e)}"

    async def _perform_reverse_lookup(self, ip_address: str) -> str:
        """Perform a reverse DNS lookup."""
        try:
            # Convert IP to reverse format for PTR lookup
            reversename = dns.reversename.from_address(ip_address)
            resolver = dns.resolver.Resolver()
            answers = resolver.resolve(reversename, "PTR")
            
            hostnames = [str(answer.target) for answer in answers]
            return f"Reverse DNS lookup for {ip_address}: {', '.join(hostnames)}"
            
        except dns.resolver.NXDOMAIN:
            return f"No hostname found for IP address {ip_address}"
        except dns.resolver.Timeout:
            return f"Reverse DNS lookup for {ip_address} timed out"
        except Exception as e:
            return f"Error performing reverse lookup for {ip_address}: {str(e)}"

    async def _perform_health_check(self):
        """
        Perform DNS-specific health checks.
        """
        try:
            # Test basic DNS resolution
            resolver = dns.resolver.Resolver()
            # Try to resolve a well-known domain
            answers = resolver.resolve("google.com", "A")
            
            if len(answers) > 0:
                self.update_health_status("healthy")
                self.logger.debug("DNS health check passed")
            else:
                self.update_health_status("unhealthy")
                self.logger.warning("DNS health check failed - no response from google.com")
        except Exception as e:
            self.update_health_status("unhealthy")
            self.logger.error(f"DNS health check failed: {e}")

    async def _start_http(self):
        """Start the server using HTTP transport with DNS-specific tool handling."""
        self.logger.info(f"Starting HTTP server on {self.host}:{self.port}")

        # Create FastAPI app
        app = FastAPI(title=self.name, description=self.description)

        # Add security headers middleware
        from starlette.middleware.base import BaseHTTPMiddleware
        from starlette.responses import Response

        class SecurityHeadersMiddleware(BaseHTTPMiddleware):
            async def dispatch(self, request, call_next):
                response = await call_next(request)
                # Add security headers
                response.headers["X-Content-Type-Options"] = "nosniff"
                response.headers["X-Frame-Options"] = "DENY"
                response.headers["X-XSS-Protection"] = "1; mode=block"
                return response

        app.add_middleware(SecurityHeadersMiddleware)

        # Add health check endpoint as required by the registry
        @app.get("/health")
        async def health_check():
            return {
                "status": self.health_status,
                "timestamp": self.last_seen.isoformat() if self.last_seen else None,
                "server": self.name
            }

        # Add security configuration for production
        import os
        if os.getenv("ENVIRONMENT") == "production":
            # Add HTTPS redirect middleware if needed
            from starlette.responses import RedirectResponse
            @app.middleware("http")
            async def force_https(request, call_next):
                if request.url.scheme != "https" and os.getenv("FORCE_HTTPS", "").lower() == "true":
                    https_url = request.url.replace(scheme="https")
                    return RedirectResponse(url=str(https_url))
                response = await call_next(request)
                return response

        # Add the MCP server routes to the FastAPI app
        # Implement both GET and POST for /rpc endpoint as per OpenRPC spec

        # Import required classes
        from fastapi import Request

        # GET /rpc: Provides information about the MCP server capabilities
        @app.get("/rpc")
        async def get_rpc_info():
            return {
                "server_info": {
                    "name": self.name,
                    "description": self.description,
                    "capabilities": self.capabilities,
                    "endpoint": self._get_endpoint()
                }
            }

        # POST /rpc: Accepts JSON-RPC 2.0 requests via POST method for MCP protocol communication
        @app.post("/rpc")
        async def handle_rpc_post(request: Request):
            from starlette.requests import Request as StarletteRequest

            # Get raw body to process JSON-RPC request
            body_bytes = await request.body()
            try:
                rpc_request = json.loads(body_bytes.decode())

                # Handle different methods
                if rpc_request.get("method") == "rpc.discover":
                    result = await self.handle_discover_method()

                    # Create JSON-RPC response
                    response = {
                        "jsonrpc": "2.0",
                        "result": result,
                        "id": rpc_request.get("id")
                    }
                    return response
                elif rpc_request.get("method") == "tools/call":
                    # Handle tool calls
                    params = rpc_request.get("params", {})
                    tool_name = params.get("name", "")
                    tool_arguments = params.get("arguments", {})
                    
                    if tool_name == "resolve_dns":
                        tool_result = await self._handle_resolve_dns(tool_arguments)
                    elif tool_name == "check_domain_availability":
                        tool_result = await self._handle_check_domain_availability(tool_arguments)
                    else:
                        # Unknown tool
                        tool_result = types.CallToolResult(
                            content=[types.TextContent(type="text", text=f"Unknown tool: {tool_name}")],
                            isError=True
                        )
                    
                    # Create JSON-RPC response for tool call
                    response = {
                        "jsonrpc": "2.0",
                        "result": {
                            "content": [{"type": "text", "text": tool_result.content[0].text}] if not tool_result.isError else [],
                            "isError": tool_result.isError
                        } if hasattr(tool_result, 'content') else {
                            "content": [],
                            "isError": True
                        },
                        "id": rpc_request.get("id")
                    }
                    return response
                else:
                    # For other methods, return method not found error
                    response = {
                        "jsonrpc": "2.0",
                        "error": {
                            "code": -32601,  # Method not found
                            "message": f"Method not implemented: {rpc_request.get('method')}"
                        },
                        "id": rpc_request.get("id")
                    }
                    return response
            except json.JSONDecodeError:
                # Invalid JSON
                response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32700,  # Parse error
                        "message": "Parse error"
                    },
                    "id": None
                }
                return response
            except Exception as e:
                # Internal error
                response = {
                    "jsonrpc": "2.0",
                    "error": {
                        "code": -32603,  # Internal error
                        "message": f"Internal error: {str(e)}"
                    },
                    "id": rpc_request.get("id") if 'rpc_request' in locals() else None
                }
                return response

        # Run the server in a background task
        config = uvicorn.Config(
            app,
            host=self.host,
            port=self.port,
            log_level="info"
        )
        server = uvicorn.Server(config)

        # Run the server in a background task
        self._http_server_task = asyncio.create_task(server.serve())

        # Wait for the server to actually start
        await asyncio.sleep(0.1)