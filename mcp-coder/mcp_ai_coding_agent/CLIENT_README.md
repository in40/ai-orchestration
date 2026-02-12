# AI Coding Agent Client

A user-friendly utility for submitting coding tasks to the AI Coding Agent via MCP protocol.

## Overview

This utility allows users to:
- Submit coding tasks to the AI Coding Agent
- Generate code solutions from requirements
- Review existing code for quality and best practices
- Check the health of the AI Coding Agent

## Features

- **Interactive Mode**: Easy-to-use menu-driven interface
- **Command-Line Mode**: Direct execution with arguments
- **Visual Feedback**: Progress indicators and status messages
- **Error Handling**: Comprehensive error reporting
- **Pseudographics**: Attractive UI with boxes and headers

## Prerequisites

- Python 3.7+
- Requests library (`pip install requests`)
- Running AI Coding Agent server
- Access to an LLM service (Ollama, LM Studio, vLLM, etc.)

## LLM Service Configuration

The AI Coding Agent needs to connect to an LLM service. Follow these steps to configure it:

1. **Set up your LLM service** (e.g., Ollama, LM Studio, vLLM)
2. **Run the setup script** to configure the connection:
   ```bash
   ./setup_llm_config.sh
   ```
3. **Start the AI Coding Agent** with your configuration:
   ```bash
   source .env && ./start_ai_coding_agent.sh
   ```

### Common LLM Endpoints:
- Ollama: `http://localhost:11434/v1`
- LM Studio: `http://asus-tus:1234/v1`
- vLLM/LiteLLM: `http://localhost:8000/v1`
- Custom service: `http://your-server:port/v1`

## Usage

### Interactive Mode
```bash
python ai_coding_agent_client.py
```

Or using the quick launcher:
```bash
./ai_coding_agent
```

Or using the shell script runner:
```bash
./run_ai_coding_agent_client.sh
```

### Command-Line Mode

#### Submit a coding task:
```bash
python ai_coding_agent_client.py --task "Create a Python function to calculate factorial"
```

Or using the quick launcher:
```bash
./ai_coding_agent --task "Create a Python function to calculate factorial"
```

Or using the shell script runner:
```bash
./run_ai_coding_agent_client.sh --task "Create a Python function to calculate factorial"
```

#### Submit a coding task with context:
```bash
python ai_coding_agent_client.py --task "Fix the bug in this code" --context "The function crashes when input is negative" --code "..."
```

#### Generate code from requirements:
```bash
python ai_coding_agent_client.py --generate "Build a REST API with Flask" --language python
```

#### Review code:
```bash
python ai_coding_agent_client.py --review "def hello(): print('Hello World')" --criteria "best practices"
```

#### Check health:
```bash
python ai_coding_agent_client.py --health
```

### All Options:
```bash
python ai_coding_agent_client.py --help
```

Or using the quick launcher:
```bash
./ai_coding_agent --help
```

Or using the shell script runner:
```bash
./run_ai_coding_agent_client.sh --help
```

## Architecture

The client follows the MCP (Model Context Protocol) specification:
1. Opens an SSE (Server-Sent Events) connection first
2. Submits requests to the `/send` endpoint
3. Receives responses via the SSE connection
4. Correlates requests and responses using unique IDs

## Components

- **AICodingAgentClient**: Main client class that handles communication with the AI Coding Agent
- **SSE Listener**: Thread that listens for responses from the agent
- **Request Handler**: Sends requests to the agent via HTTP POST
- **Response Processor**: Matches responses to requests using correlation IDs

## Supported Operations

- `execute_coding_task`: Submit a coding task for processing
- `generate_code_solution`: Generate code from requirements
- `review_code`: Review code for quality and best practices
- `health_check`: Check the health of the AI Coding Agent

## Error Handling

The client handles various error conditions:
- Connection timeouts
- Network errors
- Agent unavailability
- Request processing failures
- Response format issues

## Examples

### Simple Task Submission
```bash
python ai_coding_agent_client.py --task "Write a Python function that reverses a string"
```

### Code Generation with Constraints
```bash
python ai_coding_agent_client.py --generate "Create a bubble sort algorithm" --language python --constraints "Must include comments and error handling"
```

### Code Review
```bash
python ai_coding_agent_client.py --review "def bubble_sort(arr): n = len(arr); for i in range(n): for j in range(0, n-i-1): if arr[j] > arr[j+1]: arr[j], arr[j+1] = arr[j+1], arr[j]; return arr" --criteria "efficiency and readability"
```