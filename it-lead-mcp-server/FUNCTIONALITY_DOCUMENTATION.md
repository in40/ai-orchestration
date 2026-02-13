# IT Lead MCP Server - Comprehensive Functionality Documentation

## Table of Contents
1. [Overview](#overview)
2. [Core Architecture](#core-architecture)
3. [MCP Protocol Implementation](#mcp-protocol-implementation)
4. [Tools Capabilities](#tools-capabilities)
5. [Resources Capabilities](#resources-capabilities)
6. [Prompts Capabilities](#prompts-capabilities)
7. [Registry Integration](#registry-integration)
8. [LLM Integration](#llm-integration)
9. [Enhanced Capabilities](#enhanced-capabilities)
10. [Configuration Options](#configuration-options)
11. [Usage Examples](#usage-examples)

## Overview

The IT Lead MCP Server is an AI-powered agent that serves as a technical lead for software development teams. It accepts development tasks via MCP (Model Context Protocol) endpoints and intelligently distributes subtasks to other specialized agents or team members. The server provides comprehensive project management, code review, architecture analysis, and team coordination capabilities.

### Key Features
- **Task Assignment**: Assign development tasks to team members or sub-agents with appropriate priority and deadlines
- **Code Review**: Perform automated code reviews using LLM integration
- **Project Planning**: Generate comprehensive project plans based on requirements
- **Architecture Analysis**: Analyze and suggest improvements to software architecture
- **Team Coordination**: Schedule meetings and track task progress
- **LLM Integration**: Integrated with LM Studio for AI-powered decision making
- **Registry Integration**: Automatically registers with MCP registry for service discovery
- **PostgreSQL Support**: Uses PostgreSQL for persistent storage of tasks and services

## Core Architecture

The IT Lead MCP Server follows a modular architecture with clear separation of concerns:

- **Transports**: Handle communication via stdio, HTTP/SSE, or Streamable HTTP
- **Handlers**: Process MCP requests and responses
- **Utils**: Provide common functionality like JSON-RPC handling and notifications
- **Registry**: Manage service registration and discovery
- **Enhanced Modules**: Strategic planning, assignment logic, quality gates, etc.

### Component Flow
1. **Transport Layer**: Receives MCP requests via stdio, HTTP, or Streamable HTTP
2. **JSON-RPC Handler**: Parses and routes requests to appropriate handlers
3. **Server Handlers**: Process requests using various specialized modules
4. **LLM Integration**: Calls external LLM for AI-powered decisions
5. **Registry Integration**: Registers services and discovers other agents
6. **Task Storage**: Persists task information in PostgreSQL

## MCP Protocol Implementation

The server fully complies with the Model Context Protocol (MLM) specification:

### Supported Transports
- **STDIO Transport**: Standard input/output stream communication
- **Streamable HTTP Transport**: Modern single `/mcp` endpoint supporting both POST and GET methods
- **Legacy HTTP/SSE Transport**: Backward-compatible `/sse` and `/message` endpoints

### Standard MCP Methods
- `initialize`: Initialize the connection and exchange capabilities
- `tools/list`: List available tools with pagination support
- `tools/call`: Execute a specific tool with provided arguments
- `resources/list`: List available resources with pagination support
- `resources/read`: Read content from a specific resource
- `prompts/list`: List available prompts with pagination support
- `prompts/get`: Get and resolve a specific prompt with arguments
- `shutdown`: Gracefully shut down the server
- `ping`: Health check with detailed status information

## Tools Capabilities

### Core Development Tools

#### `assign_task`
**Description**: Assign a development task to a team member or sub-agent

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "task_id": {"type": "string", "description": "Unique identifier for the task"},
    "task_description": {"type": "string", "description": "Detailed description of the task"},
    "assignee": {"type": "string", "description": "Team member or agent to assign the task to"},
    "priority": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium"},
    "deadline": {"type": "string", "description": "Deadline for the task in ISO format"}
  },
  "required": ["task_id", "task_description", "assignee"]
}
```

**Functionality**: Assigns a development task to a specified assignee with priority and deadline, storing the assignment in the task database.

#### `review_code`
**Description**: Review code submitted by team members

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "pull_request_id": {"type": "string", "description": "ID of the pull request to review"},
    "code_diff": {"type": "string", "description": "Code changes to review"},
    "reviewer": {"type": "string", "description": "Team member assigned to review"}
  },
  "required": ["pull_request_id", "code_diff"]
}
```

**Functionality**: Performs code review using LLM integration, providing feedback on code quality, potential bugs, security concerns, and suggestions for improvement.

#### `generate_project_plan`
**Description**: Generate a project plan based on requirements

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "requirements": {"type": "string", "description": "Project requirements"},
    "team_size": {"type": "integer", "description": "Number of team members", "default": 3},
    "timeline_weeks": {"type": "integer", "description": "Timeline in weeks", "default": 8}
  },
  "required": ["requirements"]
}
```

**Functionality**: Generates a comprehensive project plan including phases, milestones, task breakdown, resource allocation, risk assessment, and dependencies.

#### `analyze_architecture`
**Description**: Analyze software architecture and suggest improvements

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "current_architecture": {"type": "string", "description": "Current architecture description"},
    "requirements": {"type": "string", "description": "System requirements"},
    "constraints": {"type": "string", "description": "Technical or business constraints"}
  },
  "required": ["current_architecture", "requirements"]
}
```

**Functionality**: Analyzes software architecture using LLM integration, providing feedback on scalability, performance, security, maintainability, and technology choices.

#### `schedule_team_meeting`
**Description**: Schedule a team meeting to discuss project matters

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "meeting_type": {"type": "string", "enum": ["standup", "planning", "retrospective", "ad_hoc"], "default": "standup"},
    "attendees": {"type": "array", "items": {"type": "string"}, "description": "List of attendees"},
    "agenda": {"type": "string", "description": "Meeting agenda"},
    "datetime": {"type": "string", "description": "Meeting date and time in ISO format"}
  },
  "required": ["meeting_type", "attendees", "datetime"]
}
```

**Functionality**: Schedules team meetings with specified type, attendees, agenda, and date/time.

#### `track_task_progress`
**Description**: Track progress of assigned tasks

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "task_ids": {"type": "array", "items": {"type": "string"}, "description": "List of task IDs to track"},
    "include_details": {"type": "boolean", "default": false, "description": "Include detailed progress information"}
  },
  "required": ["task_ids"]
}
```

**Functionality**: Tracks and reports progress for specified tasks, including completion percentage and estimated completion time.

### Enhanced Strategic Planning Tools

#### `decompose_requirements`
**Description**: Decompose high-level requirements into actionable tasks

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "requirement_document": {"type": "string", "description": "High-level requirement document"},
    "project_context": {"type": "string", "description": "Project context and constraints"},
    "existing_artifacts": {"type": "array", "items": {"type": "string"}, "description": "Existing project artifacts"}
  },
  "required": ["requirement_document", "project_context"]
}
```

**Functionality**: Uses LLM to break down high-level requirements into specific, actionable tasks with effort estimates, priorities, required expertise, dependencies, and success criteria.

#### `sequence_sdlc_tasks`
**Description**: Organize tasks into SDLC phases with proper dependencies

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "tasks": {"type": "array", "items": {"$ref": "#/definitions/task"}, "description": "List of tasks to sequence"},
    "project_constraints": {"type": "object", "description": "Project timeline and resource constraints"},
    "phase_requirements": {"type": "object", "description": "Phase-specific requirements"}
  },
  "required": ["tasks"]
}
```

**Functionality**: Organizes tasks into SDLC phases (requirements, design, implementation, testing, deployment) considering dependencies and constraints.

#### `manage_dependencies`
**Description**: Manage and track dependencies between tasks

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "tasks": {"type": "array", "items": {"$ref": "#/definitions/task"}},
    "dependency_rules": {"type": "object", "description": "Rules for dependency management"}
  },
  "required": ["tasks"]
}
```

**Functionality**: Creates dependency graphs, identifies critical path, finds parallelization opportunities, and detects potential bottlenecks.

### Enhanced Assignment Tools

#### `balance_agent_load`
**Description**: Balance workload across available agents

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "task": {"$ref": "#/definitions/task"},
    "agent_pool": {"type": "array", "items": {"type": "string"}, "description": "Pool of available agents"},
    "load_balancing_strategy": {"type": "string", "enum": ["round_robin", "least_loaded", "capability_optimized"]}
  },
  "required": ["task", "agent_pool"]
}
```

**Functionality**: Distributes tasks across agents based on current workload, capacity, and skill matching using LLM optimization.

#### `match_agent_to_task`
**Description**: Match the most suitable agent to a specific task

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "task": {"$ref": "#/definitions/task"},
    "candidate_agents": {"type": "array", "items": {"type": "string"}, "description": "Candidate agent IDs"},
    "matching_strategy": {"type": "string", "enum": ["semantic", "llm_evaluated", "hybrid"]}
  },
  "required": ["task", "candidate_agents"]
}
```

**Functionality**: Matches tasks to agents based on skill requirements, domain expertise, and complexity appropriateness using LLM evaluation.

#### `check_agent_availability`
**Description**: Check real-time availability of an agent

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "agent_id": {"type": "string", "description": "ID of the agent to check"},
    "task_requirements": {"type": "object", "description": "Requirements for the task"}
  },
  "required": ["agent_id"]
}
```

**Functionality**: Verifies agent availability, current load, and capacity before assignment.

### Enhanced Quality Tools

#### `validate_output_against_criteria`
**Description**: Validate agent output against acceptance criteria

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "task_id": {"type": "string", "description": "ID of the task"},
    "output": {"type": "string", "description": "Output to validate"},
    "acceptance_criteria": {"type": "string", "description": "Acceptance criteria to validate against"},
    "quality_standards": {"type": "object", "description": "Quality standards to apply"}
  },
  "required": ["task_id", "output", "acceptance_criteria"]
}
```

**Functionality**: Validates outputs against acceptance criteria using LLM evaluation, providing pass/fail determination with detailed feedback.

### Enhanced Human Interface Tools

#### `escalate_to_human`
**Description**: Escalate decision to human operator

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "task_id": {"type": "string", "description": "ID of the task requiring escalation"},
    "reason": {"type": "string", "description": "Reason for escalation"},
    "context": {"type": "object", "description": "Context for the decision"},
    "options": {"type": "array", "items": {"type": "string"}, "description": "Available options for decision"}
  },
  "required": ["task_id", "reason", "context"]
}
```

**Functionality**: Prepares and sends escalation requests to human operators with context and decision options.

### Enhanced Orchestration Tools

#### `execute_workflow`
**Description**: Execute a defined workflow pattern

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "workflow_type": {"type": "string", "enum": ["sequential", "parallel", "iterative", "event_driven"]},
    "tasks": {"type": "array", "items": {"$ref": "#/definitions/task"}},
    "context": {"type": "object", "description": "Workflow execution context"}
  },
  "required": ["workflow_type", "tasks"]
}
```

**Functionality**: Executes workflows using different patterns (sequential, parallel, iterative, event-driven).

#### `process_event`
**Description**: Process an event and trigger appropriate responses

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "event_type": {"type": "string", "description": "Type of event"},
    "event_data": {"type": "object", "description": "Event-specific data"},
    "handlers": {"type": "array", "items": {"type": "string"}, "description": "Event handlers to trigger"}
  },
  "required": ["event_type", "event_data"]
}
```

**Functionality**: Processes system events and triggers appropriate responses from registered handlers.

#### `resolve_conflict`
**Description**: Resolve conflicts between agent outputs

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "outputs": {"type": "array", "items": {"type": "object"}, "description": "Conflicting outputs"},
    "context": {"type": "object", "description": "Context of the conflict"},
    "resolution_strategy": {"type": "string", "enum": ["majority", "expert", "compromise", "llm_mediated"]}
  },
  "required": ["outputs", "context"]
}
```

**Functionality**: Resolves conflicts between different agent outputs using LLM mediation.

### Registry Tools

#### `registry/register`
**Description**: Register a service with the MCP registry

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "id": {"type": "string", "description": "Unique identifier for the service"},
    "name": {"type": "string", "description": "Name of the service"},
    "description": {"type": "string", "description": "Description of the service"},
    "endpoint": {"type": "string", "description": "Endpoint URL for the service"},
    "capabilities": {
      "type": "object",
      "description": "Capabilities of the service",
      "properties": {
        "tools": {"type": "array", "items": {"type": "string"}},
        "resources": {"type": "array", "items": {"type": "string"}},
        "prompts": {"type": "array", "items": {"type": "string"}}
      }
    }
  },
  "required": ["id", "name", "description", "endpoint", "capabilities"]
}
```

**Functionality**: Registers services with the MCP registry for service discovery.

#### `registry/list`
**Description**: List all registered services in the MCP registry

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "filter": {"type": "string", "description": "Optional filter for services"}
  }
}
```

**Functionality**: Lists all registered services, optionally filtered by criteria.

#### `registry/unregister`
**Description**: Unregister a service from the MCP registry

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "id": {"type": "string", "description": "ID of the service to unregister"}
  },
  "required": ["id"]
}
```

**Functionality**: Removes a service from the MCP registry.

## Resources Capabilities

### Core Resources

#### `it-lead://resource/team-status`
**Name**: Team Status Report
**Description**: Current status of the development team

**Content Format**: JSON object containing:
- team_size: Number of team members
- active_projects: Count of active projects
- overall_velocity: Team velocity metric
- current_bottlenecks: List of current bottlenecks
- upcoming_milestones: List of upcoming milestones
- team_health: Overall team health status

#### `it-lead://resource/project-plan`
**Name**: Project Plan
**Description**: Current project plan and milestones

**Content Format**: JSON object containing:
- project_name: Name of the project
- start_date: Project start date
- end_date: Project end date
- milestones: Array of project milestones with dates and status
- team_allocation: Allocation of team members to roles

#### `it-lead://resource/architecture-document`
**Name**: Architecture Document
**Description**: Software architecture documentation

**Content Format**: JSON object containing:
- architecture_style: Architecture style (e.g., microservices)
- components: Array of system components with responsibilities
- data_store: Information about data storage systems
- deployment: Deployment infrastructure information

### Enhanced Resources

#### `it-lead://resource/strategic-plan`
**Name**: Strategic Plan
**Description**: Decomposed strategic plan with tasks and dependencies

**Content Format**: JSON object containing:
- plan_id: Unique identifier for the plan
- created_at: Timestamp of creation
- tasks: Array of tasks with details
- dependencies: Object mapping task dependencies
- timeline: Projected timeline information

#### `it-lead://resource/quality-dashboard`
**Name**: Quality Dashboard
**Description**: Real-time quality metrics dashboard

**Content Format**: JSON object containing:
- dashboard_id: Unique identifier for the dashboard
- created_at: Timestamp of creation
- metrics: Object containing quality metrics
- trends: Quality trend information

#### `it-lead://resource/progress-report`
**Name**: Progress Report
**Description**: Comprehensive project progress report

**Content Format**: JSON object containing:
- report_id: Unique identifier for the report
- created_at: Timestamp of creation
- project_status: Overall project status
- completed_tasks: Count of completed tasks
- in_progress_tasks: Count of in-progress tasks
- blocked_tasks: Count of blocked tasks
- upcoming_milestones: List of upcoming milestones

## Prompts Capabilities

### Core Prompts

#### `task_assignment_prompt`
**Description**: Prompt for assigning tasks to team members

**Arguments**:
- task_description: Description of the task to assign
- assignee: Team member or agent to assign the task to
- deadline: Deadline for the task

**Functionality**: Generates detailed instructions for assigned tasks including requirements, expectations, and guidelines.

#### `code_review_prompt`
**Description**: Prompt for conducting code reviews

**Arguments**:
- code_diff: Code changes to review
- review_guidelines: Guidelines for the code review

**Functionality**: Generates comprehensive code review instructions covering correctness, standards, performance, security, and documentation.

#### `architecture_advice_prompt`
**Description**: Prompt for providing architecture advice

**Arguments**:
- current_architecture: Current architecture description
- requirements: System requirements

**Functionality**: Generates architecture advice covering scalability, performance, security, and technology recommendations.

## Registry Integration

The IT Lead server automatically registers with the MCP registry server at startup and maintains its registration through periodic heartbeats. This enables service discovery by other MCP clients and servers.

### Registration Information
- Service ID: Generated based on host and port
- Service Name: Descriptive name indicating server location
- Capabilities: All available tools, resources, and prompts
- Endpoint: HTTP endpoint for communication

### Heartbeat Management
- Regular heartbeats to maintain registration
- Stale service detection (10-minute timeout)
- Automatic re-registration if needed

## LLM Integration

The IT Lead server integrates with external LLM providers for AI-powered decision making:

### Configuration
- **LLM Provider URL**: Configurable via `--llm-provider-url` parameter
- **Model Name**: Configurable via `--llm-model` parameter
- **Temperature**: Set to 0.7 for balanced creativity and coherence

### Usage Areas
- Code review generation
- Project plan creation
- Architecture analysis
- Requirements decomposition
- Agent assignment optimization
- Output validation
- Conflict resolution
- Escalation preparation

## Enhanced Capabilities

### Strategic Planning
- **Requirements Decomposition**: Breaks down high-level requirements into actionable tasks
- **SDLC Sequencing**: Organizes tasks into proper development phases
- **Dependency Management**: Tracks and manages task dependencies

### Advanced Assignment
- **Load Balancing**: Distributes tasks based on agent workload
- **Skill Matching**: Matches tasks to agents based on expertise
- **Availability Checking**: Verifies agent availability before assignment

### Quality Gates
- **Output Validation**: Validates outputs against acceptance criteria
- **Quality Metrics**: Tracks and reports quality metrics
- **Automated Enforcement**: Prevents progression without meeting quality standards

### Human Interface
- **Escalation Logic**: Automatically escalates complex decisions
- **Progress Reporting**: Generates comprehensive reports
- **Feedback Integration**: Incorporates human feedback

### Advanced Orchestration
- **Workflow Execution**: Supports multiple workflow patterns
- **Event Processing**: Handles system events appropriately
- **Conflict Resolution**: Mediates between conflicting outputs

## Configuration Options

### Server Configuration
- `--transport`: Transport mechanism (stdio, http, streamable-http) [default: streamable-http]
- `--host`: Host for HTTP transport [default: 127.0.0.1]
- `--port`: Port for HTTP transport [default: 3061]
- `--max-concurrent-requests`: Maximum concurrent requests [default: 10]

### Registry Configuration
- `--enable-registry`: Enable registry functionality [default: False]
- `--register-with-registry`: Register this server with a registry [default: True]
- `--registry-host`: Registry server host [default: 127.0.0.1]
- `--registry-port`: Registry server port [default: 3031]

### LLM Configuration
- `--llm-provider-url`: URL for the LLM provider [default: http://asus-tus:1234/v1/chat/completions]
- `--llm-model`: LLM model name [default: qwen3-4b]

### Database Configuration
- `--use-postgres`: Use PostgreSQL instead of SQLite [default: True]
- `--postgres-host`: PostgreSQL host [default: 127.0.0.1]
- `--postgres-port`: PostgreSQL port [default: 5432]
- `--postgres-db`: Database name [default: mcp_registry]
- `--postgres-user`: Database user [default: postgres]
- `--postgres-password`: Database password [default: empty]

## Usage Examples

### Starting the Server
```bash
./start_it_lead_server.sh --port 3061 --llm-provider-url http://asus-tus:1234/v1/chat/completions --llm-model qwen3-4b
```

### Using the assign_task Tool
```json
{
  "jsonrpc": "2.0",
  "id": "1",
  "method": "tools/call",
  "params": {
    "name": "assign_task",
    "arguments": {
      "task_id": "feature-auth-001",
      "task_description": "Implement user authentication system",
      "assignee": "backend-dev-team",
      "priority": "high",
      "deadline": "2023-12-31T23:59:59Z"
    }
  }
}
```

### Using the decompose_requirements Tool
```json
{
  "jsonrpc": "2.0",
  "id": "2",
  "method": "tools/call",
  "params": {
    "name": "decompose_requirements",
    "arguments": {
      "requirement_document": "Build a customer management system with CRUD operations",
      "project_context": "Small team, 4-week timeline, cloud deployment"
    }
  }
}
```

### Reading the Team Status Resource
```json
{
  "jsonrpc": "2.0",
  "id": "3",
  "method": "resources/read",
  "params": {
    "uri": "it-lead://resource/team-status"
  }
}
```

### Getting a Prompt
```json
{
  "jsonrpc": "2.0",
  "id": "4",
  "method": "prompts/get",
  "params": {
    "name": "task_assignment_prompt",
    "arguments": {
      "task_description": "Implement API endpoint for user login",
      "assignee": "John Doe",
      "deadline": "2023-11-15"
    }
  }
}
```

This comprehensive documentation covers all the functionality of the IT Lead MCP Server, including both the original capabilities and the enhanced features that transform it into a sophisticated leader/orchestrator agent for AI development teams.