# MCP Agent Web UI Documentation

## Overview
The MCP Agent Web UI provides a user-friendly interface for human stakeholders to interact with the virtual team of MCP agents. The UI allows stakeholders to monitor agent status, assign tasks, request approvals, submit requirements, provide feedback, and view project dashboards.

## Architecture
The application follows a microservices architecture with:
- **Frontend**: React-based UI served via Vite development server
- **Backend**: FastAPI server acting as an intermediary between the UI and MCP agents
- **MCP Agents**: Various specialized agents (IT Lead, Requirements Engineer, Implementation Engineer, etc.)

## Features

### 1. Dashboard
- Real-time overview of agent statuses
- Active and completed task statistics
- Quick access to team members and tasks

### 2. Team Management
- View all team members and their current status
- See agent capabilities and last seen times
- Access detailed agent information

### 3. Task Management
- View all tasks with their status, assignee, and priority
- Create new tasks and assign them to agents
- Track task progress in real-time

### 4. IT Lead Functions
- Request human approvals for critical decisions
- Submit requirements to the system
- Provide feedback to agents
- View project dashboards

## Deployment

### Prerequisites
- Python 3.8+
- Node.js 16+
- The MCP agents must be running and accessible

### Ports Used
- IT Lead MCP Agent: Port 3061
- Web UI Backend: Port 8000
- Web UI Frontend: Port 5173

### Backend Setup
1. Navigate to the backend directory:
   ```bash
   cd /root/qwen/base/it-lead-mcp-server/web-ui/backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Start the backend server:
   ```bash
   uvicorn main:app --host 0.0.0.0 --port 8000
   ```

### Frontend Setup
1. Navigate to the frontend directory:
   ```bash
   cd /root/qwen/base/it-lead-mcp-server/web-ui/frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

3. Start the development server:
   ```bash
   npm run dev
   ```

The frontend will be available at http://localhost:5173

### Configuration
The backend connects to MCP agents using predefined URLs. To configure agent connections, modify the `AGENT_CONFIGS` dictionary in `main.py`:

```python
AGENT_CONFIGS = {
    "IT Lead": {
        "url": "http://localhost:3061",  # Update with actual IT Lead server URL
        "connected": True
    },
    "Requirements Engineer": {
        "url": "http://localhost:3062",  # Update with actual Requirements Engineer server URL
        "connected": False
    },
    # ... other agents
}
```

## API Endpoints

### Backend API
- `GET /` - Health check
- `GET /api/agents` - Get all agents and their status
- `GET /api/agents/{agent_name}` - Get specific agent details
- `POST /api/agents/{agent_name}/refresh` - Manually refresh agent status
- `POST /api/tasks/assign` - Assign a task to an agent
- `POST /api/tasks/update` - Update task status
- `GET /api/tasks` - Get all tasks
- `POST /api/approvals/request` - Request human approval
- `POST /api/requirements/submit` - Submit requirements
- `POST /api/feedback/provide` - Provide feedback
- `POST /api/dashboard/view` - Get project dashboard data
- `WS /ws` - WebSocket endpoint for real-time updates

### Frontend Routes
- `/` - Dashboard
- `/team` - Team member management
- `/tasks` - Task management
- `/it-lead` - IT Lead specific functions
- `/agent/:agentName` - Individual agent details

## Development

### Running in Development Mode
Both frontend and backend should be started separately during development:

Backend:
```bash
cd /root/qwen/base/it-lead-mcp-server/web-ui/backend
source venv/bin/activate
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

Frontend:
```bash
cd /root/qwen/base/it-lead-mcp-server/web-ui/frontend
npm run dev
```

### Adding New Agent Types
To add a new agent type:
1. Add the agent to the `AGENT_CONFIGS` dictionary in the backend
2. The system will automatically detect and manage the new agent

### Extending Functionality
New features can be added by:
1. Creating new API endpoints in the backend
2. Creating new React components in the frontend
3. Updating the routing in `App.jsx`

## Troubleshooting

### Common Issues
1. **Agent not showing as online**: Verify the agent is running and accessible at the configured URL
2. **WebSocket connection fails**: Check that the backend is running and accessible
3. **Task assignment fails**: Ensure the target agent is online and supports the required tools

### Debugging
Enable debug logging by changing the log level in `main.py`:
```python
logging.basicConfig(level=logging.DEBUG)  # Change from INFO to DEBUG
```

## Security Considerations
- The application currently has no authentication/authorization
- In production, implement proper authentication for sensitive operations
- Validate and sanitize all inputs before sending to MCP agents
- Use HTTPS in production deployments

## Startup Scripts

Two convenience scripts are provided to manage the application:

### Starting the Application
```bash
./start_web_ui.sh
```

The script accepts the following options:
- `--backend-host`: Host for backend server (default: 0.0.0.0)
- `--backend-port`: Port for backend server (default: 8000)
- `--frontend-port`: Port for frontend server (default: 5173)
- `--it-lead-host`: Host for IT Lead server (default: localhost)
- `--it-lead-port`: Port for IT Lead server (default: 3061)

### Stopping the Application
```bash
./stop_web_ui.sh
```

This will gracefully stop both the frontend and backend servers.

## Scaling
- For production use, consider using a process manager like PM2 for the backend
- Implement caching for agent status information
- Add load balancing if serving many concurrent users