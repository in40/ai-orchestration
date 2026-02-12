#!/bin/bash
# AI Coding Agent Client Runner
# Shell script to run the AI Coding Agent Client utility

# Set the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Default values
AGENT_URL=${AGENT_URL:-"http://localhost:3050"}
TIMEOUT=${TIMEOUT:-3600}  # 60 minutes default timeout

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        --agent-url)
            AGENT_URL="$2"
            shift 2
            ;;
        --task)
            TASK="$2"
            shift 2
            ;;
        --context)
            CONTEXT="$2"
            shift 2
            ;;
        --file-path)
            FILE_PATH="$2"
            shift 2
            ;;
        --generate)
            GENERATE="$2"
            shift 2
            ;;
        --language)
            LANGUAGE="$2"
            shift 2
            ;;
        --constraints)
            CONSTRAINTS="$2"
            shift 2
            ;;
        --review)
            REVIEW="$2"
            shift 2
            ;;
        --criteria)
            CRITERIA="$2"
            shift 2
            ;;
        --health)
            HEALTH=true
            shift
            ;;
        --timeout)
            TIMEOUT="$2"
            shift 2
            ;;
        --help|-h)
            echo "AI Coding Agent Client Runner"
            echo ""
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Options:"
            echo "  --agent-url URL       AI Coding Agent URL (default: http://localhost:3050)"
            echo "  --task DESCRIPTION    Submit a coding task to the AI agent"
            echo "  --context TEXT        Additional context for the coding task"
            echo "  --file-path PATH      Path to file if the task involves modifying an existing file"
            echo "  --generate REQMTS     Generate code based on requirements"
            echo "  --language LANG       Programming language for code generation (default: python)"
            echo "  --constraints TEXT    Constraints for code generation"
            echo "  --review CODE         Review code for quality and best practices"
            echo "  --criteria TEXT       Review criteria (default: general quality, efficiency, best practices)"
            echo "  --health              Check the health of the AI Coding Agent"
            echo "  --timeout SECONDS     Timeout in seconds (default: 3600 = 60 minutes)"
            echo "  --help, -h           Show this help message"
            echo ""
            echo "Examples:"
            echo "  $0 --task \"Create a Python function to calculate factorial\""
            echo "  $0 --generate \"Build a REST API with Flask\" --language python"
            echo "  $0 --review \"def hello(): print('Hello World')\" --criteria \"best practices\""
            echo "  $0 --health"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information."
            exit 1
            ;;
    esac
done

# Check if Python is available
if ! command -v python3 &> /dev/null; then
    echo "❌ Error: python3 is not installed or not in PATH"
    exit 1
fi

# Check if the Python script exists
PYTHON_SCRIPT="$SCRIPT_DIR/ai_coding_agent_client.py"
if [ ! -f "$PYTHON_SCRIPT" ]; then
    echo "❌ Error: AI Coding Agent Client script not found at $PYTHON_SCRIPT"
    exit 1
fi

# Prepare the command
CMD="python3 $PYTHON_SCRIPT --agent-url $AGENT_URL --timeout $TIMEOUT"

# Add optional arguments
if [ -n "$TASK" ]; then
    CMD="$CMD --task \"$TASK\""
fi

if [ -n "$CONTEXT" ]; then
    CMD="$CMD --context \"$CONTEXT\""
fi

if [ -n "$FILE_PATH" ]; then
    CMD="$CMD --file-path \"$FILE_PATH\""
fi

if [ -n "$GENERATE" ]; then
    CMD="$CMD --generate \"$GENERATE\""
fi

if [ -n "$LANGUAGE" ]; then
    CMD="$CMD --language \"$LANGUAGE\""
fi

if [ -n "$CONSTRAINTS" ]; then
    CMD="$CMD --constraints \"$CONSTRAINTS\""
fi

if [ -n "$REVIEW" ]; then
    CMD="$CMD --review \"$REVIEW\""
fi

if [ -n "$CRITERIA" ]; then
    CMD="$CMD --criteria \"$CRITERIA\""
fi

if [ "$HEALTH" = true ]; then
    CMD="$CMD --health"
fi

# Run the command
echo "🚀 Running AI Coding Agent Client..."
echo "Command: $CMD"
echo ""

eval $CMD