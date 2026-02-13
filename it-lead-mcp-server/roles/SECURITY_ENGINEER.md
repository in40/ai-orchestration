# Security Engineer Agent Implementation

## Overview
The Security Engineer Agent serves as a specialized AI agent responsible for performing static (SAST) and dynamic (DAST) security analysis, scanning dependencies for known vulnerabilities (SCA), validating compliance with security standards (OWASP, CIS), generating threat models for new features, and recommending security hardening measures. It ensures security throughout the development lifecycle.

## Core Responsibilities

### 1. Static and Dynamic Security Analysis
- **Primary Function**: Perform static (SAST) and dynamic (DAST) security analysis
- **Implementation**: Use LLM to analyze code for security vulnerabilities and runtime threats
- **Output**: Security vulnerability reports with CVSS scores and remediation guidance

### 2. Dependency Vulnerability Scanning
- **Primary Function**: Scan dependencies for known vulnerabilities (SCA)
- **Implementation**: Use LLM to analyze dependency trees and match against vulnerability databases
- **Output**: Dependency vulnerability scan results with remediation recommendations

### 3. Security Standards Compliance Validation
- **Primary Function**: Validate compliance with security standards (OWASP, CIS)
- **Implementation**: Use LLM to check code and configurations against security frameworks
- **Output**: Compliance gap analysis reports with remediation steps

### 4. Threat Modeling
- **Primary Function**: Generate threat models for new features
- **Implementation**: Use LLM to identify potential threats and attack vectors
- **Output**: Threat model diagrams and mitigation strategies

### 5. Security Hardening Recommendations
- **Primary Function**: Recommend security hardening measures
- **Implementation**: Use LLM to analyze systems and suggest security improvements
- **Output**: Security hardening recommendations with implementation guidance

## MCP Tools Implementation

### 1. `perform_security_analysis`
- **Description**: Perform static (SAST) and dynamic (DAST) security analysis
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "code": {"type": "string", "description": "Code to analyze for security vulnerabilities"},
    "application_type": {"type": "string", "description": "Type of application (web, mobile, API, etc.)"},
    "analysis_type": {"type": "array", "items": {"type": "string", "enum": ["sast", "dast", "iac_scan"]}, "description": "Types of security analysis to perform"},
    "security_frameworks": {"type": "array", "items": {"type": "string"}, "description": "Security frameworks to check against"},
    "custom_rules": {"type": "array", "items": {"type": "string"}, "description": "Custom security rules to apply"}
  },
  "required": ["code", "application_type", "analysis_type"]
}
```
- **Who Calls**: IT Lead Agent (primary), Implementation Engineer Agent, Human Stakeholders

### 2. `scan_dependencies`
- **Description**: Scan dependencies for known vulnerabilities (SCA)
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "dependency_manifests": {"type": "array", "items": {"type": "string"}, "description": "Dependency manifest files (package.json, requirements.txt, etc.)"},
    "vulnerability_database": {"type": "string", "description": "Vulnerability database to scan against (NVD, CVE feeds)"},
    "scan_depth": {"type": "string", "enum": ["shallow", "deep"], "default": "deep", "description": "Depth of dependency scanning"},
    "severity_threshold": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "high", "description": "Minimum severity threshold for reporting"},
    "license_compliance": {"type": "boolean", "default": false, "description": "Also check for license compliance issues"}
  },
  "required": ["dependency_manifests"]
}
```
- **Who Calls**: IT Lead Agent (primary), DevOps/Release Engineer Agent, Implementation Engineer Agent

### 3. `validate_security_compliance`
- **Description**: Validate compliance with security standards (OWASP, CIS)
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "application_code": {"type": "string", "description": "Application code to validate"},
    "infrastructure_code": {"type": "string", "description": "Infrastructure as Code to validate"},
    "security_frameworks": {"type": "array", "items": {"type": "string", "enum": ["OWASP", "CIS", "PCI-DSS", "ISO27001"]}, "description": "Security frameworks to validate against"},
    "compliance_requirements": {"type": "array", "items": {"type": "string"}, "description": "Specific compliance requirements"},
    "organization_policies": {"type": "array", "items": {"type": "string"}, "description": "Organization-specific security policies"}
  },
  "required": ["security_frameworks"]
}
```
- **Who Calls**: IT Lead Agent (primary), Human Stakeholders, DevOps/Release Engineer Agent

### 4. `generate_threat_model`
- **Description**: Generate threat models for new features
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "feature_specification": {"type": "string", "description": "Specification of the feature to model threats for"},
    "architecture_diagram": {"type": "string", "description": "Architecture diagram or description"},
    "data_flow_diagram": {"type": "string", "description": "Data flow diagram for the feature"},
    "trust_boundaries": {"type": "array", "items": {"type": "string"}, "description": "Trust boundaries in the system"},
    "threat_categories": {"type": "array", "items": {"type": "string", "enum": ["spoofing", "tampering", "repudiation", "information_disclosure", "denial_of_service", "elevation_of_privilege"]}, "description": "Categories of threats to consider"}
  },
  "required": ["feature_specification", "architecture_diagram"]
}
```
- **Who Calls**: IT Lead Agent (primary), Software Architect Agent, Human Stakeholders

### 5. `recommend_hardening_measures`
- **Description**: Recommend security hardening measures
- **Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "application_configuration": {"type": "string", "description": "Current application configuration"},
    "infrastructure_configuration": {"type": "string", "description": "Infrastructure configuration"},
    "runtime_environment": {"type": "string", "description": "Runtime environment details"},
    "security_assessment_results": {"type": "array", "items": {"type": "object"}, "description": "Results from previous security assessments"},
    "compliance_requirements": {"type": "array", "items": {"type": "string"}, "description": "Compliance requirements to meet"}
  },
  "required": ["application_configuration", "runtime_environment"]
}
```
- **Who Calls**: IT Lead Agent (primary), DevOps/Release Engineer Agent, Human Stakeholders

## Technical Implementation

### LLM Integration
- **Prompt Engineering**: Craft specific prompts for security analysis, vulnerability scanning, and compliance validation
- **Context Management**: Maintain security knowledge base and threat intelligence feeds
- **Output Validation**: Validate security findings against established vulnerability databases

### Data Structures
- **Vulnerability Reports**: Detailed reports with CVSS scores and remediation guidance
- **Dependency Scans**: Results of dependency vulnerability analysis
- **Compliance Reports**: Gap analysis against security frameworks
- **Threat Models**: STRIDE-based threat models with mitigation strategies
- **Hardening Guides**: Step-by-step security hardening recommendations

### Communication Interfaces
- **With IT Lead**: Provide security metrics and compliance status
- **With Implementation Engineers**: Share vulnerability findings and remediation guidance
- **With DevOps Team**: Coordinate on infrastructure security and hardening
- **With QA Team**: Provide security test requirements and scenarios
- **With Human Stakeholders**: Report on security posture and compliance status
- **With Software Architects**: Collaborate on secure design patterns

## Key Implementation Patterns

### Defense-in-Depth Analysis
- Implement layered security analysis covering code, configuration, and infrastructure
- Use LLM to identify security gaps across all layers

### Threat Intelligence Integration
- Integrate with threat intelligence feeds for up-to-date vulnerability information
- Use LLM to correlate findings with emerging threats

### Risk-Based Prioritization
- Prioritize security findings based on risk and business impact
- Use LLM to assess potential impact of vulnerabilities

## Call Flow Examples

### Example 1: Security Review for New Feature
1. Implementation Engineer Agent completes feature implementation
2. IT Lead Agent calls `generate_threat_model` with feature specification
3. Security Engineer Agent creates threat model for the feature
4. IT Lead Agent calls `perform_security_analysis` on the code
5. Security Engineer Agent performs SAST analysis and identifies vulnerabilities
6. IT Lead Agent calls `scan_dependencies` for the feature
7. Security Engineer Agent scans dependencies for vulnerabilities
8. IT Lead Agent calls `validate_security_compliance` against OWASP Top 10
9. Security Engineer Agent validates compliance and reports gaps

### Example 2: Dependency Security Check
1. Implementation Engineer Agent updates dependencies
2. DevOps/Release Engineer Agent calls `scan_dependencies` with new manifests
3. Security Engineer Agent scans dependencies and identifies vulnerabilities
4. Security Engineer Agent reports critical vulnerabilities to IT Lead Agent
5. Implementation Engineer Agent addresses identified vulnerabilities
6. Security Engineer Agent re-scans to verify fixes

### Example 3: Infrastructure Hardening
1. DevOps/Release Engineer Agent calls `recommend_hardening_measures` with infrastructure config
2. Security Engineer Agent analyzes configuration and provides hardening recommendations
3. DevOps/Release Engineer Agent implements hardening measures
4. IT Lead Agent calls `validate_security_compliance` to verify hardening
5. Security Engineer Agent validates compliance with security frameworks

This implementation creates a sophisticated Security Engineer Agent capable of autonomously performing comprehensive security analysis, vulnerability scanning, compliance validation, threat modeling, and security hardening throughout the development lifecycle.

## File and Artifact Exchange

### Security Artifact Exchange Mechanisms
- **MCP Resources**: Share security reports via `security://resource/vulnerability-reports`
- **Tool Arguments**: Pass code and configurations in tool calls like `perform_security_analysis`
- **Version Control**: Store security configurations and scan results in Git repositories for version control and collaboration
- **Registry Discovery**: Register security artifacts in MCP registry for other agents to discover

### Communication with Other Agents
- **With IT Lead**: Provides security metrics via `perform_security_analysis` tool and compliance status via shared resources
- **With Implementation Engineers**: Shares vulnerability findings via `perform_security_analysis` tool and remediation guidance via shared resources
- **With DevOps Team**: Coordinates on infrastructure security via `recommend_hardening_measures` tool and security configurations
- **With QA Team**: Provides security test requirements via tool arguments and security-focused test resources
- **With Human Stakeholders**: Reports on security posture via `validate_security_compliance` tool and compliance reports via shared resources
- **With Software Architects**: Collaborates on secure design patterns via `generate_threat_model` tool and architectural security resources