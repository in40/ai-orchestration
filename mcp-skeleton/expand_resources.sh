#!/bin/bash

# Expand Resources from MCP Services
# This script allows expanding resources to see their details and content

set -e  # Exit on any error

# Configuration
SERVICE_ENDPOINT="${1:-http://localhost:3050}"
ACTION="${2:-list}"
RESOURCE_URI="$3"

echo "🔍 EXPANDING RESOURCES FROM MCP SERVICE"
echo "======================================="
echo "Service Endpoint: $SERVICE_ENDPOINT"
echo "Action: $ACTION"
if [[ -n "$RESOURCE_URI" ]]; then
    echo "Resource URI: $RESOURCE_URI"
fi
echo ""

# Check if Python script exists
SCRIPT_FILE="expand_resources.py"
if [[ ! -f "$SCRIPT_FILE" ]]; then
    echo "❌ Resource expansion script not found!"
    echo "   Please ensure expand_resources.py is in the same directory"
    exit 1
fi

# Check if Python is available
if ! command -v python &> /dev/null; then
    echo "❌ Python is not available!"
    exit 1
fi

# Run the Python script based on action
case "$ACTION" in
    "list")
        echo "📋 Listing all available resources from the service..."
        python "$SCRIPT_FILE" --service-endpoint "$SERVICE_ENDPOINT" --list-resources
        ;;
    "expand"|"read")
        if [[ -z "$RESOURCE_URI" ]]; then
            echo "❌ No resource URI specified!"
            echo "   Usage: $0 <service_endpoint> expand <resource_uri>"
            exit 1
        fi
        echo "🔍 Expanding resource: $RESOURCE_URI"
        python "$SCRIPT_FILE" --service-endpoint "$SERVICE_ENDPOINT" --resource "$RESOURCE_URI"
        ;;
    "expand-all"|"read-all")
        if [[ -z "$RESOURCE_URI" ]]; then
            echo "❌ No resource URIs specified!"
            echo "   Usage: $0 <service_endpoint> expand-all 'uri1,uri2,uri3'"
            exit 1
        fi
        
        # Split comma-separated resource URIs
        IFS=',' read -ra URIS <<< "$RESOURCE_URI"
        
        echo "🔍 Expanding multiple resources..."
        for uri in "${URIS[@]}"; do
            uri=$(echo "$uri" | xargs)  # Trim whitespace
            echo "   - $uri"
            python "$SCRIPT_FILE" --service-endpoint "$SERVICE_ENDPOINT" --resource "$uri"
            echo ""
        done
        ;;
    *)
        echo "❌ Unknown action: $ACTION"
        echo "   Usage: $0 <service_endpoint> <action> [resource_uri]"
        echo "   Actions: list, expand, read, expand-all, read-all"
        echo "   Examples:"
        echo "     $0 http://localhost:3030 list"
        echo "     $0 http://localhost:3030 expand 'coding-agent://capabilities'"
        echo "     $0 http://localhost:3030 expand-all 'coding-agent://capabilities,coding-agent://status,coding-agent://health'"
        exit 1
        ;;
esac

echo ""
echo "🎯 RESOURCE EXPANSION COMPLETED"
echo "   - Used proper HTTP/SSE protocol via Python client"
echo "   - Opened SSE connection first, then sent requests"
echo "   - Received responses via SSE as per MCP specification"
echo "   - Retrieved detailed resource information"