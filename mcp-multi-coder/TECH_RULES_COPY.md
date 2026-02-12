# TECH_RULES_COPY.md - Vibe Coding AI Agent Implementation

## Architecture Decisions

### 1. Why Streamable-HTTP Transport Was Chosen
- **Modern Standard**: Streamable HTTP is the current MCP standard, replacing deprecated HTTP+SSE transport
- **Single Endpoint**: Uses one `/mcp` endpoint for bidirectional communication (POST/GET)
- **Compliance**: Required by 2025 MCP specification (protocol version 2024-11-05)
- **Performance**: More efficient than legacy transports with better connection management
- **Security**: Built-in origin header validation prevents DNS rebinding attacks

### 2. How Agentic Rulebook Compliance Was Achieved
- **AGENTS.md Governance**: Created comprehensive governance file with security policies
- **Core Principles**: Implemented Simplicity First, Security First, Token Efficiency
- **Tool Policies**: Added human confirmation for destructive operations
- **Rate Limiting**: Built-in request throttling and concurrency controls
- **Observability**: Structured logging with correlation IDs and OpenTelemetry support

### 3. Security Hardening Measures
- **Path Traversal Prevention**: All file operations validated against project root
- **Input Size Limits**: Rejection of prompts exceeding 100k characters
- **Safe Subprocess**: Sandboxed code execution with timeout protection
- **Secret Protection**: No hardcoded credentials, uses .env files
- **Confirmation Requirements**: Explicit confirmation for file writes and destructive operations

## Implementation Scenarios

### 1. LM Studio Integration Pattern
- **Async HTTP Client**: Used httpx.AsyncClient with connection pooling
- **Retry Logic**: Tenacity library with exponential backoff
- **Circuit Breaker**: Custom implementation preventing cascade failures
- **Model Discovery**: Dynamic model capability detection at startup
- **Structured Output**: JSON schema validation with depth/property limits

### 2. Tool Architecture Pattern
- **Pydantic Validation**: All tool inputs validated with Pydantic models
- **Error Handling**: McpError exceptions with descriptive messages
- **Correlation IDs**: Unique IDs for request tracing and logging
- **Security Validation**: Path sanitization and input validation in each tool
- **Governance Compliance**: Each tool respects AGENTS.md policies

### 3. Memory Management Pattern
- **Persistent Storage**: JSON file-based memory store with automatic saving
- **Categorization**: Organized memories by category for efficient retrieval
- **Access Tracking**: Counts accesses to surface frequently used information
- **Semantic Search**: Keyword-based search for relevant memories
- **Metadata Support**: Additional context stored with each memory entry

## Extension Guidelines

### 1. Adding New Tools
- Create Pydantic input model for validation
- Implement function with proper error handling and logging
- Add to server registration in mcp_server.py
- Include comprehensive docstring with usage examples
- Follow security patterns (path validation, input sanitization)

### 2. Enhancing LM Studio Client
- Add new methods to LMStudioClient class
- Implement proper retry and circuit breaker patterns
- Add response validation and error handling
- Include performance monitoring and logging
- Maintain backward compatibility

### 3. Improving Observability
- Add custom OpenTelemetry spans for business logic
- Implement structured logging with consistent field names
- Add performance metrics for tool execution times
- Include error rate monitoring and alerting
- Add distributed tracing across tool calls

## Production Considerations

### 1. Performance Optimization
- Connection pooling for LM Studio API calls
- Caching for frequently accessed data
- Async processing for I/O bound operations
- Memory management for large code files
- Efficient serialization for tool responses

### 2. Scalability Patterns
- Horizontal scaling with load balancer
- Shared memory store (Redis/PostgreSQL) for clustering
- Distributed tracing for multi-instance deployments
- Circuit breaker isolation per service dependency
- Queue-based processing for long-running operations

### 3. Monitoring and Alerting
- Health check endpoints for container orchestration
- Performance metrics for response times and throughput
- Error rate monitoring with alert thresholds
- Resource utilization tracking
- Business metric collection (tool usage patterns)

## Maintenance Procedures

### 1. Regular Maintenance Tasks
- Rotate memory store files periodically
- Clean up old log files with rotation
- Update LM Studio model references
- Review and update security policies
- Audit tool usage and performance

### 2. Emergency Procedures
- Circuit breaker manual reset capability
- Safe mode for degraded operation
- Emergency shutdown with graceful cleanup
- Backup and restore procedures for memory store
- Rollback procedures for configuration changes

### 3. Security Audits
- Regular dependency vulnerability scans
- Input validation rule reviews
- Authentication and authorization checks
- Network security configuration reviews
- Data privacy compliance verification

## Compliance Standards Met

### 1. MCP Protocol Compliance
- ✅ Streamable HTTP transport implementation
- ✅ Standard tool/resource/prompt patterns
- ✅ Proper JSON-RPC 2.0 message handling
- ✅ Notification system for dynamic updates
- ✅ Registry functionality for service discovery

### 2. Industry Standards Compliance
- ✅ AGENTS.md governance standard
- ✅ OpenTelemetry observability standard
- ✅ JSON Schema validation standard
- ✅ REST API best practices
- ✅ Security best practices (OWASP)

### 3. Quality Standards
- ✅ Comprehensive error handling
- ✅ Input validation and sanitization
- ✅ Structured logging and monitoring
- ✅ Automated testing coverage
- ✅ Documentation and examples