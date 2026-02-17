# Requirement Engineer MCP Server - Details for IT Manager Agent

## Overview
The Requirement Engineer MCP Server is a specialized AI agent responsible for eliciting, formalizing, and managing software requirements. It bridges the gap between business stakeholders and technical implementation teams by transforming stakeholder inputs into structured, technical requirements.

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

### 1. `analyze_requirements`
**Description**: Analyze incoming stakeholder inputs and extract structured requirements

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "stakeholder_inputs": {"type": "string", "description": "Raw stakeholder inputs (interviews, documents, etc.)"},
    "business_context": {"type": "string", "description": "Business context and constraints"},
    "previous_requirements": {"type": "array", "items": {"type": "object"}, "description": "Previous requirements for reference"}
  },
  "required": ["stakeholder_inputs", "business_context"]
}
```

**Usage**: Call this when you have stakeholder inputs that need to be transformed into structured requirements. The tool will analyze the inputs and return functional and non-functional requirements.

### 2. `resolve_ambiguity`
**Description**: Identify ambiguous requirements and generate clarification requests

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "requirements": {"type": "array", "items": {"type": "object"}, "description": "Requirements to analyze for ambiguity"},
    "stakeholder_context": {"type": "string", "description": "Context about stakeholders involved"},
    "clarification_history": {"type": "array", "items": {"type": "object"}, "description": "Previous clarification attempts"}
  },
  "required": ["requirements"]
}
```

**Usage**: Use this when requirements contain ambiguities that need clarification. The tool will identify issues and generate questions for stakeholders.

### 3. `translate_business_to_technical`
**Description**: Convert business requirements to technical specifications

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "business_requirements": {"type": "array", "items": {"type": "object"}, "description": "Business requirements to translate"},
    "technical_constraints": {"type": "array", "items": {"type": "string"}, "description": "Technical constraints and limitations"},
    "system_context": {"type": "string", "description": "System context and architecture constraints"}
  },
  "required": ["business_requirements", "technical_constraints"]
}
```

**Usage**: Use this to transform business requirements into technical specifications that developers can implement.

### 4. `generate_traceability_matrix`
**Description**: Create and maintain requirement-to-implementation links

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "requirements": {"type": "array", "items": {"type": "object"}, "description": "Requirements to include in matrix"},
    "design_elements": {"type": "array", "items": {"type": "object"}, "description": "Design elements linked to requirements"},
    "code_modules": {"type": "array", "items": {"type": "object"}, "description": "Code modules implementing requirements"},
    "test_cases": {"type": "array", "items": {"type": "object"}, "description": "Test cases validating requirements"}
  },
  "required": ["requirements"]
}
```

**Usage**: Generate traceability matrices to track how requirements connect to design, code, and tests.

### 5. `identify_edge_cases`
**Description**: Identify non-functional requirements and edge cases

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "functional_requirements": {"type": "array", "items": {"type": "object"}, "description": "Functional requirements to analyze"},
    "domain_context": {"type": "string", "description": "Domain-specific context for edge case identification"},
    "security_requirements": {"type": "array", "items": {"type": "string"}, "description": "Security requirements to consider"}
  },
  "required": ["functional_requirements"]
}
```

**Usage**: Identify edge cases and non-functional requirements that may not be apparent from functional requirements alone.

## Available Resources

### 1. `requirements://resource/specifications`
**Description**: Structured requirements documents and specifications

**Usage**: Access the current set of requirement specifications that have been analyzed and stored by the system. Contains functional, non-functional, technical, and edge-case requirements.

### 2. `requirements://resource/traceability-matrix`
**Description**: Matrix linking requirements to design, code, and tests

**Usage**: Retrieve the traceability matrix that shows how requirements connect to design elements, code modules, and test cases. Useful for tracking implementation progress and coverage.

### 3. `requirements://resource/ambiguity-log`
**Description**: Log of identified ambiguities and their resolution status

**Usage**: Access the log of ambiguities that have been identified and their resolution status. Helps track outstanding issues that need stakeholder attention.

## Available Prompts

### 1. `requirements_analysis_prompt`
**Description**: Prompt for analyzing requirements and extracting structured information

**Arguments**:
- `stakeholder_inputs` (string): Raw stakeholder inputs to analyze
- `business_context` (string): Business context for the requirements

**Usage**: Get a structured prompt for analyzing stakeholder inputs when you need to guide manual analysis.

### 2. `ambiguity_identification_prompt`
**Description**: Prompt for identifying ambiguous requirements

**Arguments**:
- `requirements` (string): Requirements to analyze for ambiguity

**Usage**: Get a structured prompt for identifying ambiguities in requirements when you need to guide manual review.

### 3. `business_to_technical_translation_prompt`
**Description**: Prompt for translating business requirements to technical specifications

**Arguments**:
- `business_requirements` (string): Business requirements to translate
- `technical_constraints` (string): Technical constraints to consider

**Usage**: Get a structured prompt for translating business requirements to technical specifications when you need to guide manual translation.

## Integration with IT Manager Workflows

### For Requirements Gathering Phase
1. Use `analyze_requirements` when you have stakeholder inputs to process
2. Store results and access them via `requirements://resource/specifications`
3. Use `resolve_ambiguity` to identify and track issues needing clarification

### For Architecture Planning Phase
1. Use `translate_business_to_technical` to generate technical specifications
2. Use `identify_edge_cases` to ensure comprehensive requirements
3. Access technical requirements via `requirements://resource/specifications`

### For Project Tracking
1. Use `generate_traceability_matrix` to create requirement-to-implementation links
2. Monitor progress via `requirements://resource/traceability-matrix`
3. Track outstanding issues via `requirements://resource/ambiguity-log`

### For Quality Assurance
1. Review traceability matrices to ensure all requirements are covered
2. Verify that ambiguities have been resolved before implementation
3. Confirm edge cases are addressed in requirements

## Registry Integration
The server registers itself with the MCP registry, making its capabilities discoverable to other agents. IT Manager can discover this server through the registry and delegate requirement engineering tasks automatically.

## Health and Status
Use the `ping` method to check server health. The server will return a timestamp and status indicating its operational state.