# IT Lead Agent - Details for Human Stakeholders

## Overview
The IT Lead Agent serves as the primary interface between human stakeholders and the AI development team. It manages the entire software development lifecycle by coordinating specialized AI agents, tracking progress, ensuring quality, and providing transparent reporting to human stakeholders. The IT Lead translates business requirements into technical tasks, assigns work to specialized agents, and maintains visibility into all development activities.

## Core Capabilities

### 1. Project Management and Coordination
- **Primary Function**: Manage the complete software development lifecycle from requirements to deployment
- **Implementation**: Coordinates specialized AI agents (Requirements Engineer, Implementation Engineer, Code Reviewer, etc.) to execute development tasks
- **Output**: Delivered software features that meet business requirements and quality standards

### 2. Requirements Translation and Planning
- **Primary Function**: Transform business requirements into actionable development tasks
- **Implementation**: Works with Requirements Engineer Agent to decompose requirements and create project plans
- **Output**: Structured development tasks with timelines, dependencies, and success criteria

### 3. Quality Assurance and Gatekeeping
- **Primary Function**: Ensure all deliverables meet quality standards before proceeding
- **Implementation**: Coordinates with Code Reviewer, Security Engineer, and QA/Test Engineer agents to validate all work
- **Output**: Quality-gated deliverables that meet security, performance, and reliability standards

### 4. Progress Tracking and Reporting
- **Primary Function**: Provide real-time visibility into development progress and metrics
- **Implementation**: Aggregates status from all specialized agents and generates comprehensive reports
- **Output**: Executive dashboards, progress reports, and risk assessments

### 5. Human Interface and Escalation
- **Primary Function**: Serve as the primary point of contact for human stakeholders
- **Implementation**: Manages approval workflows, handles escalations, and provides interfaces for human input
- **Output**: Human decisions incorporated into development workflow

## MCP Endpoints Available to Human Stakeholders

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

## Available Tools for Human Stakeholders

### 1. `request_human_approval`
**Description**: Request approval from human stakeholders for critical decisions

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "approval_type": {"type": "string", "enum": ["code", "architecture", "deployment", "requirement", "security"], "description": "Type of approval needed"},
    "request_title": {"type": "string", "description": "Title of the approval request"},
    "request_context": {"type": "string", "description": "Context and background for the decision"},
    "options": {"type": "array", "items": {"type": "object"}, "description": "Available options for the decision"},
    "urgency": {"type": "string", "enum": ["low", "medium", "high", "critical"], "default": "medium", "description": "Urgency level of the request"},
    "required_approver_roles": {"type": "array", "items": {"type": "string"}, "description": "Roles required to approve this request"}
  },
  "required": ["approval_type", "request_title", "request_context", "options"]
}
```

**Usage**: Call this when critical decisions require human approval, such as architectural changes, security considerations, or production deployments. The IT Lead will provide all necessary context and options for informed decision-making.

### 2. `submit_requirement_input`
**Description**: Submit requirements from human stakeholders to the system

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "requirement_type": {"type": "string", "enum": ["functional", "non_functional", "security", "performance"], "description": "Type of requirement"},
    "requirement_text": {"type": "string", "description": "Text of the requirement"},
    "priority": {"type": "string", "enum": ["critical", "high", "medium", "low"], "default": "medium", "description": "Priority of the requirement"},
    "acceptance_criteria": {"type": "array", "items": {"type": "string"}, "description": "Acceptance criteria for the requirement"},
    "attachments": {"type": "array", "items": {"type": "string"}, "description": "Attached documents or files"},
    "stakeholder_context": {"type": "string", "description": "Context from the stakeholder perspective"}
  },
  "required": ["requirement_text", "requirement_type"]
}
```

**Usage**: Use this to submit business requirements directly to the system. The IT Lead will coordinate with the Requirements Engineer Agent to formalize and validate these requirements.

### 3. `provide_feedback`
**Description**: Provide feedback to AI agents on their work

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "feedback_target": {"type": "string", "enum": ["code", "documentation", "architecture", "test", "process"], "description": "What the feedback is about"},
    "feedback_type": {"type": "string", "enum": ["positive", "constructive", "critical", "suggestion"], "description": "Type of feedback"},
    "feedback_content": {"type": "string", "description": "Content of the feedback"},
    "target_reference": {"type": "string", "description": "Reference to the specific item being commented on"},
    "suggested_improvement": {"type": "string", "description": "Suggested improvements or changes"},
    "priority": {"type": "string", "enum": ["low", "medium", "high"], "default": "medium", "description": "Priority of the feedback"}
  },
  "required": ["feedback_target", "feedback_content"]
}
```

**Usage**: Use this to provide feedback on any aspect of the development process. The IT Lead will route your feedback to the appropriate AI agents for action.

### 4. `view_project_dashboard`
**Description**: Retrieve project status and metrics for human dashboard

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "dashboard_view": {"type": "string", "enum": ["executive", "manager", "technical", "quality"], "default": "manager", "description": "Type of dashboard view requested"},
    "time_range": {"type": "string", "enum": ["week", "month", "quarter", "custom"], "default": "week", "description": "Time range for metrics"},
    "project_filters": {"type": "array", "items": {"type": "string"}, "description": "Filters for specific projects or teams"},
    "custom_metrics": {"type": "array", "items": {"type": "string"}, "description": "Additional custom metrics to include"}
  }
}
```

**Usage**: Use this to get real-time project status and metrics tailored to your role and interests. The IT Lead aggregates data from all specialized agents to provide comprehensive visibility.

### 5. `assign_task`
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

**Usage**: Use this to assign specific tasks to team members or specialized agents. The IT Lead will ensure proper assignment based on skills and availability.

### 6. `review_code`
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

**Usage**: Request code reviews for specific changes. The IT Lead coordinates with the Code Reviewer Agent to provide comprehensive feedback.

### 7. `generate_project_plan`
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

**Usage**: Generate comprehensive project plans based on your requirements. The IT Lead works with the Requirements Engineer and other agents to create realistic timelines and resource allocations.

### 8. `analyze_architecture`
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

**Usage**: Request architecture analysis and recommendations. The IT Lead coordinates with the Software Architect Agent to provide expert insights.

### 9. `schedule_team_meeting`
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

**Usage**: Schedule meetings with team members or AI agents. The IT Lead helps coordinate schedules and prepare agendas.

### 10. `track_task_progress`
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

**Usage**: Monitor the progress of specific tasks. The IT Lead aggregates progress data from all specialized agents.

### 11. `coordinate_implementation_tasks`
**Description**: Coordinate between architectural decisions and implementation engineer

**Input Schema**:
```json
{
  "type": "object",
  "properties": {
    "architectural_decisions": {"type": "string", "description": "Architectural decisions requiring implementation"},
    "implementation_requirements": {"type": "string", "description": "Specific requirements for implementation"},
    "project_context": {"type": "string", "description": "Project context and constraints"},
    "existing_artifacts": {"type": "array", "items": {"type": "string"}, "description": "Existing project artifacts"}
  },
  "required": ["architectural_decisions", "implementation_requirements", "project_context"]
}
```

**Usage**: Coordinate implementation activities based on architectural decisions. The IT Lead works with the Implementation Engineer Agent to turn designs into code.

### 12. `generate_code_from_specifications`
**Description**: Generate code from architectural specifications using implementation engineer

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

**Usage**: Generate code directly from specifications. The IT Lead coordinates with the Implementation Engineer Agent to produce production-ready code.

## Available Resources for Human Stakeholders

### 1. `it-lead://resource/team-status`
**Description**: Current status of the development team

**Usage**: Access real-time information about team capacity, current assignments, and availability. Includes information about which specialized agents are active and their current workload.

### 2. `it-lead://resource/project-plan`
**Description**: Current project plan and milestones

**Usage**: Retrieve the current project plan including phases, milestones, task breakdown, resource allocation, risk assessment, and dependencies. Updated continuously as the project progresses.

### 3. `it-lead://resource/architecture-document`
**Description**: Software architecture documentation

**Usage**: Access current architecture documentation including system components, data flows, technology stack, and design decisions. Updated as architecture evolves.

### 4. `it-lead://resource/current-implementation-status`
**Description**: Current status of implementation activities and progress

**Usage**: Track implementation progress including features completed, code generated, tests written, and refactoring tasks. Provides visibility into the development pipeline.

### 5. `it-lead://resource/code-quality-metrics`
**Description**: Metrics and reports on code quality from implementation engineer

**Usage**: Monitor code quality metrics including test coverage, complexity, duplication, maintainability index, and security vulnerabilities. Helps ensure quality standards are maintained.

### 6. `it-lead://resource/implementation-artifact-traceability`
**Description**: Traceability of implementation artifacts to requirements and design

**Usage**: Track how implementation artifacts connect to requirements and design elements. Ensures alignment between business needs and technical implementation.

## Available Prompts for Human Stakeholders

### 1. `task_assignment_prompt`
**Description**: Prompt for assigning tasks to team members

**Arguments**:
- `task_description` (string): Description of the task to assign
- `assignee` (string): Team member or agent to assign the task to
- `deadline` (string): Deadline for the task

**Usage**: Get a structured prompt for task assignment when you need to guide the assignment process.

### 2. `code_review_prompt`
**Description**: Prompt for conducting code reviews

**Arguments**:
- `code_diff` (string): Code changes to review
- `review_guidelines` (string): Guidelines for the code review

**Usage**: Get a structured prompt for code reviews when you need to guide the review process.

### 3. `architecture_advice_prompt`
**Description**: Prompt for providing architecture advice

**Arguments**:
- `current_architecture` (string): Current architecture description
- `requirements` (string): System requirements

**Usage**: Get a structured prompt for architecture advice when you need to guide architectural decisions.

## Integration with Human Stakeholder Workflows

### For Requirement Input Phase
1. Use `submit_requirement_input` to provide business requirements
2. IT Lead coordinates with Requirements Engineer Agent to formalize requirements
3. Access results via `it-lead://resource/project-plan`

### For Project Oversight Phase
1. Use `view_project_dashboard` to monitor project status
2. Access detailed metrics via `it-lead://resource/code-quality-metrics`
3. Use `track_task_progress` to monitor specific tasks

### For Approval and Decision Phase
1. Use `request_human_approval` for critical decisions requiring human input
2. Provide feedback using `provide_feedback` to guide AI agents
3. Access implementation status via `it-lead://resource/current-implementation-status`

### For Quality Assurance Phase
1. Monitor quality metrics via `it-lead://resource/code-quality-metrics`
2. Request code reviews using `review_code`
3. Track traceability via `it-lead://resource/implementation-artifact-traceability`

## Health and Status
Use the `ping` method to check IT Lead health. The server will return a timestamp and status indicating its operational state along with health details for connected services.

## Communication with Specialized AI Agents
The IT Lead coordinates with the following specialized agents:
- Requirements Engineer Agent: For requirements analysis and validation
- Implementation Engineer Agent: For code generation and feature implementation
- Code Reviewer Agent: For code quality assurance
- Security Engineer Agent: For security analysis and compliance
- QA/Test Engineer Agent: For testing and quality validation
- Software Architect Agent: For architectural decisions and design
- DevOps/Release Engineer Agent: For deployment and infrastructure
- Technical Writer Agent: For documentation generation

The IT Lead serves as your primary interface to this AI team, providing unified access to all development capabilities while maintaining transparency and control for human stakeholders.