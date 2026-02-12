#!/bin/bash

# Simulation script for memory operations
# Tests store_memory and retrieve_memory tools

set -e  # Exit on any error

echo "=== Memory Operations Simulation ==="
echo "Testing store_memory and retrieve_memory tools..."

# Test store_memory
echo "1. Testing store_memory to save a development insight..."
STORE_KEY="test_insight_$(date +%s)"
STORE_RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"id\": \"test-store-1\",
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"store_memory\",
      \"arguments\": {
        \"key\": \"$STORE_KEY\",
        \"value\": \"Always validate user inputs to prevent injection attacks\",
        \"category\": \"security_best_practices\",
        \"metadata\": {
          \"timestamp\": \"$(date -Iseconds)\",
          \"importance\": \"high\"
        }
      }
    }
  }")

echo "Store Response:"
echo "$STORE_RESPONSE" | jq '.' || echo "$STORE_RESPONSE"

# Test retrieve_memory with exact key
echo "2. Testing retrieve_memory with exact key..."
RETRIEVE_RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
  -H "Content-Type: application/json" \
  -d "{
    \"jsonrpc\": \"2.0\",
    \"id\": \"test-retrieve-1\",
    \"method\": \"tools/call\",
    \"params\": {
      \"name\": \"retrieve_memory\",
      \"arguments\": {
        \"key\": \"$STORE_KEY\"
      }
    }
  }")

echo "Retrieve by Key Response:"
echo "$RETRIEVE_RESPONSE" | jq '.' || echo "$RETRIEVE_RESPONSE"

# Test retrieve_memory with category filter
echo "3. Testing retrieve_memory with category filter..."
CATEGORY_RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-category-1",
    "method": "tools/call",
    "params": {
      "name": "retrieve_memory",
      "arguments": {
        "category": "security_best_practices",
        "limit": 5
      }
    }
  }')

echo "Retrieve by Category Response:"
echo "$CATEGORY_RESPONSE" | jq '.' || echo "$CATEGORY_RESPONSE"

# Test retrieve_memory with semantic search
echo "4. Testing retrieve_memory with semantic search..."
SEARCH_RESPONSE=$(curl -s -X POST http://localhost:3050/mcp \
  -H "Content-Type: application/json" \
  -d '{
    "jsonrpc": "2.0",
    "id": "test-search-1",
    "method": "tools/call",
    "params": {
      "name": "retrieve_memory",
      "arguments": {
        "query": "input validation",
        "limit": 3
      }
    }
  }')

echo "Semantic Search Response:"
echo "$SEARCH_RESPONSE" | jq '.' || echo "$SEARCH_RESPONSE"

echo "=== Memory Operations Simulation Complete ==="