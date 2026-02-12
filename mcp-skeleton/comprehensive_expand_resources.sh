#!/bin/bash

# Comprehensive Resource Expansion from MCP Services
# This script allows expanding resources to see their details and content using a single SSE connection

set -e  # Exit on any error

# Configuration
SERVICE_ENDPOINT="${1:-http://localhost:3050}"
ACTION="${2:-list}"
PARAMETER="$3"

echo "🔍 COMPREHENSIVE RESOURCE EXPANSION FROM MCP SERVICE"
echo "=================================================="
echo "Service Endpoint: $SERVICE_ENDPOINT"
echo "Action: $ACTION"
if [[ -n "$PARAMETER" ]]; then
    echo "Parameter: $PARAMETER"
fi
echo ""

# Check if Python script exists
SCRIPT_FILE="comprehensive_expand_resources.py"
if [[ ! -f "$SCRIPT_FILE" ]]; then
    echo "❌ Comprehensive resource expansion script not found!"
    echo "   Please ensure comprehensive_expand_resources.py is in the same directory"
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
        if [[ -z "$PARAMETER" ]]; then
            echo "❌ No resource URI specified!"
            echo "   Usage: $0 <service_endpoint> expand <resource_uri>"
            exit 1
        fi
        echo "🔍 Expanding resource: $PARAMETER"
        python "$SCRIPT_FILE" --service-endpoint "$SERVICE_ENDPOINT" --resource "$PARAMETER"
        ;;
    "expand-all"|"read-all")
        if [[ -z "$PARAMETER" ]]; then
            echo "❌ No resource URIs specified!"
            echo "   Usage: $0 <service_endpoint> expand-all 'uri1,uri2,uri3'"
            exit 1
        fi
        
        # Split comma-separated resource URIs
        IFS=',' read -ra URIS <<< "$PARAMETER"
        
        echo "🔍 Expanding multiple resources..."
        for uri in "${URIS[@]}"; do
            uri=$(echo "$uri" | xargs)  # Trim whitespace
            echo "   - $uri"
        done
        
        # Pass each URI as a separate --resource argument
        cmd="python \"$SCRIPT_FILE\" --service-endpoint \"$SERVICE_ENDPOINT\""
        for uri in "${URIS[@]}"; do
            uri=$(echo "$uri" | xargs)  # Trim whitespace
            cmd="$cmd --resource \"$uri\""
        done
        
        eval "$cmd"
        ;;
    "expand-all-from-service"|"read-all-from-service")
        echo "🔍 Expanding all resources available from the service..."
        python "$SCRIPT_FILE" --service-endpoint "$SERVICE_ENDPOINT" --expand-all-from-service
        ;;
    *)
        echo "❌ Unknown action: $ACTION"
        echo "   Usage: $0 <service_endpoint> <action> [parameter]"
        echo "   Actions: list, expand, read, expand-all, read-all, expand-all-from-service"
        echo "   Examples:"
        echo "     $0 http://localhost:3030 list"
        echo "     $0 http://localhost:3030 expand 'coding-agent://capabilities'"
        echo "     $0 http://localhost:3030 expand-all 'coding-agent://capabilities,coding-agent://status,coding-agent://health'"
        echo "     $0 http://localhost:3030 expand-all-from-service"
        exit 1
        ;;
esac

echo ""
echo "🎯 COMPREHENSIVE RESOURCE EXPANSION COMPLETED"
echo "   - Used proper HTTP/SSE protocol via Python client"
echo "   - Opened SSE connection first, then sent requests"
echo "   - Received responses via SSE as per MCP specification"
echo "   - Retrieved detailed resource information"
echo "   - Efficiently handled multiple resources in single SSE connection"