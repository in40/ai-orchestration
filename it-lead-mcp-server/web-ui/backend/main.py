"""
Backend API service for MCP Agent Web UI
This service acts as a simple proxy to the IT Lead MCP server
"""

import asyncio
import json
import logging
from enum import Enum
from typing import Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import BaseModel
import httpx
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global variable to hold agent status - now fetched from IT Lead server
agent_status: Dict[str, Dict] = {}

# IT Lead server configuration
IT_LEAD_HOST = "localhost"
IT_LEAD_PORT = 3061

# Store active WebSocket connections for real-time updates
active_connections: List[WebSocket] = []

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Initialize by fetching agent status from IT Lead server"""
    global agent_status
    await refresh_agent_status_from_it_lead()
    logger.info(f"Initialized with {len(agent_status)} agents from IT Lead server")
    yield
    # Cleanup on shutdown


app = FastAPI(title="MCP Agent Web UI Backend", version="1.0.0", lifespan=lifespan)

class AgentInfo(BaseModel):
    name: str
    status: str
    last_seen: str
    capabilities: List[str]
    uptime: Optional[str] = None
    version: Optional[str] = None

class TaskAssignment(BaseModel):
    task_id: str
    title: str
    description: str
    assignee: str
    priority: str
    due_date: Optional[str] = None
    context: Optional[str] = None

class TaskStatusUpdate(BaseModel):
    task_id: str
    status: str
    progress: int
    notes: Optional[str] = None

class ApprovalType(str, Enum):
    code = "code"
    architecture = "architecture"
    deployment = "deployment"
    requirement = "requirement"
    security = "security"

class ApprovalRequest(BaseModel):
    approval_type: ApprovalType
    request_title: str
    request_context: str
    options: List[dict]
    urgency: str = "medium"
    required_approver_roles: List[str] = []

class RequirementType(str, Enum):
    functional = "functional"
    non_functional = "non_functional"
    security = "security"
    performance = "performance"

class RequirementInput(BaseModel):
    requirement_type: RequirementType
    requirement_text: str
    priority: str = "medium"
    acceptance_criteria: List[str] = []
    attachments: List[str] = []
    stakeholder_context: str = ""

class FeedbackTarget(str, Enum):
    code = "code"
    documentation = "documentation"
    architecture = "architecture"
    test = "test"
    process = "process"

class FeedbackType(str, Enum):
    positive = "positive"
    constructive = "constructive"
    critical = "critical"
    suggestion = "suggestion"

class Feedback(BaseModel):
    feedback_target: FeedbackTarget
    feedback_type: FeedbackType
    feedback_content: str
    target_reference: str = ""
    suggested_improvement: str = ""
    priority: str = "medium"

class DashboardView(str, Enum):
    executive = "executive"
    manager = "manager"
    technical = "technical"
    quality = "quality"

class ProjectDashboardRequest(BaseModel):
    dashboard_view: DashboardView = DashboardView.manager
    time_range: str = "week"
    project_filters: List[str] = []
    custom_metrics: List[str] = []

async def refresh_agent_status_from_it_lead():
    """Fetch agent status from the registry server directly"""
    global agent_status
    try:
        # Call the registry server directly to get the list of services
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Call the registry server directly (assuming it's on port 3031)
            registry_response = await client.post(
                f"http://127.0.0.1:3031/mcp",  # Registry server address
                json={
                    "jsonrpc": "2.0",
                    "id": "list_services",
                    "method": "registry/list",
                    "params": {}
                }
            )

            if registry_response.status_code == 200:
                response_data = registry_response.json()
                logger.info(f"Raw response from registry: {response_data}")

                if "result" in response_data and "services" in response_data["result"]:
                    services = response_data["result"]["services"]
                    
                    # Define the mapping from service names to agent roles
                    agent_mapping = {
                        "requirement": "Requirements Engineer",
                        "requirements": "Requirements Engineer",
                        "implementation": "Implementation Engineer",
                        "team management": "Implementation Engineer",
                        "team_management": "Implementation Engineer",
                        "team-management": "Implementation Engineer"
                    }
                    
                    # Initialize default agent status
                    agent_status = {
                        "IT Lead": {
                            "name": "IT Lead",
                            "status": "online",  # IT Lead is this server, so it's always online
                            "last_seen": datetime.utcnow().isoformat(),
                            "capabilities": ["assign_task", "review_code", "generate_project_plan"],
                            "uptime": "N/A",
                            "version": "N/A",
                            "url": f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp"
                        },
                        "Requirements Engineer": {
                            "name": "Requirements Engineer",
                            "status": "offline",
                            "last_seen": datetime.utcnow().isoformat(),
                            "capabilities": ["analyze_requirements", "validate_requirements"],
                            "uptime": "N/A",
                            "version": "N/A",
                            "url": "N/A"
                        },
                        "Implementation Engineer": {
                            "name": "Implementation Engineer",
                            "status": "offline",
                            "last_seen": datetime.utcnow().isoformat(),
                            "capabilities": ["implement_feature", "generate_code"],
                            "uptime": "N/A",
                            "version": "N/A",
                            "url": "N/A"
                        }
                    }
                    
                    # Process each service and update agent status
                    for service in services:
                        service_name = service.get("name", "").lower()
                        
                        # Find the matching agent role
                        matched_role = None
                        for keyword, role in agent_mapping.items():
                            if keyword in service_name:
                                matched_role = role
                                break
                        
                        # If we found a matching role, update its status to online
                        if matched_role and matched_role in agent_status:
                            agent_status[matched_role] = {
                                "name": matched_role,
                                "status": "online",
                                "last_seen": datetime.utcnow().isoformat(),
                                "capabilities": service.get("capabilities", {}).get("tools", []),
                                "uptime": "N/A",
                                "version": "N/A",
                                "url": service.get("endpoint", "N/A")
                            }
                    
                    logger.info(f"Updated agent status from registry: {agent_status}")
                else:
                    logger.warning("Registry response doesn't contain expected structure")
                    # Fall back to default status if registry response is malformed
                    agent_status = {
                        "IT Lead": {
                            "name": "IT Lead",
                            "status": "online",
                            "last_seen": datetime.utcnow().isoformat(),
                            "capabilities": ["assign_task", "review_code", "generate_project_plan"],
                            "uptime": "N/A",
                            "version": "N/A",
                            "url": f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp"
                        },
                        "Requirements Engineer": {
                            "name": "Requirements Engineer",
                            "status": "offline",
                            "last_seen": datetime.utcnow().isoformat(),
                            "capabilities": ["analyze_requirements", "validate_requirements"],
                            "uptime": "N/A",
                            "version": "N/A",
                            "url": "N/A"
                        },
                        "Implementation Engineer": {
                            "name": "Implementation Engineer",
                            "status": "offline",
                            "last_seen": datetime.utcnow().isoformat(),
                            "capabilities": ["implement_feature", "generate_code"],
                            "uptime": "N/A",
                            "version": "N/A",
                            "url": "N/A"
                        }
                    }
            else:
                logger.error(f"Failed to fetch services from registry: {registry_response.status_code}")
                logger.error(f"Response: {registry_response.text}")
                # Fall back to default status if registry call fails
                agent_status = {
                    "IT Lead": {
                        "name": "IT Lead",
                        "status": "online",
                        "last_seen": datetime.utcnow().isoformat(),
                        "capabilities": ["assign_task", "review_code", "generate_project_plan"],
                        "uptime": "N/A",
                        "version": "N/A",
                        "url": f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp"
                    },
                    "Requirements Engineer": {
                        "name": "Requirements Engineer",
                        "status": "offline",
                        "last_seen": datetime.utcnow().isoformat(),
                        "capabilities": ["analyze_requirements", "validate_requirements"],
                        "uptime": "N/A",
                        "version": "N/A",
                        "url": "N/A"
                    },
                    "Implementation Engineer": {
                        "name": "Implementation Engineer",
                        "status": "offline",
                        "last_seen": datetime.utcnow().isoformat(),
                        "capabilities": ["implement_feature", "generate_code"],
                        "uptime": "N/A",
                        "version": "N/A",
                        "url": "N/A"
                    }
                }

    except httpx.RequestError as e:
        logger.error(f"Error connecting to registry server: {str(e)}")
        # Fall back to default status if there's a connection error
        agent_status = {
            "IT Lead": {
                "name": "IT Lead",
                "status": "online",
                "last_seen": datetime.utcnow().isoformat(),
                "capabilities": ["assign_task", "review_code", "generate_project_plan"],
                "uptime": "N/A",
                "version": "N/A",
                "url": f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp"
            },
            "Requirements Engineer": {
                "name": "Requirements Engineer",
                "status": "offline",
                "last_seen": datetime.utcnow().isoformat(),
                "capabilities": ["analyze_requirements", "validate_requirements"],
                "uptime": "N/A",
                "version": "N/A",
                "url": "N/A"
            },
            "Implementation Engineer": {
                "name": "Implementation Engineer",
                "status": "offline",
                "last_seen": datetime.utcnow().isoformat(),
                "capabilities": ["implement_feature", "generate_code"],
                "uptime": "N/A",
                "version": "N/A",
                "url": "N/A"
            }
        }
    except Exception as e:
        logger.error(f"Unexpected error fetching agents from registry: {str(e)}")
        # Fall back to default status if there's an unexpected error
        agent_status = {
            "IT Lead": {
                "name": "IT Lead",
                "status": "online",
                "last_seen": datetime.utcnow().isoformat(),
                "capabilities": ["assign_task", "review_code", "generate_project_plan"],
                "uptime": "N/A",
                "version": "N/A",
                "url": f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp"
            },
            "Requirements Engineer": {
                "name": "Requirements Engineer",
                "status": "offline",
                "last_seen": datetime.utcnow().isoformat(),
                "capabilities": ["analyze_requirements", "validate_requirements"],
                "uptime": "N/A",
                "version": "N/A",
                "url": "N/A"
            },
            "Implementation Engineer": {
                "name": "Implementation Engineer",
                "status": "offline",
                "last_seen": datetime.utcnow().isoformat(),
                "capabilities": ["implement_feature", "generate_code"],
                "uptime": "N/A",
                "version": "N/A",
                "url": "N/A"
            }
        }

async def broadcast_message(message: dict):
    """Broadcast message to all active WebSocket connections"""
    for connection in active_connections[:]:  # Copy list to prevent modification during iteration
        try:
            await connection.send_text(json.dumps(message))
        except WebSocketDisconnect:
            active_connections.remove(connection)

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """Handle WebSocket connections for real-time updates"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        while True:
            # Listen for messages from client
            data = await websocket.receive_text()
            message = json.loads(data)
            
            # Process different types of messages
            if message.get("type") == "get_agents":
                # Refresh agent status from IT Lead server
                await refresh_agent_status_from_it_lead()
                await websocket.send_text(json.dumps({"type": "agent_list", "data": list(agent_status.values())}))
            elif message.get("type") == "get_agent_detail":
                agent_name = message.get("agent_name")
                if agent_name in agent_status:
                    await websocket.send_text(json.dumps({
                        "type": "agent_detail", 
                        "data": agent_status[agent_name]
                    }))
            elif message.get("type") == "refresh_agent_status":
                await refresh_agent_status_from_it_lead()
                agent_name = message.get("agent_name")
                if agent_name and agent_name in agent_status:
                    await websocket.send_text(json.dumps({
                        "type": "agent_detail", 
                        "data": agent_status[agent_name]
                    }))
                else:
                    await websocket.send_text(json.dumps({"type": "agent_list", "data": list(agent_status.values())}))
            elif message.get("type") == "assign_task":
                task_data = message.get("task_data")
                # Process task assignment via IT Lead
                await handle_task_assignment_via_it_lead(task_data)
                # Broadcast update to all clients
                await broadcast_message({
                    "type": "task_assigned",
                    "data": task_data
                })
            elif message.get("type") == "request_human_approval":
                approval_data = message.get("approval_data")
                # Process approval request via IT Lead
                await handle_approval_request_via_it_lead(approval_data)
                # Broadcast update to all clients
                await broadcast_message({
                    "type": "approval_requested",
                    "data": approval_data
                })
            elif message.get("type") == "submit_requirement_input":
                requirement_data = message.get("requirement_data")
                # Process requirement submission via IT Lead
                await handle_requirement_submission_via_it_lead(requirement_data)
                # Broadcast update to all clients
                await broadcast_message({
                    "type": "requirement_submitted",
                    "data": requirement_data
                })
            elif message.get("type") == "provide_feedback":
                feedback_data = message.get("feedback_data")
                # Process feedback via IT Lead
                await handle_feedback_via_it_lead(feedback_data)
                # Broadcast update to all clients
                await broadcast_message({
                    "type": "feedback_provided",
                    "data": feedback_data
                })
            else:
                # Echo back unknown message types
                await websocket.send_text(json.dumps({"type": "error", "message": "Unknown message type"}))
    except WebSocketDisconnect:
        active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected")

async def handle_task_assignment_via_it_lead(task_data: dict):
    """Handle task assignment by calling IT Lead server"""
    logger.info(f"Assigning task via IT Lead: {task_data}")

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Submit the task directly to the IT Lead for coordination
            # The IT Lead will decide how to process and distribute the task
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "assign_task",
                    "method": "tools/call",
                    "params": {
                        "name": "assign_task",  # Submit directly to IT Lead
                        "arguments": {
                            "task_id": task_data.get("task_id"),
                            "task_description": task_data.get("description"),
                            "assignee": task_data.get("assignee"),  # This will be the intended recipient, IT Lead decides how to handle
                            "priority": task_data.get("priority", "medium"),
                            "deadline": task_data.get("due_date")
                        }
                    }
                }
            )

            if response.status_code == 200:
                logger.info(f"Task successfully submitted to IT Lead for coordination: {task_data.get('task_id')}")
            else:
                logger.error(f"Failed to submit task to IT Lead: {response.status_code}")

    except httpx.RequestError as e:
        logger.error(f"Error sending task to IT Lead: {str(e)}")

async def handle_approval_request_via_it_lead(approval_data: dict):
    """Handle approval request by calling IT Lead server"""
    logger.info(f"Handling approval request via IT Lead: {approval_data}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call the request_human_approval tool on the IT Lead server
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "approval_request",
                    "method": "tools/call",
                    "params": {
                        "name": "request_human_approval",
                        "arguments": approval_data
                    }
                }
            )
            
            if response.status_code == 200:
                logger.info("Approval request sent successfully via IT Lead")
            else:
                logger.error(f"Failed to send approval request via IT Lead: {response.status_code}")
                
    except httpx.RequestError as e:
        logger.error(f"Error sending approval request to IT Lead: {str(e)}")

async def handle_requirement_submission_via_it_lead(requirement_data: dict):
    """Handle requirement submission by calling IT Lead server"""
    logger.info(f"Handling requirement submission via IT Lead: {requirement_data}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call the submit_requirement_input tool on the IT Lead server
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "requirement_submit",
                    "method": "tools/call",
                    "params": {
                        "name": "submit_requirement_input",
                        "arguments": requirement_data
                    }
                }
            )
            
            if response.status_code == 200:
                logger.info("Requirement submitted successfully via IT Lead")
            else:
                logger.error(f"Failed to submit requirement via IT Lead: {response.status_code}")
                
    except httpx.RequestError as e:
        logger.error(f"Error submitting requirement to IT Lead: {str(e)}")

async def handle_feedback_via_it_lead(feedback_data: dict):
    """Handle feedback by calling IT Lead server"""
    logger.info(f"Handling feedback via IT Lead: {feedback_data}")
    
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Call the provide_feedback tool on the IT Lead server
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "feedback_submit",
                    "method": "tools/call",
                    "params": {
                        "name": "provide_feedback",
                        "arguments": feedback_data
                    }
                }
            )
            
            if response.status_code == 200:
                logger.info("Feedback submitted successfully via IT Lead")
            else:
                logger.error(f"Failed to submit feedback via IT Lead: {response.status_code}")
                
    except httpx.RequestError as e:
        logger.error(f"Error submitting feedback to IT Lead: {str(e)}")

@app.get("/")
async def root():
    """Root endpoint for health check"""
    return {"message": "MCP Agent Web UI Backend is running", "status": "healthy"}

@app.get("/api/agents")
async def get_agents():
    """Get list of all agents and their status from IT Lead server"""
    # Refresh status from IT Lead server before returning
    await refresh_agent_status_from_it_lead()
    return list(agent_status.values())

@app.get("/api/agents/{agent_name}")
async def get_agent_detail(agent_name: str):
    """Get detailed information about a specific agent from IT Lead server"""
    # Refresh status from IT Lead server
    await refresh_agent_status_from_it_lead()
    
    if agent_name not in agent_status:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return agent_status[agent_name]

@app.post("/api/agents/{agent_name}/refresh")
async def refresh_agent(agent_name: str):
    """Manually refresh the status of a specific agent from IT Lead server"""
    # Refresh status from IT Lead server
    await refresh_agent_status_from_it_lead()
    
    if agent_name not in agent_status:
        raise HTTPException(status_code=404, detail="Agent not found")
    
    return {"message": f"Refreshed status for {agent_name}", "data": agent_status[agent_name]}

@app.post("/api/tasks/assign")
async def assign_task_endpoint(task: TaskAssignment):
    """Endpoint to assign a task via IT Lead server"""
    logger.info(f"Task assigned via IT Lead: {task.title} to {task.assignee}")
    
    # Validate that the assignee is a known agent role
    await refresh_agent_status_from_it_lead()
    if task.assignee not in agent_status:
        raise HTTPException(status_code=400, detail=f"Unknown agent: {task.assignee}")
    
    # Simulate task assignment
    task_dict = task.dict()
    task_dict["status"] = "assigned"
    
    # Send the task assignment to IT Lead server
    await handle_task_assignment_via_it_lead(task_dict)
    
    # Broadcast the task assignment to all connected clients
    await broadcast_message({
        "type": "task_assigned",
        "data": task_dict
    })
    
    return {"message": "Task assigned successfully", "task_id": task.task_id}

@app.post("/api/approvals/request")
async def request_approval_endpoint(approval: ApprovalRequest):
    """Endpoint to request human approval via IT Lead server"""
    logger.info(f"Requesting approval via IT Lead: {approval.request_title}")
    
    # Send the approval request to IT Lead server
    await handle_approval_request_via_it_lead(approval.dict())
    
    # Broadcast the approval request to all connected clients
    await broadcast_message({
        "type": "approval_requested",
        "data": approval.dict()
    })
    
    return {"message": "Approval request submitted successfully", "request_id": f"approval-{hash(str(approval.dict())) % 10000}"}

@app.post("/api/requirements/submit")
async def submit_requirement_endpoint(requirement: RequirementInput):
    """Endpoint to submit requirements via IT Lead server"""
    logger.info(f"Submitting requirement via IT Lead: {requirement.requirement_text[:50]}...")
    
    # Send the requirement to IT Lead server
    await handle_requirement_submission_via_it_lead(requirement.dict())
    
    # Broadcast the requirement submission to all connected clients
    await broadcast_message({
        "type": "requirement_submitted",
        "data": requirement.dict()
    })
    
    return {"message": "Requirement submitted successfully", "requirement_id": f"req-{hash(str(requirement.dict())) % 10000}"}

@app.post("/api/feedback/provide")
async def provide_feedback_endpoint(feedback: Feedback):
    """Endpoint to provide feedback via IT Lead server"""
    logger.info(f"Providing feedback via IT Lead on {feedback.feedback_target}")
    
    # Send the feedback to IT Lead server
    await handle_feedback_via_it_lead(feedback.dict())
    
    # Broadcast the feedback to all connected clients
    await broadcast_message({
        "type": "feedback_provided",
        "data": feedback.dict()
    })
    
    return {"message": "Feedback provided successfully", "feedback_id": f"feedback-{hash(str(feedback.dict())) % 10000}"}

@app.post("/api/tasks/update")
async def update_task_status_endpoint(update: TaskStatusUpdate):
    """Update the status of a task"""
    logger.info(f"Task status updated: {update.task_id} - {update.status}")
    
    # Broadcast the task update to all connected clients
    await broadcast_message({
        "type": "task_updated",
        "data": update.dict()
    })
    
    return {"message": "Task status updated successfully", "task_id": update.task_id}

async def fetch_tasks_from_it_lead():
    """Fetch actual tasks from IT Lead server's task storage"""
    logger.info("Fetching tasks from IT Lead server")
    
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            # Call the IT Lead server to get all tasks using the new get_all_tasks tool
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": "fetch-all-tasks",
                    "method": "tools/call",
                    "params": {
                        "name": "get_all_tasks",  # Using the new get_all_tasks tool
                        "arguments": {}
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                logger.info(f"Fetched tasks response: {result}")
                
                # Extract tasks from the response
                if "result" in result and "result" in result["result"]:
                    tasks_result = result["result"]["result"]
                    
                    # Format tasks to match the expected structure
                    formatted_tasks = []
                    if "tasks" in tasks_result:
                        for task in tasks_result["tasks"]:
                            formatted_tasks.append({
                                "id": task.get("task_id", "unknown"),
                                "title": task.get("title", f"Task: {task.get('task_id', 'unknown')}"),
                                "assignee": task.get("assigned_to", "Unknown"),
                                "status": task.get("status", "pending"),
                                "priority": task.get("priority", "medium"),
                                "progress": task.get("progress_percentage", 0)
                            })
                    return formatted_tasks
                else:
                    logger.warning("Response doesn't contain expected structure")
                    return []
            else:
                logger.error(f"Failed to fetch tasks from IT Lead: {response.status_code}")
                return []
                
    except httpx.RequestError as e:
        logger.error(f"Error connecting to IT Lead server: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"Unexpected error fetching tasks: {str(e)}")
        return []


@app.get("/api/tasks")
async def get_tasks():
    """Get list of actual tasks from the system via IT Lead server"""
    tasks = await fetch_tasks_from_it_lead()

    # If no tasks were retrieved from IT Lead, return an empty list
    # rather than hardcoded mock data
    if not tasks:
        logger.info("No tasks retrieved from IT Lead server, returning empty list")
        return []

    return tasks

@app.get("/api/tasks/{task_id}/history")
async def get_task_history(task_id: str):
    """Get task history from IT Lead server"""
    logger.info(f"Fetching history for task: {task_id}")

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                f"http://{IT_LEAD_HOST}:{IT_LEAD_PORT}/mcp",
                json={
                    "jsonrpc": "2.0",
                    "id": f"history-{task_id}",
                    "method": "tools/call",
                    "params": {
                        "name": "get_task_history",
                        "arguments": {
                            "task_id": task_id
                        }
                    }
                }
            )

            if response.status_code == 200:
                result = response.json()
                logger.info(f"Task history response: {result}")
                
                if "result" in result and "result" in result["result"]:
                    history_result = result["result"]["result"]
                    
                    # Format the history for the frontend
                    formatted_history = {
                        "task_id": history_result.get("task_id", task_id),
                        "title": history_result.get("title", ""),
                        "current_status": history_result.get("current_status", "unknown"),
                        "submitter": history_result.get("submitter", "unknown"),
                        "submitter_type": history_result.get("submitter_type", "unknown"),
                        "transport_channel": history_result.get("transport_channel", "unknown"),
                        "assigned_to": history_result.get("assigned_to", "unassigned"),
                        "created_at": history_result.get("created_at"),
                        "updated_at": history_result.get("updated_at"),
                        "status_history": history_result.get("status_history", [])
                    }
                    return formatted_history
                else:
                    logger.warning("Unexpected response format")
                    return {"error": "Unexpected response format"}
            else:
                logger.error(f"Failed to fetch task history: {response.status_code}")
                raise HTTPException(status_code=500, detail="Failed to fetch task history")

    except httpx.RequestError as e:
        logger.error(f"Error connecting to IT Lead server: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error connecting to IT Lead server: {str(e)}")
    except Exception as e:
        logger.error(f"Unexpected error fetching task history: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Unexpected error: {str(e)}")

@app.post("/api/dashboard/view")
async def get_dashboard_data(request: ProjectDashboardRequest):
    """Get project dashboard data - for now, return a simple response"""
    logger.info(f"Getting dashboard data for view: {request.dashboard_view}")
    
    # In a real implementation, this would call the IT Lead server
    # For now, return mock data
    return {
        "dashboard_view": request.dashboard_view,
        "time_range": request.time_range,
        "project_filters": request.project_filters,
        "custom_metrics": request.custom_metrics,
        "data": {
            "projects": 3,
            "active_tasks": 12,
            "completed_tasks": 8,
            "team_members_online": 4,
            "overall_progress": 68
        }
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)