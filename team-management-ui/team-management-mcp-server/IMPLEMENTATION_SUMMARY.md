# Team Management MCP Server Implementation

## Overview
This implementation creates a specialized MCP (Model Context Protocol) server for team management functionality. It extends the standard MCP server skeleton with custom tools, resources, and prompts specifically designed for managing teams, tasks, and workflows.

## Architecture

### Core Components
1. **Team Management Server** - Main server implementation extending the base MCP server
2. **Team Management Handlers** - Custom handlers for team management functionality
3. **Web Application** - Frontend UI for human interaction
4. **MCP Integration** - Backend API accessible via MCP protocol

### Technology Stack
- **Backend**: Python-based MCP server using FastAPI
- **Frontend**: HTML/CSS/JavaScript for web UI
- **Protocol**: Model Context Protocol (MCP) for AI agent integration
- **Database**: PostgreSQL (with fallback to SQLite) for persistence

## Features Implemented

### Task Management
- Create, update, delete, and list tasks
- Assign tasks to team members
- Set due dates, priorities, and tags
- Filter tasks by status, assignee, or priority

### Team Management
- Create, update, and manage team member profiles
- Track skills, roles, and availability
- Check member availability for specific periods

### Queues and Workflows
- View task queues by status (To Do, In Progress, Review, Done)
- Track team workload and capacity
- Monitor task progress and status

### Dashboard
- Overview of team metrics
- Task completion statistics
- Upcoming deadlines and overdue tasks

## MCP Tools Available

### Task Management Tools
- `team_management/create_task` - Create a new task and assign it to a team member
- `team_management/update_task` - Update an existing task
- `team_management/delete_task` - Delete a task
- `team_management/list_tasks` - List all tasks with filtering options
- `team_management/get_task` - Get details of a specific task

### Team Management Tools
- `team_management/create_team_member` - Create a new team member profile
- `team_management/update_team_member` - Update a team member profile
- `team_management/list_team_members` - List all team members
- `team_management/get_team_member` - Get details of a specific team member
- `team_management/check_member_availability` - Check availability of a team member

### Queue and Reporting Tools
- `team_management/get_team_queues` - Get task queues for the entire team

### Resources
- `team-management://resource/tasks` - All team tasks
- `team-management://resource/team-members` - All team member profiles
- `team-management://resource/dashboard-data` - Dashboard metrics

### Prompts
- `team_management/task_summary_prompt` - Generate task summaries
- `team_management/availability_report_prompt` - Generate availability reports

## Configuration

### Server Configuration
- **Port**: 3063 (default)
- **Transport**: Streamable HTTP (default)
- **Registry**: Automatically registers with existing registry at localhost:3031
- **Database**: Supports both SQLite (default) and PostgreSQL

### Environment Variables
- `PORT`: Server port (default: 3063)
- `ENABLE_REGISTRY`: Enable registry functionality (default: false)
- `REGISTER_WITH_REGISTRY`: Register with external registry (default: true)
- `REGISTRY_HOST`: Registry server host (default: 127.0.0.1)
- `REGISTRY_PORT`: Registry server port (default: 3031)
- `USE_POSTGRES`: Use PostgreSQL instead of SQLite (default: false)

## Startup Scripts

### Starting the System
```bash
./start_system.sh
```
This starts both the MCP server and the web UI.

### Stopping the System
```bash
./stop_system.sh
```
This stops both the MCP server and the web UI.

### Starting Just the MCP Server
```bash
./start_team_management_server.sh
```

### Stopping Just the MCP Server
```bash
./stop_team_management_server.sh
```

## Web Interface
- **URL**: http://localhost:3000
- **Features**: Dashboard, task management, team management, queues view
- **Technology**: HTML/CSS/JavaScript with simulated backend

## MCP Server
- **URL**: http://localhost:3063/mcp
- **Protocol**: Model Context Protocol (MCP)
- **Transport**: Streamable HTTP
- **Functionality**: AI agent integration for team management tasks

## Testing
Run the AI agent simulation tests:
```bash
./test_team_management_ai_agent.sh
```

## Integration with Existing System
- The server automatically registers with the existing MCP registry at port 3031
- Compatible with other MCP servers in the ecosystem
- Follows MCP specification standards

## Database Configuration
The server supports both SQLite (default) and PostgreSQL for data persistence:
- SQLite: Uses local file `mcp_registry.db`
- PostgreSQL: Configurable via environment variables

## Security Considerations
- MCP protocol follows standard security practices
- Input validation for all tool parameters
- No authentication implemented (to be added based on requirements)
- Communication over HTTP (TLS/SSL to be implemented if needed)

## Future Enhancements
- Real database integration instead of mock data
- Authentication and authorization
- Real-time updates via WebSocket
- Advanced reporting and analytics
- Integration with external tools and services
- Enhanced UI with React or similar framework