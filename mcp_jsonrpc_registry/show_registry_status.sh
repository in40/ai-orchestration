#!/bin/bash

# Script to show the status of the MCP Server Registry
# Displays registered servers, identifies lost servers, and shows connection info

set -e  # Exit on any error

# Load environment variables from .env file if it exists
ENV_FILE=".env"
if [ -f "$ENV_FILE" ]; then
    echo "Loading environment variables from $ENV_FILE..."
    export $(grep -v '^#' "$ENV_FILE" | xargs)
fi

# Set default values if environment variables are not set
DATABASE_URL="${DATABASE_URL:-postgresql://mcp_user:mcp_password@localhost/mcp_registry}"
HTTP_HOST="${HTTP_HOST:-0.0.0.0}"
HTTP_PORT="${HTTP_PORT:-8080}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  MCP Server Registry Status  ${NC}"
echo -e "${BLUE}================================${NC}"
echo

# Check if psql is available
if ! command -v psql &> /dev/null; then
    echo -e "${RED}Error: psql is not installed or not in PATH${NC}" >&2
    exit 1
fi

# Extract database connection details from DATABASE_URL
DB_USER=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/\([^:]*\):.*/\1/p')
DB_PASS=$(echo "$DATABASE_URL" | sed -n 's/.*:\/\/[^:]*:\([^@]*\)@.*/\1/p')
DB_HOST=$(echo "$DATABASE_URL" | sed -n 's/.*@//; s|/.*||p')
DB_NAME=$(echo "$DATABASE_URL" | sed -n 's/.*\/\([^?]*\).*/\1/p')

# Check if we can connect to the database
echo -e "${BLUE}Checking database connectivity...${NC}"
if PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -c "SELECT 1;" > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Database connection successful${NC}"
else
    echo -e "${RED}✗ Database connection failed${NC}"
    echo -e "${RED}  Please check your DATABASE_URL in the .env file${NC}"
    exit 1
fi
echo

# Query registered servers from the database
echo -e "${BLUE}Querying registered servers...${NC}"
SERVERS_QUERY="SELECT id, name, endpoint, health_status, last_seen FROM registered_servers ORDER BY registered_at DESC;"

# Execute the query and process results
SERVERS_OUTPUT=$(PGPASSWORD="$DB_PASS" psql -h "$DB_HOST" -U "$DB_USER" -d "$DB_NAME" -t -A -F $'\t' -c "$SERVERS_QUERY" 2>/dev/null || echo "")

if [ -z "$SERVERS_OUTPUT" ] || [ "$SERVERS_OUTPUT" = "" ]; then
    echo -e "${YELLOW}No registered servers found.${NC}"
    echo
else
    # Parse and display server information
    echo -e "${GREEN}Registered Servers:${NC}"
    echo "----------------------------------------"
    
    # Track lost servers
    declare -a lost_servers=()
    
    while IFS=$'\t' read -r id name endpoint health_status last_seen; do
        # Skip empty lines
        if [ -z "$id" ]; then
            continue
        fi
        
        # Format the output based on health status
        case $health_status in
            "healthy")
                status_color="$GREEN"
                status_icon="✓"
                ;;
            "unhealthy")
                status_color="$RED"
                status_icon="✗"
                lost_servers+=("$name ($id)")
                ;;
            "unknown")
                status_color="$YELLOW"
                status_icon="?"
                ;;
            *)
                status_color="$YELLOW"
                status_icon="?"
                ;;
        esac
        
        printf "%-30s %-10s %s %s\n" "$name" "$health_status" "$status_icon" "$endpoint"
        
    done <<< "$SERVERS_OUTPUT"
    
    echo
    
    # Display lost servers if any
    if [ ${#lost_servers[@]} -gt 0 ]; then
        echo -e "${RED}Lost/Unhealthy Servers:${NC}"
        echo "----------------------------------------"
        for server in "${lost_servers[@]}"; do
            echo -e "${RED}✗ $server${NC}"
        done
        echo
    fi
fi

# Show Streamable HTTP Transport connection string
echo -e "${BLUE}Streamable HTTP Transport Connection Info:${NC}"
echo "----------------------------------------"

# Determine the appropriate host for client connections
if [ "$HTTP_HOST" = "0.0.0.0" ] || [ "$HTTP_HOST" = "::" ]; then
    # When server binds to all interfaces, suggest common addresses for clients
    echo -e "${GREEN}Connection String: http://localhost:$HTTP_PORT${NC}"
    echo -e "${GREEN}Alternative Addresses:${NC}"
    echo -e "  http://127.0.0.1:$HTTP_PORT"
    # Also try to get the actual machine IP
    LOCAL_IP=$(hostname -I | awk '{print $1}')
    if [ -n "$LOCAL_IP" ]; then
        echo -e "  http://$LOCAL_IP:$HTTP_PORT"
    fi
    echo -e "${YELLOW}Note: Server is bound to all interfaces ($HTTP_HOST)${NC}"
else
    # If the host is not 0.0.0.0, use it directly
    echo -e "${GREEN}Connection String: http://$HTTP_HOST:$HTTP_PORT${NC}"
fi

echo -e "${GREEN}Transport Type: streamable-http${NC}"
echo -e "${GREEN}Port: $HTTP_PORT${NC}"
echo

# Show registry server status (check if it's running)
echo -e "${BLUE}Registry Server Process Status:${NC}"
echo "----------------------------------------"
REGISTRY_PID=$(pgrep -f "python.*registry.main" || echo "")
if [ -n "$REGISTRY_PID" ]; then
    echo -e "${GREEN}✓ Registry server is running (PID: $REGISTRY_PID)${NC}"
    # Get more details about the process
    REGISTRY_CMD=$(ps -p "$REGISTRY_PID" -o args=)
    echo -e "  Command: $REGISTRY_CMD"
else
    echo -e "${YELLOW}⚠ Registry server is not running${NC}"
fi
echo

# Summary
TOTAL_SERVERS=$(echo "$SERVERS_OUTPUT" | wc -l)
if [ "$TOTAL_SERVERS" -gt 0 ]; then
    # Subtract 1 for the potential empty line at the end
    TOTAL_SERVERS=$((TOTAL_SERVERS - 1))
    if [ $TOTAL_SERVERS -lt 0 ]; then
        TOTAL_SERVERS=0
    fi
else
    TOTAL_SERVERS=0
fi

LOST_COUNT=${#lost_servers[@]}

echo -e "${BLUE}Summary:${NC}"
echo "----------------------------------------"
echo -e "Total Registered Servers: $TOTAL_SERVERS"
echo -e "Healthy Servers: $((TOTAL_SERVERS - LOST_COUNT))"
echo -e "Lost/Unhealthy Servers: $LOST_COUNT"
if [ "$HTTP_HOST" = "0.0.0.0" ] || [ "$HTTP_HOST" = "::" ]; then
    echo -e "HTTP Transport: http://localhost:$HTTP_PORT (use one of the addresses above)"
else
    echo -e "HTTP Transport: http://$HTTP_HOST:$HTTP_PORT"
fi
echo

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}  Status check completed        ${NC}"
echo -e "${BLUE}================================${NC}"