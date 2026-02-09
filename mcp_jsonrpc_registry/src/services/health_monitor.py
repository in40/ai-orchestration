"""Health monitoring service for registered MCP servers."""

import asyncio
import aiohttp
from typing import List
from datetime import datetime
import logging

from src.services.database import DatabaseService
from src.models.server import RegisteredServer, UpdateServerStatusRequest
from config.settings import settings


class HealthMonitorService:
    def __init__(self, db_service: DatabaseService):
        self.db_service = db_service
        self.logger = logging.getLogger(__name__)

    async def check_server_health(self, server: RegisteredServer) -> str:
        """Check the health of a registered server."""
        try:
            # For HTTP endpoints, try to make a basic request
            if server.endpoint.startswith(('http://', 'https://')):
                async with aiohttp.ClientSession() as session:
                    # Try to connect to the server's health endpoint or just the base URL
                    async with session.get(f"{server.endpoint}/health", timeout=10) as response:
                        if response.status == 200:
                            return "healthy"
                        else:
                            return "unhealthy"
            # For stdio endpoints, we can't easily check health externally
            elif server.endpoint == "stdio":
                # For stdio, we assume it's healthy if it's registered
                # In a real implementation, we'd need to track the actual process
                return "healthy"
            else:
                # For other transport types, implement specific health checks
                self.logger.warning(f"Unknown endpoint type for server {server.id}: {server.endpoint}")
                return "unknown"
        except Exception as e:
            self.logger.error(f"Health check failed for server {server.id}: {str(e)}")
            return "unhealthy"

    async def update_all_server_health(self):
        """Update health status for all registered servers."""
        servers = self.db_service.get_all_servers()
        update_tasks = []

        for server in servers:
            task = self._update_single_server_health(server)
            update_tasks.append(task)

        await asyncio.gather(*update_tasks, return_exceptions=True)

    async def _update_single_server_health(self, server: RegisteredServer):
        """Update health status for a single server."""
        health_status = await self.check_server_health(server)
        
        status_request = UpdateServerStatusRequest(health_status=health_status)
        success = self.db_service.update_server_status(server.id, status_request)
        
        if success:
            self.logger.info(f"Updated health status for server {server.id} to {health_status}")
        else:
            self.logger.error(f"Failed to update health status for server {server.id}")

    async def start_periodic_health_checks(self, interval_seconds: int = None):
        """Start periodic health checks for all servers."""
        if interval_seconds is None:
            interval_seconds = settings.health_check_interval
            
        self.logger.info(f"Starting periodic health checks every {interval_seconds} seconds")
        
        while True:
            try:
                await self.update_all_server_health()
            except Exception as e:
                self.logger.error(f"Error during periodic health checks: {str(e)}")
            
            await asyncio.sleep(interval_seconds)