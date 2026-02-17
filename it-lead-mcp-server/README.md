# IT Lead MCP Server

An AI agent serving as an IT lead for software development teams, accepting tasks via MCP endpoints and distributing subtasks to other agents.

## Overview

The IT Lead MCP Server is an AI-powered agent that acts as a technical lead for software development teams. It accepts development tasks via MCP (Model Context Protocol) endpoints and intelligently distributes subtasks to other specialized agents or team members.

## Features

- **Task Assignment**: Assign development tasks to team members or sub-agents with appropriate priority and deadlines
- **Code Review**: Perform automated code reviews using LLM integration
- **Project Planning**: Generate comprehensive project plans based on requirements
- **Architecture Analysis**: Analyze and suggest improvements to software architecture
- **Team Coordination**: Schedule meetings and track task progress
- **LLM Integration**: Integrated with LM Studio for AI-powered decision making
- **Registry Integration**: Automatically registers with MCP registry for service discovery
- **PostgreSQL Support**: Uses PostgreSQL for persistent storage of tasks and services

## Prerequisites

- Python 3.7+
- PostgreSQL (for registry functionality)
- LM Studio with qwen3-4b model running at http://asus-tus:1234/v1/chat/completions

## Installation

1. Clone the repository
2. Create a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```
3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

The server can be configured via command-line arguments:

- `--port`: Port to run the server on (default: 3061)
- `--llm-provider-url`: URL for the LLM provider (default: http://asus-tus:1234/v1/chat/completions)
- `--llm-model`: LLM model name (default: qwen3-4b)
- `--registry-host`: Registry server host (default: 127.0.0.1)
- `--registry-port`: Registry server port (default: 3031)

## Usage

### Starting the Server

Use the provided startup script:

```bash
./start_it_lead_server.sh --port 3061 --llm-provider-url http://asus-tus:1234/v1/chat/completions --llm-model qwen3-4b
```

### Available Tools

The IT Lead server provides the following tools:

1. **assign_task**: Assign a development task to a team member or sub-agent
2. **review_code**: Review code submitted by team members
3. **generate_project_plan**: Generate a project plan based on requirements
4. **analyze_architecture**: Analyze software architecture and suggest improvements
5. **schedule_team_meeting**: Schedule a team meeting to discuss project matters
6. **track_task_progress**: Track progress of assigned tasks
7. **coordinate_requirements_analysis**: Coordinate between stakeholder inputs and requirements engineer
8. **validate_requirements_completeness**: Validate completeness of requirements using requirements engineer capabilities
9. **sync_with_requirements_engineer**: Synchronize requirements with the requirements engineer agent
10. **fetch_requirements_specifications**: Fetch requirements specifications from requirements engineer
11. **submit_stakeholder_inputs**: Submit stakeholder inputs to requirements engineer for analysis
12. **validate_requirements_traceability**: Validate requirements traceability and completeness using requirements engineer capabilities
13. **coordinate_implementation_tasks**: Coordinate between architectural decisions and implementation engineer
14. **generate_code_from_specifications**: Generate code from architectural specifications using implementation engineer
15. **implement_feature_with_guidelines**: Implement specific features following architectural guidelines using implementation engineer
16. **apply_coding_standards_across_codebase**: Apply consistent coding standards and patterns to code using implementation engineer
17. **generate_unit_tests_for_code**: Generate unit tests for code following test-first approach using implementation engineer
18. **refactor_code_for_improvements**: Refactor code for maintainability and performance improvements using implementation engineer
19. **sync_with_implementation_engineer**: Synchronize implementation tasks with the implementation engineer agent
20. **fetch_implementation_artifacts**: Fetch implementation artifacts from implementation engineer

### Available Resources

1. **it-lead://resource/team-status**: Current status of the development team
2. **it-lead://resource/project-plan**: Current project plan and milestones
3. **it-lead://resource/architecture-document**: Software architecture documentation
4. **it-lead://resource/current-implementation-status**: Current status of implementation activities and progress
5. **it-lead://resource/code-quality-metrics**: Metrics and reports on code quality from implementation engineer
6. **it-lead://resource/implementation-artifact-traceability**: Traceability of implementation artifacts to requirements and design

### Available Prompts

1. **task_assignment_prompt**: Prompt for assigning tasks to team members
2. **code_review_prompt**: Prompt for conducting code reviews
3. **architecture_advice_prompt**: Prompt for providing architecture advice

## MCP Protocol Compliance

This server fully complies with the Model Context Protocol (MCP) specification:

- STDIO Transport: Standard input/output stream communication
- Streamable HTTP Transport: Modern single `/mcp` endpoint supporting both POST and GET methods
- Legacy HTTP/SSE Transport: Backward-compatible `/sse` and `/message` endpoints

## Registry Integration

The server automatically registers with the MCP registry server at startup and maintains its registration through periodic heartbeats. This enables service discovery by other MCP clients and servers.

## Architecture

The server follows a modular architecture with clear separation of concerns:

- **Transports**: Handle communication via stdio, HTTP/SSE, or Streamable HTTP
- **Handlers**: Process MCP requests and responses
- **Utils**: Provide common functionality like JSON-RPC handling and notifications
- **Registry**: Manage service registration and discovery

## License

MIT License