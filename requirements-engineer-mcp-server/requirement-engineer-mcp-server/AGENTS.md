# Requirement Engineer MCP Server Agents

This document describes the requirement engineering agents available in this MCP server implementation.

## Requirement Engineer Agent

The Requirement Engineer Agent is a specialized AI agent responsible for eliciting, formalizing, and managing software requirements. It bridges the gap between business stakeholders and technical implementation teams by transforming stakeholder inputs into structured, technical requirements.

### Core Capabilities

1. **Requirements Elicitation and Formalization**
   - Transform stakeholder inputs into structured, formal requirements
   - Generate structured Requirements Specification (SRS) documents

2. **Ambiguity Resolution**
   - Identify and resolve ambiguous requirements through clarification cycles
   - Generate clarifying questions for stakeholders

3. **Business-to-Technical Translation**
   - Translate business needs into technical specifications
   - Bridge the gap between business language and technical requirements

4. **Traceability Maintenance**
   - Maintain links between requirements and implementation
   - Create and maintain traceability matrices

5. **Edge Case Identification**
   - Identify non-functional requirements and edge cases
   - Analyze requirements for potential edge cases and non-functional aspects

### Available Tools

- `analyze_requirements`: Analyze stakeholder inputs and extract structured requirements
- `resolve_ambiguity`: Identify ambiguous requirements and generate clarification requests
- `translate_business_to_technical`: Convert business requirements to technical specifications
- `generate_traceability_matrix`: Create and maintain requirement-to-implementation links
- `identify_edge_cases`: Identify non-functional requirements and edge cases

### Available Resources

- `requirements://resource/specifications`: Structured requirements documents and specifications
- `requirements://resource/traceability-matrix`: Matrix linking requirements to design, code, and tests
- `requirements://resource/ambiguity-log`: Log of identified ambiguities and their resolution status

### Available Prompts

- `requirements_analysis_prompt`: Prompt for analyzing requirements and extracting structured information
- `ambiguity_identification_prompt`: Prompt for identifying ambiguous requirements
- `business_to_technical_translation_prompt`: Prompt for translating business requirements to technical specifications