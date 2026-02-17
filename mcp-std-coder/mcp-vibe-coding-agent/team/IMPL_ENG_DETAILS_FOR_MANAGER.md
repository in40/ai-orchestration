# Implementation Engineer MCP Server - Details for IT Manager Agent

## Overview
The Implementation Engineer MCP Server is a specialized AI agent responsible for generating production-ready code from specifications, implementing features following architectural guidelines, applying consistent coding standards, writing unit tests, and refactoring code for maintainability and performance. It bridges the gap between design and implementation, turning architectural decisions into working code.

## MCP Endpoints

### Core MCP Methods
- `initialize` - Initialize connection and exchange capabilities
- `tools/list` - List available tools with pagination support
- `tools/call` - Execute specific tools with given arguments
- `resources/list` - List available resources
- `resources/read` - Read content from specific resources
- `prompts/list` - List available prompt templates
- `prompts/get` - Get resolved prompt with arguments
- `shutdown` - Initiate graceful server shutdown
- `ping` - Health check returning timestamp and status

### Registry Methods (when enabled)
- `registry/register` - Register a service with the MCP registry
- `registry/list` - List all registered services
- `registry/unregister` - Unregister a service from the MCP registry

## Available Tools

### 1. `git_checkout_branch`
**Description**: Checkout a specific branch in a Git repository

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "repository_path": {"type": "string", "description": "Path to the Git repository"},
    "branch_name": {"type": "string", "description": "Name of the branch to checkout"},
    "create_if_not_exists": {"type": "boolean", "default": false, "description": "Create branch if it doesn't exist"},
    "remote_tracking": {"type": "boolean", "default": false, "description": "Track remote branch if creating new branch"}
  },
  "required": ["repository_path", "branch_name"]
}
```

**Usage**: Call this when you need to switch to a specific branch in a Git repository. The tool will handle checking out the branch, creating it if needed, and setting up remote tracking.

### 2. `generate_code_from_spec`
**Description**: Generate code from architectural specifications and requirements

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "specifications": {"type": "string", "description": "API specs, data models, and architectural decisions"},
    "programming_language": {"type": "string", "description": "Target programming language"},
    "framework": {"type": "string", "description": "Target framework or platform"},
    "coding_standards": {"type": "string", "description": "Coding standards and style guides"},
    "existing_codebase_context": {"type": "string", "description": "Context from existing codebase for consistency"}
  },
  "required": ["specifications", "programming_language", "framework"]
}
```

**Usage**: Use this when you have architectural specifications that need to be transformed into working code. The tool will generate production-ready code following the specified language, framework, and coding standards.

### 3. `implement_feature`
**Description**: Implement specific features following architectural guidelines

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "feature_requirements": {"type": "string", "description": "Detailed feature requirements"},
    "architectural_guidelines": {"type": "string", "description": "Architectural patterns and guidelines to follow"},
    "dependencies": {"type": "array", "items": {"type": "string"}, "description": "Dependencies and integration points"},
    "performance_requirements": {"type": "array", "items": {"type": "string"}, "description": "Performance requirements for the feature"}
  },
  "required": ["feature_requirements", "architectural_guidelines"]
}
```

**Usage**: Use this to implement specific features following architectural guidelines and considering dependencies and performance requirements. The tool will generate feature-complete code that adheres to architectural patterns.

### 4. `apply_coding_standards`
**Description**: Apply consistent coding standards and patterns to code

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "code": {"type": "string", "description": "Code to apply standards to"},
    "style_guide": {"type": "string", "description": "Style guide and coding standards"},
    "language": {"type": "string", "description": "Programming language"},
    "existing_patterns": {"type": "array", "items": {"type": "string"}, "description": "Patterns used in existing codebase"}
  },
  "required": ["code", "style_guide", "language"]
}
```

**Usage**: Use this to ensure code follows established style guides and patterns. The tool will transform the provided code to match the specified coding standards and existing codebase patterns.

### 5. `generate_unit_tests`
**Description**: Generate unit tests for code following test-first approach

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "code": {"type": "string", "description": "Code to generate tests for"},
    "requirements": {"type": "string", "description": "Functional requirements to test"},
    "test_framework": {"type": "string", "description": "Target test framework"},
    "coverage_requirements": {"type": "array", "items": {"type": "string"}, "description": "Coverage requirements"}
  },
  "required": ["code", "requirements", "test_framework"]
}
```

**Usage**: Use this to generate comprehensive unit tests for code based on functional requirements. The tool will create tests with good coverage and meaningful assertions using the specified test framework.

### 6. `refactor_code`
**Description**: Refactor code for maintainability and performance improvements

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "code": {"type": "string", "description": "Code to refactor"},
    "refactoring_goals": {"type": "array", "items": {"type": "string"}, "description": "Goals for refactoring (performance, readability, etc.)"},
    "constraints": {"type": "array", "items": {"type": "string"}, "description": "Constraints and limitations for refactoring"},
    "existing_patterns": {"type": "array", "items": {"type": "string"}, "description": "Patterns to maintain consistency with"}
  },
  "required": ["code", "refactoring_goals"]
}
```

**Usage**: Use this to refactor code based on specified goals while respecting constraints and maintaining consistency with existing patterns. The tool will improve code quality with better performance and maintainability.

## Available Resources

### 1. `implementation://resource/generated-code`
**Description**: Generated source code in appropriate languages and frameworks

**Usage**: Access the current set of generated code that has been produced by the implementation tools. Contains production-ready code files in the target programming languages and frameworks.

### 2. `implementation://resource/test-suites`
**Description**: Comprehensive unit test collections

**Usage**: Retrieve the generated test suites that have been created for implemented features. Contains unit tests with good coverage and meaningful assertions.

### 3. `implementation://resource/refactoring-reports`
**Description**: Analysis of code quality and suggested improvements

**Usage**: Access refactoring reports that analyze code quality and suggest improvements. Useful for tracking code quality metrics and improvement initiatives.

### 4. `implementation://resource/style-guides`
**Description**: Coding standards and best practices documentation

**Usage**: Retrieve the coding standards and best practices that have been applied to code. Contains style guides and patterns used in the existing codebase.

### 5. `implementation://resource/dependency-manifests`
**Description**: Project dependencies and configuration

**Usage**: Access project dependencies and configuration files that have been generated or updated. Contains dependency manifests and configuration settings.

## Available Prompts

### 1. `code_generation_prompt`
**Description**: Prompt for generating code from specifications

**Arguments**:
- `specifications` (string): API specs, data models, and architectural decisions
- `programming_language` (string): Target programming language
- `framework` (string): Target framework or platform

**Usage**: Get a structured prompt for generating code from specifications when you need to guide manual implementation.

### 2. `feature_implementation_prompt`
**Description**: Prompt for implementing features following guidelines

**Arguments**:
- `feature_requirements` (string): Detailed feature requirements
- `architectural_guidelines` (string): Architectural patterns and guidelines to follow
- `dependencies` (string): Dependencies and integration points

**Usage**: Get a structured prompt for implementing features following architectural guidelines when you need to guide manual implementation.

### 3. `code_refactoring_prompt`
**Description**: Prompt for refactoring code for improvements

**Arguments**:
- `code` (string): Code to refactor
- `refactoring_goals` (string): Goals for refactoring (performance, readability, etc.)
- `constraints` (string): Constraints and limitations for refactoring

**Usage**: Get a structured prompt for refactoring code based on specified goals when you need to guide manual refactoring.

### 4. `test_generation_prompt`
**Description**: Prompt for generating unit tests

**Arguments**:
- `code` (string): Code to generate tests for
- `requirements` (string): Functional requirements to test
- `test_framework` (string): Target test framework

**Usage**: Get a structured prompt for generating unit tests when you need to guide manual test creation.

## Integration with IT Manager Workflows

### For Code Generation Phase
1. Use `generate_code_from_spec` when you have architectural specifications to implement
2. Store results and access them via `implementation://resource/generated-code`
3. Use `apply_coding_standards` to ensure consistency with existing codebase

### For Feature Implementation Phase
1. Use `implement_feature` to implement specific features following guidelines
2. Generate corresponding tests using `generate_unit_tests`
3. Access generated code via `implementation://resource/generated-code`

### For Code Quality Assurance
1. Use `refactor_code` to improve code quality and performance
2. Monitor refactoring progress via `implementation://resource/refactoring-reports`
3. Use `apply_coding_standards` to maintain consistency

### For Git Operations
1. Use `git_checkout_branch` to manage branches during development
2. Coordinate with DevOps team for deployment preparation

### For Quality Gates
1. Review generated test suites via `implementation://resource/test-suites`
2. Verify code quality via `implementation://resource/refactoring-reports`
3. Ensure coding standards compliance via `implementation://resource/style-guides`

## Registry Integration
The server registers itself with the MCP registry, making its capabilities discoverable to other agents. IT Manager can discover this server through the registry and delegate implementation tasks automatically.

## Health and Status
Use the `ping` method to check server health. The server will return a timestamp and status indicating its operational state.