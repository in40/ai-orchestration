#!/bin/bash
# Setup script for AI Coding Agent
# This script helps configure the AI Coding Agent to connect to your LLM service

echo "🔧 AI Coding Agent Setup"
echo "========================"

# Detect if there's a known LLM service running
echo "🔍 Detecting available LLM services..."

# Check for common LLM service ports
SERVICES_DETECTED=()

if nc -z localhost 11434 2>/dev/null; then
    SERVICES_DETECTED+=("Ollama on port 11434")
    DEFAULT_ENDPOINT="http://localhost:11434/v1"
fi

if nc -z localhost 8000 2>/dev/null; then
    SERVICES_DETECTED+=("vLLM/OpenAI compatible on port 8000")
    DEFAULT_ENDPOINT="http://localhost:8000/v1"
fi

if nc -z localhost 1234 2>/dev/null; then
    SERVICES_DETECTED+=("LM Studio compatible on port 1234")
    DEFAULT_ENDPOINT="http://asus-tus:1234/v1"
fi

if [ ${#SERVICES_DETECTED[@]} -gt 0 ]; then
    echo "✅ Detected services:"
    for service in "${SERVICES_DETECTED[@]}"; do
        echo "   - $service"
    done
    echo ""
    echo "🎯 Recommended endpoint: $DEFAULT_ENDPOINT"
else
    echo "❌ No common LLM services detected"
    echo "💡 Common LLM service endpoints:"
    echo "   - Ollama: http://localhost:11434/v1"
    echo "   - vLLM/LiteLLM: http://localhost:8000/v1"
    echo "   - LM Studio: http://localhost:1234/v1"
    echo "   - Custom: http://your-server:port/v1"
    echo ""
fi

# Ask user for the LLM endpoint
echo "📋 Please enter your LLM service endpoint:"
echo "   (Press Enter to use default: $DEFAULT_ENDPOINT)"
read -p "LLM Endpoint: " INPUT_ENDPOINT

if [ -z "$INPUT_ENDPOINT" ]; then
    INPUT_ENDPOINT="$DEFAULT_ENDPOINT"
fi

# Validate the endpoint format
if [[ ! "$INPUT_ENDPOINT" =~ ^https?://[a-zA-Z0-9.-]+:[0-9]+(/.*)?$ ]]; then
    echo "❌ Invalid URL format: $INPUT_ENDPOINT"
    echo "✅ Correct format: http://hostname:port/path"
    exit 1
fi

echo "✅ Using endpoint: $INPUT_ENDPOINT"

# Ask for API key if needed
echo ""
echo "🔐 Enter API key if required by your LLM service (press Enter to skip):"
read -s -p "API Key: " API_KEY
echo ""  # New line after hidden input

if [ -z "$API_KEY" ]; then
    API_KEY="not-needed-for-local-llm"
    echo "ℹ️  Using default API key (for local services)"
else
    echo "✅ API key configured"
fi

# Ask for model name
echo ""
echo "🏷️  Enter the model name to use (press Enter for default: qwen3-4b):"
read -p "Model Name: " MODEL_NAME

if [ -z "$MODEL_NAME" ]; then
    MODEL_NAME="qwen3-4b"
fi

echo "✅ Using model: $MODEL_NAME"

# Create/update the .env file
cat > .env << EOF
# AI Coding Agent Environment Variables
LLM_BASE_URL=$INPUT_ENDPOINT
LLM_API_KEY=$API_KEY
LLM_MODEL_NAME=$MODEL_NAME
EOF

echo ""
echo "💾 Configuration saved to .env file"
echo ""
echo "📋 To start the AI Coding Agent with your configuration:"
echo "   source .env && ./start_ai_coding_agent.sh"
echo ""
echo "📋 Or to run with the configuration directly:"
echo "   LLM_BASE_URL=$INPUT_ENDPOINT LLM_API_KEY=$API_KEY LLM_MODEL_NAME=$MODEL_NAME ./start_ai_coding_agent.sh"
echo ""
echo "🚀 Your AI Coding Agent is ready to connect to your LLM service!"