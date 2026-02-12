#!/bin/bash

# Simple startup script for the Vibe Coding MCP server with default settings
# Usage: ./start_mcp_default.sh

echo "Starting Vibe Coding MCP Server with default settings..."

# Set PostgreSQL password - uncomment and update the line below with your actual password
export POSTGRES_PASSWORD="your_actual_password_here"
export PGPASSWORD="your_actual_password_here"

# Start with Streamable HTTP transport on port 3060 with PostgreSQL enabled for persistent task storage
export POSTGRES_PASSWORD
export PGPASSWORD
python -m mcp_std_server.server --transport streamable-http --port 3060 --enable-registry --register-with-registry --use-postgres