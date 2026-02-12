# AGENTS.md - Vibe Coding AI Agent

## Server Identity
- **Name**: Vibe Coding AI Agent (LM Studio / qwen3-4b)
- **Version**: 1.0.0
- **Maintainer**: Vibe Coding Team
- **Description**: Autonomous coding agent that plans, writes, debugs, and tests code using local LLM.

## Core Principles
- **Simplicity First**: Clean, readable code with minimal complexity
- **Readability Priority**: Well-documented code with clear variable names
- **Dependency Minimalism**: Use only essential dependencies
- **Security First**: Input validation, path sanitization, and safe execution
- **Test-Driven Thinking**: Comprehensive testing for all functionality
- **Token Efficiency**: Optimize prompts and responses for cost-effectiveness

## Security Guardrails

### Input Validation Rules
- Reject prompts exceeding 100,000 characters
- Validate file paths to prevent directory traversal attacks
- Sanitize all user inputs before processing
- Block attempts to access system files outside project directory

### Secret Leakage Prevention
- Never log sensitive information or API keys
- Prohibit tools from reading environment variables containing secrets
- Block attempts to write to sensitive system files
- Validate that no secrets are included in tool outputs

### File Write Confirmation
- Require explicit confirmation for file writes outside project root
- Validate file extensions to prevent executable uploads
- Check file paths against allowed directories
- Log all file write operations with timestamps

## Tool-Use Policies

### Human Confirmation Required
- File writes to system directories
- File deletions affecting multiple files
- Process execution with elevated privileges
- Network requests to external domains

### Rate Limits
- Maximum 10 concurrent requests per session
- 100 requests per minute per client
- 1MB maximum payload size per request

### Timeout Defaults
- Tool execution: 60 seconds
- File operations: 30 seconds
- Network requests: 45 seconds
- Code execution: 120 seconds

## Observability Requirements

### Logging Level
- INFO: Normal operations and successful tool calls
- WARN: Recoverable errors and degraded performance
- ERROR: Unrecoverable errors and system failures
- DEBUG: Detailed tracing for troubleshooting (disabled by default)

### Trace Correlation
- Assign unique correlation IDs to each request
- Log correlation IDs in all related messages
- Include timing information for performance analysis
- Track tool success/failure rates

## Supported Capabilities

### Development Tasks
- Code generation from natural language specifications
- Code analysis and bug detection
- Automated testing and test generation
- Code refactoring and optimization
- Documentation generation

### Project Management
- Task planning and breakdown
- Progress tracking and status updates
- Dependency management
- Version control integration

### Quality Assurance
- Static code analysis
- Unit test execution
- Code coverage reporting
- Performance profiling

## Compliance Standards
- MCP 2025-03-26 protocol compliance
- Streamable HTTP transport only
- OpenTelemetry integration for monitoring
- GDPR compliance for data handling
- SOC 2 Type II readiness

## Emergency Procedures
- Immediate shutdown on security breach detection
- Automatic circuit breaker for failed tools
- Graceful degradation when services unavailable
- Rollback capabilities for failed operations