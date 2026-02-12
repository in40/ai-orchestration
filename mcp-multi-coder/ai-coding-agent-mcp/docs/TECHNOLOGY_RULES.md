# TECHNOLOGY RULES

## Python Version
- Python 3.10+ (currently using Python 3.13.5)

## Dependencies
- httpx>=0.27.0 - for async LM Studio API calls
- python-dotenv>=1.0.0 - for .env config
- pydantic>=2.5.0 - for request/response validation
- fastapi, uvicorn, sse-starlette - for HTTP/SSE transport
- requests - for registry communication
- psycopg2-binary - for PostgreSQL registry support

## LM Studio API Limitations
- Models with <7B parameters (including Qwen3-4B) may not reliably support structured output (JSON schema enforcement)
- The server must not rely on `response_format` / JSON schema for LLM interaction
- Use free-form text prompts and parse responses heuristically or via simple regex

## Architecture Patterns
- Async queue pattern for handling tasks
- Configurable concurrent workers (controlled by CONCURRENT_WORKERS environment variable)
- In-memory task storage (no external database for tasks)
- Protected shared access using asyncio.Lock

## HTTP/SSE Transport
- Uses HTTP/SSE transport by default
- Port 3050 by default
- Supports session correlation via X-MCP-Session-ID header

## Registry Integration
- Supports auto-registration with registry servers
- Maintains heartbeat with registry every 30 seconds
- Automatically deregisters on clean shutdown