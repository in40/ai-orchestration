"""Read-only registry adapters for discovering MCP servers."""
import httpx
import urllib.parse
from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod


class ReadOnlyRegistryAdapter(ABC):
    """Abstract base class for read-only registry adapters."""

    @abstractmethod
    async def search_servers(self) -> List[Dict[str, Any]]:
        """Search for available servers (read-only)."""
        pass


class ReadOnlyLocalhostRegistryAdapter(ReadOnlyRegistryAdapter):
    """Read-only adapter for localhost:3031 default registry."""

    def __init__(self, base_url: str = "http://localhost:3031/mcp"):
        self.base_url = base_url

    async def search_servers(self) -> List[Dict[str, Any]]:
        """Return sample server data in read-only mode."""
        # In read-only mode, return sample data instead of making actual HTTP requests
        return [{
            "name": "Sample Local Server",
            "url": self.base_url,
            "description": "Sample server for demonstration (read-only)",
            "adapter_type": "localhost"
        }]


class ReadOnlyGitHubRegistryAdapter(ReadOnlyRegistryAdapter):
    """Read-only adapter for GitHub MCP registry."""

    def __init__(self, base_url: str = "https://registry.modelcontextprotocol.io/v0.1/servers"):
        self.base_url = base_url

    async def search_servers(self) -> List[Dict[str, Any]]:
        """Return sample server data in read-only mode."""
        # In read-only mode, return sample data instead of making actual HTTP requests
        return [{
            "name": "Sample GitHub Server",
            "url": "https://api.github.com/sample-mcp-endpoint",
            "description": "Sample GitHub server for demonstration (read-only)",
            "adapter_type": "github"
        }]


class ReadOnlyNacosRegistryAdapter(ReadOnlyRegistryAdapter):
    """Read-only adapter for Nacos registry."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def search_servers(self) -> List[Dict[str, Any]]:
        """Return sample server data in read-only mode."""
        # In read-only mode, return sample data instead of making actual HTTP requests
        return [{
            "name": "Sample Nacos Server",
            "url": self.base_url,
            "description": "Sample Nacos server for demonstration (read-only)",
            "adapter_type": "nacos"
        }]


class ReadOnlyCustomRegistryAdapter(ReadOnlyRegistryAdapter):
    """Read-only adapter for custom registry URLs."""

    def __init__(self, base_url: str):
        self.base_url = base_url

    async def search_servers(self) -> List[Dict[str, Any]]:
        """Return sample server data in read-only mode."""
        # In read-only mode, return sample data instead of making actual HTTP requests
        return [{
            "name": "Sample Custom Server",
            "url": self.base_url,
            "description": "Sample custom server for demonstration (read-only)",
            "adapter_type": "custom"
        }]


class ReadOnlyRegistryManager:
    """Read-only manager for registry adapters."""

    def __init__(self):
        self.adapters: List[ReadOnlyRegistryAdapter] = []
        # Add the default read-only localhost adapter
        self.add_adapter(ReadOnlyLocalhostRegistryAdapter())

    def add_adapter(self, adapter: ReadOnlyRegistryAdapter):
        """Add a read-only registry adapter."""
        self.adapters.append(adapter)

    def remove_adapter(self, adapter: ReadOnlyRegistryAdapter):
        """Remove a read-only registry adapter."""
        if adapter in self.adapters:
            self.adapters.remove(adapter)

    async def search_all_servers(self) -> List[Dict[str, Any]]:
        """Search all registered read-only adapters for available servers."""
        all_servers = []

        for adapter in self.adapters:
            try:
                servers = await adapter.search_servers()
                all_servers.extend(servers)
            except Exception:
                # Skip adapters that fail
                continue

        return all_servers