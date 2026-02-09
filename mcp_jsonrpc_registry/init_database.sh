#!/bin/bash

# Database initialization script for MCP Server Registry

echo "Initializing PostgreSQL database for MCP Server Registry..."

# Check if virtual environment is active
if [ -z "$VIRTUAL_ENV" ]; then
    echo "Warning: Virtual environment is not active."
    echo "Please activate your virtual environment before running this script."
    echo "Run: source venv/bin/activate"
    exit 1
fi

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Error: .env file not found."
    echo "Please copy .env.example to .env and configure your settings."
    exit 1
fi

# Load environment variables
export $(grep -v '^#' .env | xargs)

# Get database URL from environment or use default
DATABASE_URL=${DATABASE_URL:-"postgresql://mcp_user:mcp_password@localhost/mcp_registry"}

echo "Using database: $DATABASE_URL"

# Test database connection
echo "Testing database connection..."
python -c "
import sys
try:
    from sqlalchemy import create_engine
    engine = create_engine('$DATABASE_URL')
    connection = engine.connect()
    print('✓ Successfully connected to database')
    connection.close()
except Exception as e:
    print(f'✗ Database connection failed: {e}')
    sys.exit(1)
"

if [ $? -ne 0 ]; then
    echo "Database connection test failed. Please check your database configuration."
    exit 1
fi

echo "Database initialization completed successfully!"
echo ""
echo "The database tables will be automatically created when you start the registry server."
echo "To start the registry server, run: ./start_registry.sh"