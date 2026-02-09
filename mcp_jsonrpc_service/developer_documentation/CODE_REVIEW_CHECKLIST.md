# MCP Server Code Review Checklist

Use this checklist when reviewing MCP server code to ensure quality, security, and compliance with standards.

## Architecture & Design

### [ ] Follows Base Server Pattern
- [ ] Extends `BaseMCPServer` or implements `MCPServerExtension`
- [ ] Doesn't modify core server functionality unnecessarily
- [ ] Uses provided configuration system
- [ ] Follows layered architecture (transport, protocol, business logic, security)

### [ ] Proper Async Usage
- [ ] Uses `async`/`await` consistently
- [ ] Avoids blocking operations in async functions
- [ ] Uses `asyncio.gather()` for concurrent operations
- [ ] Properly handles cancellation and timeouts

### [ ] Error Handling
- [ ] Uses provided error classes (`InvalidParamsError`, `InternalError`, etc.)
- [ ] Implements proper error wrapping and propagation
- [ ] Provides meaningful error messages
- [ ] Uses `@handle_rpc_error` decorator where appropriate

## Security

### [ ] Input Validation
- [ ] Validates all inputs using Pydantic or similar
- [ ] Sanitizes user-provided data
- [ ] Prevents injection attacks (SQL, command, etc.)
- [ ] Implements proper bounds checking

### [ ] Authentication & Authorization
- [ ] Implements appropriate authentication if required
- [ ] Validates permissions before performing actions
- [ ] Doesn't expose sensitive information in logs or responses
- [ ] Uses secure communication (HTTPS/TLS) in production

### [ ] Data Protection
- [ ] Handles sensitive data appropriately
- [ ] Doesn't log sensitive information
- [ ] Implements proper access controls
- [ ] Encrypts data at rest if required

## Performance & Reliability

### [ ] Resource Management
- [ ] Properly manages connections (DB, external services)
- [ ] Implements connection pooling where appropriate
- [ ] Releases resources in finally blocks or context managers
- [ ] Monitors memory usage and prevents leaks

### [ ] Concurrency & Threading
- [ ] Uses async/await instead of threading where possible
- [ ] Properly synchronizes shared state
- [ ] Implements appropriate rate limiting
- [ ] Handles concurrent requests safely

### [ ] Health Monitoring
- [ ] Implements proper health check methods
- [ ] Reports accurate health status
- [ ] Monitors external dependencies
- [ ] Includes appropriate metrics

## Testing

### [ ] Test Coverage
- [ ] Unit tests cover core functionality (>80% coverage)
- [ ] Edge cases are tested
- [ ] Error conditions are tested
- [ ] Async functions have proper async tests

### [ ] Test Quality
- [ ] Tests are isolated and deterministic
- [ ] Uses appropriate fixtures and mocks
- [ ] Tests both positive and negative cases
- [ ] Includes integration tests for key workflows

## Code Quality

### [ ] Code Style
- [ ] Follows PEP 8 style guidelines
- [ ] Uses consistent naming conventions
- [ ] Code is well-formatted (use Black)
- [ ] Linting passes (use Flake8)

### [ ] Documentation
- [ ] Public methods/functions have docstrings
- [ ] Complex logic is explained with comments
- [ ] API endpoints are documented
- [ ] Configuration options are documented

### [ ] Maintainability
- [ ] Functions are reasonably sized (<50 lines when possible)
- [ ] Classes have single responsibility
- [ ] Dependencies are minimal and justified
- [ ] Code is organized logically

## MCP Protocol Compliance

### [ ] Protocol Adherence
- [ ] Follows MCP specification
- [ ] Implements required capabilities correctly
- [ ] Uses correct JSON-RPC 2.0 format
- [ ] Handles all required methods

### [ ] Registry Integration
- [ ] Properly registers with registry
- [ ] Updates health status appropriately
- [ ] Provides correct server information
- [ ] Handles registration failures gracefully

## Configuration & Deployment

### [ ] Configuration Management
- [ ] Uses provided configuration system
- [ ] Supports environment variables
- [ ] Has sensible defaults
- [ ] Validates configuration values

### [ ] Deployment Readiness
- [ ] Works with different transport methods
- [ ] Handles graceful shutdown
- [ ] Includes health check endpoint
- [ ] Logs appropriately for production

## Error Conditions

### [ ] Failure Handling
- [ ] Handles network failures gracefully
- [ ] Implements retry logic where appropriate
- [ ] Provides fallback behaviors
- [ ] Logs errors appropriately

### [ ] Recovery
- [ ] Can recover from transient failures
- [ ] Implements circuit breaker pattern if needed
- [ ] Handles resource exhaustion
- [ ] Gracefully degrades functionality

## Special Cases

### [ ] Security Review
- [ ] No hardcoded credentials
- [ ] No secrets in code or config
- [ ] Proper authentication for admin functions
- [ ] Input sanitization for all user data
- [ ] Security headers properly configured
- [ ] HTTPS enforced in production

### [ ] Performance Review
- [ ] No N+1 queries or similar issues
- [ ] Efficient algorithms used
- [ ] Caching implemented where appropriate
- [ ] Memory usage is reasonable

### [ ] Production Readiness
- [ ] Proper logging levels used
- [ ] Metrics exposed if needed
- [ ] Monitoring hooks included
- [ ] Configuration for production environments

---

**Reviewer:** _____________________ **Date:** _____________

**Overall Assessment:**
- [ ] Approve
- [ ] Approve with minor comments
- [ ] Request changes
- [ ] Reject

**Notes:**