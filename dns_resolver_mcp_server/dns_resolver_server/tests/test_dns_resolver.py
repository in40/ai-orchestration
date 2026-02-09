"""
Tests for the DNS Resolver MCP Server

This module contains unit tests for the DNS resolver functionality.
"""
import asyncio
import pytest
from unittest.mock import patch, MagicMock
import dns.resolver
import dns.exception

from dns_resolver_server.src.server import DNSResolverMCPServer


@pytest.fixture
def dns_server():
    """Create a DNS resolver server instance for testing."""
    server = DNSResolverMCPServer(transport="stdio")
    return server


@pytest.mark.asyncio
async def test_dns_resolver_initialization(dns_server):
    """Test that the DNS resolver server is properly initialized."""
    assert dns_server.name == "dns-resolver-mcp-server"
    assert dns_server.description == "An MCP server that provides DNS resolution services"
    assert "dns" in dns_server.tags
    assert "resolver" in dns_server.tags
    assert dns_server.capabilities["tools"] is True


@pytest.mark.asyncio
async def test_perform_forward_lookup_a_record(dns_server):
    """Test forward DNS lookup for A records."""
    # Mock the DNS resolver to avoid actual network calls in tests
    with patch('dns.resolver.Resolver.resolve') as mock_resolve:
        # Create a mock answer
        mock_answer = MagicMock()
        mock_answer.__str__ = MagicMock(return_value="93.184.216.34")
        mock_resolve.return_value = [mock_answer]
        
        result = await dns_server._perform_forward_lookup("example.com", "A")
        
        assert "93.184.216.34" in result
        assert "example.com" in result
        mock_resolve.assert_called_once_with("example.com", "A")


@pytest.mark.asyncio
async def test_perform_forward_lookup_nxdomain(dns_server):
    """Test forward DNS lookup when domain doesn't exist."""
    with patch('dns.resolver.Resolver.resolve') as mock_resolve:
        mock_resolve.side_effect = dns.resolver.NXDOMAIN()
        
        result = await dns_server._perform_forward_lookup("nonexistent-domain-12345.com", "A")
        
        assert "does not exist" in result


@pytest.mark.asyncio
async def test_perform_reverse_lookup(dns_server):
    """Test reverse DNS lookup."""
    with patch('dns.reversename.from_address') as mock_from_addr, \
         patch('dns.resolver.Resolver.resolve') as mock_resolve:
        
        # Mock the reverse name conversion
        mock_from_addr.return_value = "34.216.184.93.in-addr.arpa."
        
        # Create a mock answer for the reverse lookup
        mock_answer = MagicMock()
        mock_answer.target = "example.com"
        mock_answer.__str__ = MagicMock(return_value="example.com")
        mock_resolve.return_value = [mock_answer]
        
        result = await dns_server._perform_reverse_lookup("93.184.216.34")
        
        assert "93.184.216.34" in result
        assert "example.com" in result
        mock_resolve.assert_called_once()


@pytest.mark.asyncio
async def test_perform_reverse_lookup_nxdomain(dns_server):
    """Test reverse DNS lookup when no hostname is found."""
    with patch('dns.reversename.from_address') as mock_from_addr, \
         patch('dns.resolver.Resolver.resolve') as mock_resolve:
        
        mock_from_addr.return_value = "34.216.184.93.in-addr.arpa."
        mock_resolve.side_effect = dns.resolver.NXDOMAIN()
        
        result = await dns_server._perform_reverse_lookup("93.184.216.34")
        
        assert "No hostname found" in result


@pytest.mark.asyncio
async def test_handle_resolve_dns_hostname(dns_server):
    """Test handling the resolve_dns tool call with hostname."""
    with patch.object(dns_server, '_perform_forward_lookup', 
                      return_value="DNS resolution for example.com (A): 93.184.216.34") as mock_forward:
        
        arguments = {"hostname": "example.com", "record_type": "A"}
        result = await dns_server._handle_resolve_dns(arguments)
        
        assert result.content[0].text == "DNS resolution for example.com (A): 93.184.216.34"
        mock_forward.assert_called_once_with("example.com", "A")


@pytest.mark.asyncio
async def test_handle_resolve_dns_ip_address(dns_server):
    """Test handling the resolve_dns tool call with IP address."""
    with patch.object(dns_server, '_perform_reverse_lookup', 
                      return_value="Reverse DNS lookup for 93.184.216.34: example.com") as mock_reverse:
        
        arguments = {"ip_address": "93.184.216.34"}
        result = await dns_server._handle_resolve_dns(arguments)
        
        assert result.content[0].text == "Reverse DNS lookup for 93.184.216.34: example.com"
        mock_reverse.assert_called_once_with("93.184.216.34")


@pytest.mark.asyncio
async def test_handle_check_domain_availability_taken(dns_server):
    """Test checking domain availability when domain is taken."""
    with patch('dns.resolver.Resolver.resolve') as mock_resolve:
        # Mock a successful resolution (domain exists)
        mock_answer = MagicMock()
        mock_answer.__str__ = MagicMock(return_value="93.184.216.34")
        mock_resolve.return_value = [mock_answer]
        
        arguments = {"domain": "example.com"}
        result = await dns_server._handle_check_domain_availability(arguments)
        
        assert "is taken" in result.content[0].text
        assert "example.com" in result.content[0].text


@pytest.mark.asyncio
async def test_handle_check_domain_availability_available(dns_server):
    """Test checking domain availability when domain is available."""
    with patch('dns.resolver.Resolver.resolve') as mock_resolve:
        mock_resolve.side_effect = dns.resolver.NXDOMAIN()
        
        arguments = {"domain": "nonexistent-domain-12345.com"}
        result = await dns_server._handle_check_domain_availability(arguments)
        
        assert "appears to be available" in result.content[0].text


@pytest.mark.asyncio
async def test_handle_check_domain_availability_no_args(dns_server):
    """Test checking domain availability with no domain argument."""
    arguments = {}  # No domain provided
    result = await dns_server._handle_check_domain_availability(arguments)
    
    assert "Domain parameter is required" in result.content[0].text
    assert result.isError is True


@pytest.mark.asyncio
async def test_health_check_passes(dns_server):
    """Test that health check passes when DNS resolution works."""
    with patch('dns.resolver.Resolver.resolve') as mock_resolve:
        # Mock a successful resolution
        mock_answer = MagicMock()
        mock_answer.__str__ = MagicMock(return_value="8.8.8.8")
        mock_resolve.return_value = [mock_answer]
        
        # Call the health check method
        await dns_server._perform_health_check()
        
        # Check that the health status was updated to healthy
        assert dns_server.health_status == "healthy"


@pytest.mark.asyncio
async def test_health_check_fails(dns_server):
    """Test that health check fails when DNS resolution doesn't work."""
    with patch('dns.resolver.Resolver.resolve') as mock_resolve:
        mock_resolve.side_effect = Exception("Network error")
        
        # Call the health check method
        await dns_server._perform_health_check()
        
        # Check that the health status was updated to unhealthy
        assert dns_server.health_status == "unhealthy"