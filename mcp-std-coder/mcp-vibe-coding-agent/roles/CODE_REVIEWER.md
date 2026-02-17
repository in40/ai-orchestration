# Code Reviewer Agent Implementation

## Overview
The Code Reviewer Agent serves as a specialized AI agent responsible for performing static analysis for bugs, security vulnerabilities, and anti-patterns, validating adherence to architectural decisions and coding standards, suggesting improvements for readability, performance, and maintainability, cross-referencing changes against requirements traceability matrix, and coordinating multi-pass review cycles until quality gates are met.

## Core Responsibilities

### 1. Static Analysis for Bugs and Vulnerabilities
- **Primary Function**: Perform static analysis to identify bugs, security vulnerabilities, and anti-patterns
- **Implementation**: Use LLM to analyze code for common issues, security flaws, and problematic patterns
- **Output**: Annotated review comments with severity levels and suggested fixes

### 2. Architectural and Standards Compliance
- **Primary Function**: Validate adherence to architectural decisions and coding standards
- **Implementation**: Use LLM to check code against architectural guidelines and established standards
- **Output**: Compliance report with violations and recommendations

### 3. Improvement Suggestions
- **Primary Function**: Suggest improvements for readability, performance, and maintainability
- **Implementation**: Use LLM to identify optimization opportunities and improvement suggestions
- **Output**: Detailed improvement recommendations with implementation guidance

### 4. Requirements Traceability Verification
- **Primary Function**: Cross-reference changes against requirements traceability matrix
- **Implementation**: Use LLM to verify that code changes align with specified requirements
- **Output**: Traceability verification report with alignment status

### 5. Multi-Pass Review Coordination
- **Primary Function**: Coordinate multi-pass review cycles until quality gates are met
- **Implementation**: Manage review iterations and track resolution of identified issues
- **Output**: Approval/rejection decision with rationale and quality scorecard

## MCP Tools Implementation

### 1. `perform_static_analysis`
- **Description**: Perform static analysis for bugs, security vulnerabilities, and anti-patterns
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "code_diff": {"type": "string", "description": "Code changes to analyze"},
    "programming_language": {"type": "string", "description": "Language of the code being reviewed"},
    "security_checklist": {"type": "array", "items": {"type": "string"}, "description": "Security vulnerabilities to check for"},
    "bug_patterns": {"type": "array", "items": {"type": "string"}, "description": "Common bug patterns to look for"},
    "anti_patterns": {"type": "array", "items": {"type": "string"}, "description": "Anti-patterns to identify"}
  },
  "required": ["code_diff", "programming_language"]
}
```
- **Who Calls**: IT Lead Agent (primary), Implementation Engineer Agent, Human Stakeholders

### 2. `validate_architecture_compliance`
- **Description**: Validate adherence to architectural decisions and coding standards
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "code_diff": {"type": "string", "description": "Code changes to validate"},
    "architectural_guidelines": {"type": "string", "description": "Architectural guidelines to validate against"},
    "coding_standards": {"type": "string", "description": "Coding standards to validate against"},
    "design_documents": {"type": "array", "items": {"type": "string"}, "description": "Relevant design documents for context"}
  },
  "required": ["code_diff", "architectural_guidelines", "coding_standards"]
}
```
- **Who Calls**: IT Lead Agent (primary), Software Architect Agent, Implementation Engineer Agent

### 3. `suggest_improvements`
- **Description**: Suggest improvements for readability, performance, and maintainability
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "code": {"type": "string", "description": "Code to analyze for improvements"},
    "improvement_focus": {"type": "array", "items": {"type": "string"}, "enum": ["readability", "performance", "maintainability", "security"], "description": "Areas of focus for improvements"},
    "performance_requirements": {"type": "array", "items": {"type": "string"}, "description": "Performance requirements to consider"},
    "existing_codebase_context": {"type": "string", "description": "Context from existing codebase for consistency"}
  },
  "required": ["code", "improvement_focus"]
}
```
- **Who Calls**: IT Lead Agent (primary), Implementation Engineer Agent, Human Stakeholders

### 4. `verify_requirements_traceability`
- **Description**: Cross-reference changes against requirements traceability matrix
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "code_changes": {"type": "array", "items": {"type": "string"}, "description": "Code changes to verify"},
    "requirements_matrix": {"type": "string", "description": "Requirements traceability matrix"},
    "feature_requirements": {"type": "array", "items": {"type": "string"}, "description": "Specific feature requirements to verify against"},
    "test_coverage": {"type": "string", "description": "Test coverage information for verification"}
  },
  "required": ["code_changes", "requirements_matrix"]
}
```
- **Who Calls**: IT Lead Agent (primary), Requirements Engineer Agent, QA/Test Engineer Agent

### 5. `coordinate_review_cycle`
- **Description**: Coordinate multi-pass review cycles until quality gates are met
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "pull_request_id": {"type": "string", "description": "ID of the pull request being reviewed"},
    "initial_review_comments": {"type": "array", "items": {"type": "object"}, "description": "Initial review comments and issues"},
    "quality_gate_criteria": {"type": "array", "items": {"type": "string"}, "description": "Criteria for quality gate approval"},
    "review_history": {"type": "array", "items": {"type": "object"}, "description": "History of previous review cycles"},
    "author_responses": {"type": "array", "items": {"type": "object"}, "description": "Author responses to previous review comments"}
  },
  "required": ["pull_request_id", "initial_review_comments", "quality_gate_criteria"]
}
```
- **Who Calls**: IT Lead Agent (primary), Implementation Engineer Agent, Human Stakeholders

## Technical Implementation

### LLM Integration
- **Prompt Engineering**: Craft specific prompts for static analysis, compliance checking, and improvement suggestions
- **Context Management**: Maintain codebase context and architectural consistency
- **Output Validation**: Validate review findings against established quality standards

### Data Structures
- **Review Comments**: Annotated comments with severity levels and suggestions
- **Compliance Reports**: Detailed reports on architectural and standards compliance
- **Improvement Recommendations**: Actionable suggestions with implementation guidance
- **Traceability Reports**: Verification of code changes against requirements
- **Quality Scorecards**: Per-PR quality metrics and approval decisions

### Communication Interfaces
- **With IT Lead**: Provide review status and quality metrics
- **With Implementation Engineers**: Give feedback on code quality and suggestions
- **With Software Architects**: Verify architectural compliance
- **With QA Team**: Coordinate on test coverage and requirements verification
- **With Security Team**: Identify security vulnerabilities
- **With Human Stakeholders**: Provide quality reports and approval decisions

## Key Implementation Patterns

### Multi-Level Analysis
- Implement layered analysis covering syntax, semantics, architecture, and security
- Use LLM to provide comprehensive feedback at each level

### Constructive Feedback
- Focus on providing actionable, constructive feedback
- Use LLM to suggest specific improvements rather than just identifying problems

### Quality Gate Enforcement
- Implement strict quality gates with clear criteria
- Use LLM to objectively evaluate code against quality standards

## Call Flow Examples

### Example 1: Pull Request Review
1. Implementation Engineer Agent submits code changes
2. IT Lead Agent calls `perform_static_analysis` with code diff
3. Code Reviewer Agent analyzes code for bugs and vulnerabilities
4. IT Lead Agent calls `validate_architecture_compliance` with changes
5. Code Reviewer Agent validates against architectural guidelines
6. IT Lead Agent calls `verify_requirements_traceability` with changes
7. Code Reviewer Agent verifies alignment with requirements
8. IT Lead Agent calls `coordinate_review_cycle` for approval process
9. Code Reviewer Agent manages review cycle and provides approval decision

### Example 2: Quality Improvement Initiative
1. IT Lead Agent calls `suggest_improvements` for existing code
2. Code Reviewer Agent analyzes code and suggests improvements
3. Implementation Engineer Agent implements suggestions
4. IT Lead Agent calls `perform_static_analysis` on improved code
5. Code Reviewer Agent verifies improvements reduced issues

### Example 3: Architecture Compliance Check
1. Software Architect Agent calls `validate_architecture_compliance` with new code
2. Code Reviewer Agent validates against architectural guidelines
3. Code Reviewer Agent reports any violations with recommendations
4. Implementation Engineer Agent addresses violations
5. Code Reviewer Agent revalidates compliance

This implementation creates a sophisticated Code Reviewer Agent capable of autonomously performing comprehensive code reviews, ensuring quality standards, and maintaining architectural integrity throughout the development process.

## File and Artifact Exchange

### Code Review Exchange Mechanisms
- **MCP Resources**: Share review reports via `code-review://resource/review-comments`
- **Tool Arguments**: Pass code diffs and review comments in tool calls like `perform_static_analysis`
- **Version Control**: Access code from Git repositories for review
- **Registry Discovery**: Register review artifacts in MCP registry for other agents to discover

### Communication with Other Agents
- **With IT Lead**: Provides review status via `perform_static_analysis` tool and quality metrics via shared resources
- **With Implementation Engineers**: Gives feedback via `suggest_improvements` tool and review comments via shared resources
- **With Software Architects**: Verifies compliance via `validate_architecture_compliance` tool and shared architectural guidelines
- **With QA Team**: Coordinates on test coverage via tool arguments and shared test resources
- **With Security Team**: Identifies vulnerabilities via `perform_static_analysis` tool and security-focused resources
- **With Human Stakeholders**: Provides quality reports via `coordinate_review_cycle` tool and approval decisions via shared resources